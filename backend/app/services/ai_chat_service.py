"""
Minimal AI chat service used to generate assistant replies in conversations.

Uses real provider APIs configured via environment variables in `app.core.config.settings`.
"""

from __future__ import annotations

from typing import List, Literal, Dict, Any, AsyncIterator
import structlog
from openai import AsyncOpenAI
import google.generativeai as genai

from app.core.config import settings


logger = structlog.get_logger()

Role = Literal["system", "user", "assistant"]


class AIChatService:
    def _build_enriched_system_prompt(
        self,
        *,
        base_prompt: str | None,
        session_metadata: Dict[str, Any] | None,
        corrections_memory: List[str] | None,
        knowledge_terms: List[str] | None,
    ) -> str:
        meta_lines: List[str] = []
        if session_metadata:
            goals = session_metadata.get("learning_goals") or []
            level = session_metadata.get("current_level") or "unspecified"
            topic = session_metadata.get("topic") or session_metadata.get("language_code") or "ja"
            meta_lines.append(f"Learner level: {level}")
            if goals:
                meta_lines.append(f"Goals: {', '.join(goals)}")
            meta_lines.append(f"Topic: {topic}")
        if corrections_memory:
            meta_lines.append("Recent corrections to remember:")
            for c in corrections_memory[-5:]:
                meta_lines.append(f"- {c}")
        if knowledge_terms:
            meta_lines.append("Consider weaving in 1 relevant term naturally (optional):")
            meta_lines.append(", ".join(knowledge_terms[:5]))

        system_prompt = (
            (base_prompt or "")
            + (
                "\nYou are a professional Japanese language tutor."
                " Focus on coaching with micro-steps and zero fluff."
                "\nTutoring contract:"
                "\n- Never repeat the same instructional sentence twice in a row."
                "\n- If the learner already answered or says they've said it, move on."
                "\n- Prefer targeted feedback over generic praise."
                "\n- Keep responses compact (max ~2 sentences), include one concrete example when useful."
                "\n- End with at most one short question that advances the task."
                "\n- Avoid filler like 'That's exciting!'."
                "\nResponse format (when appropriate):"
                "\n1) Teach: one targeted hint or correction"
                "\n2) Example: one short example (JP + romaji/translation when helpful)"
                "\n3) Try: one short prompt"
            )
            + ("\n" + "\n".join(meta_lines) if meta_lines else "")
        ).strip()
        return system_prompt

    """Generate assistant replies using OpenAI or Google Gemini."""

    def __init__(self) -> None:
        self._openai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)

    async def generate_reply(
        self,
        provider: Literal["openai", "gemini"] = "openai",
        model: str = "gpt-4o-mini",
        messages: List[Dict[str, str]] | None = None,
        system_prompt: str | None = None,
        session_metadata: Dict[str, Any] | None = None,
        corrections_memory: List[str] | None = None,
        knowledge_terms: List[str] | None = None,
    ) -> Dict[str, Any]:
        """
        Generate a chat completion based on prior messages.

        Args:
            provider: "openai" or "gemini"
            model: model name to use
            messages: prior messages (role/content)
            system_prompt: optional system prompt to prepend

        Returns:
            Dict with keys: content, provider, model, prompt_tokens?, completion_tokens?
        """
        messages = messages or []
        # Build enriched system prompt
        system_prompt = self._build_enriched_system_prompt(
            base_prompt=system_prompt,
            session_metadata=session_metadata,
            corrections_memory=corrections_memory,
            knowledge_terms=knowledge_terms,
        )

        try:
            if provider == "gemini":
                # Gemini simple chat: concatenate to a prompt
                # Format prior messages as simple transcript
                transcript = [f"System: {system_prompt}"]
                for m in messages:
                    transcript.append(f"{m['role'].capitalize()}: {m['content']}")
                prompt = "\n".join(transcript)
                model_instance = genai.GenerativeModel(model)
                response = await model_instance.generate_content_async(prompt)
                return {
                    "content": getattr(response, "text", ""),
                    "provider": "gemini",
                    "model": model,
                }

            # Default: OpenAI
            chat_messages = [{"role": "system", "content": system_prompt}] + messages
            resp = await self._openai.chat.completions.create(
                model=model,
                messages=chat_messages,  # type: ignore[arg-type]
                temperature=0.3,
                max_tokens=300,
            )
            choice = resp.choices[0]
            result = {
                "content": choice.message.content or "",
                "provider": "openai",
                "model": model,
                "prompt_tokens": getattr(resp.usage, "prompt_tokens", None),
                "completion_tokens": getattr(resp.usage, "completion_tokens", None),
            }
            # Expose the enriched system prompt so stream builder can reuse it
            result["system_prompt"] = system_prompt
            return result
        except Exception as e:  # noqa: BLE001
            logger.error("AI reply generation failed", provider=provider, model=model, error=str(e))
            raise


    async def stream_reply(
        self,
        *,
        provider: Literal["openai", "gemini"] = "openai",
        model: str = "gpt-4o-mini",
        messages: List[Dict[str, str]] | None = None,
        system_prompt: str | None = None,
        session_metadata: Dict[str, Any] | None = None,
        corrections_memory: List[str] | None = None,
        knowledge_terms: List[str] | None = None,
    ) -> AsyncIterator[str]:
        """Yield reply chunks for streaming.

        For OpenAI, uses streaming deltas. For Gemini, yields one full chunk.
        """
        messages = messages or []
        # Build enriched system prompt without making a completion request
        system_prompt = self._build_enriched_system_prompt(
            base_prompt=system_prompt,
            session_metadata=session_metadata,
            corrections_memory=corrections_memory,
            knowledge_terms=knowledge_terms,
        ) or (
            "You are a friendly Japanese language tutor."
            " Rules:"
            " 1) Do not ask the learner to repeat the same phrase more than once."
            " 2) If the learner says they already said it (or demonstrates it), acknowledge and move forward to a new micro-step."
            " 3) Avoid loop prompts like 'Give it a try' if the learner already tried; advance the lesson."
            " 4) Keep replies very concise (1–2 sentences) and, when helpful, include exactly one short example."
            " 5) Ask at most one simple question at the end."
        )

        try:
            if provider == "gemini":
                # Fallback: no token streaming, emit full content once
                result = await self.generate_reply(provider=provider, model=model, messages=messages, system_prompt=system_prompt)
                yield result.get("content", "")
                return

            # OpenAI streaming
            chat_messages = [{"role": "system", "content": system_prompt}] + messages
            stream = await self._openai.chat.completions.create(
                model=model,
                messages=chat_messages,  # type: ignore[arg-type]
                temperature=0.3,
                max_tokens=300,
                stream=True,
            )
            async for event in stream:  # type: ignore[async-iterator]
                try:
                    delta = event.choices[0].delta.content  # type: ignore[attr-defined]
                except Exception:
                    delta = None
                if delta:
                    yield delta
        except Exception as e:  # noqa: BLE001
            logger.error("AI streaming failed", provider=provider, model=model, error=str(e))
            # Propagate to caller to decide how to finalize
            raise

