// ================================================
// AI Content Schema Extension for Word Nodes
// Adding AI-generated content properties to Word nodes
// ================================================

// Add AI-generated content properties to existing Word nodes
// These properties will be populated on-demand when content is missing

// AI Content Properties for Word nodes:
// - ai_definitions: LIST<STRING> - Multiple contextual definitions
// - ai_examples: LIST<STRING> - Usage examples with context  
// - ai_cultural_notes: STRING - Cultural context and usage tips
// - ai_kanji_breakdown: STRING - Kanji component analysis
// - ai_grammar_patterns: LIST<STRING> - Related grammar patterns
// - ai_collocations: LIST<STRING> - Common word combinations
// - ai_learning_tips: STRING - Learner-specific advice
// - ai_generated_at: DATETIME - When content was generated
// - ai_model_used: STRING - Which AI model generated it
// - ai_confidence_score: FLOAT - Quality confidence (0-1)
// - ai_content_version: STRING - Version for content updates

// Create indexes for AI content queries
CREATE INDEX word_ai_generated_at IF NOT EXISTS FOR (w:Word) ON (w.ai_generated_at);
CREATE INDEX word_ai_model_used IF NOT EXISTS FOR (w:Word) ON (w.ai_model_used);
CREATE INDEX word_ai_confidence_score IF NOT EXISTS FOR (w:Word) ON (w.ai_confidence_score);

// Create a constraint to ensure ai_content_version is unique per word
CREATE CONSTRAINT word_ai_content_version_unique IF NOT EXISTS FOR (w:Word) REQUIRE (w.standard_orthography, w.ai_content_version) IS UNIQUE;

// Example of how to add AI content to a word node:
/*
MATCH (w:Word {kanji: "水"})
SET w.ai_definitions = ["Clear, colorless liquid essential for life", "One of the five elements in traditional Japanese philosophy"]
SET w.ai_examples = ["水を飲む (mizu wo nomu) - to drink water", "水の音 (mizu no oto) - the sound of water"]
SET w.ai_cultural_notes = "Water is deeply significant in Japanese culture, representing purity and life. It's used in purification rituals and is considered one of the fundamental elements."
SET w.ai_kanji_breakdown = "水 (mizu) - The kanji 水 represents water, with the radical 氵(water radical) indicating its meaning."
SET w.ai_grammar_patterns = ["水が + verb", "水を + verb", "水の + noun"]
SET w.ai_collocations = ["水を飲む", "水の音", "水の色", "水の温度"]
SET w.ai_learning_tips = "Remember that 水 is used in many compound words like 水道 (suidou - water supply) and 水曜日 (suiyoubi - Wednesday)."
SET w.ai_generated_at = datetime()
SET w.ai_model_used = "gemini-2.5-flash"
SET w.ai_confidence_score = 0.95
SET w.ai_content_version = "1.0"
*/

// Query to find words that need AI content generation:
/*
MATCH (w:Word)
WHERE w.ai_generated_at IS NULL
RETURN w.kanji, w.hiragana, w.translation, w.difficulty_numeric
ORDER BY w.difficulty_numeric ASC
LIMIT 100
*/

// Query to find words with low confidence AI content:
/*
MATCH (w:Word)
WHERE w.ai_confidence_score < 0.7
RETURN w.kanji, w.hiragana, w.ai_confidence_score, w.ai_generated_at
ORDER BY w.ai_confidence_score ASC
LIMIT 50
*/
