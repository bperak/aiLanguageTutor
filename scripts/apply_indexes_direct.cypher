// ================================================
// Direct Neo4j Index Application Script
// Run this in Neo4j Browser or any Neo4j client
// ================================================

// =============
// NODE INDEXES
// =============

// Primary lookup indexes for Word nodes
CREATE INDEX word_kanji_lookup IF NOT EXISTS FOR (w:Word) ON (w.kanji);
CREATE INDEX word_hiragana_lookup IF NOT EXISTS FOR (w:Word) ON (w.hiragana);
CREATE INDEX word_lemma_lookup IF NOT EXISTS FOR (w:Word) ON (w.lemma);

// Composite indexes for common query patterns
CREATE INDEX word_kanji_difficulty IF NOT EXISTS FOR (w:Word) ON (w.kanji, w.difficulty_numeric);
CREATE INDEX word_kanji_pos IF NOT EXISTS FOR (w:Word) ON (w.kanji, w.pos_primary);
CREATE INDEX word_kanji_etymology IF NOT EXISTS FOR (w:Word) ON (w.kanji, w.etymology);

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

// Composite relationship index
CREATE INDEX synonym_composite_index IF NOT EXISTS FOR ()-[r:SYNONYM_OF]-() ON (r.synonym_strength DESC, r.weight DESC);

// =============
// FULLTEXT INDEXES
// =============

// Fulltext index for Word nodes (multiple properties)
CALL db.index.fulltext.createNodeIndex("word_search", ["Word"], ["kanji", "hiragana", "translation", "pos_primary"]);

// Fulltext index for SemanticDomain nodes
CALL db.index.fulltext.createNodeIndex("domain_search", ["SemanticDomain"], ["name", "translation", "description"]);

// =============
// VERIFICATION
// =============

// Show all indexes
SHOW INDEXES;

// Show index usage statistics
CALL db.indexes();

// =============
// PERFORMANCE TEST
// =============

// Test Depth 1 query performance
PROFILE MATCH (t:Word {kanji: "日本"})
OPTIONAL MATCH (t)-[r:SYNONYM_OF]-(n:Word)
OPTIONAL MATCH (n)-[:BELONGS_TO_DOMAIN]->(d:SemanticDomain)
OPTIONAL MATCH (n)-[:HAS_POS]->(p:POSTag)
WITH t, r, n,
     head(collect(d.name)) AS domain,
     head(collect(p.primary_pos)) AS pos
ORDER BY coalesce(r.synonym_strength, r.weight, 0.0) DESC
RETURN count(n) as neighbor_count
LIMIT 50;

// Test Depth 2 query performance (optimized version)
PROFILE MATCH (center:Word {kanji: "日本"})
MATCH (center)-[:SYNONYM_OF]-(neighbor:Word)
MATCH (neighbor)-[r:SYNONYM_OF]-(other:Word)
WHERE other.kanji <> center.kanji
RETURN count(r) as edge_count
LIMIT 100;
