#!/usr/bin/env python
"""
batch_translate_croatian.py

Batch translation script for Croatian nodes.
This script searches Croatian nodes in batches of 100, finds nodes without translations,
generates translations using AI, and updates the nodes with the new translations.

Usage:
    python batch_translate_croatian.py [--batch-size 100] [--dry-run] [--max-batches 10]
"""

import argparse
import logging
import time
from typing import List, Dict, Optional, Set
import networkx as nx
from croatian_helper import load_croatian_graph, save_croatian_graph, get_croatian_node_info
from croatian_ai_generation import generate_translation_and_pos, is_available

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def find_nodes_without_translations(G: nx.Graph, batch_size: int = 100, start_idx: int = 0) -> List[str]:
    """
    Find Croatian nodes that don't have translations.
    
    Args:
        G (nx.Graph): Croatian lexical graph
        batch_size (int): Number of nodes to return in this batch
        start_idx (int): Starting index for this batch
        
    Returns:
        List[str]: List of node IDs without translations
    """
    nodes_without_translation = []
    all_nodes = list(G.nodes())
    
    # Calculate the range for this batch
    end_idx = min(start_idx + batch_size, len(all_nodes))
    
    logger.info(f"Checking nodes {start_idx} to {end_idx-1} out of {len(all_nodes)} total nodes")
    
    for i in range(start_idx, end_idx):
        node_id = all_nodes[i]
        attrs = G.nodes[node_id]
        
        # Check if translation is missing or empty
        translation = attrs.get('translation', '').strip()
        if not translation:
            nodes_without_translation.append(node_id)
            logger.debug(f"Node {node_id} has no translation")
    
    logger.info(f"Found {len(nodes_without_translation)} nodes without translations in current batch")
    return nodes_without_translation

def get_total_nodes_without_translations(G: nx.Graph) -> int:
    """
    Count total number of nodes without translations.
    
    Args:
        G (nx.Graph): Croatian lexical graph
        
    Returns:
        int: Total count of nodes without translations
    """
    count = 0
    for node_id, attrs in G.nodes(data=True):
        translation = attrs.get('translation', '').strip()
        if not translation:
            count += 1
    return count

def generate_translations_for_batch(node_ids: List[str], G: nx.Graph, dry_run: bool = False) -> Dict[str, Dict]:
    """
    Generate translations for a batch of nodes.
    
    Args:
        node_ids (List[str]): List of node IDs to generate translations for
        G (nx.Graph): Croatian lexical graph
        dry_run (bool): If True, don't actually update the graph
        
    Returns:
        Dict[str, Dict]: Dictionary mapping node IDs to their generated translations
    """
    translations = {}
    
    for i, node_id in enumerate(node_ids, 1):
        logger.info(f"Processing node {i}/{len(node_ids)}: {node_id}")
        
        try:
            # Get node attributes
            attrs = G.nodes[node_id]
            natuknica = attrs.get('natuknica', '')
            natuknica_norm = attrs.get('natuknica_norm', '')
            pos = attrs.get('pos', '')
            
            # Use the most appropriate word form for translation
            word_to_translate = natuknica if natuknica else natuknica_norm
            if not word_to_translate:
                word_to_translate = node_id.split('-')[0]  # Extract word from node_id
            
            # Generate translation and POS
            context = f"POS: {pos}" if pos else None
            result = generate_translation_and_pos(
                word=word_to_translate,
                natuknica=natuknica,
                context=context
            )
            
            if "error" not in result:
                translations[node_id] = result
                logger.info(f"✅ Generated translation for {node_id}: '{word_to_translate}' -> '{result['translation']}'")
                
                # Update the node in the graph if not dry run
                if not dry_run:
                    G.nodes[node_id]['translation'] = result['translation']
                    
                    # Update POS if we got better information
                    if result.get('pos') and not pos:
                        G.nodes[node_id]['pos'] = result['pos']
                    if result.get('upos') and not attrs.get('UPOS'):
                        G.nodes[node_id]['UPOS'] = result['upos']
                    
                    logger.info(f"✅ Updated node {node_id} with translation")
            else:
                logger.error(f"❌ Failed to generate translation for {node_id}: {result['error']}")
                
        except Exception as e:
            logger.error(f"❌ Error processing node {node_id}: {e}")
            
        # Add a small delay to avoid overwhelming the API
        time.sleep(0.5)
    
    return translations

def main():
    """Main function for batch translation."""
    parser = argparse.ArgumentParser(description='Batch translate Croatian nodes')
    parser.add_argument('--batch-size', type=int, default=100, help='Number of nodes to process per batch')
    parser.add_argument('--dry-run', action='store_true', help='Run without making changes')
    parser.add_argument('--max-batches', type=int, default=10, help='Maximum number of batches to process')
    parser.add_argument('--start-from', type=int, default=0, help='Starting node index')
    
    args = parser.parse_args()
    
    logger.info("🚀 Starting Croatian batch translation script")
    logger.info(f"Settings: batch_size={args.batch_size}, dry_run={args.dry_run}, max_batches={args.max_batches}")
    
    # Check API availability
    if not is_available():
        logger.error("❌ Gemini API not available. Please check your API key configuration.")
        return
    
    logger.info("✅ Gemini API available")
    
    # Load Croatian graph
    G = load_croatian_graph()
    if G is None:
        logger.error("❌ Failed to load Croatian graph")
        return
    
    logger.info(f"✅ Croatian graph loaded: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    
    # Count total nodes without translations
    total_without_translations = get_total_nodes_without_translations(G)
    logger.info(f"📊 Total nodes without translations: {total_without_translations}")
    
    if total_without_translations == 0:
        logger.info("🎉 All nodes already have translations!")
        return
    
    # Process batches
    current_start = args.start_from
    total_processed = 0
    total_translated = 0
    
    for batch_num in range(args.max_batches):
        logger.info(f"\n🔄 Processing batch {batch_num + 1}/{args.max_batches}")
        
        # Find nodes without translations in this batch
        nodes_to_translate = find_nodes_without_translations(G, args.batch_size, current_start)
        
        if not nodes_to_translate:
            logger.info("✅ No more nodes to translate in this batch")
            break
        
        # Generate translations for this batch
        translations = generate_translations_for_batch(nodes_to_translate, G, args.dry_run)
        
        total_processed += len(nodes_to_translate)
        total_translated += len(translations)
        
        logger.info(f"📊 Batch {batch_num + 1} complete: {len(translations)}/{len(nodes_to_translate)} successful")
        
        # Move to next batch
        current_start += args.batch_size
        
        # Save progress periodically
        if not args.dry_run and len(translations) > 0:
            logger.info("💾 Saving progress...")
            if save_croatian_graph(G):
                logger.info("✅ Progress saved successfully")
            else:
                logger.error("❌ Failed to save progress")
    
    # Final summary
    logger.info("\n📋 FINAL SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Total nodes processed: {total_processed}")
    logger.info(f"Total translations generated: {total_translated}")
    logger.info(f"Success rate: {(total_translated/total_processed)*100:.1f}%" if total_processed > 0 else "N/A")
    
    if args.dry_run:
        logger.info("🔍 This was a dry run - no changes were made to the graph")
    else:
        # Final save
        if total_translated > 0:
            logger.info("💾 Performing final save...")
            if save_croatian_graph(G):
                logger.info("✅ Final save successful")
                logger.info(f"📊 Updated graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
            else:
                logger.error("❌ Final save failed")
        else:
            logger.info("ℹ️ No translations generated, nothing to save")
    
    logger.info("🏁 Batch translation complete!")

if __name__ == "__main__":
    main() 