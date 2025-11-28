# jf_cando_to_nx.py
import pandas as pd
import networkx as nx

NODE_TYPES = {
    "Reference":      {"key": "種別",            "label": "Reference"},
    "CompetenceType": {"key": "種類",            "label": "CompetenceType"},
    "Level":          {"key": "レベル",          "label": "Level"},
    "LingActivity":   {"key": "言語活動",        "label": "LingActivity"},
    "Category":       {"key": "カテゴリー",       "label": "Category"},
    "Topic":          {"key": "第1トピック",     "label": "Topic"},
}

EDGE_TEMPLATE = [                # (source-node-label, rel, target-node-label)
    ("CanDo",      "IN_REFERENCE",  "Reference"),
    ("CanDo",      "OF_TYPE",       "CompetenceType"),
    ("CanDo",      "AT_LEVEL",      "Level"),
    ("CanDo",      "HAS_ACTIVITY",  "LingActivity"),
    ("CanDo",      "IN_CATEGORY",   "Category"),
    ("CanDo",      "ABOUT_TOPIC",   "Topic"),
]

def build_graph(csv_path: str, delimiter: str = ",") -> nx.MultiDiGraph:
    """Read the JF Can-do CSV and return a populated NetworkX graph."""
    df = pd.read_csv(csv_path, delimiter=delimiter).fillna("")
    G = nx.MultiDiGraph()
    
    # Keep track of category nodes to avoid duplicates
    category_nodes = {}

    for index, row in df.iterrows():
        # 1. Create the CanDo node
        can_do_node_id = f"CanDo:{index}"
        G.add_node(
            can_do_node_id,
            no=row["No"],
            reference=row["種別"],
            competence_type=row["種類"],
            level=row["レベル"],
            linguistic_activity=row["言語活動"],
            category=row["カテゴリー"],
            topic=row["第1トピック"],
            can_do_jp=row["JF Can-do (日本語)"],
            can_do_en=row["JF Can-do (English)"],
            label="CanDo"
        )

        # 2. Create and connect category nodes
        for cat_label, cat_key in [("Level", "レベル"), ("LingActivity", "言語活動"), ("Topic", "第1トピック")]:
            cat_value = row[cat_key]
            if cat_value:
                if (cat_label, cat_value) not in category_nodes:
                    cat_node_id = f"{cat_label}:{cat_value}"
                    G.add_node(cat_node_id, label=cat_label, name=cat_value)
                    category_nodes[(cat_label, cat_value)] = cat_node_id
                else:
                    cat_node_id = category_nodes[(cat_label, cat_value)]
                
                # Add edge from CanDo node to category node
                G.add_edge(can_do_node_id, cat_node_id, rel=f"HAS_{cat_label.upper()}")
                
    return G


if __name__ == "__main__":
    # === USAGE ==========================================================
    graph = build_graph("cando/jf_cando_clean.csv")      # ← path to your CSV
    print(f"Nodes: {graph.number_of_nodes():,}, Edges: {graph.number_of_edges():,}")

    # optional: save for Neo4j / Gephi
    nx.write_graphml(graph, "jf_cando.graphml")
    print("GraphML written to jf_cando.graphml")
