"""
Minimal AI chat service used to generate assistant replies in conversations.

Uses real provider APIs configured via environment variables in `app.core.config.settings`.
"""

from __future__ import annotations

from typing import List, Literal, Dict, Any, AsyncIterator
import asyncio
import structlog
from openai import AsyncOpenAI
from google import genai
from google.genai import types
import time

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
        past_conversation_context: List[str] | None = None,
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
        if past_conversation_context:
            meta_lines.append("Relevant past conversation context:")
            for ctx in past_conversation_context[:3]:
                meta_lines.append(f"- {ctx}")

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
            self._genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        else:
            self._genai_client = None

    async def generate_reply(
        self,
        *,
        provider: Literal["openai", "gemini"] = "openai",
        model: str = "gpt-4o-mini",
        messages: List[Dict[str, str]] | None = None,
        system_prompt: str | None = None,
        session_metadata: Dict[str, Any] | None = None,
        corrections_memory: List[str] | None = None,
        knowledge_terms: List[str] | None = None,
        past_conversation_context: List[str] | None = None,
        trace_id: str | None = None,
        # Generation config knobs (mainly for Gemini)
        force_json: bool = False,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
        response_schema: Any | None = None,
        response_json_schema: Dict[str, Any] | None = None,
        timeout: int | None = None,
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
            past_conversation_context=past_conversation_context,
        )

        start_time = time.perf_counter()
        try:
            if provider == "gemini":
                if not self._genai_client:
                    raise ValueError("Gemini API key not configured")
                # Gemini simple chat: concatenate to a prompt
                # Format prior messages as simple transcript
                transcript = [f"System: {system_prompt}"]
                for m in messages:
                    transcript.append(f"{m['role'].capitalize()}: {m['content']}")
                prompt = "\n".join(transcript)
                # Prefer explicit Content/Part and config for JSON
                gen_config = None
                if force_json or temperature is not None or max_output_tokens is not None or response_schema is not None or response_json_schema is not None:
                    gen_config = types.GenerateContentConfig(
                        response_mime_type=("application/json" if force_json else None),
                        temperature=(0.0 if temperature is None else float(temperature)),
                        max_output_tokens=(max_output_tokens if max_output_tokens is not None else None),
                        # Map dict JSON schema to response_schema; avoid unsupported response_json_schema param
                        response_schema=(response_schema if response_schema is not None else response_json_schema),
                    )
                # Wrap Gemini call with timeout
                timeout_seconds = timeout or settings.AI_REQUEST_TIMEOUT_SECONDS
                try:
                    response = await asyncio.wait_for(
                        asyncio.to_thread(
                            self._genai_client.models.generate_content,
                            model=model,
                            contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
                            config=gen_config if gen_config is not None else None,
                        ),
                        timeout=timeout_seconds
                    )
                except asyncio.TimeoutError:
                    logger.error("gemini_request_timeout", model=model, timeout=timeout_seconds)
                    raise TimeoutError(f"Gemini API request timed out after {timeout_seconds} seconds")
                elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                
                # Safely extract text content
                content_text = ""
                try:
                    content_text = response.text if response.text else ""
                except (AttributeError, ValueError) as e:
                    logger.warning(
                        "gemini_response_text_extraction_failed",
                        model=model,
                        error=str(e),
                        response_type=type(response).__name__)
                    # Try alternate extraction methods
                    if hasattr(response, 'candidates') and response.candidates:
                        candidate = response.candidates[0]
                        if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                            for part in candidate.content.parts:
                                if hasattr(part, 'text'):
                                    content_text += part.text
                
                result: Dict[str, Any] = {
                    "content": content_text,
                    "provider": "gemini",
                    "model": model,
                    "elapsed_ms": elapsed_ms,
                }
                if trace_id:
                    result["trace_id"] = trace_id
                return result

            # Default: OpenAI
            timeout_seconds = timeout or settings.AI_REQUEST_TIMEOUT_SECONDS
            chat_messages = [{"role": "system", "content": system_prompt}] + messages
            
            # GPT-5 models don't support temperature=0.0, use default (1.0)
            # Other models work better with temperature=0.0 for structured output
            temp = 1.0 if model.startswith("gpt-5") or model.startswith("o1") else 0.0
            
            client = self._openai.with_options(timeout=timeout_seconds)
            resp = await client.chat.completions.create(
                model=model,
                messages=chat_messages,  # type: ignore[arg-type]
                temperature=temp,
                max_tokens=4000,
            )
            choice = resp.choices[0]
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            result = {
                "content": choice.message.content or "",
                "provider": "openai",
                "model": model,
                "prompt_tokens": getattr(resp.usage, "prompt_tokens", None),
                "completion_tokens": getattr(resp.usage, "completion_tokens", None),
                "elapsed_ms": elapsed_ms,
            }
            # Expose the enriched system prompt so stream builder can reuse it
            result["system_prompt"] = system_prompt
            if trace_id:
                result["trace_id"] = trace_id
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
        past_conversation_context: List[str] | None = None,
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
            past_conversation_context=past_conversation_context,
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
            stream = await self._openai.with_options(timeout=settings.AI_REQUEST_TIMEOUT_SECONDS).chat.completions.create(
                model=model,
                messages=chat_messages,  # type: ignore[arg-type]
                temperature=0.0,
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

