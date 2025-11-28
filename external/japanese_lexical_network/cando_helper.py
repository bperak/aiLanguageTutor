import networkx as nx
import os
import logging

logger = logging.getLogger(__name__)

CANDO_GRAPH_FILE = os.path.join('cando', 'jf_cando.graphml')
G_cando = None

def load_cando_graph():
    """
    Loads the Can-do graph from the GraphML file.

    Returns:
        nx.Graph: The loaded Can-do graph, or an empty graph if loading fails.
    """
    global G_cando
    if G_cando is not None:
        return G_cando

    if not os.path.exists(CANDO_GRAPH_FILE):
        logger.error(f"Can-do graph file not found at: {CANDO_GRAPH_FILE}")
        G_cando = nx.Graph()
        return G_cando
    
    try:
        G_cando = nx.read_graphml(CANDO_GRAPH_FILE)
        logger.info(f"Successfully loaded Can-do graph with {G_cando.number_of_nodes()} nodes and {G_cando.number_of_edges()} edges.")
    except Exception as e:
        logger.error(f"Error loading Can-do graph: {e}")
        G_cando = nx.Graph()
    
    return G_cando

def search_cando_nodes(query):
    """
    Searches for Can-do nodes in the graph based on a query.

    Args:
        query (str): The search term.

    Returns:
        list: A list of matching node data.
    """
    graph = load_cando_graph()
    if not query:
        return []

    query = query.lower()
    results = []

    for node_id, data in graph.nodes(data=True):
        if data.get('label') == 'CanDo':
            jp_text = data.get('jp', '').lower()
            en_text = data.get('en', '').lower()

            if query in jp_text or query in en_text:
                results.append({
                    'id': node_id,
                    'jp': data.get('jp', ''),
                    'en': data.get('en', '')
                })
    
    return results

def get_cando_graph_data(node_id=None):
    """
    Get Can-do graph data for visualization.
    
    Args:
        node_id (str, optional): Specific node to focus on. If None, returns the full graph.
        
    Returns:
        dict: Graph data with nodes and links in the format expected by force-graph.
    """
    graph = load_cando_graph()
    if not graph:
        return {'nodes': [], 'links': []}
    
    if node_id:
        # If a specific node is requested, get its subgraph
        if node_id not in graph:
            logger.warning(f"Node {node_id} not found in Can-do graph")
            return {'nodes': [], 'links': []}
        
        # Get the node and its neighbors (1-hop)
        neighbors = set([node_id])
        for neighbor in graph.neighbors(node_id):
            neighbors.add(neighbor)
        
        # Create subgraph
        subgraph = graph.subgraph(neighbors)
    else:
        # Return the full graph
        subgraph = graph
    
    # Convert to the format expected by force-graph
    nodes = []
    for node_id, attrs in subgraph.nodes(data=True):
        node_data = {'id': node_id}
        node_data.update(attrs)
        nodes.append(node_data)
    
    links = []
    for source, target, attrs in subgraph.edges(data=True):
        link_data = {
            'source': source,
            'target': target
        }
        link_data.update(attrs)
        links.append(link_data)
    
    return {
        'nodes': nodes,
        'links': links
    }

# Pre-load the graph when the module is imported
load_cando_graph()
