"""
Japanese text utility functions.

Centralized utilities for Japanese text handling to eliminate duplication
across services. Functions handle katakana-hiragana conversion, normalization,
and text analysis.
"""

import unicodedata
import re
from typing import Set, Dict, Any, List

try:
    from pykakasi import kakasi  # type: ignore
    _KAKASI = kakasi()
    _KAKASI.setMode("J", "H")  # Kanji to Hiragana
    _KAKASI.setMode("K", "H")  # Katakana to Hiragana
    _KAKASI.setMode("r", "Hepburn")
    _KAKASI_CONV = _KAKASI.getConverter()
except Exception:
    _KAKASI_CONV = None


def kata_to_hira(text: str) -> str:
    """Convert katakana characters to hiragana.
    
    Args:
        text: Text potentially containing katakana characters.
        
    Returns:
        Text with katakana converted to hiragana.
        
    Example:
        >>> kata_to_hira("カタカナ")
        'かたかな'
    """
    return "".join(chr(ord(ch) - 0x60) if "ァ" <= ch <= "ン" else ch for ch in text)


def hira_to_kata(text: str) -> str:
    """Convert hiragana characters to katakana.
    
    Args:
        text: Text potentially containing hiragana characters.
        
    Returns:
        Text with hiragana converted to katakana.
        
    Example:
        >>> hira_to_kata("ひらがな")
        'ヒラガナ'
    """
    return "".join(chr(ord(ch) + 0x60) if "ぁ" <= ch <= "ん" else ch for ch in text)


def normalize_jp_text(text: str) -> str:
    """Normalize Japanese text to NFKC form.
    
    Handles Unicode normalization for consistent text comparison and processing.
    NFKC (Compatibility Decomposition, followed by Canonical Composition) is
    recommended for Japanese text to unify width variants (full-width vs half-width).
    
    Args:
        text: Text to normalize.
        
    Returns:
        NFKC-normalized text.
        
    Example:
        >>> normalize_jp_text("ｈｅｌｌｏ")  # Half-width
        'ｈｅｌｌｏ'  # Normalized
    """
    return unicodedata.normalize("NFKC", text or "")


def extract_japanese_runs(text: str) -> list[str]:
    """Extract runs of Japanese characters (kanji, hiragana, katakana).
    
    Identifies contiguous sequences of Japanese characters and returns them
    in order, with deduplication. Filters to reasonable run lengths (1-6 chars)
    to prioritize lexical items over longer combinations.
    
    Args:
        text: Text to analyze.
        
    Returns:
        List of Japanese character runs, deduplicated and ordered.
        
    Example:
        >>> extract_japanese_runs("これは日本語です")
        ['これ', 'は', '日本語', 'です']
    """
    norm = normalize_jp_text(text or "")
    # Regex: Kanji, Hiragana, Katakana runs
    jp_runs = re.findall(r"[\u3040-\u30FF\u4E00-\u9FFFー々〆ヵヶ]+", norm)
    # Deduplicate while preserving order
    seen: Set[str] = set()
    tokens: list[str] = []
    for run in jp_runs:
        if run and run not in seen:
            seen.add(run)
            tokens.append(run)
    # Shortlist: keep runs with length 1-6 to bias toward lexical items
    return [t for t in tokens if 1 <= len(t) <= 6]


def generate_text_variants(text: str) -> list[str]:
    """Generate multiple text variants for fuzzy matching.
    
    Creates hiragana, katakana, and normalized variants of input text
    to improve matching across different Japanese writing systems.
    
    Args:
        text: Text to generate variants for.
        
    Returns:
        List of unique text variants (original, normalized, kata, hira).
        
    Example:
        >>> generate_text_variants("カタカナ")
        ['カタカナ', 'かたかな', ...]
    """
    variants = {
        text,
        normalize_jp_text(text),
        kata_to_hira(text),
        hira_to_kata(text),
    }
    # Also include normalized versions of conversions
    variants.add(normalize_jp_text(kata_to_hira(text)))
    variants.add(normalize_jp_text(hira_to_kata(text)))
    return list(variants)


def _is_kanji(ch: str) -> bool:
    return '\u4e00' <= ch <= '\u9fff'


def fallback_multilingual(text: str, translation: str | None = None) -> Dict[str, Any]:
    """Create a deterministic JapaneseText-like dict for UI fallback.

    - kanji: original text
    - romaji: normalized string (placeholder; not true romanization)
    - furigana: per-character segments; provide ruby for kanji chars
    - translation: optional provided or empty
    """
    norm = normalize_jp_text(text or "")
    segments: List[Dict[str, str | None]] = []
    # Prefer pykakasi if available to get reading per character span
    if _KAKASI_CONV is not None:
        hira = _KAKASI_CONV.do(norm)
        # simple alignment by characters; fallback to '?' when lengths mismatch
        i = 0
        j = 0
        while i < len(norm):
            ch = norm[i]
            if _is_kanji(ch):
                # consume at least one kana from hira as ruby
                if j < len(hira):
                    ruby = hira[j]
                    j += 1
                else:
                    ruby = "?"
                segments.append({"text": ch, "ruby": ruby})
                i += 1
            else:
                # group consecutive non-kanji
                start = i
                while i < len(norm) and not _is_kanji(norm[i]):
                    i += 1
                span = norm[start:i]
                segments.append({"text": span, "ruby": None})
        # collapse adjacent non-ruby spans
        collapsed: List[Dict[str, str | None]] = []
        for seg in segments:
            if collapsed and seg.get("ruby") is None and collapsed[-1].get("ruby") is None:
                collapsed[-1]["text"] = str(collapsed[-1]["text"]) + str(seg["text"])  # type: ignore[index]
            else:
                collapsed.append(seg)
        segments = collapsed
    else:
        for ch in norm:
            if _is_kanji(ch):
                segments.append({"text": ch, "ruby": "?"})
            else:
                segments.append({"text": ch, "ruby": None})
        # Collapse consecutive non-kanji segments into larger spans to reduce segment count
        collapsed: List[Dict[str, str | None]] = []
        for seg in segments:
            if collapsed and (seg.get("ruby") is None) and (collapsed[-1].get("ruby") is None):
                collapsed[-1]["text"] = str(collapsed[-1]["text"]) + str(seg["text"])  # type: ignore[index]
            else:
                collapsed.append(seg)
        segments = collapsed

    return {
        "kanji": norm,
        "romaji": " ".join(norm.split()),  # placeholder normalization
        "furigana": segments,
        "translation": translation or "(pending translation)"
    }


def dedupe_sentences_jp(text: str) -> str:
    """Remove immediate duplicate sentences split by '。' while preserving order.

    Very naive heuristic suitable for fallback content where exact alignment isn't critical.
    """
    norm = normalize_jp_text(text or "")
    if not norm:
        return norm
    parts = [p for p in re.split("。", norm) if p is not None]
    seen: Set[str] = set()
    out: list[str] = []
    for p in parts:
        s = p.strip()
        if not s:
            continue
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
    return "。".join(out) + ("。" if out else "")
