# Canonical Orthography Schema (Neo4j)

This project standardizes Japanese word orthography/readings to avoid ambiguity and to support non-kanji surface forms.

Canonical Word properties
- standard_orthography: canonical surface form (previously `kanji`).
- reading_hiragana: normalized hiragana reading.
- reading_katakana: normalized katakana reading (fallback from VDRJ when available).
- romaji: transliteration.

Notes
- Legacy fields `kanji`, `hiragana`, `katakana`, and `reading` are removed after migration.
- APIs still return fields named `kanji` and `hiragana`, but values are sourced from canonical properties to preserve compatibility.

Migration steps
1) Populate canonical fields and create indexes
   - Run: `python resources/migrate_orthography_properties.py`
   - Creates indexes on `(w.standard_orthography)`, `(w.reading_hiragana)`, `(w.reading_katakana)`, and `(w.standard_orthography, w.reading_hiragana)`.

2) Update code to use canonical fields
   - Matching: prefer `coalesce(w.standard_orthography, w.kanji)` and `coalesce(w.reading_hiragana, w.hiragana)` during transition.
   - Writes: set `standard_orthography`/`reading_hiragana` instead of legacy fields.

3) Cleanup legacy fields and indexes
   - Apply: `backend/migrations/2025-09-11_cleanup_orthography_schema.cypher` (drop legacy indexes/constraints, remove legacy properties, set canonical constraints).

4) Fulltext index (safe creator)
   - Run: `python resources/setup_fulltext_indexes.py`
   - Creates `word_search` (FULLTEXT) on `[standard_orthography, reading_hiragana, translation, pos_primary]` using Neo4j 5 schema form when available; falls back to procedures if installed; otherwise skips.

Query tips
- Lookup by surface form:
  `MATCH (w:Word) WHERE w.standard_orthography = $text RETURN w`
- Lookup by reading:
  `MATCH (w:Word) WHERE w.reading_hiragana = $hira RETURN w`

