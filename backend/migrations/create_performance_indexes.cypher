// ================================================
// Neo4j Performance Indexes for AI Language Tutor
// Optimizing lexical graph queries for Depth 1 & 2
// ================================================

// =============
// NODE INDEXES
// =============

// Primary lookup indexes for Word nodes (canonical fields)
CREATE INDEX word_standard_orthography_lookup IF NOT EXISTS FOR (w:Word) ON (w.standard_orthography);
CREATE INDEX word_reading_hiragana_lookup IF NOT EXISTS FOR (w:Word) ON (w.reading_hiragana);
CREATE INDEX word_lemma_lookup IF NOT EXISTS FOR (w:Word) ON (w.lemma);

// Composite indexes for common query patterns
CREATE INDEX word_std_ortho_difficulty IF NOT EXISTS FOR (w:Word) ON (w.standard_orthography, w.difficulty_numeric);
CREATE INDEX word_std_ortho_pos IF NOT EXISTS FOR (w:Word) ON (w.standard_orthography, w.pos_primary);
CREATE INDEX word_std_ortho_etymology IF NOT EXISTS FOR (w:Word) ON (w.standard_orthography, w.etymology);

// Performance indexes for classification queries
CREATE INDEX word_difficulty_numeric_perf IF NOT EXISTS FOR (w:Word) ON (w.difficulty_numeric);
CREATE INDEX word_pos_primary_perf IF NOT EXISTS FOR (w:Word) ON (w.pos_primary);
CREATE INDEX word_etymology_perf IF NOT EXISTS FOR (w:Word) ON (w.etymology);
CREATE INDEX word_jlpt_level_perf IF NOT EXISTS FOR (w:Word) ON (w.jlpt_level);

// =============
// RELATIONSHIP INDEXES
// =============

// Index for SYNONYM_OF relationships with weights
CREATE INDEX synonym_weight_index IF NOT EXISTS FOR ()-[r:SYNONYM_OF]-() ON (r.synonym_strength);
CREATE INDEX synonym_weight_desc_index IF NOT EXISTS FOR ()-[r:SYNONYM_OF]-() ON (r.synonym_strength DESC);
CREATE INDEX synonym_relation_type_index IF NOT EXISTS FOR ()-[r:SYNONYM_OF]-() ON (r.relation_type);

// Index for classification relationships
CREATE INDEX has_difficulty_index IF NOT EXISTS FOR ()-[r:HAS_DIFFICULTY]-() ON (r);
CREATE INDEX has_pos_index IF NOT EXISTS FOR ()-[r:HAS_POS]-() ON (r);
CREATE INDEX has_etymology_index IF NOT EXISTS FOR ()-[r:HAS_ETYMOLOGY]-() ON (r);
CREATE INDEX belongs_to_domain_index IF NOT EXISTS FOR ()-[r:BELONGS_TO_DOMAIN]-() ON (r);

// =============
// COMPOSITE RELATIONSHIP INDEXES
// =============

// Index for SYNONYM_OF with both nodes and weight
CREATE INDEX synonym_composite_index IF NOT EXISTS FOR ()-[r:SYNONYM_OF]-() ON (r.synonym_strength DESC, r.weight DESC);

// =============
// FULLTEXT INDEXES (for advanced search)
// =============

// Fulltext index for Word nodes (canonical properties)
CALL db.index.fulltext.createNodeIndex("word_search", ["Word"], ["standard_orthography", "reading_hiragana", "translation", "pos_primary"]);

// Fulltext index for SemanticDomain nodes
CALL db.index.fulltext.createNodeIndex("domain_search", ["SemanticDomain"], ["name", "translation", "description"]);

// =============
// STATISTICS AND MONITORING
// =============

// Show current indexes
SHOW INDEXES;

// Show index usage statistics
CALL db.indexes();

// =============
// QUERY OPTIMIZATION HINTS
// =============

// For the depth=2 query, use this optimized pattern instead of cartesian product:
/*
OPTIONAL MATCH (w1:Word {kanji: $center})-[r1:SYNONYM_OF]-(w2:Word)
OPTIONAL MATCH (w2:Word)-[r2:SYNONYM_OF]-(w3:Word)
WHERE w3.kanji IN $neighbor_ids AND w3.kanji <> w1.kanji
RETURN w2.kanji AS source, w3.kanji AS target, 
       coalesce(r2.synonym_strength, r2.weight, 1.0) AS weight,
       coalesce(r2.relation_type, 'synonym') AS relation_type
*/

// =============
// INDEX MAINTENANCE
// =============

// These indexes should be created after data import
// Monitor index usage with:
// CALL db.indexes() YIELD name, state, populationPercent
// WHERE state = 'ONLINE' AND populationPercent = 100
// RETURN name, state, populationPercent;

// =============
// EXPECTED PERFORMANCE IMPROVEMENTS
// =============

// Depth 1 queries: Should improve from ~100-500ms to ~10-50ms
// Depth 2 queries: Should improve from ~2-10s to ~100-500ms
// Node lookup: Should improve from ~50-200ms to ~5-20ms
// Relationship traversal: Should improve from ~200-1000ms to ~20-100ms
