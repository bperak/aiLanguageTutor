import networkx as nx
import matplotlib.pyplot as plt
from matplotlib import font_manager

def visualize_cando_graph(graphml_path, output_file='cando_graph.png'):
    """
    Loads, visualizes, and saves the Can-do graph.

    Args:
        graphml_path (str): The path to the GraphML file.
        output_file (str): The path to save the output PNG image.
    """
    # Load the graph
    G = nx.read_graphml(graphml_path)

    # Separate nodes by type for bipartite layout
    cando_nodes = {n for n, d in G.nodes(data=True) if d['label'] == 'CanDo'}
    category_nodes = set(G.nodes()) - cando_nodes

    # Create a layout for the graph
    pos = nx.bipartite_layout(G, cando_nodes)

    # Set up the plot
    plt.figure(figsize=(20, 15))

    # Node colors based on label
    node_colors = []
    for node in G.nodes():
        if G.nodes[node]['label'] == 'CanDo':
            node_colors.append('skyblue')
        elif G.nodes[node]['label'] == 'Level':
            node_colors.append('lightgreen')
        elif G.nodes[node]['label'] == 'LingActivity':
            node_colors.append('lightcoral')
        elif G.nodes[node]['label'] == 'Topic':
            node_colors.append('gold')
        else:
            node_colors.append('grey')

    # Draw the nodes and edges
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=500, alpha=0.8)
    nx.draw_networkx_edges(G, pos, width=1.0, alpha=0.5)

    # Draw labels
    try:
        japanese_fonts = [f for f in font_manager.findSystemFonts() if any(name in f.lower() for name in ['gothic', 'mincho', 'yu', 'meiryo', 'msgothic', 'japan'])]
        if japanese_fonts:
            font_prop = font_manager.FontProperties(fname=japanese_fonts[0])
            nx.draw_networkx_labels(G, pos, font_size=8, font_family=font_prop.get_name())
            print(f"Using Japanese font: {font_prop.get_name()}")
        else:
            nx.draw_networkx_labels(G, pos, font_size=8)
            print("Warning: No Japanese fonts found.")
    except Exception as e:
        nx.draw_networkx_labels(G, pos, font_size=8)
        print(f"Warning: Could not set Japanese font. {e}")

    # Add title and save
    plt.title("Can-Do Graph Visualization", fontsize=18)
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Visualization saved to {output_file}")

if __name__ == '__main__':
    visualize_cando_graph('jf_cando.graphml')
