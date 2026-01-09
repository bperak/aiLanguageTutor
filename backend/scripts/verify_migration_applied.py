#!/usr/bin/env python3
"""
Simple script to verify the extraction_response migration was applied.

This script connects to the database and checks if the column exists.
"""

import sys
import os
from pathlib import Path

# Try to use environment variables or defaults
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:testpassword123@localhost:5433/ai_language_tutor")

def verify_migration():
    """Verify the migration was applied by checking for the column."""
    try:
        import psycopg2
        from urllib.parse import urlparse
        
        # Parse database URL
        parsed = urlparse(DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://").replace("postgresql://", ""))
        
        # Connect to database
        conn = psycopg2.connect(
            host=parsed.hostname or "localhost",
            port=parsed.port or 5432,
            database=parsed.path.lstrip("/") if parsed.path else "ai_language_tutor",
            user=parsed.username or "postgres",
            password=parsed.password or "testpassword123"
        )
        
        cur = conn.cursor()
        
        # Check if column exists
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'user_profiles' 
              AND column_name = 'extraction_response'
        """)
        
        result = cur.fetchone()
        
        if result:
            print("✅ Migration applied successfully!")
            print(f"   Column: {result[0]}")
            print(f"   Type: {result[1]}")
            print(f"   Nullable: {result[2]}")
            cur.close()
            conn.close()
            return 0
        else:
            print("❌ Migration not applied - column not found")
            print("   The migration will apply automatically on backend startup")
            cur.close()
            conn.close()
            return 1
            
    except ImportError:
        print("⚠️  psycopg2 not installed. Install with: pip install psycopg2-binary")
        print("   Or verify migration manually with:")
        print("   psql -d ai_language_tutor -c \"SELECT column_name FROM information_schema.columns WHERE table_name = 'user_profiles' AND column_name = 'extraction_response';\"")
        return 2
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        print("   Make sure PostgreSQL is running and DATABASE_URL is correct")
        return 1


if __name__ == "__main__":
    print("=" * 70)
    print("VERIFYING EXTRACTION_RESPONSE MIGRATION")
    print("=" * 70)
    print()
    sys.exit(verify_migration())
