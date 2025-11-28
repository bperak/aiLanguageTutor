"""
Service for generating titles for CanDoDescriptors using AI.

This service generates concise, full-sentence titles in both English and Japanese
from CanDoDescriptor descriptions.
"""

from __future__ import annotations

from typing import Dict, Optional
import structlog
from app.services.ai_chat_service import AIChatService

logger = structlog.get_logger()


class CanDoTitleService:
    """Service for generating CanDoDescriptor titles using AI."""
    
    def __init__(self):
        self.ai_service = AIChatService()
        self.default_provider = "openai"
        self.default_model = "gpt-4o-mini"
    
    async def generate_title(
        self,
        description_en: Optional[str] = None,
        description_ja: Optional[str] = None,
        language: str = "en"
    ) -> str:
        """
        Generate a concise full-sentence title from CanDo description.
        
        Args:
            description_en: English description
            description_ja: Japanese description
            language: Target language ("en" or "ja")
            
        Returns:
            Generated title in requested language
        """
        if language not in ["en", "ja"]:
            raise ValueError(f"Unsupported language: {language}. Must be 'en' or 'ja'")
        
        # Build description text for prompt
        description_parts = []
        if description_en:
            description_parts.append(f"English: {description_en}")
        if description_ja:
            description_parts.append(f"Japanese: {description_ja}")
        
        if not description_parts:
            raise ValueError("At least one description (en or ja) must be provided")
        
        description_text = "\n".join(description_parts)
        
        # Build prompt based on target language
        if language == "en":
            system_prompt = (
                "You are a language learning curriculum expert. "
                "Generate a concise, full-sentence title for a Can-Do descriptor. "
                "The title should start with 'Can' and be a complete sentence that summarizes the learning objective. "
                "Keep it clear and concise (one sentence, maximum 15 words)."
            )
            user_prompt = (
                f"Generate a concise full-sentence title (starting with 'Can...') from this CanDo description:\n\n"
                f"{description_text}\n\n"
                f"Title:"
            )
        else:  # ja
            system_prompt = (
                "あなたは言語学習カリキュラムの専門家です。 "
                "Can-Do記述子の簡潔で完全な文のタイトルを生成してください。 "
                "タイトルは「〜できる」で始まり、学習目標を要約する完全な文である必要があります。 "
                "明確で簡潔にしてください（1文、最大15語）。"
            )
            user_prompt = (
                f"このCanDo記述から簡潔な完全な文のタイトル（「〜できる」で始まる）を生成してください：\n\n"
                f"{description_text}\n\n"
                f"タイトル："
            )
        
        try:
            response = await self.ai_service.generate_reply(
                provider=self.default_provider,
                model=self.default_model,
                system_prompt=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=0.3,
                max_output_tokens=50
            )
            
            title = response.get("content", "").strip()
            
            # Clean up title (remove quotes if present, ensure it starts correctly)
            title = title.strip('"\'')
            if language == "en" and not title.startswith("Can "):
                # Try to fix if AI didn't follow format
                if title.lower().startswith("can "):
                    title = "Can " + title[4:].strip()
                else:
                    title = "Can " + title.strip()
            
            logger.info("Generated CanDo title", language=language, title=title[:50])
            return title
            
        except Exception as e:
            logger.error("Failed to generate CanDo title", 
                        language=language, 
                        error=str(e))
            raise
    
    async def generate_titles(
        self,
        description_en: Optional[str] = None,
        description_ja: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Generate both English and Japanese titles in parallel.
        
        Args:
            description_en: English description
            description_ja: Japanese description
            
        Returns:
            Dictionary with "titleEn" and "titleJa" keys
        """
        import asyncio
        
        # Generate both titles concurrently
        title_en_task = self.generate_title(description_en, description_ja, language="en")
        title_ja_task = self.generate_title(description_en, description_ja, language="ja")
        
        title_en, title_ja = await asyncio.gather(title_en_task, title_ja_task)
        
        return {
            "titleEn": title_en,
            "titleJa": title_ja
        }

