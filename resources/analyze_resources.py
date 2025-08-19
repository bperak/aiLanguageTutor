#!/usr/bin/env python
"""Analyze the structure of Lee TSV and NetworkX pickle files"""

import pickle
import networkx as nx
import pandas as pd
from pathlib import Path

def analyze_lee_tsv():
    """Analyze the Lee TSV file structure"""
    print("=" * 60)
    print("ANALYZING LEE TSV FILE")
    print("=" * 60)
    
    # Read TSV with tab separator
    df = pd.read_csv('Lee李  分類語彙表学習者用goi.xlsx - Sheet1.tsv', sep='\t')
    
    print(f"Total rows: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    print("\nFirst 5 rows:")
    print(df.head())
    
    # Check for unique IDs
    print(f"\nUnique 'No' values: {df['No'].nunique()}")
    print(f"Has duplicates in 'No': {df['No'].duplicated().any()}")
    
    # Check JLPT levels
    if 'Level 語彙の難易度' in df.columns:
        print(f"\nUnique levels: {df['Level 語彙の難易度'].unique()[:10]}")
    
    return df

def analyze_networkx_pickle():
    """Analyze the NetworkX pickle file structure"""
    print("\n" + "=" * 60)
    print("ANALYZING NETWORKX PICKLE FILE")
    print("=" * 60)
    
    with open('G_synonyms_2024_09_18.pickle', 'rb') as f:
        g = pickle.load(f)
    
    print(f"Graph type: {type(g)}")
    print(f"Number of nodes: {g.number_of_nodes()}")
    print(f"Number of edges: {g.number_of_edges()}")
    print(f"Is MultiGraph: {isinstance(g, nx.MultiGraph)}")
    print(f"Is directed: {g.is_directed()}")
    
    # Node attributes
    print("\n--- NODE STRUCTURE ---")
    nodes_with_attrs = list(g.nodes(data=True))[:5]
    for node, attrs in nodes_with_attrs:
        print(f"Node: '{node}' | Attributes: {attrs}")
    
    # Check if nodes have any attributes
    all_node_attrs = set()
    for node, attrs in g.nodes(data=True):
        all_node_attrs.update(attrs.keys())
    print(f"\nAll node attribute keys: {all_node_attrs if all_node_attrs else 'NONE (nodes have no attributes)'}")
    
    # Edge attributes
    print("\n--- EDGE STRUCTURE ---")
    edges_sample = list(g.edges(data=True))[:3]
    for u, v, attrs in edges_sample:
        print(f"Edge: '{u}' -> '{v}'")
        print(f"  Attributes: {attrs}")
    
    # Collect all edge attribute keys
    edge_attr_keys = set()
    for u, v, attrs in g.edges(data=True):
        edge_attr_keys.update(attrs.keys())
    
    print(f"\nAll edge attribute keys: {sorted(edge_attr_keys)}")
    
    # Check if edges have weights
    if 'weight' in edge_attr_keys:
        weights = [attrs.get('weight', 0) for u, v, attrs in g.edges(data=True)]
        print(f"\nWeight range: {min(weights)} to {max(weights)}")
    
    return g

def check_node_correspondence(df, g):
    """Check if Lee words are in the NetworkX graph"""
    print("\n" + "=" * 60)
    print("CHECKING NODE CORRESPONDENCE")
    print("=" * 60)
    
    # Get unique words from Lee TSV
    lee_words = set()
    if 'Standard orthography (kanji or other) 標準的な表記' in df.columns:
        lee_words = set(df['Standard orthography (kanji or other) 標準的な表記'].dropna())
    
    # Get nodes from NetworkX
    nx_nodes = set(g.nodes())
    
    print(f"Unique words in Lee TSV: {len(lee_words)}")
    print(f"Nodes in NetworkX graph: {len(nx_nodes)}")
    
    # Check overlap
    overlap = lee_words & nx_nodes
    print(f"Words in both: {len(overlap)}")
    print(f"Lee words NOT in graph: {len(lee_words - nx_nodes)}")
    print(f"Graph nodes NOT in Lee: {len(nx_nodes - lee_words)}")
    
    print("\nSample Lee words NOT in graph:")
    for word in list(lee_words - nx_nodes)[:10]:
        print(f"  - {word}")
    
    print("\nSample graph nodes NOT in Lee:")
    for word in list(nx_nodes - lee_words)[:10]:
        print(f"  - {word}")
    
    return lee_words, nx_nodes

def propose_migration_strategy(df, g):
    """Propose a migration strategy"""
    print("\n" + "=" * 60)
    print("PROPOSED MIGRATION STRATEGY")
    print("=" * 60)
    
    print("""
PHASE 1: Import all Lee words as :Word nodes
- Use 'No' column as source_id (it's unique)
- Map columns:
  * No -> source_id
  * Standard orthography -> lemma
  * Katakana reading -> reading
  * Level -> old_jlpt_level
  * 品詞1 -> pos
  * 語種 -> word_type (和語/漢語/外来語/混種語)

PHASE 2: Import NetworkX nodes that are NOT in Lee
- These become :Word nodes with source='NetworkX'
- Use the word itself as source_id

PHASE 3: Import synonym relationships
- MultiGraph edges become :SYNONYM_OF relationships
- Preserve ALL edge attributes:
  * synonym_strength -> strength
  * relation_type -> relation_type
  * mutual_sense -> mutual_sense
  * mutual_sense_hiragana -> mutual_sense_hiragana
  * mutual_sense_translation -> mutual_sense_translation
  * synonymy_domain -> synonymy_domain
  * synonymy_domain_hiragana -> synonymy_domain_hiragana
  * synonymy_domain_translation -> synonymy_domain_translation
  * synonymy_explanation -> synonymy_explanation
  * weight -> weight

PHASE 4: Handle multi-edges
- Since it's a MultiGraph, same word pairs can have multiple edges
- Create separate :SYNONYM_OF relationships for each
- Add an edge_id property to distinguish them
""")

if __name__ == "__main__":
    df = analyze_lee_tsv()
    g = analyze_networkx_pickle()
    lee_words, nx_nodes = check_node_correspondence(df, g)
    propose_migration_strategy(df, g)
