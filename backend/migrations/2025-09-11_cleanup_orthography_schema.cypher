// ================================================
// Cleanup Orthography Schema (canonical fields)
// - Drop legacy indexes/constraints on kanji/hiragana/katakana
// - Remove legacy properties from Word nodes
// - Recreate fulltext index on canonical fields
// - Add unique constraint on standard_orthography (optional but recommended)
// ================================================

// 1) Drop legacy indexes/constraints if present
DROP INDEX word_kanji_lookup IF EXISTS;
DROP INDEX word_hiragana_lookup IF EXISTS;
DROP INDEX word_kanji_text IF EXISTS;
DROP INDEX word_katakana_text IF EXISTS;
DROP INDEX word_kanji_difficulty IF EXISTS;
DROP INDEX word_kanji_pos IF EXISTS;
DROP INDEX word_kanji_etymology IF EXISTS;

// Some environments may have created these with different names; ignore errors if they don't exist
// Keep translation index

// Unique constraint originally on w.kanji
DROP CONSTRAINT word_kanji_unique IF EXISTS;

// AI content version uniqueness based on kanji
DROP CONSTRAINT word_ai_content_version_unique IF EXISTS;

// 2) Create recommended canonical constraints/indexes
// Unique identifier for words by standard_orthography (adjust as needed for your identity model)
CREATE CONSTRAINT word_standard_orthography_unique IF NOT EXISTS FOR (w:Word) REQUIRE w.standard_orthography IS UNIQUE;

// AI content uniqueness on canonical field
CREATE CONSTRAINT word_ai_content_version_unique IF NOT EXISTS FOR (w:Word)
REQUIRE (w.standard_orthography, w.ai_content_version) IS UNIQUE;

// 3) Recreate fulltext index on canonical fields
// Drop fulltext index if present (ignore errors if missing)
CALL db.index.fulltext.drop('word_search');

CALL db.index.fulltext.createNodeIndex(
  'word_search',
  ['Word'],
  ['standard_orthography', 'reading_hiragana', 'translation', 'pos_primary']
);

// 4) Remove legacy properties (after all code has migrated)
// Note: irreversible. Run only after verifying all callers use canonical fields.
MATCH (w:Word) WHERE w.kanji IS NOT NULL REMOVE w.kanji;
MATCH (w:Word) WHERE w.hiragana IS NOT NULL REMOVE w.hiragana;
MATCH (w:Word) WHERE w.katakana IS NOT NULL REMOVE w.katakana;
MATCH (w:Word) WHERE w.reading IS NOT NULL REMOVE w.reading;

// 5) Verify counts (optional; enable as needed)
// MATCH (w:Word) RETURN count(w) as total,
//   sum(CASE WHEN w.standard_orthography IS NOT NULL THEN 1 ELSE 0 END) as with_std,
//   sum(CASE WHEN w.reading_hiragana IS NOT NULL THEN 1 ELSE 0 END) as with_hira;
