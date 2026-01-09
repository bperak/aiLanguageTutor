"""
Word Resolution Service

Normalizes and resolves AI-proposed target words to existing Neo4j :Word nodes.
Handles kana/kanji variants, na-adjective normalization, and ranked matching.
"""

import unicodedata
from typing import Dict, List, Literal, Optional, Tuple

import structlog

logger = structlog.get_logger()

# Try to import jaconv for kana conversion
try:
    import jaconv
    JACONV_AVAILABLE = True
except ImportError:
    JACONV_AVAILABLE = False
    logger.warning("jaconv not available - kana conversion will be limited")


ResolutionStatus = Literal["resolved", "ambiguous", "not_found"]


def normalize_orthography(raw: str, expected_pos: Optional[str] = None) -> List[str]:
    """
    Normalize orthography string and generate variants.
    
    Args:
        raw: Raw orthography string from AI
        expected_pos: Expected POS (e.g., "形容動詞" for na-adjectives)
        
    Returns:
        List of normalized orthography variants to try
    """
    if not raw:
        return []
    
    # NFKC normalization (handles fullwidth/halfwidth, punctuation variants)
    normalized = unicodedata.normalize("NFKC", raw.strip())
    
    variants = {normalized}  # Use set to avoid duplicates
    
    # Na-adjective handling: if expected_pos is 形容動詞, try removing trailing な
    if expected_pos == "形容動詞" and normalized.endswith("な") and len(normalized) > 1:
        # Only strip if it's exactly one trailing な (not part of the lemma like なな)
        variants.add(normalized[:-1])
    
    # Remove common punctuation/whitespace artifacts
    cleaned = normalized.replace("・", "").replace(" ", "").replace("　", "")
    if cleaned != normalized:
        variants.add(cleaned)
    
    return list(variants)


def normalize_reading(raw: str) -> List[str]:
    """
    Normalize reading string to hiragana and katakana forms.
    
    Args:
        raw: Raw reading string (may be hiragana, katakana, or mixed)
        
    Returns:
        List of normalized reading variants (hiragana preferred, katakana as fallback)
    """
    if not raw:
        return []
    
    normalized = raw.strip()
    variants = {normalized}
    
    if JACONV_AVAILABLE:
        try:
            # Convert to hiragana (preferred)
            hiragana = jaconv.kata2hira(normalized)
            if hiragana != normalized:
                variants.add(hiragana)
            
            # Convert to katakana (fallback)
            katakana = jaconv.hira2kata(normalized)
            if katakana != normalized:
                variants.add(katakana)
        except Exception as e:
            logger.warning("jaconv conversion failed", reading=raw, error=str(e))
    else:
        # Fallback: simple manual conversion for common cases
        # This is limited but better than nothing
        if any(ord(c) >= 0x30A0 and ord(c) <= 0x30FF for c in normalized):  # Has katakana
            # Simple katakana -> hiragana (basic range)
            hira = ""
            for c in normalized:
                if 0x30A1 <= ord(c) <= 0x30F6:  # Katakana range
                    hira += chr(ord(c) - 0x60)
                else:
                    hira += c
            if hira != normalized:
                variants.add(hira)
    
    return list(variants)


def rank_candidates(
    candidates: List[Dict],
    expected_pos: Optional[List[str]] = None,
) -> Tuple[Optional[Dict], ResolutionStatus, Dict]:
    """
    Rank candidate Word nodes and return the best match.
    
    Ranking priority:
    1. Exact standard_orthography match
    2. Exact kanji match
    3. Exact unidic_lemma / unidic_orth_base match
    4. Exact reading match (reading_hiragana / reading_katakana / unidic_lemma_reading)
    5. Prefer matching POS when equal
    
    Args:
        candidates: List of candidate Word node dicts from Neo4j
        expected_pos: List of allowed POS values (e.g., ["形容詞", "形容動詞"])
        
    Returns:
        Tuple of (best_match_dict | None, status, metadata)
        status: "resolved" | "ambiguous" | "not_found"
        metadata: dict with resolution details
    """
    if not candidates:
        return None, "not_found", {"reason": "no_candidates"}
    
    # Deduplicate identical word+pos combos to avoid spurious ambiguity
    # Use canonical POS (pos_primary field now contains canonical POS from query)
    deduped = []
    seen = set()
    for cand in candidates:
        key = (cand.get("standard_orthography"), cand.get("pos_primary"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(cand)
    
    # Score each candidate
    scored = []
    for cand in deduped:
        score = 0
        match_fields = []
        
        # Priority 1: standard_orthography exact match (score = 1000)
        if cand.get("standard_orthography"):
            score += 1000
            match_fields.append("standard_orthography")
        
        # Priority 2: kanji exact match (score = 900)
        if cand.get("kanji"):
            score += 900
            match_fields.append("kanji")
        
        # Priority 3: unidic_lemma / unidic_orth_base (score = 800)
        if cand.get("unidic_lemma") or cand.get("unidic_orth_base"):
            score += 800
            match_fields.append("unidic_lemma")
        
        # Priority 4: reading match (score = 500)
        if cand.get("reading_hiragana") or cand.get("reading_katakana") or cand.get("unidic_lemma_reading"):
            score += 500
            match_fields.append("reading")
        
        # Priority 5: POS match bonus (score += 100)
        # pos_primary field now contains canonical POS from query
        if expected_pos and cand.get("pos_primary") in expected_pos:
            score += 100
            match_fields.append("pos_match")
        
        scored.append((score, cand, match_fields))
    
    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)
    
    if not scored or scored[0][0] == 0:
        return None, "not_found", {"reason": "no_matches"}
    
    best_score = scored[0][0]
    best_candidates = [c for s, c, _ in scored if s == best_score]
    
    if len(best_candidates) == 1:
        # Unique best match
        best = best_candidates[0]
        return (
            best,
            "resolved",
            {
                "score": best_score,
                "match_fields": scored[0][2],
                "method": "ranked_match",
                "confidence": min(1.0, best_score / 1000.0),  # Normalize to [0, 1]
            },
        )
    else:
        # Ambiguous: multiple candidates with same top score
        # If all have same POS, we could still pick one deterministically (e.g., first by standard_orthography)
        # But for safety, mark as ambiguous
        return (
            None,
            "ambiguous",
            {
                "reason": "multiple_top_matches",
                "count": len(best_candidates),
                "top_score": best_score,
                "samples": [
                    {
                        "word": c.get("standard_orthography") or c.get("kanji", ""),
                        "pos": c.get("pos_primary"),  # Already canonical from query
                    }
                    for c in best_candidates[:3]
                ],
            },
        )


async def resolve_target_word(
    session,
    target_orthography: str,
    target_reading: Optional[str],
    expected_pos: Optional[List[str]] = None,
) -> Tuple[Optional[str], ResolutionStatus, Dict]:
    """
    Resolve AI-proposed target word to an existing Neo4j Word node.
    
    Args:
        session: Neo4j async session
        target_orthography: Orthography string from AI
        target_reading: Reading string from AI (optional)
        expected_pos: List of allowed POS (e.g., ["形容詞", "形容動詞"])
        
    Returns:
        Tuple of (resolved_word_key | None, status, metadata)
        resolved_word_key: standard_orthography of matched Word (or None)
        status: "resolved" | "ambiguous" | "not_found"
        metadata: resolution details
    """
    # Normalize inputs
    orth_variants = normalize_orthography(
        target_orthography,
        expected_pos=expected_pos[0] if expected_pos and len(expected_pos) == 1 else None,
    )
    # Primary reading variants from provided reading
    reading_variants = normalize_reading(target_reading) if target_reading else []
    # Fallback: derive readings from orthography variants when reading is absent
    if not reading_variants:
        derived_readings = set()
        for orth in orth_variants:
            for r in normalize_reading(orth):
                derived_readings.add(r)
        reading_variants = list(derived_readings)
    
    if not orth_variants and not reading_variants:
        return None, "not_found", {"reason": "empty_input"}
    
    # Build Neo4j query to find candidates (property-only to avoid warnings)
    query = """
    MATCH (w:Word)
    WHERE (
        ($orth_forms IS NOT NULL AND w.standard_orthography IN $orth_forms)
        OR ($reading_forms IS NOT NULL AND (
            w.reading_hiragana IN $reading_forms
            OR w.reading_katakana IN $reading_forms
        ))
    )
    AND ($expected_pos IS NULL OR coalesce(w.pos_primary_norm, w.pos1, w.pos_primary) IN $expected_pos)
    RETURN 
        w.standard_orthography AS word_key,
        w.standard_orthography AS standard_orthography,
        w.reading_hiragana AS reading_hiragana,
        w.reading_katakana AS reading_katakana,
        coalesce(w.pos_primary_norm, w.pos1, w.pos_primary) AS pos_primary
    LIMIT 20
    """
    
    # Execute query
    orth_forms_param = orth_variants if orth_variants else None
    reading_forms_param = reading_variants if reading_variants else None
    
    result = await session.run(
        query,
        orth_forms=orth_forms_param,
        reading_forms=reading_forms_param,
        expected_pos=expected_pos,
    )
    
    candidates = [dict(record) for record in await result.data()]
    
    # Rank and select best match
    best, status, metadata = rank_candidates(candidates, expected_pos=expected_pos)
    
    if status == "resolved" and best:
        resolved_key = best.get("word_key") or best.get("standard_orthography")
        return resolved_key, status, metadata
    else:
        return None, status, metadata
