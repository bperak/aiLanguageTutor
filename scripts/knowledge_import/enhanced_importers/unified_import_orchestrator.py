"""
Unified Import Orchestrator
Coordinates the import of both Lee's vocabulary and NetworkX synonym graph
to create a comprehensive knowledge graph.
"""

import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import structlog
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from lee_vocabulary_importer import LeeVocabularyImporter
from networkx_graph_importer import NetworkXGraphImporter

logger = structlog.get_logger()


class UnifiedImportOrchestrator:
    """Orchestrate the import of all lexical resources into Neo4j."""
    
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.import_stats = {}
    
    async def setup_schema(self):
        """Set up the Neo4j schema before importing data."""
        from neo4j import AsyncGraphDatabase
        
        logger.info("Setting up Neo4j schema")
        
        driver = AsyncGraphDatabase.driver(
            self.neo4j_uri, 
            auth=(self.neo4j_user, self.neo4j_password)
        )
        
        try:
            async with driver.session() as session:
                # Read and execute schema file
                schema_file = Path(__file__).parent.parent.parent.parent / "backend" / "migrations" / "enhanced_neo4j_schema.cypher"
                
                if schema_file.exists():
                    with open(schema_file, 'r', encoding='utf-8') as f:
                        schema_content = f.read()
                    
                    # Split by semicolons and execute each statement
                    statements = [stmt.strip() for stmt in schema_content.split(';') if stmt.strip()]
                    
                    for statement in statements:
                        # Skip comments and empty lines
                        if statement.startswith('//') or not statement:
                            continue
                        
                        try:
                            await session.run(statement)
                            logger.debug("Executed schema statement", statement=statement[:100])
                        except Exception as e:
                            # Some statements might fail if constraints already exist
                            logger.warning("Schema statement failed (may be expected)", 
                                         statement=statement[:100], 
                                         error=str(e))
                    
                    logger.info("Schema setup completed")
                else:
                    logger.warning("Schema file not found", path=str(schema_file))
                    
        except Exception as e:
            logger.error("Failed to setup schema", error=str(e))
            raise
        finally:
            await driver.close()
    
    async def import_lee_vocabulary(self) -> Dict[str, Any]:
        """Import Lee's vocabulary database."""
        logger.info("Starting Lee's vocabulary import")
        
        vocab_file = Path(__file__).parent.parent.parent.parent / "resources" / "Lee李  分類語彙表学習者用goi.xlsx - Sheet1.tsv"
        
        if not vocab_file.exists():
            logger.error("Lee's vocabulary file not found", path=str(vocab_file))
            raise FileNotFoundError(f"Vocabulary file not found: {vocab_file}")
        
        importer = LeeVocabularyImporter(
            self.neo4j_uri, 
            self.neo4j_user, 
            self.neo4j_password
        )
        
        try:
            stats = await importer.load_and_import_vocabulary(vocab_file)
            logger.info("Lee's vocabulary import completed", **stats)
            return stats
        finally:
            await importer.close()
    
    async def import_networkx_graph(self) -> Dict[str, Any]:
        """Import NetworkX synonym graph."""
        logger.info("Starting NetworkX graph import")
        
        graph_file = Path(__file__).parent.parent.parent.parent / "resources" / "G_synonyms_2024_09_18.pickle"
        
        if not graph_file.exists():
            logger.error("NetworkX graph file not found", path=str(graph_file))
            raise FileNotFoundError(f"Graph file not found: {graph_file}")
        
        importer = NetworkXGraphImporter(
            self.neo4j_uri, 
            self.neo4j_user, 
            self.neo4j_password
        )
        
        try:
            stats = await importer.load_and_import_graph(graph_file)
            logger.info("NetworkX graph import completed", **stats)
            return stats
        finally:
            await importer.close()
    
    async def post_import_analysis(self):
        """Analyze the imported data and create additional relationships."""
        from neo4j import AsyncGraphDatabase
        
        logger.info("Running post-import analysis")
        
        driver = AsyncGraphDatabase.driver(
            self.neo4j_uri, 
            auth=(self.neo4j_user, self.neo4j_password)
        )
        
        try:
            async with driver.session() as session:
                # Update word counts on classification nodes
                await session.run("""
                    MATCH (d:DifficultyLevel)<-[:HAS_DIFFICULTY]-(w:Word)
                    WITH d, COUNT(w) as word_count
                    SET d.word_count = word_count
                """)
                
                await session.run("""
                    MATCH (p:POSTag)<-[:HAS_POS]-(w:Word)
                    WITH p, COUNT(w) as word_count
                    SET p.word_count = word_count
                """)
                
                await session.run("""
                    MATCH (e:Etymology)<-[:HAS_ETYMOLOGY]-(w:Word)
                    WITH e, COUNT(w) as word_count
                    SET e.word_count = word_count
                """)
                
                await session.run("""
                    MATCH (d:SemanticDomain)<-[:BELONGS_TO_DOMAIN]-(w:Word)
                    WITH d, COUNT(w) as word_count
                    SET d.word_count = word_count
                """)
                
                # Create prerequisite relationships based on difficulty levels
                await session.run("""
                    MATCH (d1:DifficultyLevel), (d2:DifficultyLevel)
                    WHERE d1.numeric_level = d2.numeric_level - 1
                    MERGE (d1)-[:PRECEDES]->(d2)
                """)
                
                # Create commonly used together relationships for high-strength synonyms
                await session.run("""
                    MATCH (w1:Word)-[r:SYNONYM_OF]->(w2:Word)
                    WHERE r.synonym_strength > 0.8
                    MERGE (w1)-[:COMMONLY_USED_WITH]->(w2)
                """)
                
                logger.info("Post-import analysis completed")
                
        except Exception as e:
            logger.error("Post-import analysis failed", error=str(e))
        finally:
            await driver.close()
    
    async def generate_import_report(self) -> Dict[str, Any]:
        """Generate a comprehensive report of the import process."""
        from neo4j import AsyncGraphDatabase
        
        logger.info("Generating import report")
        
        driver = AsyncGraphDatabase.driver(
            self.neo4j_uri, 
            auth=(self.neo4j_user, self.neo4j_password)
        )
        
        try:
            async with driver.session() as session:
                # Count nodes by type
                node_counts = {}
                
                for node_type in ['Word', 'DifficultyLevel', 'POSTag', 'Etymology', 
                                'SemanticDomain', 'MutualSense']:
                    result = await session.run(f"MATCH (n:{node_type}) RETURN COUNT(n) as count")
                    record = await result.single()
                    node_counts[node_type] = record['count'] if record else 0
                
                # Count relationships by type
                rel_counts = {}
                
                for rel_type in ['HAS_DIFFICULTY', 'HAS_POS', 'HAS_ETYMOLOGY', 
                               'BELONGS_TO_DOMAIN', 'SYNONYM_OF', 'HAS_MUTUAL_SENSE']:
                    result = await session.run(f"MATCH ()-[r:{rel_type}]->() RETURN COUNT(r) as count")
                    record = await result.single()
                    rel_counts[rel_type] = record['count'] if record else 0
                
                # Get difficulty level distribution
                difficulty_dist = {}
                result = await session.run("""
                    MATCH (w:Word)-[:HAS_DIFFICULTY]->(d:DifficultyLevel)
                    RETURN d.level, COUNT(w) as count
                    ORDER BY d.numeric_level
                """)
                
                async for record in result:
                    difficulty_dist[record['d.level']] = record['count']
                
                # Get etymology distribution
                etymology_dist = {}
                result = await session.run("""
                    MATCH (w:Word)-[:HAS_ETYMOLOGY]->(e:Etymology)
                    RETURN e.type, COUNT(w) as count
                    ORDER BY count DESC
                """)
                
                async for record in result:
                    etymology_dist[record['e.type']] = record['count']
                
                # Get top semantic domains
                top_domains = {}
                result = await session.run("""
                    MATCH (w:Word)-[:BELONGS_TO_DOMAIN]->(d:SemanticDomain)
                    RETURN d.name, d.translation, COUNT(w) as count
                    ORDER BY count DESC
                    LIMIT 20
                """)
                
                async for record in result:
                    top_domains[record['d.name']] = {
                        'translation': record['d.translation'],
                        'word_count': record['count']
                    }
                
                report = {
                    'import_timestamp': datetime.now().isoformat(),
                    'node_counts': node_counts,
                    'relationship_counts': rel_counts,
                    'difficulty_distribution': difficulty_dist,
                    'etymology_distribution': etymology_dist,
                    'top_semantic_domains': top_domains,
                    'import_statistics': self.import_stats
                }
                
                logger.info("Import report generated", **report)
                return report
                
        except Exception as e:
            logger.error("Failed to generate import report", error=str(e))
            return {}
        finally:
            await driver.close()
    
    async def run_complete_import(self) -> Dict[str, Any]:
        """Run the complete import process."""
        logger.info("Starting complete lexical import process")
        start_time = datetime.now()
        
        try:
            # Step 1: Setup schema
            await self.setup_schema()
            
            # Step 2: Import Lee's vocabulary (foundation)
            lee_stats = await self.import_lee_vocabulary()
            self.import_stats['lee_vocabulary'] = lee_stats
            
            # Step 3: Import NetworkX graph (enrichment)
            networkx_stats = await self.import_networkx_graph()
            self.import_stats['networkx_graph'] = networkx_stats
            
            # Step 4: Post-import analysis
            await self.post_import_analysis()
            
            # Step 5: Generate report
            report = await self.generate_import_report()
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.info("Complete import process finished", 
                       duration_seconds=duration,
                       total_words=report.get('node_counts', {}).get('Word', 0))
            
            report['import_duration_seconds'] = duration
            return report
            
        except Exception as e:
            logger.error("Import process failed", error=str(e))
            raise


async def main():
    """Main function to run the complete import."""
    # Configuration from environment
    # Override Neo4j URI for external access (not Docker internal)
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687").replace("neo4j://neo4j:7687", "bolt://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USERNAME", "neo4j")  
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
    
    # Create orchestrator
    orchestrator = UnifiedImportOrchestrator(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    try:
        # Run complete import
        report = await orchestrator.run_complete_import()
        
        # Save report
        import json
        report_file = Path("import_report.json")
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info("Import report saved", file=str(report_file))
        
        # Print summary
        print("\n" + "="*60)
        print("LEXICAL IMPORT COMPLETED SUCCESSFULLY")
        print("="*60)
        print(f"Total Words: {report.get('node_counts', {}).get('Word', 0):,}")
        print(f"Synonym Relationships: {report.get('relationship_counts', {}).get('SYNONYM_OF', 0):,}")
        print(f"Semantic Domains: {report.get('node_counts', {}).get('SemanticDomain', 0):,}")
        print(f"Import Duration: {report.get('import_duration_seconds', 0):.1f} seconds")
        print("="*60)
        
    except Exception as e:
        logger.error("Import process failed", error=str(e))
        raise


if __name__ == "__main__":
    asyncio.run(main())
