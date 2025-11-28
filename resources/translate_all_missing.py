#!/usr/bin/env python3
"""
Translate ALL remaining LeeGoi words missing English translations.

Uses the same prompt style as batch_translate_remaining.py but removes the level filter.
Writes: w.translation, w.updated_at, w.ai_translated=true.

Environment:
- OPENAI_API_KEY or GEMINI_API_KEY required
- AI_PROVIDER=openai|gemini (defaults to openai if present)
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase


def load_env():
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
    uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    if uri.startswith('neo4j://neo4j:'):
        uri = uri.replace('neo4j://neo4j:', 'bolt://localhost:')
    elif uri.startswith('neo4j://'):
        uri = uri.replace('neo4j://', 'bolt://')
    user = os.getenv('NEO4J_USERNAME') or os.getenv('NEO4J_USER') or 'neo4j'
    pw = os.getenv('NEO4J_PASSWORD')
    if not pw:
        raise RuntimeError('NEO4J_PASSWORD not set in .env')
    # Decide provider
    provider = os.getenv('AI_PROVIDER')
    if not provider:
        provider = 'openai' if os.getenv('OPENAI_API_KEY') else ('gemini' if os.getenv('GEMINI_API_KEY') else None)
    return uri, user, pw, provider


def fetch_batch(session, batch_size=50):
    query = (
        """
        MATCH (w:Word)
        WHERE w.source = 'LeeGoi'
          AND (w.translation IS NULL OR w.translation = '')
        RETURN coalesce(w.standard_orthography, w.lemma) AS word,
               coalesce(w.reading_hiragana, '') AS reading,
               coalesce(w.pos, w.pos_primary) AS pos,
               coalesce(w.level_int, 0) AS level,
               w.lee_id AS lee_id
        ORDER BY level ASC, word
        LIMIT $batch_size
        """
    )
    return [dict(r) for r in session.run(query, batch_size=batch_size)]


def translate_word(enhancer, provider, word, reading, pos, level):
    prompt = f"""Translate this Japanese word to English. Provide a concise, accurate translation:

Japanese: {word}
Reading: {reading}
Part of Speech: {pos}
Level: {level}

Provide ONLY the English translation (1-4 words maximum):"""
    if provider == 'gemini':
        response = enhancer.model.generate_content(prompt)
        text = (response.text or '').strip()
    else:
        response = enhancer.client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=30,
        )
        text = (response.choices[0].message.content or '').strip()
    # Basic cleanup
    t = text.replace('"', '').replace("'", '').strip()
    if ':' in t:
        t = t.split(':')[-1].strip()
    return t


def update_translation(session, lee_id, translation):
    session.run(
        """
        MATCH (w:Word {source: 'LeeGoi', lee_id: $lee_id})
        SET w.translation = $translation,
            w.updated_at = datetime(),
            w.ai_translated = true
        """,
        lee_id=lee_id, translation=translation,
    )


def main():
    # Make stdout tolerant to non-ASCII consoles (Windows cp1252)
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
    except Exception:
        pass
    uri, user, pw, provider = load_env()
    if not provider:
        print('AI provider/keys not available. Set OPENAI_API_KEY or GEMINI_API_KEY in .env')
        return
    # Lazy import enhancer
    from ai_synonym_enhancer import AISynonymEnhancer
    enhancer = AISynonymEnhancer(provider)

    driver = GraphDatabase.driver(uri, auth=(user, pw))
    total_translated = 0
    batch_size = int(os.getenv('TRANSLATE_BATCH_SIZE', '50'))
    max_batches = os.getenv('TRANSLATE_MAX_BATCHES')
    max_batches = int(max_batches) if max_batches and max_batches.isdigit() else None

    try:
        with driver.session() as session:
            # Initial status
            miss = session.run(
                "MATCH (w:Word) WHERE w.source='LeeGoi' AND (w.translation IS NULL OR w.translation='') RETURN count(w) AS c"
            ).single()['c']
            print(f'Missing translations (LeeGoi): {miss}')

            batches_run = 0
            while True:
                batch = fetch_batch(session, batch_size=batch_size)
                if not batch:
                    break
                print(f'Translating batch of {len(batch)}...')
                for i, item in enumerate(batch, 1):
                    w = item['word'] or ''
                    r = item['reading'] or ''
                    p = item['pos'] or ''
                    lvl = item['level'] or 0
                    lee_id = item['lee_id']
                    try:
                        t = translate_word(enhancer, provider, w, r, p, lvl)
                        if t:
                            update_translation(session, lee_id, t)
                            total_translated += 1
                            print(f'  [{i}/{len(batch)}] {w} -> {t}')
                        else:
                            print(f'  [{i}/{len(batch)}] {w} -> (empty)')
                    except Exception as e:
                        print(f'  [{i}/{len(batch)}] {w} error: {e}')
                    time.sleep(0.4)
                # brief pause between batches
                time.sleep(2)
                batches_run += 1
                if max_batches and batches_run >= max_batches:
                    print(f'Max batches reached ({max_batches}). Stopping.')
                    break

            # Final status
            stats = session.run(
                """
                MATCH (w:Word) WHERE w.source='LeeGoi'
                RETURN count(w) AS total,
                       sum(CASE WHEN w.translation IS NOT NULL AND w.translation<>'' THEN 1 ELSE 0 END) AS with_tr
                """
            ).single()
            print('Done.')
            print(f'Total translated this run: {total_translated}')
            print(f"LeeGoi coverage: {stats['with_tr']} / {stats['total']} ({stats['with_tr']/stats['total']*100:.1f}%)")
    finally:
        driver.close()


if __name__ == '__main__':
    main()
