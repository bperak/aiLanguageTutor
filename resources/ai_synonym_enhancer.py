#!/usr/bin/env python
"""AI-powered synonym enhancement using Gemini or OpenAI APIs"""
import os
import json
import time
from pathlib import Path
from neo4j import GraphDatabase  # type: ignore
from dotenv import load_dotenv
try:
    import google.generativeai as genai  # type: ignore
except ImportError:
    genai = None

try:
    from openai import OpenAI  # type: ignore
except ImportError:
    OpenAI = None

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# API configurations
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini")  # 'gemini' or 'openai'

# Neo4j connection
URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
if URI.startswith("neo4j://neo4j:"):
    URI = URI.replace("neo4j://neo4j:", "bolt://localhost:")
elif URI.startswith("neo4j://"):
    URI = URI.replace("neo4j://", "bolt://")
USER = os.getenv("NEO4J_USER", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD")
AUTH = (USER, PASSWORD)

# Simple hiragana to romaji conversion mapping
HIRAGANA_TO_ROMAJI = {
    'あ': 'a', 'い': 'i', 'う': 'u', 'え': 'e', 'お': 'o',
    'か': 'ka', 'き': 'ki', 'く': 'ku', 'け': 'ke', 'こ': 'ko',
    'が': 'ga', 'ぎ': 'gi', 'ぐ': 'gu', 'げ': 'ge', 'ご': 'go',
    'さ': 'sa', 'し': 'shi', 'す': 'su', 'せ': 'se', 'そ': 'so',
    'ざ': 'za', 'じ': 'ji', 'ず': 'zu', 'ぜ': 'ze', 'ぞ': 'zo',
    'た': 'ta', 'ち': 'chi', 'つ': 'tsu', 'て': 'te', 'と': 'to',
    'だ': 'da', 'ぢ': 'ji', 'づ': 'zu', 'で': 'de', 'ど': 'do',
    'な': 'na', 'に': 'ni', 'ぬ': 'nu', 'ね': 'ne', 'の': 'no',
    'は': 'ha', 'ひ': 'hi', 'ふ': 'fu', 'へ': 'he', 'ほ': 'ho',
    'ば': 'ba', 'び': 'bi', 'ぶ': 'bu', 'べ': 'be', 'ぼ': 'bo',
    'ぱ': 'pa', 'ぴ': 'pi', 'ぷ': 'pu', 'ぺ': 'pe', 'ぽ': 'po',
    'ま': 'ma', 'み': 'mi', 'む': 'mu', 'め': 'me', 'も': 'mo',
    'や': 'ya', 'ゆ': 'yu', 'よ': 'yo',
    'ら': 'ra', 'り': 'ri', 'る': 'ru', 'れ': 're', 'ろ': 'ro',
    'わ': 'wa', 'を': 'wo', 'ん': 'n',
    'ー': '', 'っ': '',  # Long vowel and small tsu
    'ゃ': 'ya', 'ゅ': 'yu', 'ょ': 'yo',
    'ぁ': 'a', 'ぃ': 'i', 'ぅ': 'u', 'ぇ': 'e', 'ぉ': 'o'
}

def hiragana_to_romaji(hiragana_text):
    """Simple hiragana to romaji conversion"""
    if not hiragana_text:
        return hiragana_text
    
    romaji = ""
    i = 0
    while i < len(hiragana_text):
        char = hiragana_text[i]
        
        # Handle small tsu (っ) - doubles next consonant
        if char == 'っ' and i + 1 < len(hiragana_text):
            next_char = hiragana_text[i + 1]
            if next_char in HIRAGANA_TO_ROMAJI:
                next_romaji = HIRAGANA_TO_ROMAJI[next_char]
                if next_romaji and next_romaji[0] not in 'aeiou':
                    romaji += next_romaji[0]  # Double the consonant
            i += 1
            continue
        
        # Handle long vowel mark (ー)
        if char == 'ー':
            if romaji and romaji[-1] in 'aeiou':
                romaji += romaji[-1]  # Repeat last vowel
            i += 1
            continue
        
        # Regular conversion
        if char in HIRAGANA_TO_ROMAJI:
            romaji += HIRAGANA_TO_ROMAJI[char]
        else:
            romaji += char  # Keep unknown characters as-is
        
        i += 1
    
    return romaji

driver = GraphDatabase.driver(URI, auth=AUTH)

class AISynonymEnhancer:
    def __init__(self, provider="gemini"):
        self.provider = provider
        
        if provider == "gemini" and GEMINI_API_KEY:
            genai.configure(api_key=GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
        elif provider == "openai" and OPENAI_API_KEY:
            self.client = OpenAI(api_key=OPENAI_API_KEY)
        else:
            raise ValueError(f"API key not found for {provider}. Check your .env file.")
    
    def generate_synonyms_prompt(self, word, reading=None, pos=None, translation=None, existing_synonyms=None):
        """Create a prompt for generating Japanese synonyms with rich semantic structure"""
        existing_info = ""
        if existing_synonyms:
            existing_info = f"""
EXISTING SYNONYMS (do NOT repeat these):
{chr(10).join([f"- {syn['synonym']} ({syn['reading']}) = {syn['translation']} [strength: {syn['strength']:.2f}]" for syn in existing_synonyms[:10]])}
"""
        
        prompt = f"""You are a Japanese linguistics expert. For the Japanese word:

Word: {word}
Reading: {reading or 'unknown'}
Part of Speech: {pos or 'unknown'}
Translation: {translation or 'unknown'}{existing_info}

Please provide Japanese synonyms with comprehensive semantic information for each:

Return ONLY a valid JSON array like this:
[
  {{
    "synonym": "愛情",
    "reading": "あいじょう",
    "translation": "affection",
    "pos": "名詞",
    "strength": 0.85,
    "explanation": "Both express love, but 愛情 is more emotional",
    "mutual_sense": "感情",
    "mutual_sense_hiragana": "かんじょう",
    "mutual_sense_translation": "emotion",
    "synonymy_domain": "心理",
    "synonymy_domain_hiragana": "しんり", 
    "synonymy_domain_translation": "psychology",
    "relation_type": "NEAR_SYNONYM"
  }}
]

Required fields for each synonym:
- synonym: Japanese word (kanji/hiragana)
- reading: hiragana reading
- translation: English translation of the synonym
- pos: part of speech (名詞, 動詞, 形容詞, etc.)
- strength: 0.1-1.0 (semantic similarity)
- explanation: why they are synonymous
- mutual_sense: shared semantic concept (in Japanese)
- mutual_sense_hiragana: hiragana reading of mutual_sense
- mutual_sense_translation: English translation of mutual_sense
- synonymy_domain: semantic domain/category (in Japanese)
- synonymy_domain_hiragana: hiragana reading of domain
- synonymy_domain_translation: English translation of domain
- relation_type: SYNONYM, NEAR_SYNONYM, or RELATED

IMPORTANT GUIDELINES:
- Focus on SIMPLE, COMMON synonyms appropriate for Level 1 learners
- Avoid advanced, literary, or specialized vocabulary
- Prefer everyday words over formal/academic terms
- The original word is Level 1, so synonyms should be similar difficulty

IMPORTANT: 
- Only suggest NEW synonyms that are NOT in the existing list above
- Only include real Japanese words that actually exist
- Limit to 2-3 NEW synonyms maximum for quality
- If no good new synonyms exist, return an empty array []"""
        
        return prompt
    
    def get_ai_synonyms(self, word, reading=None, pos=None, translation=None, existing_synonyms=None):
        """Get synonyms using AI API"""
        prompt = self.generate_synonyms_prompt(word, reading, pos, translation, existing_synonyms)
        
        try:
            if self.provider == "gemini":
                response = self.model.generate_content(prompt)
                content = response.text
            elif self.provider == "openai":
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3
                )
                content = response.choices[0].message.content
            
            # Parse JSON response
            # Clean up potential markdown formatting
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            synonyms = json.loads(content.strip())
            return synonyms if isinstance(synonyms, list) else []
            
        except Exception as e:
            print(f"Error getting AI synonyms for '{word}': {e}")
            return []

def get_words_needing_synonyms(session, limit=100):
    """Get words that have few or no synonym relationships"""
    result = session.run("""
        MATCH (w:Word)
        WHERE w.source = 'LeeGoi'  // Focus on Lee vocabulary first
        AND w.level_int <= 1  // Level 1 or less (easier words)
        WITH w, COUNT {(w)-[:SYNONYM_OF]-()} as syn_count
        WHERE syn_count < 5  // Words with fewer than 5 synonyms
        RETURN w.lemma as word, w.hiragana as reading, 
               w.pos_primary as pos, w.translation as translation,
               syn_count, w.level_int as level
        ORDER BY syn_count ASC, w.level_int ASC, rand()
        LIMIT $limit
    """, limit=limit)
    
    return [dict(record) for record in result]

def get_existing_synonyms(session, word):
    """Get existing synonyms for a word to show to AI"""
    result = session.run("""
        MATCH (w1:Word {lemma: $word})-[r:SYNONYM_OF]-(w2:Word)
        RETURN w2.lemma as synonym, w2.hiragana as reading, 
               w2.translation as translation, r.synonym_strength as strength
        ORDER BY r.synonym_strength DESC
        LIMIT 15
    """, word=word)
    
    existing = []
    for record in result:
        existing.append({
            'synonym': record['synonym'],
            'reading': record['reading'] or 'unknown',
            'translation': record['translation'] or 'unknown',
            'strength': record['strength'] or 0.5
        })
    
    return existing

def check_synonym_exists(session, word1, word2):
    """Check if a synonym relationship already exists between two words"""
    result = session.run("""
        MATCH (w1:Word {lemma: $word1})-[r:SYNONYM_OF]-(w2:Word {lemma: $word2})
        RETURN count(r) > 0 as exists
    """, word1=word1, word2=word2)
    
    return result.single()['exists']

def store_ai_synonyms(session, word, ai_synonyms):
    """Store AI-generated synonyms in Neo4j, creating missing nodes if needed"""
    if not ai_synonyms:
        return 0, 0
    
    created_relationships = 0
    created_nodes = 0
    missing_synonyms = []
    skipped_duplicates = []
    
    for syn_data in ai_synonyms:
        synonym = syn_data.get('synonym')
        reading = syn_data.get('reading')
        
        if not synonym:
            continue
        
        # Check if this synonym relationship already exists
        if check_synonym_exists(session, word, synonym):
            skipped_duplicates.append(synonym)
            print(f"    ⚠️ Skipping '{synonym}' - relationship already exists")
            continue
            
        try:
            # Convert hiragana to romaji
            romaji = hiragana_to_romaji(reading) if reading else synonym
            
            # Strategy: Create missing synonym nodes automatically with proper structure
            result = session.run("""
                // Ensure both words exist
                MERGE (w1:Word {lemma: $word})
                MERGE (w2:Word {lemma: $synonym})
                ON CREATE SET w2.source = 'AI_Generated',
                              w2.source_id = $synonym,
                              w2.kanji = $synonym,
                              w2.hiragana = $reading,
                              w2.reading = $reading,
                              w2.romaji = $romaji,
                              w2.translation = $translation,
                              w2.lang = 'ja',
                              w2.level = 'AI推定 AI生成語',
                              w2.level_int = 99,  // Mark as unknown/AI-generated level
                              w2.pos = COALESCE($pos, 'AI推定'),
                              w2.pos_detail = 'AI生成語',
                              w2.word_type = 'AI推定',
                              w2.created_at = datetime(),
                              w2.updated_at = datetime(),
                              w2.ai_generated_node = true
                
                // Create relationship if words are different
                WITH w1, w2
                WHERE w1 <> w2
                MERGE (w1)-[r:SYNONYM_OF {source: 'AI_Generated'}]->(w2)
                ON CREATE SET r.ai_provider = $provider,
                              r.weight = $strength,
                              r.synonym_strength = $strength,
                              r.synonymy_explanation = $explanation,
                              r.relation_type = $relation_type,
                              r.mutual_sense = $mutual_sense,
                              r.mutual_sense_hiragana = $mutual_sense_hiragana,
                              r.mutual_sense_translation = $mutual_sense_translation,
                              r.synonymy_domain = $synonymy_domain,
                              r.synonymy_domain_hiragana = $synonymy_domain_hiragana,
                              r.synonymy_domain_translation = $synonymy_domain_translation,
                              r.ai_generated = true,
                              r.created_at = datetime()
                
                RETURN 
                    CASE WHEN w2.created_at = datetime() THEN 1 ELSE 0 END as new_node,
                    count(r) as new_relationship
            """, 
            word=word,
            synonym=synonym,
            reading=reading,
            romaji=romaji,
            translation=syn_data.get('translation', ''),
            pos=syn_data.get('pos', ''),
            provider=AI_PROVIDER,
            strength=syn_data.get('strength', 0.5),
            explanation=syn_data.get('explanation', ''),
            relation_type=syn_data.get('relation_type', 'AI_SYNONYM'),
            mutual_sense=syn_data.get('mutual_sense', ''),
            mutual_sense_hiragana=syn_data.get('mutual_sense_hiragana', ''),
            mutual_sense_translation=syn_data.get('mutual_sense_translation', ''),
            synonymy_domain=syn_data.get('synonymy_domain', ''),
            synonymy_domain_hiragana=syn_data.get('synonymy_domain_hiragana', ''),
            synonymy_domain_translation=syn_data.get('synonymy_domain_translation', '')
            )
            
            stats = result.single()
            if stats:
                created_relationships += stats['new_relationship'] or 0
                created_nodes += stats['new_node'] or 0
            
        except Exception as e:
            print(f"Error storing synonym '{synonym}' for '{word}': {e}")
            missing_synonyms.append({
                'word': word,
                'synonym': synonym,
                'error': str(e)
            })
    
    # Log any issues
    if missing_synonyms:
        print(f"    ⚠️  {len(missing_synonyms)} synonyms had issues:")
        for miss in missing_synonyms[:3]:
            print(f"      - {miss['synonym']}: {miss['error'][:50]}...")
    
    if skipped_duplicates:
        print(f"    ℹ️  Skipped {len(skipped_duplicates)} existing synonyms: {', '.join(skipped_duplicates[:3])}")
    
    return created_relationships, created_nodes

def enhance_synonyms_with_ai(session, enhancer, batch_size=10):
    """Enhance synonym network using AI"""
    print("=" * 60)
    print(f"AI SYNONYM ENHANCEMENT USING {AI_PROVIDER.upper()}")
    print("=" * 60)
    
    # Get words that need more synonyms
    words_to_enhance = get_words_needing_synonyms(session, limit=100)  # Start small
    print(f"Found {len(words_to_enhance)} words needing synonym enhancement")
    
    total_created = 0
    total_nodes_created = 0
    processed = 0
    
    for word_data in words_to_enhance:
        word = word_data['word']
        
        print(f"Processing: {word} ({word_data.get('reading', 'N/A')}) [Level {word_data.get('level', '?')}] - currently has {word_data.get('syn_count', 0)} synonyms")
        
        # Get existing synonyms to show to AI
        existing_synonyms = get_existing_synonyms(session, word)
        if existing_synonyms:
            print(f"  Existing synonyms: {', '.join([s['synonym'] for s in existing_synonyms[:5]])}")
        
        # Get AI synonyms with context of existing ones
        ai_synonyms = enhancer.get_ai_synonyms(
            word=word,
            reading=word_data.get('reading'),
            pos=word_data.get('pos'),
            translation=word_data.get('translation'),
            existing_synonyms=existing_synonyms
        )
        
        if ai_synonyms:
            created_rels, created_nodes = store_ai_synonyms(session, word, ai_synonyms)
            total_created += created_rels
            total_nodes_created += created_nodes
            print(f"  → Added {created_rels} relationships, {created_nodes} new nodes")
            
            # Show what was added
            for syn in ai_synonyms[:3]:  # Show first 3
                print(f"    • {syn.get('synonym')} ({syn.get('strength', 'N/A')}) - {syn.get('explanation', '')[:50]}...")
        else:
            print(f"  → No synonyms generated")
        
        processed += 1
        
        # Rate limiting
        time.sleep(2)  # Be respectful to APIs
        
        if processed % 10 == 0:
            print(f"\nProgress: {processed}/{len(words_to_enhance)} words, {total_created} relationships, {total_nodes_created} new nodes\n")
    
    print(f"\n✓ AI Enhancement complete: {total_created} relationships, {total_nodes_created} new nodes created")
    return total_created, total_nodes_created

def verify_ai_synonyms(session):
    """Verify AI-generated synonyms"""
    print("\n" + "=" * 60)
    print("AI SYNONYM VERIFICATION")
    print("=" * 60)
    
    # Count AI-generated synonyms
    result = session.run("""
        MATCH ()-[r:SYNONYM_OF {source: 'AI_Generated'}]->()
        RETURN count(r) as count
    """)
    
    ai_count = result.single()['count']
    print(f"Total AI-generated synonyms: {ai_count}")
    
    if ai_count > 0:
        # Show samples
        result = session.run("""
            MATCH (w1)-[r:SYNONYM_OF {source: 'AI_Generated'}]->(w2)
            RETURN w1.kanji as word1, w2.kanji as word2,
                   r.weight as strength, r.synonymy_explanation as explanation,
                   r.ai_provider as provider
            ORDER BY r.strength DESC
            LIMIT 10
        """)
        
        print("\nTop AI-generated synonyms by strength:")
        for record in result:
            strength = record['strength'] if record['strength'] else 'N/A'
            explanation = record['explanation'][:60] + "..." if len(record['explanation'] or '') > 60 else record['explanation']
            print(f"  {record['word1']} ↔ {record['word2']} ({strength}) - {explanation}")

def main():
    """Main function to enhance synonyms with AI"""
    
    if not (GEMINI_API_KEY or OPENAI_API_KEY):
        print("ERROR: No AI API key found in .env file")
        print("Add either GEMINI_API_KEY or OPENAI_API_KEY to your .env file")
        print("Also set AI_PROVIDER=gemini or AI_PROVIDER=openai")
        return
    
    try:
        enhancer = AISynonymEnhancer(AI_PROVIDER)
        
        with driver.session() as session:
            total_created = enhance_synonyms_with_ai(session, enhancer)
            verify_ai_synonyms(session)
            
            print(f"\n✅ AI synonym enhancement complete!")
            print(f"Created {total_created} new synonym relationships using {AI_PROVIDER.upper()}")
    
    except Exception as e:
        print(f"Error during AI enhancement: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        driver.close()

if __name__ == "__main__":
    main()
