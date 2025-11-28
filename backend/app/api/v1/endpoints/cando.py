"""
CanDo endpoints under /api/v1/cando/*.

This router now OWNS CanDo listing/filtering concerns (list/count/levels/topics).
Lesson-related operations may still leverage services shared with lexical.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from neo4j import AsyncSession
from sqlalchemy.ext.asyncio import AsyncSession as PgSession
from datetime import datetime

from app.api.v1.endpoints.lexical import (
    get_lesson_package as _get_lesson_package,
    get_stages as _get_stages,
    get_pragmatics as _get_pragmatics,
)
from app.services.pragmatics_service import pragmatics_service
from app.services.cando_exercises_service import cando_exercises
from app.services.cando_lesson_session_service import cando_lesson_sessions
from app.services.cando_v2_compile_service import compile_lessonroot
# entity_resolution_service functions moved to cando_lesson_session_service
from app.db import get_neo4j_session, get_postgresql_session
from sqlalchemy import text
from app.services.embedding_service import EmbeddingService
from app.services.cando_embedding_service import CanDoEmbeddingService
from app.services.cando_creation_service import CanDoCreationService
from app.services.lesson_persistence_service import lesson_persistence_service
from app.schemas.lesson import LessonMaster
from app.services.ai_chat_service import AIChatService
from app.services.cando_v2_compile_service import compile_lessonroot
from app.services.cando_image_service import ensure_image_paths_for_lesson, extract_image_specs
from app.services.dialogue_generation_service import (
    dialogue_generation_service,
    ExtendDialogueRequest,
    NewDialogueRequest,
)
from app.models.multilingual import DialogueCard as MLDialogueCard
import asyncio
import os

router = APIRouter()


def _normalize_bilingual(master: Dict[str, Any]) -> Dict[str, Any]:
    """Convert legacy 'meta' fields to bilingual keys.

    - For generic card bodies: if body.meta is present, copy to body.en (and keep body.jp if present).
    - For teach-type bodies that expect 'translation', also mirror to body.translation when missing.
    - For dialogue turns: if turn.meta exists, copy to turn.en.
    """
    try:
        ui = (master or {}).get("ui", {}) or {}
        # Normalize header title/subtitle to bilingual if provided as strings
        header = ui.get("header") or {}
        if isinstance(header, dict):
            for key in ("title", "subtitle"):
                val = header.get(key)
                if isinstance(val, str):
                    header[key] = {"jp": val, "en": val}
                elif isinstance(val, dict):
                    # ensure both keys exist
                    if "jp" in val and "en" not in val:
                        val["en"] = val.get("jp")
                    if "en" in val and "jp" not in val:
                        val["jp"] = val.get("en")
        ui["header"] = header
        sections = ui.get("sections", []) or []
        for sec in sections:
            # Section title normalization
            sec_title = sec.get("title")
            if isinstance(sec_title, str):
                sec["title"] = {"jp": sec_title, "en": sec_title}
            elif isinstance(sec_title, dict):
                if "jp" in sec_title and "en" not in sec_title:
                    sec_title["en"] = sec_title.get("jp")
                if "en" in sec_title and "jp" not in sec_title:
                    sec_title["jp"] = sec_title.get("en")
            cards = sec.get("cards", []) or []
            for c in cards:
                # Card title/subtitle normalization
                for tkey in ("title", "subtitle"):
                    tval = c.get(tkey)
                    if isinstance(tval, str):
                        c[tkey] = {"jp": tval, "en": tval}
                    elif isinstance(tval, dict):
                        if "jp" in tval and "en" not in tval:
                            tval["en"] = tval.get("jp")
                        if "en" in tval and "jp" not in tval:
                            tval["jp"] = tval.get("en")
                body = c.get("body") or {}
                # body.meta -> body.en
                if isinstance(body, dict) and "meta" in body:
                    if not body.get("en"):
                        body["en"] = body.get("meta")
                    # remove legacy key to keep schema strict
                    try:
                        del body["meta"]
                    except Exception:
                        pass
                # Ensure body has both jp and en keys when possible by mirroring
                if isinstance(body, dict):
                    has_jp = body.get("jp") is not None
                    has_en = body.get("en") is not None
                    if has_jp and not has_en:
                        body["en"] = body.get("jp")
                    if has_en and not has_jp:
                        body["jp"] = body.get("en")
                # teach card convenience: body.translation
                if (sec.get("type") == "teach") and isinstance(body, dict):
                    if body.get("en") and not body.get("translation"):
                        body["translation"] = body.get("en")
                # dialogue turns: turn.meta -> turn.en
                if sec.get("type") == "dialogue":
                    # If model produced 'lines' with named speakers, convert to 'turns' with speakerIndex
                    lines = c.get("lines") or []
                    if lines and not c.get("turns"):
                        speakers = c.get("speakers") or []
                        name_to_idx = {str(n): i for i, n in enumerate(speakers)} if isinstance(speakers, list) else {}
                        turns_built = []
                        for ln in lines:
                            if not isinstance(ln, dict):
                                continue
                            sp_name = ln.get("speaker")
                            sp_idx = name_to_idx.get(str(sp_name), 0)
                            t_item = {
                                "speakerIndex": sp_idx,
                                "jp": ln.get("jp"),
                            }
                            if ln.get("meta") and not t_item.get("en"):
                                t_item["en"] = ln.get("meta")
                            turns_built.append(t_item)
                        if turns_built:
                            c["turns"] = turns_built
                            try:
                                del c["lines"]
                            except Exception:
                                pass
                    turns = c.get("turns") or []
                    for t in turns:
                        if isinstance(t, dict) and t.get("meta"):
                            if not t.get("en"):
                                t["en"] = t.get("meta")
                            try:
                                del t["meta"]
                            except Exception:
                                pass
                        # Ensure bilingual in turns too
                        if isinstance(t, dict):
                            if t.get("jp") and not t.get("en"):
                                t["en"] = t.get("jp")
                            if t.get("en") and not t.get("jp"):
                                t["jp"] = t.get("en")
    except Exception:
        # best-effort normalization
        pass
    return master


def _kana_to_romaji(text: str) -> str:
    """Lightweight kana→romaji (Hepburn-ish) for teaching display.

    Handles basic digraphs, sokuon (っ/ッ), and long vowel mark ー.
    Not perfect but good enough for beginner materials without extra deps.
    """
    if not isinstance(text, str) or not text:
        return ""
    # Mapping tables
    digraphs = {
        "きゃ": "kya", "きゅ": "kyu", "きょ": "kyo",
        "しゃ": "sha", "しゅ": "shu", "しょ": "sho",
        "ちゃ": "cha", "ちゅ": "chu", "ちょ": "cho",
        "にゃ": "nya", "にゅ": "nyu", "にょ": "nyo",
        "ひゃ": "hya", "ひゅ": "hyu", "ひょ": "hyo",
        "みゃ": "mya", "みゅ": "myu", "みょ": "myo",
        "りゃ": "rya", "りゅ": "ryu", "りょ": "ryo",
        "ぎゃ": "gya", "ぎゅ": "gyu", "ぎょ": "gyo",
        "じゃ": "ja",  "じゅ": "ju",  "じょ": "jo",
        "びゃ": "bya", "びゅ": "byu", "びょ": "byo",
        "ぴゃ": "pya", "ぴゅ": "pyu", "ぴょ": "pyo",
        # Katakana equivalents
        "キャ": "kya", "キュ": "kyu", "キョ": "kyo",
        "シャ": "sha", "シュ": "shu", "ショ": "sho",
        "チャ": "cha", "チュ": "chu", "チョ": "cho",
        "ニャ": "nya", "ニュ": "nyu", "ニョ": "nyo",
        "ヒャ": "hya", "ヒュ": "hyu", "ヒョ": "hyo",
        "ミャ": "mya", "ミュ": "myu", "ミョ": "myo",
        "リャ": "rya", "リュ": "ryu", "リョ": "ryo",
        "ギャ": "gya", "ギュ": "gyu", "ギョ": "gyo",
        "ジャ": "ja",  "ジュ": "ju",  "ジョ": "jo",
        "ビャ": "bya", "ビュ": "byu", "ビョ": "byo",
        "ピャ": "pya", "ピュ": "pyu", "ピョ": "pyo",
    }
    base = {
        "あ":"a","い":"i","う":"u","え":"e","お":"o",
        "か":"ka","き":"ki","く":"ku","け":"ke","こ":"ko",
        "さ":"sa","し":"shi","す":"su","せ":"se","そ":"so",
        "た":"ta","ち":"chi","つ":"tsu","て":"te","と":"to",
        "な":"na","に":"ni","ぬ":"nu","ね":"ne","の":"no",
        "は":"ha","ひ":"hi","ふ":"fu","へ":"he","ほ":"ho",
        "ま":"ma","み":"mi","む":"mu","め":"me","も":"mo",
        "や":"ya","ゆ":"yu","よ":"yo",
        "ら":"ra","り":"ri","る":"ru","れ":"re","ろ":"ro",
        "わ":"wa","を":"o","ん":"n",
        "が":"ga","ぎ":"gi","ぐ":"gu","げ":"ge","ご":"go",
        "ざ":"za","じ":"ji","ず":"zu","ぜ":"ze","ぞ":"zo",
        "だ":"da","ぢ":"ji","づ":"zu","で":"de","ど":"do",
        "ば":"ba","び":"bi","ぶ":"bu","べ":"be","ぼ":"bo",
        "ぱ":"pa","ぴ":"pi","ぷ":"pu","ぺ":"pe","ぽ":"po",
        # small vowels
        "ぁ":"a","ぃ":"i","ぅ":"u","ぇ":"e","ぉ":"o",
        # katakana equivalents
        "ア":"a","イ":"i","ウ":"u","エ":"e","オ":"o",
        "カ":"ka","キ":"ki","ク":"ku","ケ":"ke","コ":"ko",
        "サ":"sa","シ":"shi","ス":"su","セ":"se","ソ":"so",
        "タ":"ta","チ":"chi","ツ":"tsu","テ":"te","ト":"to",
        "ナ":"na","ニ":"ni","ヌ":"nu","ネ":"ne","ノ":"no",
        "ハ":"ha","ヒ":"hi","フ":"fu","ヘ":"he","ホ":"ho",
        "マ":"ma","ミ":"mi","ム":"mu","メ":"me","モ":"mo",
        "ヤ":"ya","ユ":"yu","ヨ":"yo",
        "ラ":"ra","リ":"ri","ル":"ru","レ":"re","ロ":"ro",
        "ワ":"wa","ヲ":"o","ン":"n",
        "ガ":"ga","ギ":"gi","グ":"gu","ゲ":"ge","ゴ":"go",
        "ザ":"za","ジ":"ji","ズ":"zu","ゼ":"ze","ゾ":"zo",
        "ダ":"da","ヂ":"ji","ヅ":"zu","デ":"de","ド":"do",
        "バ":"ba","ビ":"bi","ブ":"bu","ベ":"be","ボ":"bo",
        "パ":"pa","ピ":"pi","プ":"pu","ペ":"pe","ポ":"po",
        "ァ":"a","ィ":"i","ゥ":"u","ェ":"e","ォ":"o",
        "ー":"-",
    }
    # Process text
    out: list[str] = []
    i = 0
    prev_romaji_last = ""
    while i < len(text):
        ch = text[i]
        pair = text[i:i+2]
        if pair in digraphs:
            rom = digraphs[pair]
            out.append(rom)
            prev_romaji_last = rom[-1]
            i += 2
            continue
        # sokuon (small tsu) doubles next consonant
        if ch in ("っ", "ッ"):
            if i + 1 < len(text):
                # look ahead one kana
                nxt = text[i+1:i+3]
                rom = None
                if nxt in digraphs:
                    rom = digraphs[nxt]
                else:
                    rom = base.get(text[i+1], "")
                if rom:
                    out.append(rom[0])
            i += 1
            continue
        if ch == "ー":
            # elongate previous vowel if any
            if out:
                # replace '-' with previous vowel
                v = prev_romaji_last if prev_romaji_last in "aeiou" else "-"
                out.append(v if v in "aeiou" else "")
            i += 1
            continue
        rom = base.get(ch)
        if rom:
            out.append(rom)
            prev_romaji_last = rom[-1]
        else:
            out.append(ch)
            prev_romaji_last = ch[-1] if ch else ""
        i += 1
    # Collapse hyphen artifacts
    return "".join(out).replace("-", "")


def _ensure_romaji(master: Dict[str, Any]) -> Dict[str, Any]:
    """Populate romaji for reading paragraphs, dialogue turns, and teach examples/bodies if missing."""
    try:
        ui = (master or {}).get("ui", {}) or {}
        for sec in (ui.get("sections") or []):
            s_type = sec.get("type")
            for c in (sec.get("cards") or []):
                body = c.get("body") or {}
                # reading body JP
                if s_type == "reading":
                    if isinstance(body, dict) and body.get("jp") and not body.get("romaji"):
                        body["romaji"] = _kana_to_romaji(str(body.get("jp")))
                    # paragraphs
                    for p in (c.get("paragraphs") or []):
                        if isinstance(p, dict) and p.get("jp") and not p.get("romaji"):
                            p["romaji"] = _kana_to_romaji(str(p.get("jp")))
                # dialogue turns
                if s_type == "dialogue":
                    for t in (c.get("turns") or []):
                        if isinstance(t, dict) and t.get("jp") and not t.get("romaji"):
                            t["romaji"] = _kana_to_romaji(str(t.get("jp")))
                # teach examples and body
                if s_type == "teach":
                    for ex in (c.get("examples") or []):
                        if isinstance(ex, dict) and ex.get("jp") and not ex.get("romaji"):
                            ex["romaji"] = _kana_to_romaji(str(ex.get("jp")))
                    if isinstance(body, dict) and body.get("jp") and not body.get("romaji"):
                        body["romaji"] = _kana_to_romaji(str(body.get("jp")))
    except Exception:
        pass
    return master


def _is_japanese(text: str) -> bool:
    if not isinstance(text, str):
        return False
    for ch in text:
        code = ord(ch)
        if (
            0x3040 <= code <= 0x30FF  # Hiragana/Katakana
            or 0x4E00 <= code <= 0x9FFF  # CJK Unified Ideographs
        ):
            return True
    return False


async def _translate(text: str, *, to_lang: str = "en", provider: str = "gemini") -> str:
    if not text:
        return text
    svc = AIChatService()
    prompt = (
        "Translate the following text precisely. Return ONLY the translation without quotes.\n"
        f"Target language: {'English' if to_lang=='en' else 'Japanese'}\nText:\n{text}"
    )
    try:
        reply = await svc.generate_reply(
            provider="gemini" if provider != "openai" else "openai",
            model=("gemini-2.5-pro" if provider != "openai" else "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
            system_prompt="Return only the translated text.",
        )
        return (reply.get("content") or "").strip()
    except Exception:
        return text


async def _global_bilingual_and_romaji(master: Dict[str, Any], *, provider: str) -> Dict[str, Any]:
    async def ensure_pair(d: Dict[str, Any]) -> None:
        # Do NOT translate; require model to return both jp and en.
        # Only add romaji when jp exists and romaji is missing.
        if isinstance(d.get("jp"), str) and not d.get("romaji"):
            d["romaji"] = _kana_to_romaji(d.get("jp"))

    async def walk(node: Any) -> None:
        if isinstance(node, dict):
            # Normalize title/subtitle objects
            for key in ("title", "subtitle"):
                if key in node:
                    val = node[key]
                    if isinstance(val, str):
                        # Convert plain strings to triplet shells (no translation); romaji if jp string
                        node[key] = {"jp": val, "en": val, "romaji": _kana_to_romaji(val) if _is_japanese(val) else ""}
                    elif isinstance(val, dict):
                        await ensure_pair(val)
            # Generic bilingual body-like objects
            if ("jp" in node) or ("en" in node):
                await ensure_pair(node)
            # Recurse
            for v in list(node.values()):
                await walk(v)
        elif isinstance(node, list):
            for item in node:
                await walk(item)

    await walk(master)
    # Metadata mapping: topic_ja/topic_en/topic_romaji
    md = (master or {}).get("metadata") or {}
    topic_ja = md.get("topic") or md.get("topic_ja") or ""
    if topic_ja:
        md["topic_ja"] = topic_ja
        if not md.get("topic_romaji"):
            md["topic_romaji"] = _kana_to_romaji(topic_ja)
    master["metadata"] = md
    return master


def _normalize_exercises_shape(master: Dict[str, Any]) -> Dict[str, Any]:
    """Map loosely-shaped exercises to strict Pydantic Exercise shape.

    - id: prefer `id` else `exerciseId`
    - type: passthrough
    - stem: build TextTriplet from `stem` (obj), or from `question`/`prompt`/`text` strings
    - choices: normalize list of strings or TextTriplet items into TextTriplet list (mirror en/jp if missing; add romaji from jp)
    - answerKey: prefer `answerKey` else `correct`/`solution`/`answer`
    - rationale: if present, map to TextTriplet similarly
    """
    try:
        exs = master.get("exercises") or []
        out = []
        for ex in exs:
            if not isinstance(ex, dict):
                continue
            mapped: Dict[str, Any] = {}
            mapped["id"] = ex.get("id") or ex.get("exerciseId") or ex.get("uid") or "ex-unnamed"
            mapped["type"] = ex.get("type") or ex.get("mode") or "cloze"

            # stem (broad discovery + fallbacks)
            stem = ex.get("stem")
            s_jp = ""
            s_en = ""
            if isinstance(stem, dict):
                s_jp = stem.get("jp") or stem.get("ja") or stem.get("japanese") or ""
                s_en = stem.get("en") or stem.get("english") or (s_jp or "")
            else:
                # collect potential fields and common nests
                candidates: List[str] = []
                for key in ("question_jp","jp","question","prompt","text","title","label"):
                    val = ex.get(key)
                    if isinstance(val, str) and val.strip():
                        candidates.append(val)
                body = ex.get("body") or {}
                if isinstance(body, dict):
                    for key in ("jp","ja","text"):
                        val = body.get(key)
                        if isinstance(val, str) and val.strip():
                            candidates.append(val)
                # choose the longest jp-like string
                s_jp = max(candidates, key=len) if candidates else ""
                s_en = ex.get("question_en") or ex.get("en") or ex.get("translation") or (s_jp or "")
            s_romaji = _kana_to_romaji(str(s_jp)) if s_jp else (ex.get("romaji") or "")
            mapped["stem"] = {"jp": str(s_jp), "en": str(s_en), "romaji": str(s_romaji)}

            # choices
            choices = ex.get("choices") or ex.get("options") or []
            norm_choices = []
            for ch in choices:
                if isinstance(ch, dict):
                    cj = ch.get("jp") or ch.get("ja") or ch.get("text") or ""
                    ce = ch.get("en") or ch.get("translation") or (cj or "")
                else:
                    cj = str(ch)
                    ce = str(ch)
                cr = _kana_to_romaji(str(cj)) if cj else ""
                norm_choices.append({"jp": str(cj), "en": str(ce), "romaji": str(cr)})
            if norm_choices:
                mapped["choices"] = norm_choices

            # answerKey
            mapped["answerKey"] = ex.get("answerKey")
            if mapped["answerKey"] is None:
                mapped["answerKey"] = ex.get("correct") if ex.get("correct") is not None else ex.get("solution")
            if mapped["answerKey"] is None:
                mapped["answerKey"] = ex.get("answer")
            if mapped["answerKey"] is None:
                # final fallback to satisfy schema in dry-run
                mapped["answerKey"] = ""

            # rationale
            rat = ex.get("rationale") or ex.get("explanation")
            if isinstance(rat, dict):
                rj = rat.get("jp") or rat.get("ja") or rat.get("japanese") or ""
                re = rat.get("en") or rat.get("english") or (rj or "")
            elif isinstance(rat, str):
                rj = rat
                re = rat
            else:
                rj = ""
                re = ""
            if rj or re:
                mapped["rationale"] = {"jp": str(rj), "en": str(re), "romaji": _kana_to_romaji(str(rj)) if rj else ""}

            # optional levelTag
            if ex.get("levelTag") is not None:
                mapped["levelTag"] = ex.get("levelTag")

            out.append(mapped)
        if out:
            master["exercises"] = out
    except Exception:
        # best-effort only
        pass
    return master


@router.get("/list")
async def list_cando(
    q: Optional[str] = Query(None, description="Search in uid or primaryTopic"),
    level: Optional[str] = Query(None),
    topic: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    sort: Optional[str] = Query("level", pattern="^(level|topic)$"),
    session: AsyncSession = Depends(get_neo4j_session),
) -> Dict[str, Any]:
    try:
        # Normalize empty strings to None for consistent query behavior
        q = q if q and q.strip() else None
        level = level if level and level.strip() else None
        topic = topic if topic and topic.strip() else None
        
        # Build WHERE conditions dynamically to avoid CONTAINS with NULL (matches count endpoint)
        conditions = []
        params = {}
        
        if level is not None:
            conditions.append("toString(c.level) = $level")
            params["level"] = level
        # When level is None, don't filter by level (matches original behavior)
        
        if topic is not None:
            conditions.append("toString(c.primaryTopic) CONTAINS $topic")
            params["topic"] = topic
        
        if q is not None:
            conditions.append("(toString(c.uid) CONTAINS $q OR toString(c.primaryTopic) CONTAINS $q OR toString(c.titleEn) CONTAINS $q OR toString(c.titleJa) CONTAINS $q)")
            params["q"] = q
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        params["limit"] = limit
        params["offset"] = offset
        params["sort"] = sort
        
        query = f"""
        MATCH (c:CanDoDescriptor)
        WHERE {where_clause}
        RETURN c.uid AS uid, 
               c.primaryTopic AS primaryTopic,
               c.primaryTopicEn AS primaryTopicEn,
               c.level AS level, 
               c.type AS type, 
               c.skillDomain AS skillDomain,
               coalesce(c.description, c.descriptionEn) AS description,
               c.exampleSentence AS exampleSentence,
               c.descriptionJa AS descriptionJa,
               c.titleEn AS titleEn,
               c.titleJa AS titleJa
        ORDER BY CASE WHEN $sort = 'topic' THEN toString(c.primaryTopic) ELSE toString(c.level) END ASC
        SKIP $offset
        LIMIT $limit
        """
        result = await session.run(query, **params)
        items: List[Dict[str, Any]] = [dict(r) async for r in result]
        return {"items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ai-models")
async def get_available_ai_models() -> Dict[str, Any]:
    """
    Get list of available AI models and their configurations.
    Returns model options for both OpenAI and Gemini with timeout settings.
    """
    from app.core.config import settings
    
    return {
        "providers": {
            "openai": {
                "name": "OpenAI",
                "icon": "🤖",
                "models": settings.AVAILABLE_OPENAI_MODELS,
                "builtin": True
            },
            "gemini": {
                "name": "Google Gemini",
                "icon": "🔷",
                "models": settings.AVAILABLE_GEMINI_MODELS,
                "builtin": True
            }
        },
        "timeout": {
            "default": settings.AI_REQUEST_TIMEOUT_SECONDS,
            "min": settings.AI_REQUEST_MIN_TIMEOUT,
            "max": settings.AI_REQUEST_MAX_TIMEOUT,
        },
        "current": {
            "provider": settings.CANDO_AI_PROVIDER,
            "model": settings.CANDO_AI_MODEL,
            "timeout": settings.AI_REQUEST_TIMEOUT_SECONDS,
        }
    }


@router.get("/lessons/package")
async def get_lesson_package(can_do_id: str, session: AsyncSession = Depends(get_neo4j_session)) -> Dict[str, Any]:
    """Return a combined lesson package; fallback to minimal package if compiled assets are missing."""
    try:
        return await _get_lesson_package(can_do_id=can_do_id, session=session)
    except HTTPException as e:
        if e.status_code != 404:
            raise
        # Fallback: build a minimal package from available graph pragmatics
        try:
            items = await pragmatics_service.get_pragmatics(session=session, can_do_id=can_do_id)
        except Exception:
            items = []
        return {
            "can_do_id": can_do_id,
            "lesson_plan": {
                "title": f"Lesson for {can_do_id}",
                "objectives": ["Explore pragmatics and practice basic exercises"],
            },
            "pragmatics": items,
            "exercises": [],
            "manifest": {"version": 1},
        }


@router.post("/lessons/generate-exercises")
async def generate_exercises(
    can_do_id: str = Query(...),
    n: int = Query(3, ge=1, le=20),
    modes: Optional[str] = Query(None),  # kept for future use
    phase: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_neo4j_session),
) -> Dict[str, Any]:
    """Generate real exercises using AI and graph seeds (no mock)."""
    try:
        return await cando_exercises.generate_for_cando(
            session=session, can_do_id=can_do_id, phase=phase, n=n
        )
    except Exception as e:
        # Surface error details for the client
        raise HTTPException(status_code=500, detail=f"exercise_generation_failed: {str(e)}")


@router.get("/lessons/stages")
async def get_stages(can_do_id: str, session: AsyncSession = Depends(get_neo4j_session)) -> Dict[str, Any]:
    return await _get_stages(can_do_id=can_do_id)


@router.get("/lessons/pragmatics")
async def get_pragmatics(can_do_id: str, session: AsyncSession = Depends(get_neo4j_session)) -> Dict[str, Any]:
    return await _get_pragmatics(can_do_id=can_do_id, session=session)


@router.post("/lessons/start")
async def start_lesson(
    can_do_id: str = Query(...),
    phase: Optional[str] = Query(None),
    provider: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    timeout: Optional[int] = Query(None),
    level: Optional[int] = Query(None, ge=1, le=6),
    session: AsyncSession = Depends(get_neo4j_session),
    pg: PgSession = Depends(get_postgresql_session),
) -> Dict[str, Any]:
    """Start lesson with optional model and timeout override"""
    from app.core.config import settings
    
    # Validate and cap timeout
    if timeout is not None:
        timeout = max(
            settings.AI_REQUEST_MIN_TIMEOUT,
            min(timeout, settings.AI_REQUEST_MAX_TIMEOUT)
        )
    
    try:
        return await cando_lesson_sessions.start_lesson(
            graph=session,
            pg=pg,
            can_do_id=can_do_id,
            phase=phase,
            provider=provider,
            model=model,
            timeout=timeout,
            learner_level=level,
        )
    except Exception as e:
        import traceback
        import structlog
        logger = structlog.get_logger()
        logger.error(
            "lesson_start_endpoint_failed",
            can_do_id=can_do_id,
            phase=phase,
            level=level,
            error=str(e),
            traceback=traceback.format_exc(),
        )
        raise HTTPException(status_code=500, detail=f"lesson_start_failed: {str(e)}")


@router.get("/lessons/stage1")
async def get_stage1_only(
    can_do_id: str = Query(...),
    provider: Optional[str] = Query("openai"),
    model: Optional[str] = Query("gpt-4o"),
    timeout: Optional[int] = Query(180, ge=30, le=600),
    session: AsyncSession = Depends(get_neo4j_session),
) -> Dict[str, Any]:
    """Return Stage 1 (simple) lesson JSON only, without Stage 2 enhancement.

    Useful for prompt inspection and debugging content completeness before multilingual structuring.
    """
    try:
        meta = await cando_lesson_sessions._get_cando_meta(session, can_do_id)
        topic = meta.get("primaryTopic") or "general conversation"
        level_str = str(meta.get("level"))
        data = await cando_lesson_sessions._generate_simple_content(
            can_do_id=can_do_id,
            topic=topic,
            level=level_str,
            provider=(provider or "openai"),
            model=(model or "gpt-4o"),
            timeout=int(timeout or 180),
            meta_extra={
                "type": meta.get("type"),
                "skillDomain": meta.get("skillDomain"),
                "exampleSentence": meta.get("exampleSentence"),
                "description": meta.get("description"),
                "descriptionEn": meta.get("descriptionEn"),
                "descriptionJa": meta.get("descriptionJa"),
            },
        )
        # ensure required opening metadata for user inspection
        data.setdefault("__meta", {})
        data["__meta"].update({
            "description": meta.get("description"),
            "descriptionEn": meta.get("descriptionEn"),
            "descriptionJa": meta.get("descriptionJa"),
            "topic": topic,
            "level": level_str,
        })
        return {"status": "ok", "stage1": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"stage1_failed: {str(e)}")


@router.post("/lessons/{can_do_id}/save")
async def save_lesson_permanently(
    can_do_id: str,
    session_id: Optional[str] = Query(None, description="Session ID if saving from active session"),
    approved_by: Optional[str] = Query(None, description="Teacher/reviewer username"),
    notes: Optional[str] = Query(None, description="Approval notes or comments"),
    neo4j_session: AsyncSession = Depends(get_neo4j_session),
    pg: PgSession = Depends(get_postgresql_session),
) -> Dict[str, Any]:
    """
    Save an AI-generated lesson to permanent storage (lessons + lesson_versions tables).
    
    This endpoint allows teachers to review and approve lessons for permanent storage.
    Once saved, these lessons will be prioritized over AI generation.
    """
    import structlog
    logger = structlog.get_logger()
    
    try:
        # 1. Find the lesson to save (either from session_id or latest for can_do_id)
        if session_id:
            result = await pg.execute(
                text("SELECT master_json FROM lesson_sessions WHERE id = :sid AND can_do_id = :cid LIMIT 1"),
                {"sid": session_id, "cid": can_do_id}
            )
        else:
            result = await pg.execute(
                text("SELECT master_json FROM lesson_sessions WHERE can_do_id = :cid ORDER BY created_at DESC LIMIT 1"),
                {"cid": can_do_id}
            )
        
        row = result.first()
        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"No lesson session found for {can_do_id}"
            )
        
        master_json = row[0]
        if not master_json:
            raise HTTPException(
                status_code=400,
                detail="Lesson session has no master lesson data"
            )
        
        # 2. Add approval metadata
        if approved_by:
            master_json["approvedBy"] = approved_by
        if notes:
            master_json["approvalNotes"] = notes
        master_json["approvedAt"] = datetime.utcnow().isoformat()
        
        # 3. Check if lesson already exists in permanent storage
        existing = await pg.execute(
            text("SELECT id FROM lessons WHERE can_do_id = :cid LIMIT 1"),
            {"cid": can_do_id}
        )
        existing_lesson = existing.first()
        
        if existing_lesson:
            # Increment version
            version_result = await pg.execute(
                text("SELECT MAX(version) FROM lesson_versions WHERE lesson_id = :lid"),
                {"lid": existing_lesson[0]}
            )
            max_version = version_result.scalar() or 0
            new_version = max_version + 1
        else:
            new_version = 1
        
        # 4. Save using LessonPersistenceService
        await lesson_persistence_service.persist_lesson_from_payload(
            pg=pg,
            neo4j=neo4j_session,
            can_do_id=can_do_id,
            payload=master_json,
            version=new_version,
            status="active"
        )
        
        logger.info(
            "lesson_saved_permanently",
            can_do_id=can_do_id,
            version=new_version,
            approved_by=approved_by
        )
        
        return {
            "status": "saved",
            "can_do_id": can_do_id,
            "version": new_version,
            "message": f"Lesson approved and saved as version {new_version}",
            "approved_by": approved_by,
            "approved_at": master_json.get("approvedAt")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(
            "lesson_save_failed",
            can_do_id=can_do_id,
            error=str(e),
            traceback=traceback.format_exc()
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save lesson: {str(e)}"
        )


@router.post("/lessons/turn")
async def lesson_turn(
    session_id: str = Query(...),
    message: str = Query(...),
    provider: Optional[str] = Query("gemini"),
    pg: PgSession = Depends(get_postgresql_session),
) -> Dict[str, Any]:
    try:
        return await cando_lesson_sessions.user_turn(
            session_id=session_id,
            user_message=message,
            provider=(provider or "openai"),
            pg=pg,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"lesson_turn_failed: {str(e)}")


@router.post("/lessons/compile")
async def compile_lesson(
    can_do_id: str = Query(...),
    version: int = Query(1, ge=1),
    provider: Optional[str] = Query(None),
    fast: bool = Query(False, description="Skip entity resolution and embeddings"),
    dry_run: bool = Query(False, description="Validate only; do not persist"),
    neo: AsyncSession = Depends(get_neo4j_session),
    pg: PgSession = Depends(get_postgresql_session),
) -> Dict[str, Any]:
    """Compile a MasterLesson for a CanDo and persist it to Postgres; link in Neo4j."""
    try:
        meta = await cando_lesson_sessions._get_cando_meta(neo, can_do_id)
        topic = meta.get("primaryTopic") or "general conversation"
        # Generate master using two-stage pipeline (more robust than single-shot)
        try:
            master = await cando_lesson_sessions._generate_master_lesson_twostage_with_fallback(
                can_do_id=can_do_id,
                topic=topic,
                original_level_str=str(meta.get("level")),
                original_level_num=cando_lesson_sessions._map_cando_level_to_numeric(str(meta.get("level"))),
                meta_extra={
                    "type": meta.get("type"),
                    "skillDomain": meta.get("skillDomain"),
                    "exampleSentence": meta.get("exampleSentence"),
                    "description": meta.get("description"),
                },
            )
        except Exception as gen_err:
            raise HTTPException(status_code=500, detail=f"generation_failed: {repr(gen_err)}")
        master = _normalize_bilingual(master)
        master = await _global_bilingual_and_romaji(master, provider=(provider or "openai"))
        master = _normalize_exercises_shape(master)
        # Metadata bilingual topic enrichment
        try:
            meta_obj = master.get("metadata") or {}
            if isinstance(meta_obj, dict):
                topic_en = meta.get("descriptionEn") or meta_obj.get("topic")
                meta_obj["topic_en"] = topic_en
                master["metadata"] = meta_obj
        except Exception:
            pass
        # Inject JP learning objectives from Neo4j when available
        try:
            lo_ja = meta.get("learningObjectivesJa") or meta.get("descriptionJa")
            if lo_ja:
                if isinstance(lo_ja, list):
                    master["learningObjectivesJa"] = [str(x) for x in lo_ja if str(x).strip()]
                else:
                    master["learningObjectivesJa"] = [str(lo_ja)]
        except Exception:
            pass
        # Variant guideline notes_ja (mirror notes for now to ensure JP key exists)
        try:
            vg = master.get("variantGuidelines") or {}
            if isinstance(vg, dict):
                for lvl, cfg in vg.items():
                    if isinstance(cfg, dict) and cfg.get("notes") and not cfg.get("notes_ja"):
                        cfg["notes_ja"] = list(cfg.get("notes") or [])
        except Exception:
            pass

        # Extract and resolve entities from UI content (skip in fast mode)
        entities: Dict[str, Any] = {"words": [], "grammarPatterns": []}
        entities_error: Optional[str] = None
        if not fast:
            try:
                # Flatten UI text
                text_blob = cando_lesson_sessions._flatten_ui_text(master)
                # Model-assisted extraction
                extracted = await cando_lesson_sessions._extract_entities_from_text(
                    text_blob=text_blob, provider=(provider or "gemini")
                )
                # Resolve model words first
                words_res = await cando_lesson_sessions._resolve_words(neo, extracted.get("words") or [])
                # If empty, fallback to deterministic from UI text
                if not words_res:
                    words_res = await cando_lesson_sessions._deterministic_words(neo, text_blob)
                # Grammar: prefer model-extracted, resolve where possible; fallback to deterministic only if model empty
                grammar_res: List[Dict[str, Any]] = []
                if extracted.get("grammarPatterns"):
                    for g in extracted.get("grammarPatterns") or []:
                        pat = g.get("pattern")
                        if not pat:
                            continue
                        try:
                            q = "MATCH (p:GrammarPattern) WHERE p.pattern = $p RETURN p.id AS id, p.pattern AS pattern, p.classification AS classification LIMIT 1"
                            rec = await (await neo.run(q, p=str(pat))).single()
                            if rec:
                                grammar_res.append(dict(rec))
                            else:
                                grammar_res.append({"id": None, "pattern": pat, "classification": None, "unresolved": True})
                        except Exception:
                            grammar_res.append({"id": None, "pattern": pat, "classification": None, "unresolved": True})
                if not grammar_res:
                    grammar_res = await cando_lesson_sessions._deterministic_grammar(neo, text_blob)
                remapped_words = []
                for w in words_res:
                    remapped_words.append(
                        {
                            "text": w.get("translation") or w.get("orth") or "",
                            "standard_orthography": w.get("orth") or "",
                            "hiragana": w.get("hiragana") or "",
                            "romaji": w.get("romaji") or "",
                        }
                    )
                entities = {"words": remapped_words, "grammarPatterns": grammar_res}
                master["extractedEntities"] = entities
            except Exception as ex:
                # keep empty entities on failure and surface error in dry_run result
                entities_error = str(ex)
        if dry_run:
            # Validate final master; do not persist
            try:
                _ = LessonMaster.model_validate(master)
            except Exception as e:
                # Attach a short preview of exercises to debug normalization
                preview = None
                try:
                    exs = master.get("exercises") or []
                    preview = exs[:1]
                except Exception:
                    preview = None
                return {"status": "error", "error": f"validation_failed: {str(e)}", "exercises_preview": preview}
            out: Dict[str, Any] = {"persisted": False, "entities": entities}
            if entities_error:
                out["entities_error"] = entities_error
            return {"status": "ok", "result": out}
        # Persist; in fast mode, avoid chunk embeddings by not passing master to chunker
        result = await lesson_persistence_service.persist_payload(
            can_do_id=can_do_id,
            lesson_plan=master,
            master=(None if fast else master),
            entities=entities,
            pg=pg,
            neo=neo,
            version=version,
        )
        # Validate final master against Pydantic schema (best-effort)
        try:
            _ = LessonMaster.model_validate(master)
        except Exception:
            pass
        return {"status": "ok", "result": result}
    except HTTPException as he:
        if dry_run:
            # Surface error in-body for diagnostics instead of HTTP 500
            return {"status": "error", "error": getattr(he, "detail", str(he))}
        # pass-through HTTPException with existing detail
        raise
    except Exception as e:
        if dry_run:
            # Degrade gracefully in dry-run to surface the error details without 500
            import traceback  # local import to avoid global cost
            tb = traceback.format_exc()
            return {"status": "error", "error": f"{repr(e)}", "trace": tb}
        import traceback  # local import to avoid global cost
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"compile_failed: {repr(e)}\n{tb}")


@router.post("/lessons/compile_v2")
async def compile_lesson_v2(
    can_do_id: str = Query(...),
    metalanguage: str = Query("en"),
    model: str = Query("gpt-4.1"),
    neo: AsyncSession = Depends(get_neo4j_session),
    pg: PgSession = Depends(get_postgresql_session),
) -> Dict[str, Any]:
    """Compile a LessonRoot (V2) and persist JSON into lessons/lesson_versions.

    Post-generation enrichment sets neo4j_id on grammar patterns when exact match found.
    """
    try:
        return await compile_lessonroot(
            neo=neo, pg=pg, can_do_id=can_do_id, metalanguage=metalanguage, model=model
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"compile_v2_failed: {str(e)}")


@router.get("/lessons/list")
async def list_lessons(
    can_do_id: str = Query(None),
    pg: PgSession = Depends(get_postgresql_session),
) -> Dict[str, Any]:
    """List all lessons, optionally filtered by can_do_id"""
    try:
        import json
        if can_do_id:
            result = await pg.execute(
                text("""
                    SELECT l.id, l.can_do_id, l.status, l.created_at,
                           lv.version, lv.created_at as version_created_at
                    FROM lessons l
                    JOIN lesson_versions lv ON l.id = lv.lesson_id
                    WHERE l.can_do_id = :can_do_id
                    ORDER BY lv.version DESC
                """),
                {"can_do_id": can_do_id}
            )
        else:
            result = await pg.execute(
                text("""
                    SELECT l.id, l.can_do_id, l.status, l.created_at,
                           lv.version, lv.created_at as version_created_at
                    FROM lessons l
                    JOIN lesson_versions lv ON l.id = lv.lesson_id
                    ORDER BY l.created_at DESC
                    LIMIT 100
                """)
            )
        
        rows = result.fetchall()
        lessons = [
            {
                "id": row[0],
                "can_do_id": row[1],
                "status": row[2],
                "created_at": row[3].isoformat() if row[3] else None,
                "version": row[4],
                "version_created_at": row[5].isoformat() if row[5] else None,
            }
            for row in rows
        ]
        
        return {"lessons": lessons}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"list_lessons_failed: {str(e)}")


@router.get("/lessons/fetch/{lesson_id}")
async def fetch_lesson(
    lesson_id: int,
    version: int = Query(None),
    pg: PgSession = Depends(get_postgresql_session),
) -> Dict[str, Any]:
    """Fetch a specific lesson by ID and optional version.
    
    Automatically generates missing images if GEMINI_API_KEY is available.
    """
    try:
        import json
        
        # First get can_do_id from lessons table
        can_do_result = await pg.execute(
            text("SELECT can_do_id FROM lessons WHERE id = :lesson_id LIMIT 1"),
            {"lesson_id": lesson_id}
        )
        can_do_row = can_do_result.fetchone()
        if not can_do_row:
            raise HTTPException(status_code=404, detail="Lesson not found")
        can_do_id = can_do_row[0]
        
        if version:
            result = await pg.execute(
                text("""
                    SELECT lv.lesson_plan, lv.version
                    FROM lesson_versions lv
                    WHERE lv.lesson_id = :lesson_id AND lv.version = :version
                    LIMIT 1
                """),
                {"lesson_id": lesson_id, "version": version}
            )
        else:
            result = await pg.execute(
                text("""
                    SELECT lv.lesson_plan, lv.version
                    FROM lesson_versions lv
                    WHERE lv.lesson_id = :lesson_id
                    ORDER BY lv.version DESC
                    LIMIT 1
                """),
                {"lesson_id": lesson_id}
            )
        
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Lesson not found")
        
        lesson_plan = row[0]
        lesson_version = row[1]
        if lesson_plan is None:
            raise HTTPException(status_code=404, detail="Lesson plan is empty or not found")
        
        if isinstance(lesson_plan, str):
            lesson_plan = json.loads(lesson_plan)
        
        # Validate that we have actual lesson data
        if not lesson_plan or (isinstance(lesson_plan, dict) and len(lesson_plan) == 0):
            raise HTTPException(status_code=404, detail="Lesson plan is empty")
        
        # Check for missing images and generate them if GEMINI_API_KEY is available
        if os.getenv("GEMINI_API_KEY"):
            try:
                # Check if there are any images without paths
                missing_images = extract_image_specs(lesson_plan)
                if missing_images:
                    # Generate missing images
                    images_generated, _ = await asyncio.to_thread(
                        ensure_image_paths_for_lesson,
                        lesson_plan,
                        can_do_id=can_do_id,
                    )
                    if images_generated > 0:
                        # Update the lesson_plan in database with new image paths
                        await pg.execute(
                            text("""
                                UPDATE lesson_versions 
                                SET lesson_plan = :plan 
                                WHERE lesson_id = :lid AND version = :ver
                            """),
                            {
                                "plan": json.dumps(lesson_plan, ensure_ascii=False),
                                "lid": lesson_id,
                                "ver": lesson_version,
                            }
                        )
                        await pg.commit()
            except Exception as exc:
                # Log but don't fail the request if image generation fails
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Image generation failed for lesson {lesson_id}: {exc}")
        
        return lesson_plan
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"fetch_lesson_failed: {str(e)}")


@router.post("/lessons/guided/flush")
async def flush_guided_state(
    session_id: str = Query(..., description="Lesson session id"),
    pg: PgSession = Depends(get_postgresql_session),
) -> Dict[str, Any]:
    """Flush guided dialogue state for a session (reset stage index and state)."""
    try:
        await pg.execute(
            text(
                "UPDATE lesson_sessions SET guided_stage_idx = NULL, guided_state = NULL, guided_flushed_at = NOW(), updated_at = CURRENT_TIMESTAMP WHERE id = :id"
            ),
            {"id": session_id},
        )
        await pg.commit()
        return {"status": "ok", "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"guided_flush_failed: {str(e)}")

@router.get("/lessons/latest")
async def get_latest_lesson(
    can_do_id: str = Query(...),
    pg: PgSession = Depends(get_postgresql_session),
) -> Dict[str, Any]:
    """Return latest persisted lesson payload (master, entities, timings).
    
    Automatically generates missing images if GEMINI_API_KEY is available.
    """
    try:
        import json
        # Find lesson_id
        res = await pg.execute(text("SELECT id FROM lessons WHERE can_do_id = :can LIMIT 1"), {"can": can_do_id})
        lesson_id = res.scalar_one_or_none()
        if not lesson_id:
            raise HTTPException(status_code=404, detail="lesson_not_found")
        # Get latest version row
        res2 = await pg.execute(
            text(
                "SELECT version, master, entities, timings, lesson_plan, created_at "
                "FROM lesson_versions WHERE lesson_id = :lid ORDER BY version DESC LIMIT 1"
            ),
            {"lid": int(lesson_id)},
        )
        row = res2.first()
        if not row:
            raise HTTPException(status_code=404, detail="lesson_version_not_found")
        
        lesson_plan = row.lesson_plan or row.master
        if isinstance(lesson_plan, str):
            lesson_plan = json.loads(lesson_plan)
        
        # Check for missing images and generate them if GEMINI_API_KEY is available
        if os.getenv("GEMINI_API_KEY") and lesson_plan:
            try:
                # Check if there are any images without paths
                missing_images = extract_image_specs(lesson_plan)
                if missing_images:
                    # Generate missing images
                    images_generated, _ = await asyncio.to_thread(
                        ensure_image_paths_for_lesson,
                        lesson_plan,
                        can_do_id=can_do_id,
                    )
                    if images_generated > 0:
                        # Update the lesson_plan in database with new image paths
                        await pg.execute(
                            text("""
                                UPDATE lesson_versions 
                                SET lesson_plan = :plan 
                                WHERE lesson_id = :lid AND version = :ver
                            """),
                            {
                                "plan": json.dumps(lesson_plan, ensure_ascii=False),
                                "lid": int(lesson_id),
                                "ver": int(row.version),
                            }
                        )
                        await pg.commit()
            except Exception as exc:
                # Log but don't fail the request if image generation fails
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Image generation failed for lesson {can_do_id}: {exc}")
        
        return {
            "can_do_id": can_do_id,
            "lesson_id": int(lesson_id),
            "version": int(row.version),
            "master": lesson_plan or row.master,
            "entities": row.entities or {},
            "timings": row.timings or {},
            "created_at": row.created_at,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lessons/generate-images")
async def generate_lesson_images(
    can_do_id: str = Query(...),
    pg: PgSession = Depends(get_postgresql_session),
) -> Dict[str, Any]:
    """Manually generate images for a lesson.
    
    This endpoint scans the lesson for missing images and generates them.
    Useful for regenerating images or generating images for lessons that were
    compiled before image generation was enabled.
    """
    try:
        import json
        
        if not os.getenv("GEMINI_API_KEY"):
            raise HTTPException(
                status_code=400, 
                detail="GEMINI_API_KEY not configured. Image generation requires Gemini API key."
            )
        
        # Find lesson_id
        res = await pg.execute(
            text("SELECT id FROM lessons WHERE can_do_id = :can LIMIT 1"), 
            {"can": can_do_id}
        )
        lesson_id = res.scalar_one_or_none()
        if not lesson_id:
            raise HTTPException(status_code=404, detail="lesson_not_found")
        
        # Get latest version row
        res2 = await pg.execute(
            text(
                "SELECT version, lesson_plan FROM lesson_versions "
                "WHERE lesson_id = :lid ORDER BY version DESC LIMIT 1"
            ),
            {"lid": int(lesson_id)},
        )
        row = res2.first()
        if not row:
            raise HTTPException(status_code=404, detail="lesson_version_not_found")
        
        lesson_plan = row.lesson_plan
        if isinstance(lesson_plan, str):
            lesson_plan = json.loads(lesson_plan)
        
        if not lesson_plan:
            raise HTTPException(status_code=404, detail="lesson_plan_empty")
        
        # Check for missing images (including those with invalid/non-existent paths)
        from pathlib import Path as PathLib
        repo_root = PathLib(__file__).resolve().parents[3]
        
        def check_image_exists(image_path: str) -> bool:
            """Check if image file actually exists on disk."""
            if not image_path:
                return False
            # Remove leading slash if present
            clean_path = image_path.lstrip('/')
            # Build full path: frontend/public/{clean_path}
            full_path = repo_root / "frontend" / "public" / clean_path
            return full_path.exists() and full_path.is_file()
        
        # Get all images, not just those without paths
        all_images = extract_image_specs(lesson_plan)
        
        # Also check images with paths that don't exist
        missing_images = []
        def find_missing_images(obj, path=[]):
            if isinstance(obj, dict):
                if "prompt" in obj and "style" in obj:
                    existing_path = obj.get("path", "")
                    if not existing_path or not check_image_exists(existing_path):
                        missing_images.append((obj, path))
                for key, value in obj.items():
                    find_missing_images(value, path + [key])
            elif isinstance(obj, list):
                for idx, item in enumerate(obj):
                    find_missing_images(item, path + [str(idx)])
        
        find_missing_images(lesson_plan)
        
        if not missing_images:
            return {
                "status": "success",
                "message": "No missing images found. All images already have valid paths.",
                "can_do_id": can_do_id,
                "lesson_id": int(lesson_id),
                "images_generated": 0,
            }
        
        # Clear invalid paths so extract_image_specs will find them
        for img_obj, _ in missing_images:
            if img_obj.get("path") and not check_image_exists(img_obj["path"]):
                img_obj["path"] = None
        
        # Generate missing images
        images_generated, images_skipped = await asyncio.to_thread(
            ensure_image_paths_for_lesson,
            lesson_plan,
            can_do_id=can_do_id,
        )
        
        if images_generated > 0:
            # Update the lesson_plan in database with new image paths
            await pg.execute(
                text("""
                    UPDATE lesson_versions 
                    SET lesson_plan = :plan 
                    WHERE lesson_id = :lid AND version = :ver
                """),
                {
                    "plan": json.dumps(lesson_plan, ensure_ascii=False),
                    "lid": int(lesson_id),
                    "ver": int(row.version),
                }
            )
            await pg.commit()
        
        return {
            "status": "success",
            "can_do_id": can_do_id,
            "lesson_id": int(lesson_id),
            "images_generated": images_generated,
            "images_skipped": images_skipped,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"generate_images_failed: {str(e)}")


class SearchRequest(BaseModel):
    q: str
    k: int = 10
    can_do_id: Optional[str] = None
    lang: Optional[str] = None  # 'jp' | 'en'


@router.post("/lessons/search")
async def search_lessons(
    payload: SearchRequest,
    pg: PgSession = Depends(get_postgresql_session),
) -> Dict[str, Any]:
    """Vector search across lesson_chunks using pgvector (text-embedding-3-small)."""
    try:
        embedder = EmbeddingService()
        emb = await embedder.generate_content_embedding(payload.q, provider="openai")
        where = ["1=1"]
        params: Dict[str, Any] = {"emb": emb, "k": int(min(max(payload.k, 1), 50))}
        if payload.can_do_id:
            where.append("can_do_id = :can")
            params["can"] = payload.can_do_id
        if payload.lang:
            where.append("lang = :lang")
            params["lang"] = payload.lang
        where_sql = " AND ".join(where)
        sql = (
            "SELECT lesson_id, version, can_do_id, section, card_id, lang, text, "
            "       1 - (embedding <=> :emb) AS similarity "
            "FROM lesson_chunks WHERE " + where_sql + " AND embedding IS NOT NULL "
            "ORDER BY embedding <=> :emb LIMIT :k"
        )
        res = await pg.execute(text(sql), params)
        rows = res.fetchall()
        items = [
            {
                "lesson_id": int(r.lesson_id),
                "version": int(r.version),
                "can_do_id": r.can_do_id,
                "section": r.section,
                "card_id": r.card_id,
                "lang": r.lang,
                "text": r.text,
                "similarity": float(r.similarity),
            }
            for r in rows
        ]
        return {"items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/count")
async def count_cando(
    q: Optional[str] = Query(None, description="Search in uid or primaryTopic"),
    level: Optional[str] = Query(None),
    topic: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_neo4j_session),
) -> Dict[str, Any]:
    try:
        # Normalize empty strings to None to match list endpoint behavior
        q = q if q and q.strip() else None
        level = level if level and level.strip() else None
        topic = topic if topic and topic.strip() else None
        
        # Build WHERE conditions dynamically to avoid CONTAINS with NULL
        conditions = []
        params = {}
        
        if level is not None:
            conditions.append("toString(c.level) = $level")
            params["level"] = level
        # When level is None, don't filter by level (matches original behavior)
        
        if topic is not None:
            conditions.append("toString(c.primaryTopic) CONTAINS $topic")
            params["topic"] = topic
        
        if q is not None:
            conditions.append("(toString(c.uid) CONTAINS $q OR toString(c.primaryTopic) CONTAINS $q OR toString(c.titleEn) CONTAINS $q OR toString(c.titleJa) CONTAINS $q)")
            params["q"] = q
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query = f"""
        MATCH (c:CanDoDescriptor)
        WHERE {where_clause}
        RETURN count(c) AS total
        """
        result = await session.run(query, **params)
        rec = await result.single()
        total = int(rec["total"]) if rec and "total" in rec else 0
        return {"total": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/levels")
async def list_levels(session: AsyncSession = Depends(get_neo4j_session)) -> Dict[str, Any]:
    try:
        query = """
        MATCH (c:CanDoDescriptor)
        WITH DISTINCT toString(c.level) AS lvl
        WHERE lvl IS NOT NULL AND lvl <> ''
        RETURN lvl ORDER BY lvl
        """
        result = await session.run(query)
        levels = [r["lvl"] async for r in result]
        return {"levels": levels}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/topics")
async def list_topics(session: AsyncSession = Depends(get_neo4j_session)) -> Dict[str, Any]:
    try:
        query = """
        MATCH (c:CanDoDescriptor)
        WITH DISTINCT toString(c.primaryTopic) AS topic
        WHERE topic IS NOT NULL AND topic <> ''
        RETURN topic ORDER BY topic
        """
        result = await session.run(query)
        topics = [r["topic"] async for r in result]
        return {"topics": topics}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/similar")
async def find_similar_candos(
    can_do_id: str = Query(..., description="CanDoDescriptor UID to find similar ones for"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of similar CanDoDescriptors to return"),
    similarity_threshold: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum similarity score (default: 0.65)"),
    session: AsyncSession = Depends(get_neo4j_session),
) -> Dict[str, Any]:
    """
    Find semantically similar CanDoDescriptors using vector embeddings.
    
    This endpoint uses vector similarity search to find CanDoDescriptors that are
    semantically related to the given CanDoDescriptor, enabling adaptive learning paths
    that connect concepts beyond explicit prerequisites.
    
    Args:
        can_do_id: CanDoDescriptor UID (e.g., "JFまるごと:13")
        limit: Maximum number of results (1-50)
        similarity_threshold: Minimum similarity score (0.0-1.0, default: 0.65)
        
    Returns:
        Dictionary with similar CanDoDescriptors and their similarity scores
    """
    try:
        service = CanDoEmbeddingService()
        
        similar = await service.find_similar_candos(
            session,
            can_do_id,
            limit=limit,
            similarity_threshold=similarity_threshold
        )
        
        return {
            "can_do_id": can_do_id,
            "similar": similar,
            "count": len(similar)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CreateCanDoRequest(BaseModel):
    """Request model for creating a new CanDoDescriptor."""
    descriptionEn: Optional[str] = None
    descriptionJa: Optional[str] = None


@router.post("/create")
async def create_cando(
    request: CreateCanDoRequest,
    session: AsyncSession = Depends(get_neo4j_session),
) -> Dict[str, Any]:
    """
    Create a new CanDoDescriptor with automatic processing.
    
    This endpoint accepts minimal input (descriptions only) and automatically:
    - Translates descriptions if only one language provided
    - Infers fields (level, topic, skillDomain, type) using AI
    - Generates titles (titleEn, titleJa) using AI
    - Generates embeddings
    - Creates similarity relationships
    
    Request body:
    {
        "descriptionEn": "Optional English description",
        "descriptionJa": "Optional Japanese description"
    }
    
    At least one of descriptionEn or descriptionJa must be provided.
    
    Returns:
        Created CanDoDescriptor with all generated properties
    """
    try:
        description_en = request.descriptionEn
        description_ja = request.descriptionJa
        
        if not description_en and not description_ja:
            raise HTTPException(
                status_code=400,
                detail="At least one description (descriptionEn or descriptionJa) must be provided"
            )
        
        if description_en and not description_en.strip():
            description_en = None
        if description_ja and not description_ja.strip():
            description_ja = None
        
        if not description_en and not description_ja:
            raise HTTPException(
                status_code=400,
                detail="At least one non-empty description must be provided"
            )
        
        creation_service = CanDoCreationService()
        
        created = await creation_service.create_cando_with_auto_processing(
            description_en=description_en,
            description_ja=description_ja,
            session=session
        )
        
        return {
            "success": True,
            "canDo": created
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create CanDo: {str(e)}")


@router.post("/lessons/guided/flush")
async def flush_guided_state(
    session_id: str = Query(..., description="Session ID to flush guided state for"),
    pg: PgSession = Depends(get_postgresql_session),
) -> Dict[str, Any]:
    """
    Flush/reset the guided dialogue state for a specific session.
    
    This endpoint safely resets the guided dialogue progression by:
    - Setting guided_stage_idx back to 0
    - Clearing guided_state JSONB
    - Setting guided_flushed_at to current timestamp
    
    Args:
        session_id: The UUID of the lesson session to flush
        
    Returns:
        Success message with timestamp of flush operation
    """
    try:
        # Update the session to flush guided state
        result = await pg.execute(
            text("""
                UPDATE lesson_sessions 
                SET guided_stage_idx = 0,
                    guided_state = '{}'::jsonb,
                    guided_flushed_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :session_id
                RETURNING id, guided_flushed_at
            """),
            {"session_id": session_id}
        )
        
        row = result.fetchone()
        if not row:
            raise HTTPException(
                status_code=404, 
                detail=f"Session {session_id} not found"
            )
        
        return {
            "status": "ok",
            "session_id": session_id,
            "flushed_at": row[1].isoformat(),
            "message": "Guided dialogue state flushed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"flush_failed: {str(e)}")


class GuidedTurnRequest(BaseModel):
    session_id: str
    stage_idx: int
    learner_input: str


class GuidedInitialMessageRequest(BaseModel):
    session_id: str
    stage_idx: int


class CreateLessonSessionRequest(BaseModel):
    can_do_id: str


@router.post("/lessons/session/create")
async def create_lesson_session(
    request: CreateLessonSessionRequest,
    pg: PgSession = Depends(get_postgresql_session),
) -> Dict[str, Any]:
    """
    Create a lightweight lesson session without generating the full lesson.
    This is used for guided dialogue which can fetch lesson data separately.
    """
    import uuid
    from datetime import datetime, timedelta
    
    try:
        # Check if session already exists
        result = await pg.execute(
            text("""
                SELECT id FROM lesson_sessions 
                WHERE can_do_id = :can_do_id AND expires_at > NOW()
                ORDER BY created_at DESC LIMIT 1
            """),
            {"can_do_id": request.can_do_id}
        )
        existing = result.fetchone()
        if existing:
            return {"session_id": str(existing[0])}
        
        # Create new session
        session_id = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(hours=24)
        await pg.execute(
            text("""
                INSERT INTO lesson_sessions (id, can_do_id, phase, completed_count, expires_at, created_at, updated_at)
                VALUES (:id, :can_do_id, :phase, :completed_count, :expires_at, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """),
            {
                "id": session_id,
                "can_do_id": request.can_do_id,
                "phase": "lexicon_and_patterns",
                "completed_count": 0,
                "expires_at": expires_at
            }
        )
        await pg.commit()
        
        return {"session_id": session_id}
    except Exception as e:
        await pg.rollback()
        import traceback
        import structlog
        logger = structlog.get_logger()
        logger.error("session_creation_failed", can_do_id=request.can_do_id, error=str(e), traceback=traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@router.post("/lessons/guided/initial-message")
async def get_guided_initial_message(
    request: GuidedInitialMessageRequest,
    pg: PgSession = Depends(get_postgresql_session),
    neo: AsyncSession = Depends(get_neo4j_session),
) -> Dict[str, Any]:
    """
    Generate initial AI greeting message for guided dialogue with full meta structure.
    
    This endpoint:
    - Retrieves the current GuidedDialogueCard and stage
    - Generates an initial AI greeting with CONVERSATIONAL_RESPONSE, TRANSLITERATION, TRANSLATION, TEACHING_DIRECTION
    - Returns message with full meta structure similar to Grammar Patterns chat
    
    Args:
        request: Contains session_id and stage_idx
        
    Returns:
        Initial AI message with full meta structure (message, transliteration, translation, feedback)
    """
    try:
        from app.services.ai_chat_service import AIChatService
        import json
        
        # 1. Retrieve session and lesson
        session_result = await pg.execute(
            text("""
                SELECT id, can_do_id, guided_stage_idx, package_json
                FROM lesson_sessions
                WHERE id = :session_id
            """),
            {"session_id": request.session_id}
        )
        session_row = session_result.fetchone()
        if not session_row:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session_id, can_do_id, current_stage_idx, package_json_raw = session_row
        
        # 2. Get the lesson with GuidedDialogueCard
        lesson_data = None
        if package_json_raw:
            package = json.loads(package_json_raw) if isinstance(package_json_raw, str) else package_json_raw
            lesson_data = package.get("lesson")
        
        if not lesson_data:
            # Fetch from lessons table
            lesson_result = await pg.execute(
                text("""
                    SELECT lv.lesson_plan
                    FROM lessons l
                    JOIN lesson_versions lv ON l.id = lv.lesson_id
                    WHERE l.can_do_id = :can_do_id
                    ORDER BY lv.version DESC
                    LIMIT 1
                """),
                {"can_do_id": can_do_id}
            )
            lesson_row = lesson_result.fetchone()
            if lesson_row:
                lesson_plan = lesson_row[0]
                if isinstance(lesson_plan, str):
                    lesson_plan = json.loads(lesson_plan)
                lesson_data = lesson_plan.get("lesson", lesson_plan)
        
        if not lesson_data:
            raise HTTPException(status_code=404, detail="Lesson not found for this session")
        
        # 3. Extract GuidedDialogueCard
        cards = lesson_data.get("cards", {})
        guided_card = cards.get("guided_dialogue")
        if not guided_card:
            raise HTTPException(status_code=400, detail="No guided dialogue card in this lesson")
        
        stages = guided_card.get("stages", [])
        if request.stage_idx >= len(stages):
            raise HTTPException(status_code=400, detail="Stage index out of range")
        
        current_stage = stages[request.stage_idx]
        
        # 4. Build AI prompt for initial greeting with full meta structure
        ai_service = AIChatService()
        
        goal_en = current_stage.get('goal_en', '')
        expected_patterns = ', '.join(current_stage.get('expected_patterns', []))
        hints_text = "\n".join([
            f"- {h.get('en', '')} / {h.get('ja', '')}" 
            for h in current_stage.get('hints', [])
        ])
        
        initial_prompt = f"""
You are a Japanese language tutor starting a guided conversation practice session.

Current Stage Goal: {goal_en}
Expected Patterns: {expected_patterns}
Stage Hints:
{hints_text}

Provide an opening greeting in this format:

CONVERSATIONAL_RESPONSE: [A natural Japanese greeting (1-2 sentences) that introduces the stage goal and invites the learner to respond. Make it contextually appropriate and encouraging. This should feel like a natural conversation starter that sets up the practice for the goal: "{goal_en}".]

TRANSLITERATION: [Provide the romanized version (romaji) of your Japanese greeting to help with pronunciation]

TRANSLATION: [Provide the English translation of your Japanese greeting]

TEACHING_DIRECTION: [English explanation of: 1) Your teaching strategy for this opening, 2) How your greeting sets up the conversation to practice the stage goal, 3) SPECIFIC HINT: "Try responding with..." - give them a concrete example of how to respond using the expected patterns, 4) What they should focus on for this stage, 5) Overall dialogue direction for achieving the stage goal]

Make the greeting warm, natural, and contextually appropriate. Always include a specific response hint that shows exactly how they can respond to achieve the stage goal.
"""
        
        system_prompt = f"""You are a Japanese language tutor conducting a guided conversation practice.

Current Stage Goal: {goal_en}
Expected Patterns: {expected_patterns}

Provide natural, encouraging guidance. Always provide CONVERSATIONAL_RESPONSE, TRANSLITERATION, TRANSLATION, and TEACHING_DIRECTION sections."""
        
        # 5. Get AI response with full meta structure
        ai_response = await ai_service.generate_reply(
            provider="openai",
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": initial_prompt}],
            system_prompt=system_prompt
        )
        
        # 6. Parse the response
        response_content = ai_response.get("content", "")
        
        # Extract all parts
        ai_message = "こんにちは！よろしくお願いします。"  # Default fallback
        transliteration = ""  # Default fallback
        translation = ""  # Default fallback
        teaching_direction = f"Welcome! Let's practice: {goal_en}"  # Default fallback
        
        # Parse CONVERSATIONAL_RESPONSE
        if "CONVERSATIONAL_RESPONSE:" in response_content:
            conv_start = response_content.find("CONVERSATIONAL_RESPONSE:")
            translit_start = response_content.find("TRANSLITERATION:")
            
            if conv_start != -1 and translit_start != -1:
                ai_message = response_content[conv_start + 24:translit_start].strip()
            elif conv_start != -1:
                # Fallback if no transliteration section
                teach_start = response_content.find("TEACHING_DIRECTION:")
                if teach_start != -1:
                    ai_message = response_content[conv_start + 24:teach_start].strip()
        
        # Parse TRANSLITERATION
        if "TRANSLITERATION:" in response_content:
            translit_start = response_content.find("TRANSLITERATION:")
            trans_start = response_content.find("TRANSLATION:")
            
            if translit_start != -1 and trans_start != -1:
                transliteration = response_content[translit_start + 16:trans_start].strip()
            elif translit_start != -1:
                # Fallback if no translation section
                teach_start = response_content.find("TEACHING_DIRECTION:")
                if teach_start != -1:
                    transliteration = response_content[translit_start + 16:teach_start].strip()
        
        # Parse TRANSLATION
        if "TRANSLATION:" in response_content:
            trans_start = response_content.find("TRANSLATION:")
            teach_start = response_content.find("TEACHING_DIRECTION:")
            
            if trans_start != -1 and teach_start != -1:
                translation = response_content[trans_start + 12:teach_start].strip()
            elif trans_start != -1:
                translation = response_content[trans_start + 12:].strip()
        
        # Parse TEACHING_DIRECTION
        if "TEACHING_DIRECTION:" in response_content:
            teach_start = response_content.find("TEACHING_DIRECTION:")
            if teach_start != -1:
                teaching_direction = response_content[teach_start + 19:].strip()
        
        # 7. Return response with full meta structure
        return {
            "status": "ok",
            "message": ai_message,
            "transliteration": transliteration if transliteration else None,
            "translation": translation if translation else None,
            "feedback": teaching_direction,
            "grammar_focus": expected_patterns,
            "hints": [f"💡 Focus on: {goal_en}"] if goal_en else []
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate initial message: {str(e)}")


@router.post("/lessons/guided/turn")
async def guided_dialogue_turn(
    request: GuidedTurnRequest,
    pg: PgSession = Depends(get_postgresql_session),
    neo: AsyncSession = Depends(get_neo4j_session),
) -> Dict[str, Any]:
    """
    Process a learner turn in guided dialogue with stage-aware evaluation.
    
    This endpoint:
    - Retrieves the current GuidedDialogueCard and stage
    - Evaluates learner input against expected patterns and rubric
    - Provides AI feedback and response
    - Advances stage if goals are met
    - Persists turn history and scores in guided_state
    
    Args:
        request: Contains session_id, stage_idx, learner_input
        
    Returns:
        AI response, feedback, stage progress, and advancement status
    """
    try:
        from app.services.ai_chat_service import AIChatService
        import json
        
        # 1. Retrieve session and lesson
        session_result = await pg.execute(
            text("""
                SELECT id, can_do_id, guided_stage_idx, guided_state, package_json
                FROM lesson_sessions
                WHERE id = :session_id
            """),
            {"session_id": request.session_id}
        )
        session_row = session_result.fetchone()
        if not session_row:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session_id, can_do_id, current_stage_idx, guided_state_raw, package_json_raw = session_row
        # Handle guided_state - it might be a dict (JSONB) or a string
        if guided_state_raw is None:
            guided_state = {}
        elif isinstance(guided_state_raw, dict):
            guided_state = guided_state_raw
        elif isinstance(guided_state_raw, str):
            guided_state = json.loads(guided_state_raw)
        else:
            guided_state = {}
        
        # 2. Get the lesson with GuidedDialogueCard
        # Try to get from package_json first, then fetch from lessons table
        lesson_data = None
        if package_json_raw:
            package = json.loads(package_json_raw) if isinstance(package_json_raw, str) else package_json_raw
            lesson_data = package.get("lesson")
        
        if not lesson_data:
            # Fetch from lessons table
            lesson_result = await pg.execute(
                text("""
                    SELECT lv.lesson_plan
                    FROM lessons l
                    JOIN lesson_versions lv ON l.id = lv.lesson_id
                    WHERE l.can_do_id = :can_do_id
                    ORDER BY lv.version DESC
                    LIMIT 1
                """),
                {"can_do_id": can_do_id}
            )
            lesson_row = lesson_result.fetchone()
            if lesson_row:
                lesson_plan = lesson_row[0]
                if isinstance(lesson_plan, str):
                    lesson_plan = json.loads(lesson_plan)
                lesson_data = lesson_plan.get("lesson", lesson_plan)
        
        if not lesson_data:
            raise HTTPException(status_code=404, detail="Lesson not found for this session")
        
        # 3. Extract GuidedDialogueCard
        cards = lesson_data.get("cards", {})
        guided_card = cards.get("guided_dialogue")
        if not guided_card:
            raise HTTPException(status_code=400, detail="No guided dialogue card in this lesson")
        
        stages = guided_card.get("stages", [])
        if request.stage_idx >= len(stages):
            return {
                "status": "completed",
                "message": "All stages completed!",
                "stage_idx": request.stage_idx,
                "total_stages": len(stages)
            }
        
        current_stage = stages[request.stage_idx]
        
        # 4. Build AI prompt with stage context
        ai_service = AIChatService()
        
        system_prompt = f"""You are a Japanese language tutor conducting a guided conversation practice.

Current Stage Goal: {current_stage.get('goal_en', '')}
Expected Patterns: {', '.join(current_stage.get('expected_patterns', []))}

Rubric for evaluation: {', '.join(current_stage.get('ai_feedback', {}).get('rubric', []))}

Always provide responses in this exact format:
CONVERSATIONAL_RESPONSE: [Your response in Japanese]
TRANSLITERATION: [Romaji transliteration]
TRANSLATION: [English translation]
TEACHING_DIRECTION: [Brief feedback, hints, or corrections in English]

Provide natural, encouraging feedback. If the learner's response aligns with the expected patterns and goals, acknowledge their success. If not, gently guide them using hints without being too direct."""
        
        hints_text = "\n".join([f"- {h.get('en', '')} / {h.get('ja', '')}" for h in current_stage.get('hints', [])])
        user_prompt = f"""Stage Hints:
{hints_text}

Learner said: "{request.learner_input}"

Evaluate their response and provide feedback. If they met the goal, congratulate them and suggest they're ready for the next stage. If not, provide guidance."""
        
        # 5. Get AI response
        ai_response_dict = await ai_service.generate_reply(
            provider="openai",
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": user_prompt}],
            system_prompt=system_prompt
        )
        
        # Extract content from response
        response_content = ai_response_dict.get("content", "")
        
        # Parse response for meta structure (similar to initial message)
        ai_message = response_content  # Default to full response
        transliteration = None
        translation = None
        teaching_direction = None
        
        # Try to parse structured response if present
        if "CONVERSATIONAL_RESPONSE:" in response_content:
            conv_start = response_content.find("CONVERSATIONAL_RESPONSE:")
            translit_start = response_content.find("TRANSLITERATION:")
            trans_start = response_content.find("TRANSLATION:")
            teach_start = response_content.find("TEACHING_DIRECTION:")
            
            if conv_start != -1:
                if translit_start != -1:
                    ai_message = response_content[conv_start + 24:translit_start].strip()
                elif trans_start != -1:
                    ai_message = response_content[conv_start + 24:trans_start].strip()
                elif teach_start != -1:
                    ai_message = response_content[conv_start + 24:teach_start].strip()
            
            if translit_start != -1:
                if trans_start != -1:
                    transliteration = response_content[translit_start + 16:trans_start].strip()
                elif teach_start != -1:
                    transliteration = response_content[translit_start + 16:teach_start].strip()
                else:
                    transliteration = response_content[translit_start + 16:].strip()
            
            if trans_start != -1:
                if teach_start != -1:
                    translation = response_content[trans_start + 12:teach_start].strip()
                else:
                    translation = response_content[trans_start + 12:].strip()
            
            if teach_start != -1:
                teaching_direction = response_content[teach_start + 19:].strip()
        
        # 6. Simple pattern matching evaluation (can be enhanced with LLM later)
        expected_patterns = current_stage.get('expected_patterns', [])
        pattern_matched = any(pattern in request.learner_input for pattern in expected_patterns) if expected_patterns else True
        
        # Word count check
        learner_schema = current_stage.get('learner_turn_schema', {})
        word_count = len(request.learner_input.split())
        min_words = learner_schema.get('min_words', 0)
        max_words = learner_schema.get('max_words', 100)
        word_count_ok = min_words <= word_count <= max_words
        
        # Determine if stage goals are met (simple heuristic)
        goals_met = pattern_matched and word_count_ok
        
        # 7. Update guided state
        if 'history' not in guided_state:
            guided_state['history'] = []
        
        turn_record = {
            "stage_idx": request.stage_idx,
            "timestamp": datetime.utcnow().isoformat(),
            "learner_input": request.learner_input,
            "ai_response": ai_message,
            "pattern_matched": pattern_matched,
            "word_count": word_count,
            "goals_met": goals_met
        }
        guided_state['history'].append(turn_record)
        
        # Advance stage if goals met
        new_stage_idx = request.stage_idx
        if goals_met:
            new_stage_idx = min(request.stage_idx + 1, len(stages))
        
        # 8. Persist updated state
        await pg.execute(
            text("""
                UPDATE lesson_sessions
                SET guided_stage_idx = :new_stage_idx,
                    guided_state = :guided_state,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :session_id
            """),
            {
                "session_id": request.session_id,
                "new_stage_idx": new_stage_idx,
                "guided_state": json.dumps(guided_state)
            }
        )
        await pg.commit()
        
        # 9. Return response
        return {
            "status": "ok",
            "ai_response": ai_message,  # String content, not full dict
            "transliteration": transliteration,
            "translation": translation,
            "feedback": {
                "pattern_matched": pattern_matched,
                "word_count": word_count,
                "word_count_ok": word_count_ok,
                "goals_met": goals_met,
                "teaching_direction": teaching_direction
            },
            "stage_progress": {
                "current_stage": request.stage_idx,
                "new_stage": new_stage_idx,
                "total_stages": len(stages),
                "advanced": new_stage_idx > request.stage_idx,
                "completed": new_stage_idx >= len(stages)
            },
            "current_stage_goal": current_stage.get('goal_en', '')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"guided_turn_failed: {str(e)}")


# ===== Dialogue Generation (Extend/New/Store) =====

class StoreDialogueRequest(BaseModel):
    can_do_id: str
    dialogue_card: Dict[str, Any]


@router.post("/dialogue/extend")
async def extend_dialogue(payload: ExtendDialogueRequest) -> Dict[str, Any]:
    """Extend an existing dialogue, returning a full DialogueCard including setting/characters."""
    try:
        card = await dialogue_generation_service.extend_dialogue(payload)
        return card.model_dump(mode="python")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"extend_failed: {str(e)}")


@router.post("/dialogue/new")
async def new_dialogue(payload: NewDialogueRequest) -> Dict[str, Any]:
    """Generate a fresh dialogue within the same domain, with contextual opening setting."""
    try:
        card = await dialogue_generation_service.new_dialogue(payload)
        return card.model_dump(mode="python")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"new_failed: {str(e)}")


@router.post("/dialogue/store")
async def store_dialogue(
    req: StoreDialogueRequest,
    pg: PgSession = Depends(get_postgresql_session),
) -> Dict[str, Any]:
    """Persist a generated dialogue card for the user. MVP returns success without deep storage."""
    try:
        # TODO: integrate with user-specific saved dialogues when table exists
        return {"status": "stored", "can_do_id": req.can_do_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"store_failed: {str(e)}")
