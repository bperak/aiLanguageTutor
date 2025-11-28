"""
Image generation service using Gemini 2.5 Flash Image Preview.

Reuses patterns from generate_grammar_illustrations.py for consistency.
"""

import base64
import logging
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

import os

logger = logging.getLogger(__name__)

MODEL_ID = "gemini-2.5-flash-image-preview"


def create_gemini_client(api_key: Optional[str] = None):
    """Lazy import google-genai client to keep tests light.
    
    Uses the same pattern as ai_chat_service.py and other services.
    """
    # Import at function level to match existing codebase pattern
    from google import genai  # type: ignore
    from google.genai import types  # type: ignore
    
    if api_key is None:
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required (set in .env or pass as parameter)")
    
    return genai.Client(api_key=api_key)


def _extract_image_bytes(result) -> Optional[bytes]:
    """Best-effort extraction of image bytes from google-genai response shapes."""
    if result is None:
        return None
    
    # 0) Preferred: generate_content returns candidates[].content.parts[].inline_data.data
    try:
        candidates = getattr(result, 'candidates', None)
        if candidates:
            for cand in candidates:
                content = getattr(cand, 'content', None)
                parts = getattr(content, 'parts', []) if content else []
                for part in parts:
                    inline_data = getattr(part, 'inline_data', None)
                    if inline_data is not None:
                        data = getattr(inline_data, 'data', None)
                        if isinstance(data, (bytes, bytearray)) and data:
                            return bytes(data)
                        if isinstance(data, str) and data:
                            try:
                                return base64.b64decode(data)
                            except Exception:
                                pass
    except Exception:
        pass
    
    # 1) client.images.generate returns result.images[0].image.bytes or .bytes
    try:
        images = getattr(result, 'images', None) or getattr(result, 'generated_images', None)
        if images:
            first = images[0]
            if hasattr(first, 'image') and hasattr(first.image, 'bytes') and first.image.bytes:
                return first.image.bytes
            if hasattr(first, 'bytes') and first.bytes:
                return first.bytes
            if hasattr(first, 'b64_data') and first.b64_data:
                return base64.b64decode(first.b64_data)
    except Exception:
        pass
    
    # 2) Some responses include a single image field
    try:
        image = getattr(result, 'image', None)
        if image and hasattr(image, 'bytes') and image.bytes:
            return image.bytes
    except Exception:
        pass
    
    # 3) JSON payload with base64
    try:
        if isinstance(result, dict):
            b64 = result.get('image_b64') or result.get('data')
            if b64:
                return base64.b64decode(b64)
    except Exception:
        pass
    
    return None


def generate_image_from_prompt(
    prompt: str,
    negative_prompt: Optional[str] = None,
    size: str = "1024x1024",
    api_key: Optional[str] = None,
    max_retries: int = 3,
) -> bytes:
    """
    Generate an image from a prompt using Gemini 2.5 Flash Image Preview.
    
    Uses the same pattern as resources/generate_grammar_illustrations.py.
    
    Args:
        prompt: The image generation prompt
        negative_prompt: Optional negative prompt (things to avoid)
        size: Image size (e.g., "1024x1024", "1280x720")
        api_key: Optional API key (defaults to GEMINI_API_KEY env var)
        max_retries: Maximum number of retry attempts
        
    Returns:
        Image bytes (PNG format)
        
    Raises:
        RuntimeError: If image generation fails after retries
        ValueError: If API key is missing
    """
    client = create_gemini_client(api_key)
    
    # Build final prompt with negative prompt if provided
    final_prompt = prompt
    if negative_prompt:
        final_prompt = f"{prompt}\n\nNegative prompt: {negative_prompt}"
    
    # Add style guidance for consistency
    style_guidance = (
        "Clean, educational illustration style. "
        "No text, letters, numbers, or readable signage in the image. "
        "Suitable for language learning materials."
    )
    final_prompt = f"{final_prompt}\n\n{style_guidance}"
    
    last_error = None
    for attempt in range(max_retries):
        try:
            # Use generate_content as preferred method (matches generate_grammar_illustrations.py)
            result = client.models.generate_content(model=MODEL_ID, contents=[final_prompt])
            img_bytes = _extract_image_bytes(result)
            
            if img_bytes:
                logger.info(f"Successfully generated image (attempt {attempt + 1})")
                return img_bytes
            else:
                raise RuntimeError("No image bytes returned from Gemini")
                
        except Exception as e:
            last_error = e
            logger.warning(f"Image generation attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                # Wait a bit before retry
                import time
                time.sleep(1)
    
    raise RuntimeError(f"Image generation failed after {max_retries} attempts: {last_error}")


def save_image_bytes(image_bytes: bytes, output_path: Path) -> None:
    """
    Save image bytes to a file.
    
    Args:
        image_bytes: Image data as bytes
        output_path: Path where to save the image
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(image_bytes)
    logger.info(f"Saved image to {output_path}")

