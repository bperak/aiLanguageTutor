// ===============================================
// Enhanced Neo4j Schema for AI Language Tutor
// Incorporating Lee's 分類語彙表 + NetworkX Synonym Graph
// ===============================================

// =============
// CORE LEXICAL NODES
// =============

// Word nodes from Lee's vocabulary database
CREATE CONSTRAINT word_kanji_unique IF NOT EXISTS FOR (w:Word) REQUIRE w.kanji IS UNIQUE;
CREATE CONSTRAINT word_id_unique IF NOT EXISTS FOR (w:Word) REQUIRE w.lee_id IS UNIQUE;

// Enhanced Word node structure
(:Word {
    // Lee's data
    lee_id: INTEGER,                    // Original No from Lee's data
    kanji: STRING,                      // Standard orthography (kanji or other)
    katakana: STRING,                   // Katakana reading
    hiragana: STRING,                   // Hiragana reading (from NetworkX)
    
    // Difficulty and classification
    difficulty_level: STRING,           // "1.初級前半" to "6.上級後半"
    difficulty_numeric: INTEGER,        // 1-6 for easy querying
    pos_primary: STRING,                // 品詞1 (primary POS)
    pos_detailed: STRING,               // 品詞2 (detailed POS)
    etymology: STRING,                  // 和語/漢語/外来語/混種語
    
    // NetworkX enrichment
    translation: STRING,                // English translation
    jlpt_level: FLOAT,                 // JLPT level (1-5)
    jlpt_jisho_lemma: FLOAT,           // Additional JLPT data
    
    // Metadata
    created_at: DATETIME,
    updated_at: DATETIME,
    source: STRING                      // "lee_vocab" or "networkx_graph"
})

// =============
// SEMANTIC DOMAIN NODES
// =============

// Semantic domains from NetworkX synonym analysis
CREATE CONSTRAINT domain_name_unique IF NOT EXISTS FOR (d:SemanticDomain) REQUIRE d.name IS UNIQUE;

(:SemanticDomain {
    name: STRING,                       // e.g., "物質" (material)
    hiragana: STRING,                   // e.g., "ぶっしつ"
    translation: STRING,                // e.g., "material"
    description: STRING,                // Domain explanation
    word_count: INTEGER,                // Number of words in this domain
    
    created_at: DATETIME,
    updated_at: DATETIME
})

// =============
// DIFFICULTY LEVEL NODES
// =============

CREATE CONSTRAINT difficulty_level_unique IF NOT EXISTS FOR (l:DifficultyLevel) REQUIRE l.level IS UNIQUE;

(:DifficultyLevel {
    level: STRING,                      // "1.初級前半", "2.初級後半", etc.
    numeric_level: INTEGER,             // 1, 2, 3, 4, 5, 6
    stage: STRING,                      // "初級", "中級", "上級"
    substage: STRING,                   // "前半", "後半"
    description: STRING,                // Level description
    word_count: INTEGER,                // Number of words at this level
    
    created_at: DATETIME
})

// =============
// POS (Part of Speech) NODES
// =============

CREATE CONSTRAINT pos_tag_unique IF NOT EXISTS FOR (p:POSTag) REQUIRE p.tag IS UNIQUE;

(:POSTag {
    tag: STRING,                        // e.g., "名詞-普通名詞-一般"
    primary_pos: STRING,                // e.g., "名詞"
    secondary_pos: STRING,              // e.g., "普通名詞"
    tertiary_pos: STRING,               // e.g., "一般"
    description: STRING,                // POS explanation
    word_count: INTEGER,                // Number of words with this POS
    
    created_at: DATETIME
})

// =============
// ETYMOLOGY NODES
// =============

CREATE CONSTRAINT etymology_type_unique IF NOT EXISTS FOR (e:Etymology) REQUIRE e.type IS UNIQUE;

(:Etymology {
    type: STRING,                       // "和語", "漢語", "外来語", "混種語"
    name_en: STRING,                    // "Native Japanese", "Sino-Japanese", etc.
    description: STRING,                // Etymology explanation
    word_count: INTEGER,                // Number of words of this etymology
    
    created_at: DATETIME
})

// =============
// MUTUAL SENSE NODES (from NetworkX)
// =============

CREATE CONSTRAINT mutual_sense_unique IF NOT EXISTS FOR (m:MutualSense) REQUIRE m.sense IS UNIQUE;

(:MutualSense {
    sense: STRING,                      // e.g., "物品"
    hiragana: STRING,                   // e.g., "ぶっぴん"
    translation: STRING,                // e.g., "goods"
    description: STRING,                // Sense explanation
    
    created_at: DATETIME
})

// =============
// RELATIONSHIP DEFINITIONS
// =============

// Basic classification relationships
(:Word)-[:HAS_DIFFICULTY]->(:DifficultyLevel)
(:Word)-[:HAS_POS]->(:POSTag)
(:Word)-[:HAS_ETYMOLOGY]->(:Etymology)
(:Word)-[:BELONGS_TO_DOMAIN]->(:SemanticDomain)

// Synonym relationships from NetworkX
(:Word)-[:SYNONYM_OF {
    synonym_strength: FLOAT,            // 0.0 - 1.0
    relation_type: STRING,              // "TR_MERONYM", etc.
    mutual_sense: STRING,               // Shared meaning
    synonymy_explanation: STRING,       // Why they're synonyms
    weight: FLOAT,                      // Edge weight
    source: STRING                      // "networkx_graph"
}]->(:Word)

// Mutual sense relationships
(:Word)-[:HAS_MUTUAL_SENSE]->(:MutualSense)
(:MutualSense)-[:IN_DOMAIN]->(:SemanticDomain)

// Hierarchical relationships
(:DifficultyLevel)-[:PRECEDES]->(:DifficultyLevel)
(:POSTag)-[:SUBTYPE_OF]->(:POSTag)

// Learning progression relationships
(:Word)-[:PREREQUISITE_FOR]->(:Word)
(:Word)-[:COMMONLY_USED_WITH]->(:Word)

// =============
// INDEXES FOR PERFORMANCE
// =============

// Text search indexes
CREATE INDEX word_kanji_text IF NOT EXISTS FOR (w:Word) ON (w.kanji);
CREATE INDEX word_katakana_text IF NOT EXISTS FOR (w:Word) ON (w.katakana);
CREATE INDEX word_hiragana_text IF NOT EXISTS FOR (w:Word) ON (w.hiragana);
CREATE INDEX word_translation_text IF NOT EXISTS FOR (w:Word) ON (w.translation);

// Classification indexes
CREATE INDEX word_difficulty_numeric IF NOT EXISTS FOR (w:Word) ON (w.difficulty_numeric);
CREATE INDEX word_jlpt_level IF NOT EXISTS FOR (w:Word) ON (w.jlpt_level);
CREATE INDEX word_etymology IF NOT EXISTS FOR (w:Word) ON (w.etymology);

// Relationship indexes
CREATE INDEX synonym_strength IF NOT EXISTS FOR ()-[r:SYNONYM_OF]-() ON (r.synonym_strength);
CREATE INDEX synonym_relation_type IF NOT EXISTS FOR ()-[r:SYNONYM_OF]-() ON (r.relation_type);

// =============
// SAMPLE QUERIES
// =============

// Find all words in a difficulty level
// MATCH (w:Word)-[:HAS_DIFFICULTY]->(d:DifficultyLevel {level: "1.初級前半"})
// RETURN w.kanji, w.katakana, w.translation LIMIT 10;

// Find strong synonyms for a word
// MATCH (w1:Word {kanji: "物"})-[r:SYNONYM_OF]->(w2:Word)
// WHERE r.synonym_strength > 0.8
// RETURN w2.kanji, w2.translation, r.synonym_strength, r.synonymy_explanation
// ORDER BY r.synonym_strength DESC;

// Find words in the same semantic domain
// MATCH (w1:Word {kanji: "物"})-[:BELONGS_TO_DOMAIN]->(d:SemanticDomain)<-[:BELONGS_TO_DOMAIN]-(w2:Word)
// WHERE w1 <> w2
// RETURN w2.kanji, w2.translation, d.name
// LIMIT 10;

// Find etymology distribution
// MATCH (w:Word)-[:HAS_ETYMOLOGY]->(e:Etymology)
// RETURN e.type, COUNT(w) as word_count
// ORDER BY word_count DESC;
