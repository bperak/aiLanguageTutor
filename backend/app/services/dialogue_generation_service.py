"""
Dialogue generation service for extending or creating dialogues within a CanDo domain.

Keeps prompts compact and returns a unified DialogueCard structure with contextual
`setting`, optional `characters`, and `dialogue_turns` (Stage 2 multilingual models).
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.ai_chat_service import AIChatService
from app.models.multilingual import DialogueTurn as MLDialogueTurn, DialogueCard as MLDialogueCard, JapaneseText


class ExtendDialogueRequest(BaseModel):
    can_do_id: str
    setting: str
    dialogue_turns: List[MLDialogueTurn] = Field(default_factory=list)
    characters: Optional[List[str]] = None
    vocabulary: Optional[List[str]] = None
    grammar_patterns: Optional[List[str]] = None
    num_turns: int = Field(default=3, ge=1, le=8)


class NewDialogueRequest(BaseModel):
    can_do_id: str
    seed_setting: Optional[str] = None
    vocabulary: Optional[List[str]] = None
    grammar_patterns: Optional[List[str]] = None
    num_turns: int = Field(default=6, ge=2, le=12)
    characters: Optional[List[str]] = None


class DialogueGenerationService:
    def __init__(self) -> None:
        self.ai = AIChatService()

    async def extend_dialogue(self, req: ExtendDialogueRequest) -> MLDialogueCard:
        provider = settings.CANDO_AI_PROVIDER
        model = settings.CANDO_AI_MODEL

        # Use only the last N turns for brevity (empty list if none provided)
        context_turns = req.dialogue_turns[-6:] if req.dialogue_turns else []

        sys = (
            "You generate short, natural Japanese dialogues for learners. "
            "Use simple, level-appropriate language. Maintain the given setting and characters. "
            "Ensure consistency and keep each turn concise."
        )

        # Compact instruction, nudging grammar/vocab without forcing
        guidance_parts: List[str] = [
            f"CanDo: {req.can_do_id}",
            f"Setting: {req.setting}",
        ]
        if req.characters:
            guidance_parts.append(f"Characters: {', '.join(req.characters)}")
        if req.vocabulary:
            guidance_parts.append(f"Vocab: {', '.join(req.vocabulary[:12])}")
        if req.grammar_patterns:
            guidance_parts.append(f"Grammar: {', '.join(req.grammar_patterns[:8])}")
        guidance_parts.append(f"Add {req.num_turns} new turns continuing the flow.")

        if context_turns:
            user = "\n".join(guidance_parts + [
                "Previous turns:",
                *[f"{t.speaker}: {t.japanese.kanji}" for t in context_turns],
            ])
        else:
            user = "\n".join(guidance_parts + [
                "Continue from the given setting."
            ])

        # Use the AI abstraction to get structured Japanese lines; fallback to plain strings
        # Ask for JSON array of turns and parse
        instr = (
            "Return JSON array of 'turns': list of {speaker,text,romaji,translation,furigana:[{text,ruby}]} of length "
            f"{req.num_turns}."
        )
        reply = await self.ai.generate_reply(
            provider=provider,
            model=model,
            messages=[{"role": "user", "content": user + "\n\n" + instr}],
            system_prompt=sys,
        )
        content = reply.get("content", "")
        try:
            import json as _json
            parsed = _json.loads(content)
            generated_lines = parsed.get("turns", parsed)
        except Exception:
            generated_lines = []

        new_turns: List[MLDialogueTurn] = []
        for line in generated_lines[: req.num_turns]:
            jt = JapaneseText(
                kanji=line.get("text", ""),
                romaji=line.get("romaji", ""),
                furigana=line.get("furigana", []) or [{"text": line.get("text", ""), "ruby": None}],
                translation=line.get("translation", ""),
            )
            new_turns.append(MLDialogueTurn(speaker=line.get("speaker", "A"), japanese=jt))

        full_turns = (list(req.dialogue_turns) if req.dialogue_turns else []) + new_turns

        return MLDialogueCard(
            title=None,
            setting=req.setting,
            characters=req.characters,
            dialogue_turns=full_turns,
        )

    async def new_dialogue(self, req: NewDialogueRequest) -> MLDialogueCard:
        provider = settings.CANDO_AI_PROVIDER
        model = settings.CANDO_AI_MODEL

        sys = (
            "You generate short, natural Japanese dialogues for learners. "
            "Start with a contextual opening setting (one paragraph) that guides the dialogue and sets the specific context (real place, people, motives, context) in line with the canDo domain, and then provide turns using the characters, their roles (including their names), and the setting in line with the canDo domain."
        )

        guidance_parts: List[str] = [f"CanDo: {req.can_do_id}"]
        if req.seed_setting:
            guidance_parts.append(f"Setting: {req.seed_setting}")
        if req.characters:
            guidance_parts.append(f"Characters: {', '.join(req.characters)}")
        if req.vocabulary:
            guidance_parts.append(f"Vocab: {', '.join(req.vocabulary[:12])}")
        if req.grammar_patterns:
            guidance_parts.append(f"Grammar: {', '.join(req.grammar_patterns[:8])}")
        guidance_parts.append(f"Provide {req.num_turns} turns after the setting.")

        user = "\n".join(guidance_parts)

        # Ask for JSON structure and parse
        instr = (
            "Return JSON with keys: setting (string), turns (array of {speaker,text,romaji,translation,furigana:[{text,ruby}]})."
            " Keep it in line with the canDo domain."
            " Keep it concise."
        )
        reply = await self.ai.generate_reply(
            provider=provider,
            model=model,
            messages=[{"role": "user", "content": user + "\n\n" + instr}],
            system_prompt=sys,
        )
        content = reply.get("content", "")
        try:
            import json as _json
            parsed = _json.loads(content)
        except Exception:
            parsed = {"setting": req.seed_setting or "", "turns": []}

        setting_text: str = parsed.get("setting", req.seed_setting or "")
        lines: List[Dict[str, Any]] = parsed.get("turns", [])

        turns: List[MLDialogueTurn] = []
        for line in lines:
            jt = JapaneseText(
                kanji=line.get("text", ""),
                romaji=line.get("romaji", ""),
                furigana=line.get("furigana", []) or [{"text": line.get("text", ""), "ruby": None}],
                translation=line.get("translation", ""),
            )
            turns.append(MLDialogueTurn(speaker=line.get("speaker", "A"), japanese=jt))

        return MLDialogueCard(
            title=None,
            setting=setting_text,
            characters=req.characters,
            dialogue_turns=turns,
        )


dialogue_generation_service = DialogueGenerationService()


