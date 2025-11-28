#!/usr/bin/env python
"""
croatian_helper.py

Croatian language helper functions for the lexical graph system.
Provides Croatian-specific functionality similar to the Japanese helpers.

Key functionalities:
- Loading Croatian graph
- Node lookup and information extraction
- Croatian text processing
- Translation services
- Lexical analysis
"""

import os
import pickle
import logging
import networkx as nx
from typing import Dict, List, Optional, Any, Tuple
import config

# Set up logging
logger = logging.getLogger(__name__)

# Croatian-specific constants
CROATIAN_GRAPH_PATH = 'graph_models/G_synonyms_croatian.pickle'

# Croatian POS tag mappings (UPOS to human-readable)
CROATIAN_POS_MAPPING = {
    'NOUN': 'Imenica (Noun)',
    'VERB': 'Glagol (Verb)',
    'ADJ': 'Pridjev (Adjective)',
    'ADV': 'Prilog (Adverb)',
    'PRON': 'Zamjenica (Pronoun)',
    'DET': 'Determinanta (Determiner)',
    'ADP': 'Prijedlog (Preposition)',
    'CCONJ': 'Veznik (Conjunction)',
    'SCONJ': 'Podređeni veznik (Subordinating conjunction)',
    'NUM': 'Broj (Number)',
    'PART': 'Čestica (Particle)',
    'INTJ': 'Uzvik (Interjection)',
    'PUNCT': 'Interpunkcija (Punctuation)',
    'X': 'Ostalo (Other)'
}

def load_croatian_graph() -> Optional[nx.Graph]:
    """
    Load the Croatian lexical graph from pickle file.
    
    Returns:
        nx.Graph: Croatian lexical graph or None if loading fails
    """
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
    """
    Save the Croatian lexical graph to pickle file.
    
    Args:
        G (nx.Graph): Croatian lexical graph to save
        
    Returns:
        bool: True if successful, False otherwise
    """
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

def find_croatian_nodes(G: nx.Graph, term: str, exact: bool = False) -> List[str]:
    """
    Find Croatian nodes matching a search term.
    
    Args:
        G (nx.Graph): Croatian lexical graph
        term (str): Search term
        exact (bool): Whether to do exact matching
        
    Returns:
        List[str]: List of matching node IDs
    """
    if not G:
        return []
    
    matching_nodes = []
    term_lower = term.lower()
    
    for node_id, attrs in G.nodes(data=True):
        # Search in various fields
        natuknica = attrs.get('natuknica', '').lower()
        natuknica_norm = attrs.get('natuknica_norm', '').lower()
        translation = attrs.get('translation', '').lower()
        
        if exact:
            if (term_lower == natuknica or 
                term_lower == natuknica_norm or 
                term_lower == translation or
                term_lower == node_id.lower()):
                matching_nodes.append(node_id)
        else:
            if (term_lower in natuknica or 
                term_lower in natuknica_norm or 
                term_lower in translation or
                term_lower in node_id.lower()):
                matching_nodes.append(node_id)
    
    return matching_nodes

def get_croatian_node_info(G: nx.Graph, node_id: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a Croatian node.
    
    Args:
        G (nx.Graph): Croatian lexical graph
        node_id (str): Node ID to get information for
        
    Returns:
        Dict[str, Any]: Node information or None if not found
    """
    if not G or node_id not in G:
        return None
    
    attrs = G.nodes[node_id]
    
    # Format POS information
    upos = attrs.get('UPOS', '')
    pos_readable = CROATIAN_POS_MAPPING.get(upos, upos)
    
    # Count neighbors/relationships
    neighbors = list(G.neighbors(node_id))
    
    node_info = {
        'id': node_id,
        'natuknica': attrs.get('natuknica', ''),
        'natuknica_norm': attrs.get('natuknica_norm', ''),
        'pos': attrs.get('pos', ''),
        'UPOS': upos,
        'pos_readable': pos_readable,
        'translation': attrs.get('translation', ''),
        'tekst': attrs.get('tekst', ''),
        'language': attrs.get('language', 'croatian'),
        'neighbor_count': len(neighbors),
        'neighbors': neighbors[:10] if neighbors else []  # Limit to first 10
    }
    
    return node_info

def get_croatian_subgraph(G: nx.Graph, source_nodes: List[str], depth: int = 1) -> nx.Graph:
    """
    Extract subgraph around Croatian source nodes.
    
    Args:
        G (nx.Graph): Croatian lexical graph
        source_nodes (List[str]): Source node IDs
        depth (int): Depth of subgraph extraction
        
    Returns:
        nx.Graph: Extracted subgraph
    """
    if not G or not source_nodes:
        return nx.Graph()
    
    # Start with source nodes
    subgraph_nodes = set(source_nodes)
    
    # Add neighbors up to specified depth
    current_level = set(source_nodes)
    for _ in range(depth):
        next_level = set()
        for node in current_level:
            if node in G:
                neighbors = set(G.neighbors(node))
                next_level.update(neighbors)
        subgraph_nodes.update(next_level)
        current_level = next_level
    
    # Create subgraph
    subgraph = G.subgraph(subgraph_nodes).copy()
    return subgraph

def translate_croatian_to_english(text: str, model_name: str = None) -> str:
    """
    Translate Croatian text to English using AI.
    
    Args:
        text (str): Croatian text to translate
        model_name (str): Optional model name for translation
        
    Returns:
        str: English translation
    """
    try:
        from gemini_helper import generate_content
        
        if not model_name:
            model_name = config.get_gemini_default_model()
        
        prompt = f"""Translate the following Croatian text to English. Provide only the translation without additional explanation:

Croatian text: {text}

English translation:"""
        
        response = generate_content(prompt, model_name=model_name)
        if response:
            return response.strip()
        else:
            logger.warning(f"No translation received for: {text}")
            return ""
            
    except Exception as e:
        logger.error(f"Error translating Croatian text '{text}': {e}")
        return ""

def analyze_croatian_text(text: str, model_name: str = None) -> Dict[str, Any]:
    """
    Analyze Croatian text for linguistic features.
    
    Args:
        text (str): Croatian text to analyze
        model_name (str): Optional model name for analysis
        
    Returns:
        Dict[str, Any]: Analysis results
    """
    try:
        from gemini_helper import generate_content
        
        if not model_name:
            model_name = config.get_gemini_default_model()
        
        prompt = f"""Analyze the following Croatian text and provide a structured analysis in JSON format:

Croatian text: {text}

Please provide analysis with these keys:
- "translation": English translation
- "word_count": Number of words
- "complexity": "simple", "moderate", or "complex"
- "pos_analysis": List of part-of-speech tags for main words
- "linguistic_notes": Brief notes about grammar or linguistic features
- "difficulty_level": "beginner", "intermediate", or "advanced"

Respond with valid JSON only:"""
        
        response = generate_content(prompt, model_name=model_name)
        if response:
            import json
            try:
                analysis = json.loads(response.strip())
                return analysis
            except json.JSONDecodeError:
                logger.warning(f"Could not parse JSON response for text analysis: {response}")
                return {"error": "Invalid JSON response"}
        else:
            return {"error": "No response from AI model"}
            
    except Exception as e:
        logger.error(f"Error analyzing Croatian text '{text}': {e}")
        return {"error": str(e)}

def get_croatian_neighbors_info(G: nx.Graph, node_id: str, max_neighbors: int = 10) -> List[Dict[str, Any]]:
    """
    Get information about Croatian node neighbors.
    
    Args:
        G (nx.Graph): Croatian lexical graph
        node_id (str): Node ID to get neighbors for
        max_neighbors (int): Maximum number of neighbors to return
        
    Returns:
        List[Dict[str, Any]]: List of neighbor information
    """
    if not G or node_id not in G:
        return []
    
    neighbors_info = []
    neighbors = list(G.neighbors(node_id))[:max_neighbors]
    
    for neighbor_id in neighbors:
        neighbor_attrs = G.nodes[neighbor_id]
        edge_data = G.get_edge_data(node_id, neighbor_id)
        
        # Determine relationship type and strength
        relationship_type = "connected"
        relationship_strength = 1.0
        
        if edge_data:
            if 'synonym' in edge_data:
                relationship_type = "synonym"
                relationship_strength = edge_data['synonym'].get('synonym_strength', 1.0)
            elif 'antonym' in edge_data:
                relationship_type = "antonym"
                relationship_strength = edge_data['antonym'].get('antonym_strength', 1.0)
            elif 'weight' in edge_data:
                relationship_strength = edge_data['weight']
        
        neighbor_info = {
            'id': neighbor_id,
            'natuknica': neighbor_attrs.get('natuknica', ''),
            'pos': neighbor_attrs.get('UPOS', ''),
            'translation': neighbor_attrs.get('translation', ''),
            'relationship': relationship_type,
            'strength': relationship_strength
        }
        
        neighbors_info.append(neighbor_info)
    
    # Sort by relationship strength
    neighbors_info.sort(key=lambda x: x['strength'], reverse=True)
    return neighbors_info

def validate_croatian_lempos(lempos: str) -> bool:
    """
    Validate Croatian lempos format.
    
    Args:
        lempos (str): Lempos string to validate
        
    Returns:
        bool: True if valid format, False otherwise
    """
    if not lempos or not isinstance(lempos, str):
        return False
    
    # Croatian lempos format: word-POS (e.g., "abeceda-NOUN")
    parts = lempos.split('-')
    if len(parts) != 2:
        return False
    
    word, pos = parts
    if not word or not pos:
        return False
    
    # Check if POS is valid
    valid_pos_tags = set(CROATIAN_POS_MAPPING.keys())
    return pos in valid_pos_tags

def get_croatian_word_forms(base_word: str, G: nx.Graph) -> List[Dict[str, Any]]:
    """
    Find different forms/inflections of a Croatian word.
    
    Args:
        base_word (str): Base word to find forms for
        G (nx.Graph): Croatian lexical graph
        
    Returns:
        List[Dict[str, Any]]: List of word forms found
    """
    if not G:
        return []
    
    word_forms = []
    base_word_lower = base_word.lower()
    
    for node_id, attrs in G.nodes(data=True):
        natuknica = attrs.get('natuknica', '').lower()
        natuknica_norm = attrs.get('natuknica_norm', '').lower()
        
        # Check if this could be a form of the base word
        if (base_word_lower in natuknica or 
            base_word_lower in natuknica_norm or
            natuknica in base_word_lower or
            natuknica_norm in base_word_lower):
            
            word_form = {
                'lempos': node_id,
                'natuknica': attrs.get('natuknica', ''),
                'pos': attrs.get('UPOS', ''),
                'translation': attrs.get('translation', ''),
                'similarity_score': 1.0 if natuknica == base_word_lower else 0.8
            }
            word_forms.append(word_form)
    
    # Sort by similarity score
    word_forms.sort(key=lambda x: x['similarity_score'], reverse=True)
    return word_forms[:20]  # Limit to top 20 matches

def generate_croatian_explanation(node_id, G=None, model_name=None):
    """
    Generate a comprehensive explanation for a Croatian term using Gemini.
    Similar to the Japanese explanation system but tailored for Croatian language.
    
    Args:
        node_id (str): The Croatian node ID to explain
        G (NetworkX graph): Optional Croatian graph to use
        model_name (str, optional): Gemini model to use
        
    Returns:
        dict: The explanation results with overview, cultural_context, usage_examples, nuances
    """
    from gemini_helper import DEFAULT_MODEL, HAS_VALID_API_KEY
    import google.generativeai as genai
    import json
    from cache_helper import cache
    
    if not HAS_VALID_API_KEY:
        return {"error": "No valid Gemini API key configured"}

    current_model_name = model_name if model_name else DEFAULT_MODEL

    # Check cache first
    cache_key = f"croatian_explanation_{node_id}_{current_model_name}"
    cached_result = cache.get(cache_key)
    if cached_result:
        try:
            return json.loads(cached_result)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in cache for Croatian term '{node_id}'. Regenerating content.")

    if G is None:
        G = load_croatian_graph()
        if G is None:
            return {"error": "Failed to load Croatian graph"}

    try:
        # Get Croatian node context
        context = get_croatian_node_info(G, node_id)
        if not context:
            return {"error": f"Croatian node '{node_id}' not found"}

        natuknica = context.get('natuknica', node_id)
        pos = context.get('pos', '')
        tekst = context.get('tekst', '')
        translation = context.get('translation', '')
        
        # Get neighbors for additional context
        neighbors = []
        if node_id in G.nodes():
            for neighbor in G.neighbors(node_id):
                neighbor_data = G.nodes[neighbor]
                neighbors.append({
                    'word': neighbor_data.get('natuknica', neighbor),
                    'translation': neighbor_data.get('translation', '')
                })
                if len(neighbors) >= 5:
                    break

        # Create comprehensive prompt
        prompt = f"""
        Explain the Croatian word "{natuknica}" in detail.
        
        Additional context:
        - Croatian word: {natuknica}
        - Parts of speech: {pos}
        - Definition: {tekst}
        - English translation: {translation}
        - Related Croatian words: {', '.join([n['word'] for n in neighbors[:3]])}
        
        IMPORTANT: Your response MUST be a valid JSON object with the EXACT following structure:
        {{
            "overview": "Detailed explanation of what the Croatian word means, its etymology if relevant, and its primary uses",
            "cultural_context": "Croatian cultural context, regional usage, or cultural significance if relevant, otherwise 'Standard Croatian usage'",
            "usage_examples": ["Primjer 1: [Croatian sentence] - [English translation]", "Primjer 2: [Croatian sentence] - [English translation]", "Primjer 3: [Croatian sentence] - [English translation]"],
            "nuances": "Any nuances in meaning, formality levels, or subtle differences from similar words"
        }}
        
        Guidelines:
        - Write the overview in English but include the Croatian word
        - Usage examples should be in Croatian with English translations
        - Focus on practical, everyday usage
        - Include cultural context specific to Croatian/Balkan culture when relevant
        - Mention regional variations if they exist (Croatian vs Serbian vs Bosnian usage)
        
        DO NOT include any text before or after the JSON.
        DO NOT use markdown formatting or code blocks around the JSON.
        ONLY return the raw JSON object itself.
        """

        logger.info(f"Sending Croatian explanation request to Gemini API for: {natuknica} using model: {current_model_name}")
        
        model = genai.GenerativeModel(current_model_name)
        response = model.generate_content(prompt)
        model_used = current_model_name
        
        # Log the raw response for debugging
        logger.info(f"Raw Gemini API response for Croatian term '{natuknica}': {response.text!r}")
        
        # Create an explanation with fallback values
        explanation = {
            "overview": f"Croatian word '{natuknica}' means {translation or 'information not available'}.",
            "cultural_context": "Standard Croatian usage.",
            "usage_examples": [f"Primjer: {natuknica} - {translation or 'example not available'}"],
            "nuances": "Information not available.",
            "raw_response": response.text,
            "_model_used": model_used
        }
            
        # Parse response as JSON
        if not response.text or response.text.strip() == "":
            logger.warning(f"Empty response from Gemini API for Croatian term '{natuknica}'")
            explanation["generation_note"] = "Failed to generate content - received empty response"
        else:
            try:
                # Clean the response text - extract JSON from various formats
                json_text = response.text.strip()
                logger.info(f"Initial cleaned JSON text for Croatian '{natuknica}': {json_text!r}")
                
                # Check if response is wrapped in ```json code blocks
                import re
                json_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', json_text)
                if json_block_match:
                    json_text = json_block_match.group(1).strip()
                    logger.info(f"Extracted JSON from code block for Croatian '{natuknica}': {json_text!r}")
                
                # Try to find JSON object between braces
                if not (json_text.startswith('{') and json_text.endswith('}')):
                    json_object_match = re.search(r'({[\s\S]*?})', json_text)
                    if json_object_match:
                        json_text = json_object_match.group(1).strip()
                        logger.info(f"Extracted JSON object for Croatian '{natuknica}': {json_text!r}")
                
                # Parse the cleaned JSON
                logger.info(f"Final JSON text before parsing for Croatian '{natuknica}': {json_text!r}")
                parsed_json = json.loads(json_text)
                logger.info(f"Successfully parsed JSON for Croatian '{natuknica}'")
                
                # Update the explanation with parsed values
                explanation.update(parsed_json)
                
                # Ensure all required fields exist with defaults
                required_fields = ["overview", "cultural_context", "usage_examples", "nuances"]
                for field in required_fields:
                    if field not in explanation:
                        logger.warning(f"Missing field '{field}' in response for Croatian '{natuknica}', adding default value")
                        if field == "usage_examples":
                            explanation[field] = [f"Primjer: {natuknica} - {translation or 'example not available'}"]
                        elif field == "cultural_context":
                            explanation[field] = "Standard Croatian usage"
                        elif field == "overview":
                            explanation[field] = f"Croatian word '{natuknica}' means {translation or 'information not available'}."
                        else:
                            explanation[field] = "Information not available"
                
            except (json.JSONDecodeError, AttributeError) as e:
                logger.warning(f"Invalid response from Gemini API for Croatian term '{natuknica}': {e}")
                explanation["generation_note"] = f"Parse error: {str(e)}"
        
        # Cache the result for 3 days
        try:
            cache.set(cache_key, json.dumps(explanation), 3 * 24 * 60 * 60)
        except Exception as e:
            logger.warning(f"Failed to cache Croatian explanation for '{natuknica}': {e}")
        
        return explanation
    
    except Exception as e:
        logger.error(f"Error generating Croatian explanation for {natuknica}: {e}")
        return {
            "overview": f"An error occurred while generating information about Croatian word '{natuknica}'.",
            "cultural_context": "N/A",
            "usage_examples": [],
            "nuances": "N/A",
            "error": str(e)
        }

def main():
    """Main function for testing Croatian helper functions."""
    print("Testing Croatian Helper Functions")
    print("=" * 50)
    
    # Load Croatian graph
    G = load_croatian_graph()
    if not G:
        print("Failed to load Croatian graph")
        return
    
    print(f"Loaded Croatian graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    
    # Test node search
    search_terms = ['a', 'abeceda', 'NOUN']
    for term in search_terms:
        nodes = find_croatian_nodes(G, term)
        print(f"Search '{term}': found {len(nodes)} nodes")
        if nodes:
            print(f"  First few: {nodes[:3]}")
    
    # Test node info
    if G.nodes():
        sample_node = list(G.nodes())[0]
        node_info = get_croatian_node_info(G, sample_node)
        if node_info:
            print(f"Sample node info for '{sample_node}':")
            for key, value in node_info.items():
                print(f"  {key}: {value}")

if __name__ == "__main__":
    main() 