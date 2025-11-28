#!/usr/bin/env python
"""
repair_croatian_graph.py

Script to repair the Croatian graph that has NetworkX compatibility issues.
This script will try to fix the graph and save it in a compatible format.
"""

import os
import pickle
import logging
import networkx as nx
from typing import Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CROATIAN_GRAPH_PATH = 'graph_models/G_synonyms_croatian.pickle'
BACKUP_PATH = 'graph_models/G_synonyms_croatian_backup_repaired.pickle'

def repair_croatian_graph():
    """Attempt to repair the Croatian graph with compatibility issues."""
    
    if not os.path.exists(CROATIAN_GRAPH_PATH):
        logger.error(f"Croatian graph file not found: {CROATIAN_GRAPH_PATH}")
        return False
    
    try:
        # Try to load the graph directly first
        with open(CROATIAN_GRAPH_PATH, 'rb') as f:
            raw_data = pickle.load(f)
        
        logger.info(f"Successfully loaded raw data, type: {type(raw_data)}")
        
        # Check if it's already a proper NetworkX graph
        if hasattr(raw_data, 'nodes') and hasattr(raw_data, 'edges'):
            try:
                # Try to access nodes to test if it works
                num_nodes = raw_data.number_of_nodes()
                num_edges = raw_data.number_of_edges()
                logger.info(f"Graph appears healthy: {num_nodes} nodes, {num_edges} edges")
                return True
            except AttributeError as e:
                logger.warning(f"Graph has attribute issues: {e}")
                # Continue with repair attempt
        
        # Create a backup
        backup_path = BACKUP_PATH
        with open(backup_path, 'wb') as f:
            pickle.dump(raw_data, f)
        logger.info(f"Created backup at: {backup_path}")
        
        # Create a new graph and manually copy data
        new_graph = nx.Graph()
        
        # If the raw data has _node or _adj attributes, try to access them
        if hasattr(raw_data, '_node'):
            logger.info("Found _node attribute, copying nodes...")
            for node_id, node_data in raw_data._node.items():
                new_graph.add_node(node_id, **node_data)
            logger.info(f"Copied {new_graph.number_of_nodes()} nodes")
        
        # Try to copy edges
        if hasattr(raw_data, '_adj'):
            logger.info("Found _adj attribute, copying edges...")
            edge_count = 0
            for u, neighbors in raw_data._adj.items():
                for v, edge_data in neighbors.items():
                    if u != v:  # Skip self-loops
                        new_graph.add_edge(u, v, **edge_data)
                        edge_count += 1
            logger.info(f"Copied {edge_count} edges")
        elif hasattr(raw_data, '_succ'):
            logger.info("Found _succ attribute, copying edges...")
            edge_count = 0
            for u, neighbors in raw_data._succ.items():
                for v, edge_data in neighbors.items():
                    if u != v:  # Skip self-loops
                        new_graph.add_edge(u, v, **edge_data)
                        edge_count += 1
            logger.info(f"Copied {edge_count} edges")
        
        # Save the repaired graph
        with open(CROATIAN_GRAPH_PATH, 'wb') as f:
            pickle.dump(new_graph, f)
        
        logger.info(f"Successfully repaired and saved Croatian graph with {new_graph.number_of_nodes()} nodes and {new_graph.number_of_edges()} edges")
        return True
        
    except Exception as e:
        logger.error(f"Error repairing Croatian graph: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_repaired_graph():
    """Verify that the repaired graph can be loaded properly."""
    try:
        # Try to load using the Croatian helper
        from croatian_helper import load_croatian_graph
        G = load_croatian_graph()
        
        if G:
            logger.info(f"✅ Verification successful: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
            
            # Show a few sample nodes
            sample_nodes = list(G.nodes())[:5]
            logger.info(f"Sample nodes: {sample_nodes}")
            
            return True
        else:
            logger.error("❌ Verification failed: Could not load graph")
            return False
            
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        return False

def main():
    """Main function to repair the Croatian graph."""
    print("🔧 Croatian Graph Repair Tool")
    print("=" * 40)
    
    print("\n🔍 Attempting to repair Croatian graph...")
    if repair_croatian_graph():
        print("✅ Graph repair completed successfully!")
        
        print("\n🧪 Verifying repaired graph...")
        if verify_repaired_graph():
            print("✅ Graph verification successful!")
            print("\n💡 The Croatian graph has been repaired and should now work properly.")
        else:
            print("❌ Graph verification failed!")
    else:
        print("❌ Graph repair failed!")

if __name__ == "__main__":
    main() 