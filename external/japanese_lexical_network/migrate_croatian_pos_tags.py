#!/usr/bin/env python
"""
migrate_croatian_pos_tags.py

Migration script to convert Croatian nodes from Croatian-specific POS tags 
(like "im", "gl", "pr") to Universal POS tags (like "NOUN", "VERB", "ADJ").

This ensures consistency in the Croatian lexical graph.
"""

import os
import pickle
import logging
import networkx as nx
from typing import Dict, List, Optional, Tuple

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Croatian POS tag mappings (old format -> Universal POS)
CROATIAN_TO_UNIVERSAL_POS = {
    'im': 'NOUN',          # imenica (noun)
    'gl': 'VERB',          # glagol (verb)
    'pr': 'ADJ',           # pridjev (adjective)
    'pril': 'ADV',         # prilog (adverb)
    'zamj': 'PRON',        # zamjenica (pronoun)
    'prijedl': 'ADP',      # prijedlog (preposition)
    'vezn': 'CCONJ',       # veznik (conjunction)
    'broj': 'NUM',         # broj (numeral)
    'čest': 'PART',        # čestica (particle)
    'uzv': 'INTJ',         # uzvik (interjection)
    'det': 'DET',          # determinanta (determiner)
    'sconj': 'SCONJ',      # podređeni veznik (subordinating conjunction)
    'punct': 'PUNCT',      # interpunkcija (punctuation)
    'x': 'X',              # ostalo (other)
}

CROATIAN_GRAPH_PATH = 'graph_models/G_synonyms_croatian.pickle'

def load_croatian_graph() -> Optional[nx.Graph]:
    """Load the Croatian lexical graph from pickle file."""
    try:
        if not os.path.exists(CROATIAN_GRAPH_PATH):
            logger.error(f"Croatian graph file not found: {CROATIAN_GRAPH_PATH}")
            return None
            
        with open(CROATIAN_GRAPH_PATH, 'rb') as f:
            G = pickle.load(f)
        
        logger.info(f"Loaded Croatian graph with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
        return G
    except Exception as e:
        logger.error(f"Error loading Croatian graph: {e}")
        return None

def save_croatian_graph(G: nx.Graph) -> bool:
    """Save the Croatian lexical graph to pickle file."""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(CROATIAN_GRAPH_PATH), exist_ok=True)
        
        with open(CROATIAN_GRAPH_PATH, 'wb') as f:
            pickle.dump(G, f)
        
        logger.info(f"Saved Croatian graph with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
        return True
    except Exception as e:
        logger.error(f"Error saving Croatian graph: {e}")
        return False

def migrate_node_id(node_id: str) -> str:
    """
    Convert a node ID from Croatian POS format to Universal POS format.
    
    Args:
        node_id (str): Original node ID (e.g., "naočale-im")
        
    Returns:
        str: New node ID with Universal POS (e.g., "naočale-NOUN")
    """
    if '-' not in node_id:
        return node_id
    
    parts = node_id.split('-')
    if len(parts) != 2:
        return node_id
    
    word, pos = parts
    
    # Convert Croatian POS to Universal POS
    universal_pos = CROATIAN_TO_UNIVERSAL_POS.get(pos.lower(), pos)
    
    # If it's already a Universal POS tag, keep it as is
    if pos.upper() in ['NOUN', 'VERB', 'ADJ', 'ADV', 'PRON', 'ADP', 'CCONJ', 'SCONJ', 'NUM', 'PART', 'INTJ', 'DET', 'PUNCT', 'X']:
        return node_id
    
    new_node_id = f"{word}-{universal_pos}"
    return new_node_id

def migrate_croatian_pos_tags(dry_run: bool = False) -> Dict[str, int]:
    """
    Migrate Croatian POS tags from Croatian-specific to Universal format.
    
    Args:
        dry_run (bool): If True, only report what would be changed without making changes
        
    Returns:
        dict: Statistics about the migration
    """
    stats = {
        'total_nodes': 0,
        'nodes_migrated': 0,
        'edges_updated': 0,
        'pos_attributes_updated': 0,
        'errors': 0
    }
    
    # Load the Croatian graph
    G = load_croatian_graph()
    if G is None:
        logger.error("Failed to load Croatian graph")
        return stats
    
    stats['total_nodes'] = G.number_of_nodes()
    
    # Create a mapping of old node IDs to new node IDs
    node_mapping = {}
    
    # First pass: identify nodes that need migration
    for node_id in list(G.nodes()):
        new_node_id = migrate_node_id(node_id)
        if new_node_id != node_id:
            node_mapping[node_id] = new_node_id
            logger.info(f"Will migrate: {node_id} -> {new_node_id}")
    
    logger.info(f"Found {len(node_mapping)} nodes that need migration")
    
    if dry_run:
        logger.info("DRY RUN: No changes will be made")
        stats['nodes_migrated'] = len(node_mapping)
        return stats
    
    # Second pass: actually migrate the nodes
    for old_node_id, new_node_id in node_mapping.items():
        try:
            # Get the node's attributes
            node_attrs = G.nodes[old_node_id].copy()
            
            # Update POS attributes to use Universal POS
            if 'pos' in node_attrs:
                old_pos = node_attrs['pos']
                if old_pos.lower() in CROATIAN_TO_UNIVERSAL_POS:
                    node_attrs['pos'] = CROATIAN_TO_UNIVERSAL_POS[old_pos.lower()]
                    stats['pos_attributes_updated'] += 1
            
            # Ensure UPOS is set correctly
            if 'UPOS' not in node_attrs or not node_attrs['UPOS']:
                # Extract POS from new node ID
                if '-' in new_node_id:
                    _, pos_part = new_node_id.split('-', 1)
                    node_attrs['UPOS'] = pos_part
                    stats['pos_attributes_updated'] += 1
            
            # Get all neighbors and their edge data
            neighbors_data = []
            for neighbor in G.neighbors(old_node_id):
                edge_data = G.get_edge_data(old_node_id, neighbor)
                neighbors_data.append((neighbor, edge_data))
            
            # Remove the old node
            G.remove_node(old_node_id)
            
            # Add the new node with updated attributes
            G.add_node(new_node_id, **node_attrs)
            
            # Reconnect all edges with the new node ID
            for neighbor, edge_data in neighbors_data:
                # Check if neighbor also needs migration
                new_neighbor = node_mapping.get(neighbor, neighbor)
                G.add_edge(new_node_id, new_neighbor, **edge_data)
                stats['edges_updated'] += 1
            
            stats['nodes_migrated'] += 1
            logger.info(f"✅ Migrated: {old_node_id} -> {new_node_id}")
            
        except Exception as e:
            logger.error(f"Error migrating node {old_node_id}: {e}")
            stats['errors'] += 1
    
    # Save the updated graph
    if stats['nodes_migrated'] > 0:
        if save_croatian_graph(G):
            logger.info("✅ Successfully saved migrated Croatian graph")
        else:
            logger.error("❌ Failed to save migrated Croatian graph")
            stats['errors'] += 1
    
    return stats

def main():
    """Main function to run the migration."""
    print("🔄 Croatian POS Tag Migration Tool")
    print("=" * 50)
    
    # First, run a dry run to see what would change
    print("\n📊 Running dry run to analyze changes...")
    dry_stats = migrate_croatian_pos_tags(dry_run=True)
    
    print(f"\n📈 Dry Run Results:")
    print(f"  Total nodes: {dry_stats['total_nodes']}")
    print(f"  Nodes to migrate: {dry_stats['nodes_migrated']}")
    
    if dry_stats['nodes_migrated'] == 0:
        print("✅ No nodes need migration. All POS tags are already in Universal format.")
        return
    
    # Ask for confirmation
    print(f"\n⚠️  This will migrate {dry_stats['nodes_migrated']} nodes.")
    response = input("Do you want to proceed? (y/N): ").strip().lower()
    
    if response != 'y':
        print("Migration cancelled.")
        return
    
    # Run the actual migration
    print("\n🔄 Running migration...")
    stats = migrate_croatian_pos_tags(dry_run=False)
    
    print(f"\n📈 Migration Results:")
    print(f"  Total nodes: {stats['total_nodes']}")
    print(f"  Nodes migrated: {stats['nodes_migrated']}")
    print(f"  Edges updated: {stats['edges_updated']}")
    print(f"  POS attributes updated: {stats['pos_attributes_updated']}")
    print(f"  Errors: {stats['errors']}")
    
    if stats['errors'] == 0:
        print("✅ Migration completed successfully!")
    else:
        print(f"⚠️  Migration completed with {stats['errors']} errors.")

if __name__ == "__main__":
    main() 