"""
Readability Service for Japanese text using jreadability (optional).

This wraps the external jreadability + fugashi stack if available.
Falls back gracefully when packages are not installed.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, Optional
import logging
import re


logger = logging.getLogger(__name__)


class ReadabilityService:
    def __init__(self) -> None:
        self._available = self._check_available()
        self._tagger = None

    def _check_available(self) -> bool:
        try:
            from jreadability import compute_readability  # noqa: F401
            return True
        except Exception:
            logger.info("jreadability not available; readability API will return 'available=False'")
            return False

    @property
    def is_available(self) -> bool:
        return self._available

    def _get_tagger(self):
        if self._tagger is None:
            try:
                from fugashi import Tagger  # type: ignore
                self._tagger = Tagger()
            except Exception:
                self._tagger = None
        return self._tagger

    def extract_japanese_text(self, text: str) -> str:
        pattern = r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF\u3000-\u303F\uFF01-\uFF60\u30FC]"
        chars = re.findall(pattern, text or "")
        return "".join(chars)

    def compute_score(self, text: str, japanese_only: bool = True) -> Optional[float]:
        if not self._available:
            return None
        if not text:
            return None
        if japanese_only:
            text = self.extract_japanese_text(text)
        if not text.strip():
            return None
        try:
            from jreadability import compute_readability
            tagger = self._get_tagger()
            if tagger:
                return float(compute_readability(text, tagger))
            return float(compute_readability(text))
        except Exception as e:
            logger.warning("Failed to compute readability", extra={"error": str(e)})
            return None

    @lru_cache(maxsize=256)
    def interpret(self, score: float) -> Dict[str, Any]:
        if 0.5 <= score < 1.5:
            return {"level": "Upper-advanced", "numeric_level": 6, "range": "[0.5, 1.5)", "color": "#8B0000"}
        if 1.5 <= score < 2.5:
            return {"level": "Lower-advanced", "numeric_level": 5, "range": "[1.5, 2.5)", "color": "#FF4500"}
        if 2.5 <= score < 3.5:
            return {"level": "Upper-intermediate", "numeric_level": 4, "range": "[2.5, 3.5)", "color": "#FF8C00"}
        if 3.5 <= score < 4.5:
            return {"level": "Lower-intermediate", "numeric_level": 3, "range": "[3.5, 4.5)", "color": "#FFD700"}
        if 4.5 <= score < 5.5:
            return {"level": "Upper-elementary", "numeric_level": 2, "range": "[4.5, 5.5)", "color": "#9ACD32"}
        if 5.5 <= score < 6.5:
            return {"level": "Lower-elementary", "numeric_level": 1, "range": "[5.5, 6.5)", "color": "#32CD32"}
        return {"level": "Out of range", "numeric_level": 0, "range": f"Score: {score:.3f}", "color": "#808080"}

    def analyze(self, text: str, japanese_only: bool = True) -> Dict[str, Any]:
        if not self._available:
            return {"available": False, "error": "jreadability not installed"}
        jp_text = self.extract_japanese_text(text) if japanese_only else (text or "")
        score = self.compute_score(text, japanese_only)
        if score is None:
            return {
                "available": True,
                "score": None,
                "japanese_text": jp_text,
                "error": "unable to compute score",
            }
        meta = self.interpret(score)
        return {
            "available": True,
            "score": score,
            "japanese_text": jp_text,
            **meta,
        }


readability_service = ReadabilityService()

