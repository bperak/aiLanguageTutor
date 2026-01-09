"""
Prompt Engineering for Lexical Relation Generation

Builds POS-aware prompts with few-shot examples for AI relation generation.
"""

import json
from typing import Dict, List

from app.services.lexical_network.few_shot_examples import (
    POS_INSTRUCTIONS,
    SYSTEM_PROMPT,
    get_few_shot_examples,
)
from app.services.lexical_network.relation_types import (
    RELATION_DEFINITIONS,
    get_valid_relations_for_pos,
)


class LexicalPromptBuilder:
    """Builds POS-aware prompts for relation generation."""
    
    PROMPT_VERSION = "1.0.0"
    
    def build_system_prompt(self) -> str:
        """Build system prompt for lexical relation AI."""
        return SYSTEM_PROMPT
    
    def build_relation_prompt(
        self,
        word_data: Dict,
        candidates: List[Dict],
        relation_types: List[str],
        pos: str,
        max_results: int = 20,
    ) -> str:
        """
        Build POS-aware relation finding prompt.
        
        Args:
            word_data: Word data dictionary from Neo4j
            candidates: List of candidate words from embedding similarity
            relation_types: List of relation types to find
            pos: Part of speech
            max_results: Maximum number of relations to return
            
        Returns:
            Formatted prompt string
        """
        # Get POS-specific instructions
        pos_instructions = POS_INSTRUCTIONS.get(pos, "")
        
        # Get valid relations for this POS
        valid_relations = get_valid_relations_for_pos(pos)
        
        # Filter relation_types to only valid ones
        valid_relation_types = [rt for rt in relation_types if rt in valid_relations]
        if not valid_relation_types:
            valid_relation_types = ["SYNONYM"]  # Fallback
        
        # Build relation type descriptions
        relation_desc = self._format_relation_types(valid_relation_types)
        
        # Format candidates
        candidate_str = self._format_candidates(candidates)
        
        # Get few-shot examples
        examples = get_few_shot_examples(pos, valid_relation_types)
        examples_str = self._format_examples(examples)
        
        # Build prompt
        prompt = f"""## TARGET WORD
- 漢字/表記: {word_data.get('standard_orthography', word_data.get('kanji', ''))}
- 読み: {word_data.get('reading_hiragana', '')}
- 翻訳: {word_data.get('translation', '')}
- 品詞: {pos}
- 語種: {word_data.get('etymology', '')}
- 難易度: {word_data.get('difficulty_numeric', '')}

## VALID RELATION TYPES FOR {pos}
{relation_desc}

## POS-SPECIFIC INSTRUCTIONS
{pos_instructions}

## CANDIDATE WORDS (from embedding similarity + database)
{candidate_str}

## FEW-SHOT EXAMPLES
{examples_str}

## OUTPUT FORMAT
Return a JSON array with up to {max_results} relations. Each relation must have this structure:
{{
  "source_word": "{word_data.get('standard_orthography', '')}",
  "target_orthography": "target kanji/kana surface form (REQUIRED)",
  "target_reading": "target reading in hiragana (REQUIRED - use katakana only if hiragana unknown)",
  "relation_type": "one of: {', '.join(valid_relation_types)}",
  "relation_category": "{pos}",
  "weight": 0.85,
  "confidence": 0.9,
  "is_symmetric": true/false,
  "shared_meaning_en": "What they share",
  "distinction_en": "How they differ",
  "usage_context_en": "When each is used",
  "when_prefer_source_en": "When source is better",
  "when_prefer_target_en": "When target is better",
  "register_source": "neutral|colloquial|formal|literary|slang",
  "register_target": "neutral|colloquial|formal|literary|slang",
  "formality_difference": "same|source_higher|target_higher",
  "scale_dimension": "intensity|size|temperature|etc" or null,
  "scale_position_source": 0.3,
  "scale_position_target": 0.7,
  "transitivity_source": "transitive|intransitive|both" or null,
  "transitivity_target": "transitive|intransitive|both" or null,
  "domain_tags": ["domain1", "domain2"],
  "domain_weights": [0.8, 0.5],
  "context_tags": ["context1"],
  "context_weights": [0.9]
}}

IMPORTANT RULES:
1. Only use relation types valid for {pos}: {', '.join(valid_relation_types)}
2. Set is_symmetric based on relation type
3. For asymmetric relations, direction matters (source → target)
4. Include scale_dimension and scale_position only for scalar relations
5. Include transitivity only for verbs
6. All weights must be in [0.0, 1.0]
7. domain_tags/context_tags must align with domain_weights/context_weights
8. **CRITICAL**: Always provide both target_orthography (kanji/kana) AND target_reading (hiragana preferred). The reading helps resolve the word accurately.
9. If you provide kanji/kana, also provide the reading in hiragana (or katakana if unsure).
10. Output ONLY the JSON array, no other text"""
        
        return prompt
    
    def _format_relation_types(self, relation_types: List[str]) -> str:
        """Format relation type descriptions."""
        lines = []
        for rel_type in relation_types:
            meta = RELATION_DEFINITIONS.get(rel_type, {})
            if meta:
                lines.append(
                    f"- {rel_type} ({meta.get('ja', '')}): {meta.get('description', '')} "
                    f"(例: {meta.get('example_ja', '')})"
                )
        return "\n".join(lines) if lines else "No relation types specified"
    
    def _format_candidates(self, candidates: List[Dict]) -> str:
        """Format candidate words for prompt."""
        if not candidates:
            return "No candidate words provided"
        
        lines = []
        for i, cand in enumerate(candidates[:30], 1):  # Limit to 30 candidates
            kanji = cand.get("word", cand.get("kanji", ""))
            reading = cand.get("reading", cand.get("reading_hiragana", ""))
            translation = cand.get("translation", "")
            pos = cand.get("pos", cand.get("pos_primary", ""))
            similarity = cand.get("similarity", cand.get("score", ""))
            
            line = f"{i}. {kanji}"
            if reading:
                line += f" ({reading})"
            if translation:
                line += f" - {translation}"
            if pos:
                line += f" [{pos}]"
            if similarity:
                line += f" (similarity: {similarity:.3f})"
            
            lines.append(line)
        
        return "\n".join(lines)
    
    def _format_examples(self, examples: List[Dict]) -> str:
        """Format few-shot examples as JSON."""
        if not examples:
            return "No examples provided"
        
        # Format as JSON array for clarity
        try:
            return json.dumps(examples, indent=2, ensure_ascii=False)
        except Exception:
            # Fallback to simple text
            return "\n".join([f"- {ex.get('source_word', '')} → {ex.get('target_word', '')} ({ex.get('relation_type', '')})" for ex in examples])
