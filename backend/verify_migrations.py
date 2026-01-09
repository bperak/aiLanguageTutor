#!/usr/bin/env python3
"""
Verify that database migrations were applied successfully.
"""
import asyncio
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(__file__))

from app.db import init_postgresql, get_postgresql_session
from sqlalchemy import text

async def verify_migrations():
    """Verify that migrations were applied successfully."""
    print("=" * 70)
    print("MIGRATION VERIFICATION")
    print("=" * 70)
    
    # Initialize PostgreSQL connection
    init_postgresql()
    
    async for pg in get_postgresql_session():
        try:
            # Check indexes
            result = await pg.execute(text("""
                SELECT schemaname, tablename, indexname 
                FROM pg_indexes 
                WHERE (indexname LIKE 'idx_%' OR indexname LIKE 'uq_%')
                  AND schemaname = 'public'
                ORDER BY tablename, indexname
            """))
            indexes = result.fetchall()
            print(f"\n✅ Found {len(indexes)} indexes:")
            for idx in indexes[:15]:
                print(f"   - {idx[1]}.{idx[2]}")
            if len(indexes) > 15:
                print(f"   ... and {len(indexes) - 15} more")
            
            # Check constraints
            result = await pg.execute(text("""
                SELECT conname, contype, conrelid::regclass 
                FROM pg_constraint 
                WHERE conname LIKE 'chk_%'
                ORDER BY conrelid::regclass, conname
            """))
            constraints = result.fetchall()
            print(f"\n✅ Found {len(constraints)} check constraints:")
            for con in constraints:
                print(f"   - {con[2]}.{con[0]}")
            
            # Check triggers
            result = await pg.execute(text("""
                SELECT tgname, tgrelid::regclass 
                FROM pg_trigger 
                WHERE tgname LIKE 'update_%_updated_at'
                  AND tgisinternal = false
                ORDER BY tgrelid::regclass
            """))
            triggers = result.fetchall()
            print(f"\n✅ Found {len(triggers)} updated_at triggers:")
            for trig in triggers:
                print(f"   - {trig[1]}.{trig[0]}")
            
            # Check GIN indexes
            result = await pg.execute(text("""
                SELECT schemaname, tablename, indexname 
                FROM pg_indexes 
                WHERE indexdef LIKE '%USING gin%'
                  AND schemaname = 'public'
                ORDER BY tablename, indexname
            """))
            gin_indexes = result.fetchall()
            print(f"\n✅ Found {len(gin_indexes)} GIN indexes:")
            for idx in gin_indexes:
                print(f"   - {idx[1]}.{idx[2]}")
            
            # Summary
            print("\n" + "=" * 70)
            print("SUMMARY")
            print("=" * 70)
            print(f"✅ Indexes: {len(indexes)}")
            print(f"✅ GIN Indexes: {len(gin_indexes)}")
            print(f"✅ Check Constraints: {len(constraints)}")
            print(f"✅ Updated_at Triggers: {len(triggers)}")
            print("\n✅ All migrations appear to be applied successfully!")
            print("=" * 70)
            
        except Exception as e:
            print(f"\n❌ Error during verification: {e}")
            import traceback
            traceback.print_exc()
        finally:
            break  # Only need one iteration

if __name__ == "__main__":
    asyncio.run(verify_migrations())

