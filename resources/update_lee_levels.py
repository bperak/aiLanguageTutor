#!/usr/bin/env python
"""Update :Word nodes with 'level' and 'level_int' from Lee TSV"""
import os
import re
from pathlib import Path
import pandas as pd
from neo4j import GraphDatabase  # type: ignore
from dotenv import load_dotenv

# Load environment variables from project .env
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Neo4j connection setup
URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
if URI.startswith("neo4j://neo4j:"):
    URI = URI.replace("neo4j://neo4j:", "bolt://localhost:")
elif URI.startswith("neo4j://"):
    URI = URI.replace("neo4j://", "bolt://")
USER = os.getenv("NEO4J_USER", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD")
if not PASSWORD:
    raise RuntimeError("NEO4J_PASSWORD not set in .env")

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

# Read Lee TSV file
tsv_path = Path(__file__).parent / 'Lee李  分類語彙表学習者用goi.xlsx - Sheet1.tsv'
df = pd.read_csv(tsv_path, sep='\t')

# Prepare updates
updates = []
for _, row in df.iterrows():
    source_id = str(row['No'])
    level = row.get('Level 語彙の難易度')
    if pd.isna(level):
        continue
    level_str = str(level).strip()
    # Extract leading integer
    m = re.match(r"(\d+)", level_str)
    level_int = int(m.group(1)) if m else None
    updates.append({
        'source_id': source_id,
        'level': level_str,
        'level_int': level_int
    })

batch_size = 1000
updated = 0

# Apply updates in batches
with driver.session() as session:
    for i in range(0, len(updates), batch_size):
        batch = updates[i:i+batch_size]
        session.run(
            """
            UNWIND $batch AS b
            MATCH (w:Word {source:'LeeGoi', source_id: b.source_id})
            SET w.level = b.level,
                w.level_int = b.level_int
            REMOVE w.old_jlpt_level
            """,
            batch=batch
        )
        updated += len(batch)
        print(f"Updated level for {updated:,} Lee words...")

print(f"Done. Total Lee words updated: {updated:,}")
driver.close()
