"""
Entity Resolution Service

Handles Neo4j-based entity resolution for words and grammar patterns.
"""

from __future__ import annotations

from typing import Any, Dict, List, Set
from neo4j import AsyncSession
import structlog

from app.core.japanese_utils import generate_text_variants, extract_japanese_runs

logger = structlog.get_logger()


def flatten_ui_text(master: Dict[str, Any]) -> str:
    """Extract all text from lesson UI for entity extraction."""
    ui = master.get("ui", {}) or {}
    lines: List[str] = []
    header = ui.get("header") or {}
    if header.get("title"):
        lines.append(str(header.get("title")))
    if header.get("subtitle"):
        lines.append(str(header.get("subtitle")))
    for sec in ui.get("sections", []) or []:
        title = sec.get("title")
        if title:
            lines.append(str(title))
        for card in sec.get("cards", []) or []:
            if card.get("title"):
                lines.append(str(card.get("title")))
            body = card.get("body") or {}
            jp = body.get("jp")
            meta = body.get("meta")
            if jp:
                lines.append(str(jp))
            if meta:
                lines.append(str(meta))
            for b in card.get("bullets", []) or []:
                lines.append(str(b))
    return "\n".join(lines)[:12000]


async def deterministic_words(
    graph: AsyncSession, text_blob: str
) -> List[Dict[str, Any]]:
    """Deterministically extract words from text using token analysis."""
    candidates = extract_japanese_runs(text_blob)
    results: List[Dict[str, Any]] = []
    seen_ids: Set[str] = set()
    
    for tok in candidates:
        variants = list(set(generate_text_variants(tok)))
        q = (
            "MATCH (w:Word)\n"
            "WHERE ANY(x IN $vars WHERE "
            " w.standard_orthography = x OR w.reading_katakana = x OR w.romaji = x OR "
            " w.lemma = x OR w.hiragana = x OR w.kanji = x)\n"
            "RETURN elementId(w) AS elementId, w.standard_orthography AS orth, w.reading_katakana AS katakana, "
            " w.romaji AS romaji, w.pos_primary AS pos, w.translation AS translation\n"
            "LIMIT 1"
        )
        rec = await (await graph.run(q, vars=variants)).single()
        if rec:
            d = dict(rec)
            gid = str(d.get("elementId")) if d.get("elementId") is not None else f"tok::{tok}"
            if gid in seen_ids:
                continue
            seen_ids.add(gid)
            d["source_text"] = tok
            results.append(d)
        if len(results) >= 20:
                        break
    
    logger.info("deterministic_words_extracted", count=len(results))
    return results


async def deterministic_grammar(
    graph: AsyncSession, text_blob: str
) -> List[Dict[str, Any]]:
    """Deterministically extract grammar patterns from text using pattern matching."""
    import unicodedata
    norm = unicodedata.normalize("NFKC", text_blob or "")
    # Fetch patterns and check inclusion
    q = "MATCH (p:GrammarPattern) RETURN p.id AS id, p.pattern AS pattern, p.classification AS classification LIMIT 1000"
    cursor = await graph.run(q)
    out: List[Dict[str, Any]] = []
    count = 0
    async for rec in cursor:
        rid = rec.get("id")
        pat = rec.get("pattern")
        if not pat:
            continue
        pnorm = unicodedata.normalize("NFKC", str(pat))
        # Simple inclusion check
        if pnorm and pnorm in norm:
            out.append({"id": rid, "pattern": pat, "classification": rec.get("classification")})
            count += 1
            if count >= 10:
                break
    logger.info("deterministic_grammar_extracted", count=len(out))
    return out


class EntityResolutionService:
    """Service for resolving words and grammar patterns to Neo4j entities."""

    def __init__(self) -> None:
        pass

    async def resolve_words(
        self, graph: AsyncSession, items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Resolve word items to Neo4j Word nodes."""
    out: List[Dict[str, Any]] = []
    for w in items or []:
            k = str(w.get("kanji") or w.get("text") or "").strip()
            h = str(w.get("hiragana") or "").strip()
        if not (k or h):
            continue
            
            variants = list(set(generate_text_variants(k) | generate_text_variants(h)))
        q = (
            "MATCH (w:Word)\n"
                "WHERE ANY(x IN $vars WHERE "
                " w.standard_orthography = x OR w.reading_katakana = x OR w.romaji = x OR "
                " w.lemma = x OR w.hiragana = x OR w.kanji = x)\n"
                "RETURN elementId(w) AS elementId, w.standard_orthography AS orth, w.reading_katakana AS katakana, "
                " w.romaji AS romaji, w.pos_primary AS pos, w.translation AS translation\n"
            "LIMIT 1"
        )
        rec = await (await graph.run(q, vars=variants)).single()
        if rec:
            d = dict(rec)
            d["source_text"] = w.get("text")
            out.append(d)
                logger.debug("word_resolved", text=w.get("text"), pos=d.get("pos"))
        
        logger.info("words_resolved", count=len(out), attempted=len(items))
    return out

    async def resolve_grammar(
        self, graph: AsyncSession, items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Resolve grammar pattern items to Neo4j GrammarPattern nodes."""
    out: List[Dict[str, Any]] = []
    for g in items or []:
        pid = str(g.get("patternId") or "").strip()
        pat = str(g.get("pattern") or "").strip()
        if pid:
            q = "MATCH (p:GrammarPattern {id: $id}) RETURN p.id AS id, p.pattern AS pattern, p.classification AS classification LIMIT 1"
            rec = await (await graph.run(q, id=pid)).single()
        else:
            q = "MATCH (p:GrammarPattern) WHERE p.pattern = $p RETURN p.id AS id, p.pattern AS pattern, p.classification AS classification LIMIT 1"
            rec = await (await graph.run(q, p=pat)).single()
        if rec:
            out.append(dict(rec))
                logger.debug("grammar_resolved", pattern=pat)
        
        logger.info("grammar_patterns_resolved", count=len(out), attempted=len(items))
    return out


entity_resolution = EntityResolutionService()
