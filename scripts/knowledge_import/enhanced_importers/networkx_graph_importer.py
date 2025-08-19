"""
NetworkX Synonym Graph Importer
Imports the sophisticated synonym graph with semantic relationships into Neo4j.
"""

import asyncio
import pickle
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import structlog
from neo4j import AsyncGraphDatabase
import networkx as nx
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = structlog.get_logger()


class NetworkXGraphImporter:
    """Import NetworkX synonym graph into Neo4j knowledge graph."""
    
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self.driver = AsyncGraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        self.imported_nodes = 0
        self.imported_edges = 0
        self.updated_nodes = 0
        self.error_count = 0
        
    async def close(self):
        """Close Neo4j connection."""
        await self.driver.close()
    
    def clean_node_data(self, node_data: Dict) -> Dict:
        """Clean and validate node data from NetworkX."""
        cleaned = {}
        
        # Handle NaN values and convert to appropriate types
        for key, value in node_data.items():
            if pd.isna(value) if 'pd' in globals() else str(value).lower() == 'nan':
                cleaned[key] = None
            elif key in ['JLPT', 'jlpt_jisho_lemma'] and value is not None:
                try:
                    cleaned[key] = float(value)
                except (ValueError, TypeError):
                    cleaned[key] = None
            else:
                cleaned[key] = str(value).strip() if value is not None else None
        
        return cleaned
    
    def clean_edge_data(self, edge_data: Dict) -> Dict:
        """Clean and validate edge data from NetworkX."""
        cleaned = {}
        
        for key, value in edge_data.items():
            if pd.isna(value) if 'pd' in globals() else str(value).lower() == 'nan':
                cleaned[key] = None
            elif key in ['synonym_strength', 'weight'] and value is not None:
                try:
                    cleaned[key] = float(value)
                except (ValueError, TypeError):
                    cleaned[key] = 0.0
            else:
                cleaned[key] = str(value).strip() if value is not None else None
        
        return cleaned
    
    async def create_semantic_domains(self, session, graph: nx.Graph):
        """Extract and create semantic domain nodes."""
        logger.info("Creating semantic domains")
        
        domains = set()
        
        # Extract domains from edge data
        for _, _, edge_data in graph.edges(data=True):
            domain = edge_data.get('synonymy_domain')
            domain_hiragana = edge_data.get('synonymy_domain_hiragana')
            domain_translation = edge_data.get('synonymy_domain_translation')
            
            if domain and str(domain).strip() and str(domain).lower() != 'nan':
                domains.add((
                    str(domain).strip(),
                    str(domain_hiragana).strip() if domain_hiragana and str(domain_hiragana).lower() != 'nan' else '',
                    str(domain_translation).strip() if domain_translation and str(domain_translation).lower() != 'nan' else ''
                ))
        
        # Create domain nodes
        for domain_name, hiragana, translation in domains:
            try:
                await session.run("""
                    MERGE (d:SemanticDomain {name: $name})
                    SET d.hiragana = $hiragana,
                        d.translation = $translation,
                        d.created_at = coalesce(d.created_at, datetime()),
                        d.updated_at = datetime()
                """, {
                    'name': domain_name,
                    'hiragana': hiragana,
                    'translation': translation
                })
            except Exception as e:
                logger.error("Error creating semantic domain", 
                           domain=domain_name, error=str(e))
        
        logger.info("Created semantic domains", count=len(domains))
    
    async def create_mutual_senses(self, session, graph: nx.Graph):
        """Extract and create mutual sense nodes."""
        logger.info("Creating mutual senses")
        
        mutual_senses = set()
        
        # Extract mutual senses from edge data
        for _, _, edge_data in graph.edges(data=True):
            sense = edge_data.get('mutual_sense')
            sense_hiragana = edge_data.get('mutual_sense_hiragana')
            sense_translation = edge_data.get('mutual_sense_translation')
            
            if sense and str(sense).strip() and str(sense).lower() != 'nan':
                mutual_senses.add((
                    str(sense).strip(),
                    str(sense_hiragana).strip() if sense_hiragana and str(sense_hiragana).lower() != 'nan' else '',
                    str(sense_translation).strip() if sense_translation and str(sense_translation).lower() != 'nan' else ''
                ))
        
        # Create mutual sense nodes
        for sense, hiragana, translation in mutual_senses:
            try:
                await session.run("""
                    MERGE (m:MutualSense {sense: $sense})
                    SET m.hiragana = $hiragana,
                        m.translation = $translation,
                        m.created_at = coalesce(m.created_at, datetime()),
                        m.updated_at = datetime()
                """, {
                    'sense': sense,
                    'hiragana': hiragana,
                    'translation': translation
                })
            except Exception as e:
                logger.error("Error creating mutual sense", 
                           sense=sense, error=str(e))
        
        logger.info("Created mutual senses", count=len(mutual_senses))
    
    async def import_nodes_batch(self, session, nodes_batch: List[Tuple[str, Dict]]) -> int:
        """Import a batch of nodes from NetworkX graph."""
        imported = 0
        updated = 0
        
        for node_id, node_data in nodes_batch:
            try:
                cleaned_data = self.clean_node_data(node_data)
                
                # Check if this is a new node or update to existing Lee vocab
                result = await session.run("""
                    MERGE (w:Word {kanji: $kanji})
                    ON CREATE SET 
                        w.hiragana = $hiragana,
                        w.translation = $translation,
                        w.pos_primary = $pos,
                        w.jlpt_level = $jlpt_level,
                        w.jlpt_jisho_lemma = $jlpt_jisho_lemma,
                        w.source = 'networkx_graph',
                        w.created_at = datetime(),
                        w.updated_at = datetime()
                    ON MATCH SET
                        w.hiragana = coalesce($hiragana, w.hiragana),
                        w.translation = coalesce($translation, w.translation),
                        w.jlpt_level = coalesce($jlpt_level, w.jlpt_level),
                        w.jlpt_jisho_lemma = coalesce($jlpt_jisho_lemma, w.jlpt_jisho_lemma),
                        w.source = CASE 
                            WHEN w.source = 'lee_vocab' THEN 'lee_vocab+networkx'
                            ELSE 'networkx_graph'
                        END,
                        w.updated_at = datetime()
                    
                    RETURN w.kanji as word, 
                           CASE WHEN w.created_at = w.updated_at THEN 'created' ELSE 'updated' END as action
                """, {
                    'kanji': node_id,
                    'hiragana': cleaned_data.get('hiragana'),
                    'translation': cleaned_data.get('translation'),
                    'pos': cleaned_data.get('POS'),
                    'jlpt_level': cleaned_data.get('JLPT'),
                    'jlpt_jisho_lemma': cleaned_data.get('jlpt_jisho_lemma')
                })
                
                record = await result.single()
                if record:
                    if record['action'] == 'created':
                        imported += 1
                    else:
                        updated += 1
                        
            except Exception as e:
                logger.error("Error importing node", 
                           node_id=node_id, 
                           error=str(e))
                self.error_count += 1
        
        self.imported_nodes += imported
        self.updated_nodes += updated
        return imported + updated
    
    async def import_edges_batch(self, session, edges_batch: List[Tuple[str, str, Dict]]) -> int:
        """Import a batch of synonym relationships."""
        imported = 0
        
        for source, target, edge_data in edges_batch:
            try:
                cleaned_data = self.clean_edge_data(edge_data)
                
                # Create synonym relationship
                result = await session.run("""
                    MATCH (w1:Word {kanji: $source}), (w2:Word {kanji: $target})
                    MERGE (w1)-[r:SYNONYM_OF]->(w2)
                    SET r.synonym_strength = $synonym_strength,
                        r.relation_type = $relation_type,
                        r.mutual_sense = $mutual_sense,
                        r.synonymy_explanation = $synonymy_explanation,
                        r.weight = $weight,
                        r.source = 'networkx_graph',
                        r.created_at = coalesce(r.created_at, datetime()),
                        r.updated_at = datetime()
                    
                    // Link to mutual sense if it exists
                    WITH w1, w2, r
                    OPTIONAL MATCH (m:MutualSense {sense: $mutual_sense})
                    FOREACH (sense IN CASE WHEN m IS NOT NULL THEN [m] ELSE [] END |
                        MERGE (w1)-[:HAS_MUTUAL_SENSE]->(sense)
                        MERGE (w2)-[:HAS_MUTUAL_SENSE]->(sense)
                    )
                    
                    // Link to semantic domain if it exists
                    WITH w1, w2, r
                    OPTIONAL MATCH (d:SemanticDomain {name: $synonymy_domain})
                    FOREACH (domain IN CASE WHEN d IS NOT NULL THEN [d] ELSE [] END |
                        MERGE (w1)-[:BELONGS_TO_DOMAIN]->(domain)
                        MERGE (w2)-[:BELONGS_TO_DOMAIN]->(domain)
                    )
                    
                    RETURN r
                """, {
                    'source': source,
                    'target': target,
                    'synonym_strength': cleaned_data.get('synonym_strength', 0.0),
                    'relation_type': cleaned_data.get('relation_type'),
                    'mutual_sense': cleaned_data.get('mutual_sense'),
                    'synonymy_explanation': cleaned_data.get('synonymy_explanation'),
                    'weight': cleaned_data.get('weight', 0.0),
                    'synonymy_domain': cleaned_data.get('synonymy_domain')
                })
                
                if await result.single():
                    imported += 1
                    
            except Exception as e:
                logger.error("Error importing edge", 
                           source=source, 
                           target=target, 
                           error=str(e))
                self.error_count += 1
        
        self.imported_edges += imported
        return imported
    
    async def load_and_import_graph(self, graph_path: Path) -> Dict[str, int]:
        """
        Load NetworkX graph and import into Neo4j.
        
        Args:
            graph_path: Path to the pickle file
            
        Returns:
            Dict with import statistics
        """
        logger.info("Starting NetworkX graph import", file=str(graph_path))
        
        # Load NetworkX graph
        try:
            with open(graph_path, 'rb') as f:
                graph = pickle.load(f)
            
            logger.info("Loaded NetworkX graph", 
                       nodes=graph.number_of_nodes(),
                       edges=graph.number_of_edges())
        except Exception as e:
            logger.error("Failed to load graph file", error=str(e))
            raise
        
        async with self.driver.session() as session:
            # Create supporting structures first
            await self.create_semantic_domains(session, graph)
            await self.create_mutual_senses(session, graph)
            
            # Import nodes in batches
            logger.info("Importing nodes")
            batch_size = 1000
            nodes_data = list(graph.nodes(data=True))
            
            for i in range(0, len(nodes_data), batch_size):
                batch = nodes_data[i:i + batch_size]
                batch_processed = await self.import_nodes_batch(session, batch)
                
                logger.info("Imported node batch", 
                          batch_num=i // batch_size + 1,
                          batch_size=len(batch),
                          processed=batch_processed)
            
            # Import edges in batches
            logger.info("Importing synonym relationships")
            edges_data = list(graph.edges(data=True))
            
            for i in range(0, len(edges_data), batch_size):
                batch = edges_data[i:i + batch_size]
                batch_imported = await self.import_edges_batch(session, batch)
                
                logger.info("Imported edge batch", 
                          batch_num=i // batch_size + 1,
                          batch_size=len(batch),
                          imported=batch_imported)
        
        return {
            'nodes_imported': self.imported_nodes,
            'nodes_updated': self.updated_nodes,
            'edges_imported': self.imported_edges,
            'errors': self.error_count,
            'total_nodes': graph.number_of_nodes(),
            'total_edges': graph.number_of_edges()
        }


async def main():
    """Main import function."""
    import os
    from pathlib import Path
    
    # Configuration
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687").replace("neo4j://neo4j:7687", "bolt://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USERNAME", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
    
    # File path
    graph_file = Path(__file__).parent.parent.parent.parent / "resources" / "G_synonyms_2024_09_18.pickle"
    
    if not graph_file.exists():
        logger.error("Graph file not found", path=str(graph_file))
        return
    
    # Import graph
    importer = NetworkXGraphImporter(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    try:
        stats = await importer.load_and_import_graph(graph_file)
        logger.info("Import completed", **stats)
    except Exception as e:
        logger.error("Import failed", error=str(e))
    finally:
        await importer.close()


if __name__ == "__main__":
    asyncio.run(main())
