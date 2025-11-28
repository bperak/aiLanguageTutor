# Lexical Layer Rethink — Representation, Resources, Exercises

Goal: refine lexical knowledge representation and exercise generation using existing Lee vocabulary + NetworkX synonym data, and extend where it adds clear value.

## Current State (Neo4j)
- Data sources:
  - Lee vocabulary TSV → `:Word` nodes with difficulty, POS, etymology; links to `:DifficultyLevel`, `:POSTag`, `:Etymology`.
  - NetworkX synonym graph → updates/merges `:Word` nodes (hiragana, translation, JLPT) and creates `:SYNONYM_OF` edges with `synonym_strength`, `relation_type`, `mutual_sense`, and `synonymy_domain` (+ `:SemanticDomain`, `:MutualSense`).
- Indexing & constraints: unique on word keys and taxonomy nodes; indexes on word text fields and synonym edge props for performance.

## Gaps & Constraints
- Word-level only: no explicit `:WordSense`, so polysemy is conflated.
- Sparse usage context: few/no example sentences or collocations tied to words/senses.
- Difficulty signals fragmented: Lee level vs JLPT vs real usage; no unified learner‑aware difficulty.
- No explicit “exercise item” entity to persist target/distractors/context and results.

## Proposed Data Model Extensions
- `(:Word)-[:HAS_SENSE]->(:WordSense)`
  - WordSense props: `sense_id`, `definition_ja`, `definition_en`, `pos`, `register`, `domain`, `examples_count`, `source`, `created_at`, `updated_at`.
  - Optional: `(:WordSense)-[:SENSE_SYNONYM_OF {strength, relation_type, mutual_sense}]->(:WordSense)` to move synonymy to the sense level when available.
- `:ExampleSentence`
  - Props: `text_ja`, `romaji`, `translation_en`, `source`, `register`, `topic`, `difficulty_hint`, timestamps.
  - Rels: `(:ExampleSentence)-[:USES_WORD]->(:Word)` and/or `(:ExampleSentence)-[:ILLUSTRATES]->(:WordSense)`.
- Collocations
  - Relationship: `(:Word)-[:COLLOCATES_WITH {strength, pattern?, source}]->(:Word)`.
  - Optional node variant: `(:Collocation {pattern, pos_frame})` linked by `:HAS_COLLOCATION` if we need richer modeling.
- Synset / Grouping
  - Keep current `:MutualSense` and `:SemanticDomain` as first‑class groupings. Optionally add `:Synset` later if sense granularity stabilizes.
- Unified difficulty score
  - Add `Word.learning_difficulty` (or a separate `:LearningProfile` relation later) computed from:
    - Lee `difficulty_numeric` (scaled), JLPT level, degree/centrality from synonym graph, semantic domain rarity, and learner history.
  - Store constituent signals to support transparent reasoning and later reweighting.

## Exercise Types (v1 using current data)
- Synonym recognition (MCQ)
  - Target = `t:Word`. Correct options = neighbors via `:SYNONYM_OF` with highest `synonym_strength`.
  - Distractors = same `:POSTag` and `:SemanticDomain`, low/no `:SYNONYM_OF` link to `t`.
- Domain categorization
  - Given k words, select the odd one out by `:BELONGS_TO_DOMAIN` or assign words to domains.
- Relationship strength ordering
  - Rank candidates by estimated similarity using edge `synonym_strength`.
- Minimal pairs (form confusion)
  - Initially heuristic: select words with small edit distance or same reading but different domain. Persist later as `:FORM_SIMILAR_TO {distance}`.
- Cloze with paraphrase
  - Use paraphrase of `t` (from existing `translation` or `mutual_sense`) and distractors from same POS/domain.

## Exercise Types (v2 after extensions)
- Sense disambiguation
  - Given `:ExampleSentence`, choose the correct `:WordSense` or correct synonym at sense level.
- Collocation fit
  - Fill‑in best collocate for a pattern using `:COLLOCATES_WITH`.
- Definition match
  - Select the sense definition that fits the sentence; distractors from same domain but different mutual sense.

## Query Templates (Cypher sketches)
- Synonym recognition MCQ
```
// Inputs: $kanji, $limit_correct, $limit_distractors
MATCH (t:Word {kanji: $kanji})
OPTIONAL MATCH (t)-[:HAS_POS]->(p:POSTag)
OPTIONAL MATCH (t)-[:BELONGS_TO_DOMAIN]->(d:SemanticDomain)
// correct options
MATCH (t)-[r:SYNONYM_OF]->(c:Word)
WITH t,p,d,c,r
ORDER BY r.synonym_strength DESC
WITH t,p,d,collect({w:c, strength:r.synonym_strength})[0..$limit_correct] AS correct
// distractors from same pos & domain, excluding synonyms and target
MATCH (t)
OPTIONAL MATCH (t)-[:BELONGS_TO_DOMAIN]->(d1:SemanticDomain)
OPTIONAL MATCH (t)-[:HAS_POS]->(p1:POSTag)
MATCH (x:Word)
WHERE x <> t
  AND (p1 IS NULL OR (x)-[:HAS_POS]->(p1))
  AND (d1 IS NULL OR (x)-[:BELONGS_TO_DOMAIN]->(d1))
  AND NOT (t)-[:SYNONYM_OF]-(x)
WITH t, correct, x
RETURN t.kanji AS target,
       [c IN correct | c.w.kanji][0..$limit_correct] AS correct_kanji,
       collect(x.kanji)[0..$limit_distractors] AS distractor_kanji;
```
- Domain odd‑one‑out
```
// Pick 3 from same domain + 1 from different domain
MATCH (d:SemanticDomain)<-[:BELONGS_TO_DOMAIN]-(w:Word)
WITH d, collect(w)[0..50] AS ws
WHERE size(ws) >= 3
WITH d, ws[0..3] AS group3
MATCH (w2:Word)
WHERE NOT (w2)-[:BELONGS_TO_DOMAIN]->(d)
RETURN [w IN group3 | w.kanji] + [w2.kanji] AS options, d.name AS target_domain;
```

## Incremental Plan
- Phase 1 (fast, no new data):
  - Implement MCQ generators using `:SYNONYM_OF`, `:POSTag`, `:SemanticDomain`.
  - Add REST endpoints to serve exercise items and minimal scoring.
  - Persist served items and responses in Postgres for analytics.
- Phase 2 (usage context):
  - Introduce `:ExampleSentence` and basic `:COLLOCATES_WITH` from existing texts or curated seeds.
  - Add domain/pos‑balanced distractor strategies; add minimal pairs store (`:FORM_SIMILAR_TO`).
- Phase 3 (senses):
  - Add `:WordSense`; gradually attach senses to high‑frequency words; migrate synonymy to sense edges where clear.
  - Enable sense‑aware exercises and better disambiguation.
- Phase 4 (personalization):
  - Compute `learning_difficulty`; adapt item selection per user history and strengths/weaknesses.

## Data Sourcing & Augmentation (non‑blocking)
- Use current resources first (Lee + NetworkX). Later consider adding:
  - Example sentences (e.g., curated corpora or validated internal lists).
  - Collocations (extracted heuristically from sentences, then human‑validated).
  - JLPT/frequency refinements from public lists (merge into existing JLPT fields).
- Human‑in‑the‑loop via Validation UI to approve senses, examples, collocations.

## Open Questions
- How granular should `:WordSense` be initially (coarse senses vs dictionary‑level)?
- Do we need a separate `:Synset` beyond `:MutualSense`, or can we extend `:MutualSense` with identifiers and governance?
- Which difficulty weighting feels right for beginner content (e.g., upweight JLPT vs Lee)?
- Minimum set of exercise types to ship v1 for fast feedback?

