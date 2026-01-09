# UniDic POS Normalization Implementation

## Overview

This document describes the implementation of UniDic-based POS (Part of Speech) normalization in the Neo4j lexical network. All POS data from various sources (Lee dictionary, Matsushita dictionary, UniDic enrichment, AI gap-fill) is normalized to a canonical UniDic format for consistency and queryability.

## Architecture

### Canonical POS Fields

All Word nodes now have the following canonical POS fields:

- `pos1`: Primary POS category (e.g., "名詞", "動詞", "形容詞", "形状詞")
- `pos2`: Secondary POS category (e.g., "普通名詞", "一般")
- `pos3`: Tertiary POS category (e.g., "人名", "一般")
- `pos4`: Quaternary POS category (e.g., "一般")
- `pos_primary_norm`: Normalized primary POS for app use (same as pos1)
- `pos_source`: Source of canonical POS ("unidic", "matsushita", "lee", "ai")
- `pos_confidence`: Confidence score (0.0-1.0) for POS assignment

### Source Priority

POS sources have the following priority (higher = more authoritative):

1. **unidic** (priority 4) - Direct morphological analysis via fugashi/UniDic
2. **matsushita** (priority 3) - UniDic-style POS from Matsushita dictionary
3. **lee** (priority 2) - Mapped POS from Lee dictionary
4. **ai** (priority 1) - AI gap-fill (lowest priority, only when no authoritative source)

### Preserved Fields

Original source fields are preserved for traceability:

- `pos_primary`: Original primary POS from source
- `pos_detailed`: Original detailed POS (Lee only)
- `unidic_pos1-4`: UniDic morphological analysis fields

## Implementation Components

### 1. POS Mapper (`pos_mapper.py`)

Utility module for mapping and parsing POS tags:

- `parse_unidic_pos()`: Parses UniDic-style POS strings (e.g., "名詞-普通名詞-一般")
- `map_lee_pos_to_unidic()`: Maps Lee POS labels to UniDic format
- `map_matsushita_pos_to_unidic()`: Parses Matsushita POS (already UniDic-style)
- `get_pos_priority()`: Returns priority for POS source
- `should_update_canonical_pos()`: Determines if canonical POS should be updated

### 2. Dictionary Import Service Updates

`dictionary_import_service.py` now:

- Maps Lee POS to canonical UniDic format during import
- Parses Matsushita POS into canonical fields
- Sets `pos_source` and `pos_confidence` appropriately
- Only updates canonical POS if new source has higher priority

### 3. UniDic Enrichment Service Updates

`unidic_enrichment_service.py` now:

- Sets canonical POS from UniDic analysis (pos1-pos4 from unidic_pos1-4)
- Only updates if UniDic has higher priority than existing source
- Sets `pos_source="unidic"` with confidence 1.0

### 4. AI Gap-Fill Service Updates

`ai_gap_fill_service.py` now:

- Only fills POS when no authoritative source exists
- Checks for unidic/matsushita/lee sources before filling
- Maps AI-filled POS to canonical format
- Sets `pos_source="ai"` with confidence from AI response

### 5. Migration Scripts

- `migrate_pos_to_unidic.py`: Python script for detailed migration with priority logic
- `migrate_pos_data.cypher`: Simplified Cypher-based migration (already executed)

### 6. Schema Migrations

- `unidic_pos_schema.cypher`: Creates indexes for canonical POS fields
- `unidic_pos_indexes_complete.cypher`: Creates additional composite indexes

## Indexes

The following indexes are created for efficient querying:

### Individual Field Indexes
- `word_pos1`: Index on pos1
- `word_pos2`: Index on pos2
- `word_pos3`: Index on pos3
- `word_pos4`: Index on pos4
- `word_pos_primary_norm`: Index on pos_primary_norm
- `word_pos_source`: Index on pos_source
- `word_pos_confidence`: Index on pos_confidence

### Composite Indexes
- `word_pos_primary_norm_source`: Composite index for (pos_primary_norm, pos_source)
- `word_pos1_pos2`: Composite index for (pos1, pos2)
- `word_pos1_pos2_pos3`: Composite index for (pos1, pos2, pos3)
- `word_pos_primary_norm_unidic`: Composite index for (pos_primary_norm, unidic_lemma)

## API Endpoints

### Updated Endpoints

- `GET /api/v1/lexical-network/stats`: Uses canonical POS (pos_primary_norm) with fallback
- `GET /api/v1/lexical-network/relations/sample`: Filters by canonical POS
- `GET /api/v1/lexical-network/coverage-report`: Includes canonical POS coverage

### New Endpoints

- `GET /api/v1/lexical-network/pos-coverage`: Returns POS coverage statistics, source distribution, and hierarchy coverage

## Current Status

As of implementation completion:

- **Total words**: 76,187
- **Words with canonical POS**: 25,100 (33%)
- **POS source breakdown**:
  - From UniDic: 8,584 (highest quality - morphological analysis)
  - From Lee: 16,514 (mapped from Lee dictionary)
  - From Matsushita: 0 (not imported yet)
  - From AI: 0

- **POS hierarchy coverage**:
  - pos1: 25,100 words
  - pos2: 8,584 words (UniDic and Matsushita sources)
  - pos3: 8,584 words (UniDic and Matsushita sources)
  - pos4: 8,584 words (UniDic and Matsushita sources)

## Usage Examples

### Query words by canonical POS

```cypher
MATCH (w:Word)
WHERE w.pos_primary_norm = '名詞'
RETURN w.standard_orthography, w.pos1, w.pos2, w.pos_source
LIMIT 10
```

### Find words with UniDic canonical POS

```cypher
MATCH (w:Word)
WHERE w.pos_source = 'unidic'
RETURN w.standard_orthography, w.pos1, w.pos2, w.pos3
LIMIT 10
```

### Query by POS hierarchy

```cypher
MATCH (w:Word)
WHERE w.pos1 = '名詞' AND w.pos2 = '普通名詞'
RETURN w.standard_orthography, w.pos_primary_norm
LIMIT 10
```

## Next Steps

1. **Import Matsushita dictionary**: Will add more canonical POS data
2. **Continue UniDic enrichment**: Process remaining words to increase coverage
3. **Monitor coverage**: Use `/api/v1/lexical-network/pos-coverage` endpoint

## Dependencies

- `fugashi ^1.5.2`: MeCab wrapper for Japanese tokenization
- `unidic ^1.1.0`: UniDic dictionary package

Both are now included in `pyproject.toml` for future deployments.
