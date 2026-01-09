"""
Script to run the RAG migration (Phase 1) manually.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from app.core.config import settings


def run_migration():
    """Run the migration SQL file."""
    migration_file = Path(__file__).parent.parent / "migrations" / "2025-11-06_enrich_chat_sessions_pgvector.sql"
    
    if not migration_file.exists():
        print(f"ERROR: Migration file not found: {migration_file}")
        return False
    
    # Read migration SQL
    with open(migration_file, 'r', encoding='utf-8') as f:
        migration_sql = f.read()
    
    # Parse DATABASE_URL to get connection details
    db_url = settings.DATABASE_URL.replace("+asyncpg", "")
    # Extract connection details
    # Format: postgresql://user:password@host:port/database
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "")
    
    # For local testing, use psycopg2 (sync)
    try:
        # Try to connect using environment defaults
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="ai_language_tutor",
            user="postgres",
            password="testpassword123"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        cursor = conn.cursor()
        
        print("Running migration...")
        # Execute migration SQL
        cursor.execute(migration_sql)
        
        print("Migration completed successfully!")
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"ERROR running migration: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)

