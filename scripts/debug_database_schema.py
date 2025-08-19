"""
Debug script to check database schema and SQLAlchemy model compatibility.
"""

import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text, inspect

async def debug_database():
    """Debug database schema and model compatibility."""
    print("🔍 DATABASE SCHEMA DEBUG")
    print("=" * 50)
    
    # Database connection
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+asyncpg://postgres:postgres@localhost:5432/ai_language_tutor')
    
    try:
        engine = create_async_engine(DATABASE_URL)
        
        async with engine.connect() as conn:
            print("✅ Connected to database")
            
            # Check if users table exists
            result = await conn.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                ORDER BY ordinal_position;
            """))
            
            columns = result.fetchall()
            
            if columns:
                print(f"\n📊 USERS TABLE SCHEMA ({len(columns)} columns):")
                print("-" * 70)
                for col in columns:
                    nullable = "NULL" if col.is_nullable == "YES" else "NOT NULL"
                    default = f" DEFAULT {col.column_default}" if col.column_default else ""
                    print(f"  {col.column_name:<25} {col.data_type:<20} {nullable}{default}")
                
                # Test a simple query
                print(f"\n🔍 TESTING SIMPLE QUERY:")
                try:
                    result = await conn.execute(text("SELECT COUNT(*) as user_count FROM users"))
                    count = result.scalar()
                    print(f"✅ Users table accessible: {count} users")
                except Exception as e:
                    print(f"❌ Query failed: {e}")
                
                # Check table constraints
                print(f"\n🔒 TABLE CONSTRAINTS:")
                result = await conn.execute(text("""
                    SELECT constraint_name, constraint_type 
                    FROM information_schema.table_constraints 
                    WHERE table_name = 'users'
                """))
                constraints = result.fetchall()
                for constraint in constraints:
                    print(f"  {constraint.constraint_name:<30} {constraint.constraint_type}")
                
            else:
                print("❌ Users table not found!")
                
                # List all tables
                result = await conn.execute(text("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """))
                tables = result.fetchall()
                print(f"\n📋 AVAILABLE TABLES:")
                for table in tables:
                    print(f"  - {table.table_name}")
            
        await engine.dispose()
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(debug_database())
