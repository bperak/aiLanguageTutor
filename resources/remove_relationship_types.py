#!/usr/bin/env python3
"""
Remove specific relationship types from Neo4j database

This script removes the following relationship types:
- HAS_ETYMOLOGY
- HAS_POS  
- HAS_DIFFICULTY
- RELATIONSHIP_TRANSFERRED
- BELONGS_TO_DOMAIN
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('remove_relationships.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_environment():
    """Load environment variables and setup Neo4j connection"""
    # Load environment variables from root directory
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
    
    # Also try loading from current directory as fallback
    if not env_path.exists():
        load_dotenv()
    
    print(f"Environment loaded from: {env_path}")
    print(f"Current working directory: {Path.cwd()}")
    print(f"Environment file exists: {env_path.exists()}")
    
    # Neo4j connection configuration
    URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    USER = os.getenv("NEO4J_USERNAME", "neo4j")
    
    # Try environment password first, then fallback to Docker default
    env_password = os.getenv("NEO4J_PASSWORD")
    PASSWORD = env_password if env_password else "testpassword123"
    
    # Debug environment variables
    print(f"Environment variables loaded:")
    print(f"  NEO4J_URI: {URI}")
    print(f"  NEO4J_USERNAME: {USER}")
    print(f"  NEO4J_PASSWORD: {'***' if PASSWORD else 'NOT SET'}")
    print(f"  NEO4J_PASSWORD length: {len(PASSWORD) if PASSWORD else 0}")
    
    # Handle Docker container URIs
    if URI.startswith("neo4j://neo4j:"):
        URI = URI.replace("neo4j://neo4j:", "bolt://localhost:")
    elif URI.startswith("neo4j://"):
        URI = URI.replace("neo4j://", "bolt://localhost:")
    
    print(f"Connecting to Neo4j at: {URI}")
    print(f"User: {USER}")
    print(f"Password set: {'Yes' if PASSWORD else 'No'}")
    
    # Test connection with multiple password attempts
    # Skip environment password due to rate limiting, use only working password
    passwords_to_try = ["testpassword123"]
    
    for i, password in enumerate(passwords_to_try, 1):
        if password == PASSWORD and env_password:
            print(f"Trying environment password (attempt {i})")
        else:
            print(f"Trying fallback password (attempt {i})")
            
        try:
            driver = GraphDatabase.driver(URI, auth=(USER, password))
            with driver.session() as session:
                result = session.run("RETURN 'Connection successful' as status")
                status = result.single()['status']
                print(f"✅ {status}")
            return driver
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            if driver:
                driver.close()
            continue
    
    print("❌ All connection attempts failed")
    return None

def get_relationship_counts(driver):
    """Get counts of relationships to be deleted"""
    relationship_types = [
        'HAS_ETYMOLOGY',
        'HAS_POS', 
        'HAS_DIFFICULTY',
        'RELATIONSHIP_TRANSFERRED',
        'BELONGS_TO_DOMAIN'
    ]
    
    counts = {}
    
    with driver.session() as session:
        for rel_type in relationship_types:
            result = session.run(f"""
                MATCH ()-[r:{rel_type}]->()
                RETURN count(r) as count
            """)
            count = result.single()['count']
            counts[rel_type] = count
            logger.info(f"Found {count} {rel_type} relationships")
    
    return counts

def remove_relationship_types(driver):
    """Remove the specified relationship types"""
    relationship_types = [
        'HAS_ETYMOLOGY',
        'HAS_POS', 
        'HAS_DIFFICULTY',
        'RELATIONSHIP_TRANSFERRED',
        'BELONGS_TO_DOMAIN'
    ]
    
    total_deleted = 0
    
    with driver.session() as session:
        for rel_type in relationship_types:
            logger.info(f"Deleting {rel_type} relationships...")
            
            # Delete relationships
            result = session.run(f"""
                MATCH ()-[r:{rel_type}]->()
                DELETE r
                RETURN count(r) as deleted_count
            """)
            
            deleted_count = result.single()['deleted_count']
            total_deleted += deleted_count
            logger.info(f"✅ Deleted {deleted_count} {rel_type} relationships")
    
    return total_deleted

def main():
    """Main function to remove relationship types"""
    logger.info("=" * 80)
    logger.info("REMOVE RELATIONSHIP TYPES")
    logger.info("=" * 80)
    
    # Load environment and connect to database
    driver = load_environment()
    if not driver:
        logger.error("Cannot proceed without database connection")
        return
    
    try:
        # Get initial counts
        logger.info("Getting relationship counts...")
        initial_counts = get_relationship_counts(driver)
        
        total_initial = sum(initial_counts.values())
        logger.info(f"Total relationships to delete: {total_initial}")
        
        if total_initial == 0:
            logger.info("No relationships found to delete. Exiting.")
            return
        
        # Confirm deletion
        logger.info("=" * 50)
        logger.info("RELATIONSHIP DELETION SUMMARY:")
        for rel_type, count in initial_counts.items():
            if count > 0:
                logger.info(f"  {rel_type}: {count} relationships")
        logger.info("=" * 50)
        
        # Remove relationships
        logger.info("Starting relationship deletion...")
        total_deleted = remove_relationship_types(driver)
        
        # Verify deletion
        logger.info("Verifying deletion...")
        final_counts = get_relationship_counts(driver)
        total_final = sum(final_counts.values())
        
        # Final statistics
        logger.info("=" * 80)
        logger.info("RELATIONSHIP DELETION COMPLETED")
        logger.info("=" * 80)
        logger.info(f"Initial relationships: {total_initial}")
        logger.info(f"Deleted relationships: {total_deleted}")
        logger.info(f"Remaining relationships: {total_final}")
        logger.info(f"Success rate: {total_deleted/total_initial*100:.1f}%")
        
        # Show final counts
        logger.info("\nFinal relationship counts:")
        for rel_type, count in final_counts.items():
            logger.info(f"  {rel_type}: {count} relationships")
        
    except Exception as e:
        logger.error(f"Error during relationship deletion: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if driver:
            driver.close()
            logger.info("Database connection closed")

if __name__ == "__main__":
    main()


