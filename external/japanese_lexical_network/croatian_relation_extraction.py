#!/usr/bin/env python
"""
Croatian Relation Extraction Module

This module provides functionality to extract and analyze relationships between Croatian words
in the lexical graph. It builds on the AI generation capabilities to create a comprehensive
network of Croatian lexical relations.

Key functionalities:
- Extract semantic relationships (synonyms, antonyms, hypernyms, hyponyms)
- Analyze relationship strength and patterns
- Build relation networks and clusters
- Generate relation statistics and insights
- Support relation-based search and discovery
"""

import logging
import json
from typing import Dict, List, Set, Optional, Any, Tuple
from collections import defaultdict, Counter
import networkx as nx

from croatian_helper import load_croatian_graph, save_croatian_graph, get_croatian_node_info
from croatian_ai_generation import generate_croatian_lexical_relations, add_generated_relations_to_croatian_graph

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CroatianRelationExtractor:
    """
    Croatian Relation Extraction Class
    
    Provides comprehensive functionality for extracting and analyzing 
    relationships between Croatian words in the lexical graph.
    """
    
    def __init__(self, graph: nx.Graph = None):
        """
        Initialize the Croatian relation extractor.
        
        Args:
            graph (nx.Graph): Optional pre-loaded Croatian graph
        """
        self.graph = graph or load_croatian_graph()
        if not self.graph:
            logger.error("Failed to load Croatian graph")
            raise ValueError("Croatian graph not available")
        
        logger.info(f"Croatian relation extractor initialized with {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} edges")
    
    def extract_node_relations(self, node_id: str) -> Dict[str, Any]:
        """
        Extract all relations for a specific Croatian node.
        
        Args:
            node_id (str): The node ID to extract relations for
            
        Returns:
            dict: Comprehensive relation information for the node
        """
        if node_id not in self.graph.nodes():
            logger.warning(f"Node {node_id} not found in Croatian graph")
            return {}
        
        node_info = get_croatian_node_info(self.graph, node_id)
        if not node_info:
            logger.warning(f"Failed to get node info for {node_id}")
            return {}
        
        relations = {
            'node_id': node_id,
            'node_info': node_info,
            'synonyms': [],
            'antonyms': [],
            'hypernyms': [],
            'hyponyms': [],
            'related_terms': [],
            'relation_stats': {
                'total_relations': 0,
                'synonym_count': 0,
                'antonym_count': 0,
                'hypernym_count': 0,
                'hyponym_count': 0,
                'related_count': 0
            }
        }
        
        # Extract direct neighbors and their relations
        for neighbor_id in self.graph.neighbors(node_id):
            edge_data = self.graph[node_id][neighbor_id]
            
            # Extract synonyms
            if 'synonym' in edge_data:
                synonym_info = {
                    'node_id': neighbor_id,
                    'strength': edge_data['synonym'].get('synonym_strength', 0.5),
                    'mutual_sense': edge_data['synonym'].get('mutual_sense', ''),
                    'domain': edge_data['synonym'].get('synonymy_domain', ''),
                    'explanation': edge_data['synonym'].get('synonymy_explanation', '')
                }
                # Add neighbor node info
                neighbor_info = get_croatian_node_info(self.graph, neighbor_id)
                if neighbor_info:
                    synonym_info.update(neighbor_info)
                relations['synonyms'].append(synonym_info)
                relations['relation_stats']['synonym_count'] += 1
            
            # Extract antonyms
            if 'antonym' in edge_data:
                antonym_info = {
                    'node_id': neighbor_id,
                    'strength': edge_data['antonym'].get('antonym_strength', 0.5),
                    'domain': edge_data['antonym'].get('antonymy_domain', ''),
                    'explanation': edge_data['antonym'].get('antonym_explanation', '')
                }
                # Add neighbor node info
                neighbor_info = get_croatian_node_info(self.graph, neighbor_id)
                if neighbor_info:
                    antonym_info.update(neighbor_info)
                relations['antonyms'].append(antonym_info)
                relations['relation_stats']['antonym_count'] += 1
            
            # Extract hypernyms/hyponyms and other relations
            if 'hypernym' in edge_data:
                hypernym_info = {
                    'node_id': neighbor_id,
                    'strength': edge_data['hypernym'].get('strength', 0.5),
                    'domain': edge_data['hypernym'].get('domain', ''),
                    'explanation': edge_data['hypernym'].get('explanation', '')
                }
                neighbor_info = get_croatian_node_info(self.graph, neighbor_id)
                if neighbor_info:
                    hypernym_info.update(neighbor_info)
                relations['hypernyms'].append(hypernym_info)
                relations['relation_stats']['hypernym_count'] += 1
            
            if 'hyponym' in edge_data:
                hyponym_info = {
                    'node_id': neighbor_id,
                    'strength': edge_data['hyponym'].get('strength', 0.5),
                    'domain': edge_data['hyponym'].get('domain', ''),
                    'explanation': edge_data['hyponym'].get('explanation', '')
                }
                neighbor_info = get_croatian_node_info(self.graph, neighbor_id)
                if neighbor_info:
                    hyponym_info.update(neighbor_info)
                relations['hyponyms'].append(hyponym_info)
                relations['relation_stats']['hyponym_count'] += 1
            
            # Extract other related terms
            if not any(rel in edge_data for rel in ['synonym', 'antonym', 'hypernym', 'hyponym']):
                related_info = {
                    'node_id': neighbor_id,
                    'relation_type': 'related',
                    'strength': edge_data.get('weight', 0.3),
                    'edge_data': edge_data
                }
                neighbor_info = get_croatian_node_info(self.graph, neighbor_id)
                if neighbor_info:
                    related_info.update(neighbor_info)
                relations['related_terms'].append(related_info)
                relations['relation_stats']['related_count'] += 1
        
        # Calculate total relations
        relations['relation_stats']['total_relations'] = sum([
            relations['relation_stats']['synonym_count'],
            relations['relation_stats']['antonym_count'],
            relations['relation_stats']['hypernym_count'],
            relations['relation_stats']['hyponym_count'],
            relations['relation_stats']['related_count']
        ])
        
        # Sort relations by strength
        for rel_type in ['synonyms', 'antonyms', 'hypernyms', 'hyponyms', 'related_terms']:
            if relations[rel_type]:
                relations[rel_type].sort(key=lambda x: x.get('strength', 0), reverse=True)
        
        logger.info(f"Extracted {relations['relation_stats']['total_relations']} relations for node {node_id}")
        return relations
    
    def find_relation_patterns(self, pos_filter: str = None, min_relations: int = 2) -> Dict[str, Any]:
        """
        Find patterns in Croatian lexical relations.
        
        Args:
            pos_filter (str): Optional POS filter (e.g., 'NOUN', 'VERB')
            min_relations (int): Minimum number of relations to include a node
            
        Returns:
            dict: Analysis of relation patterns
        """
        patterns = {
            'high_connectivity_nodes': [],
            'pos_distribution': Counter(),
            'relation_type_distribution': Counter(),
            'strength_distribution': {'synonym': [], 'antonym': [], 'hypernym': [], 'hyponym': []},
            'domain_analysis': Counter(),
            'isolated_nodes': [],
            'statistics': {
                'total_nodes': 0,
                'nodes_with_relations': 0,
                'average_relations_per_node': 0.0,
                'max_relations': 0,
                'min_relations': float('inf')
            }
        }
        
        nodes_with_relations = 0
        total_relations = 0
        
        for node_id, node_data in self.graph.nodes(data=True):
            # Apply POS filter if specified
            if pos_filter and node_data.get('UPOS') != pos_filter:
                continue
            
            patterns['statistics']['total_nodes'] += 1
            patterns['pos_distribution'][node_data.get('UPOS', 'Unknown')] += 1
            
            # Count relations for this node
            node_relations = len(list(self.graph.neighbors(node_id)))
            
            if node_relations >= min_relations:
                nodes_with_relations += 1
                total_relations += node_relations
                
                # Track high connectivity nodes
                if node_relations > 10:  # Arbitrary threshold for high connectivity
                    patterns['high_connectivity_nodes'].append({
                        'node_id': node_id,
                        'natuknica': node_data.get('natuknica', ''),
                        'pos': node_data.get('UPOS', ''),
                        'translation': node_data.get('translation', ''),
                        'relation_count': node_relations
                    })
                
                # Analyze relation types and strengths
                for neighbor_id in self.graph.neighbors(node_id):
                    edge_data = self.graph[node_id][neighbor_id]
                    
                    for rel_type in ['synonym', 'antonym', 'hypernym', 'hyponym']:
                        if rel_type in edge_data:
                            patterns['relation_type_distribution'][rel_type] += 1
                            
                            # Track strength distribution
                            strength = edge_data[rel_type].get(f'{rel_type}_strength', edge_data[rel_type].get('strength', 0.5))
                            patterns['strength_distribution'][rel_type].append(strength)
                            
                            # Track domain analysis
                            domain = edge_data[rel_type].get(f'{rel_type}y_domain', edge_data[rel_type].get('domain', ''))
                            if domain:
                                patterns['domain_analysis'][domain] += 1
                
                # Update statistics
                patterns['statistics']['max_relations'] = max(patterns['statistics']['max_relations'], node_relations)
                patterns['statistics']['min_relations'] = min(patterns['statistics']['min_relations'], node_relations)
            
            elif node_relations == 0:
                patterns['isolated_nodes'].append({
                    'node_id': node_id,
                    'natuknica': node_data.get('natuknica', ''),
                    'pos': node_data.get('UPOS', ''),
                    'translation': node_data.get('translation', '')
                })
        
        # Calculate final statistics
        patterns['statistics']['nodes_with_relations'] = nodes_with_relations
        patterns['statistics']['average_relations_per_node'] = total_relations / nodes_with_relations if nodes_with_relations > 0 else 0
        
        # Sort high connectivity nodes by relation count
        patterns['high_connectivity_nodes'].sort(key=lambda x: x['relation_count'], reverse=True)
        
        # Calculate strength averages
        for rel_type, strengths in patterns['strength_distribution'].items():
            if strengths:
                patterns['strength_distribution'][rel_type] = {
                    'count': len(strengths),
                    'average': sum(strengths) / len(strengths),
                    'min': min(strengths),
                    'max': max(strengths)
                }
        
        logger.info(f"Found patterns in {patterns['statistics']['total_nodes']} nodes with {patterns['statistics']['nodes_with_relations']} having relations")
        return patterns
    
    def build_relation_network(self, center_node: str, max_depth: int = 2, min_strength: float = 0.3) -> nx.Graph:
        """
        Build a relation network around a center node.
        
        Args:
            center_node (str): The center node to build network around
            max_depth (int): Maximum depth of relations to include
            min_strength (float): Minimum relation strength to include
            
        Returns:
            nx.Graph: Subgraph containing the relation network
        """
        if center_node not in self.graph.nodes():
            logger.warning(f"Center node {center_node} not found in graph")
            return nx.Graph()
        
        # Use BFS to build network
        visited = set()
        queue = [(center_node, 0)]  # (node_id, depth)
        network_nodes = set()
        
        while queue:
            current_node, depth = queue.pop(0)
            
            if current_node in visited or depth > max_depth:
                continue
            
            visited.add(current_node)
            network_nodes.add(current_node)
            
            # Add neighbors if within depth limit
            if depth < max_depth:
                for neighbor in self.graph.neighbors(current_node):
                    if neighbor not in visited:
                        # Check if relation meets minimum strength requirement
                        edge_data = self.graph[current_node][neighbor]
                        max_strength = 0.0
                        
                        for rel_type in ['synonym', 'antonym', 'hypernym', 'hyponym']:
                            if rel_type in edge_data:
                                strength = edge_data[rel_type].get(f'{rel_type}_strength', edge_data[rel_type].get('strength', 0.5))
                                max_strength = max(max_strength, strength)
                        
                        if max_strength >= min_strength:
                            queue.append((neighbor, depth + 1))
        
        # Create subgraph
        relation_network = self.graph.subgraph(network_nodes).copy()
        
        logger.info(f"Built relation network with {relation_network.number_of_nodes()} nodes and {relation_network.number_of_edges()} edges")
        return relation_network
    
    def get_relation_clusters(self, min_cluster_size: int = 3) -> List[List[str]]:
        """
        Find clusters of related Croatian words.
        
        Args:
            min_cluster_size (int): Minimum size of clusters to return
            
        Returns:
            list: List of clusters, each containing related word IDs
        """
        # Use community detection algorithms
        try:
            import networkx.algorithms.community as nx_comm
            
            # Remove isolated nodes for clustering
            connected_graph = self.graph.copy()
            isolated_nodes = [node for node, degree in connected_graph.degree() if degree == 0]
            connected_graph.remove_nodes_from(isolated_nodes)
            
            if connected_graph.number_of_nodes() == 0:
                logger.warning("No connected nodes found for clustering")
                return []
            
            # Find communities using greedy modularity optimization
            communities = nx_comm.greedy_modularity_communities(connected_graph)
            
            # Filter clusters by minimum size
            clusters = [list(community) for community in communities if len(community) >= min_cluster_size]
            
            logger.info(f"Found {len(clusters)} clusters with minimum size {min_cluster_size}")
            return clusters
            
        except ImportError:
            logger.warning("NetworkX community detection not available")
            return []
    
    def generate_relation_report(self, node_id: str = None) -> str:
        """
        Generate a comprehensive relation report.
        
        Args:
            node_id (str): Optional specific node to focus report on
            
        Returns:
            str: Formatted relation report
        """
        if node_id:
            # Single node report
            relations = self.extract_node_relations(node_id)
            if not relations:
                return f"No relations found for node {node_id}"
            
            report = f"Croatian Relation Report for: {node_id}\n"
            report += "=" * 60 + "\n\n"
            
            # Node information
            node_info = relations['node_info']
            report += f"Word: {node_info.get('natuknica', 'N/A')}\n"
            report += f"POS: {node_info.get('pos_readable', 'N/A')}\n"
            report += f"Translation: {node_info.get('translation', 'N/A')}\n\n"
            
            # Relation statistics
            stats = relations['relation_stats']
            report += f"Total Relations: {stats['total_relations']}\n"
            report += f"  Synonyms: {stats['synonym_count']}\n"
            report += f"  Antonyms: {stats['antonym_count']}\n"
            report += f"  Hypernyms: {stats['hypernym_count']}\n"
            report += f"  Hyponyms: {stats['hyponym_count']}\n"
            report += f"  Related: {stats['related_count']}\n\n"
            
            # List top relations
            for rel_type, label in [('synonyms', 'Synonyms'), ('antonyms', 'Antonyms'), 
                                   ('hypernyms', 'Hypernyms'), ('hyponyms', 'Hyponyms')]:
                if relations[rel_type]:
                    report += f"{label}:\n"
                    for i, rel in enumerate(relations[rel_type][:5], 1):  # Top 5
                        report += f"  {i}. {rel.get('natuknica', 'N/A')} ({rel.get('strength', 0):.2f})\n"
                    report += "\n"
            
            return report
        
        else:
            # Global report
            patterns = self.find_relation_patterns()
            
            report = "Croatian Lexical Relations - Global Report\n"
            report += "=" * 60 + "\n\n"
            
            # Statistics
            stats = patterns['statistics']
            report += f"Total Nodes: {stats['total_nodes']}\n"
            report += f"Nodes with Relations: {stats['nodes_with_relations']}\n"
            report += f"Average Relations per Node: {stats['average_relations_per_node']:.2f}\n"
            report += f"Max Relations: {stats['max_relations']}\n"
            report += f"Isolated Nodes: {len(patterns['isolated_nodes'])}\n\n"
            
            # POS Distribution
            report += "POS Distribution:\n"
            for pos, count in patterns['pos_distribution'].most_common(10):
                report += f"  {pos}: {count}\n"
            report += "\n"
            
            # Relation Type Distribution
            report += "Relation Type Distribution:\n"
            for rel_type, count in patterns['relation_type_distribution'].most_common():
                report += f"  {rel_type}: {count}\n"
            report += "\n"
            
            # High Connectivity Nodes
            if patterns['high_connectivity_nodes']:
                report += "High Connectivity Nodes (Top 10):\n"
                for node in patterns['high_connectivity_nodes'][:10]:
                    report += f"  {node['node_id']}: {node['relation_count']} relations\n"
            
            return report

# Convenience functions for easy access
def extract_croatian_relations(node_id: str) -> Dict[str, Any]:
    """Extract relations for a Croatian node."""
    extractor = CroatianRelationExtractor()
    return extractor.extract_node_relations(node_id)

def analyze_croatian_relation_patterns(pos_filter: str = None) -> Dict[str, Any]:
    """Analyze patterns in Croatian relations."""
    extractor = CroatianRelationExtractor()
    return extractor.find_relation_patterns(pos_filter)

def build_croatian_relation_network(center_node: str, max_depth: int = 2) -> nx.Graph:
    """Build a relation network around a Croatian node."""
    extractor = CroatianRelationExtractor()
    return extractor.build_relation_network(center_node, max_depth)

def main():
    """Main function for testing Croatian relation extraction."""
    print("Croatian Relation Extraction - Test Run")
    print("=" * 50)
    
    try:
        # Initialize extractor
        extractor = CroatianRelationExtractor()
        
        # Test relation extraction for a node
        test_node = "ljubav-NOUN"
        if test_node in extractor.graph.nodes():
            print(f"Testing relation extraction for: {test_node}")
            relations = extractor.extract_node_relations(test_node)
            print(f"Found {relations['relation_stats']['total_relations']} relations")
            
            # Generate report
            report = extractor.generate_relation_report(test_node)
            print(report)
        
        # Test pattern analysis
        print("\nAnalyzing relation patterns...")
        patterns = extractor.find_relation_patterns()
        print(f"Analysis complete: {patterns['statistics']['nodes_with_relations']} nodes with relations")
        
    except Exception as e:
        print(f"Error during testing: {e}")
        logger.error(f"Error during testing: {e}")

if __name__ == "__main__":
    main() 