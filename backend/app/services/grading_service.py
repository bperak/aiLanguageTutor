"""
Grading service for lesson exercise responses.

MVP heuristic grading:
- If the answer is empty or whitespace-only → score 0.0
- If the exercise type is "fill_in" or "reorder":
  basic completeness check based on token count vs prompt placeholders.
- If the exercise type is "short_write":
  score based on character length bands and presence of simple Japanese chars.

This is intentionally simple and deterministic. It will be replaced by
AI-assisted rubric grading in a later task.
"""

from __future__ import annotations

from typing import Any, Dict, List


class GradingService:
    def _is_empty(self, answer: str) -> bool:
        return not answer or not answer.strip()

    def _contains_japanese(self, text: str) -> bool:
        # Quick check for hiragana/katakana/kanji ranges
        return any(
            (
                "\u3040" <= ch <= "\u30ff"  # Hiragana/Katakana
                or "\u4e00" <= ch <= "\u9faf"  # CJK Unified Ideographs
            )
            for ch in text
        )

    def _score_fill_in(self, prompt: str, answer: str) -> float:
        blanks = prompt.count("（ ") + prompt.count("(")
        token_like = len(answer.strip().split())
        if self._is_empty(answer):
            return 0.0
        if blanks <= 1:
            return 1.0 if len(answer.strip()) >= 1 else 0.4
        # Multi-blank: require at least blanks tokens
        return min(1.0, max(0.4, token_like / max(1, blanks)))

    def _score_reorder(self, prompt: str, answer: str) -> float:
        if self._is_empty(answer):
            return 0.0
        src_parts = [p for p in prompt.replace("／", "/").split("/") if p.strip()]
        ans_parts = [p for p in answer.replace("／", "/").split("/") if p.strip()]
        if not src_parts:
            return 0.5
        overlap = sum(1 for p in ans_parts if any(p.strip() in s for s in src_parts))
        return min(1.0, max(0.2, overlap / len(src_parts)))

    def _score_short_write(self, answer: str) -> float:
        if self._is_empty(answer):
            return 0.0
        length = len(answer)
        has_jp = self._contains_japanese(answer)
        base = 0.4 if length < 10 else 0.7 if length < 60 else 0.9
        if has_jp:
            base = min(1.0, base + 0.1)
        return base

    def grade_response(self, *, exercise: Dict[str, Any], answer: str) -> Dict[str, Any]:
        ex_type = str(exercise.get("type") or "").lower()
        prompt = str(exercise.get("prompt") or "")

        if ex_type == "fill_in":
            score = self._score_fill_in(prompt, answer)
        elif ex_type == "reorder":
            score = self._score_reorder(prompt, answer)
        elif ex_type == "short_write":
            score = self._score_short_write(answer)
        else:
            score = 1.0 if not self._is_empty(answer) else 0.0

        feedback: List[str] = []
        if score < 0.3:
            feedback.append("Try adding more detail. Keep it simple but complete.")
        elif score < 0.7:
            feedback.append("Good start. Add another detail or refine word order.")
        else:
            feedback.append("Nice work! You covered the main idea clearly.")

        hints: List[str] = []
        if ex_type == "fill_in":
            hints.append("Use the target word in correct form to complete the sentence.")
        elif ex_type == "reorder":
            hints.append("Check subject–object–verb placement in Japanese word order.")
        elif ex_type == "short_write":
            hints.append("Include 1–2 reasons using 〜から if appropriate.")

        return {
            "exercise_id": exercise.get("id"),
            "type": ex_type,
            "score": round(float(score), 2),
            "feedback": feedback,
            "hints": hints,
            "next_actions": [
                "Try another similar exercise",
                "Review key vocabulary",
            ],
        }


grading_service = GradingService()


