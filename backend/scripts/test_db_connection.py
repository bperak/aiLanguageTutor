"""Test database connection."""
import asyncio
import asyncpg
import sys

async def test_connection():
    """Test PostgreSQL connection."""
    url = "postgresql://postgres:testpassword123@localhost:5433/ai_language_tutor"
    print(f"Testing connection to: {url}")
    print("=" * 60)
    
    try:
        conn = await asyncpg.connect(url)
        print("✅ Connection successful!")
        
        # Test query
        result = await conn.fetchval("SELECT current_database(), current_user")
        print(f"✅ Query successful")
        
        # Check if user exists
        user = await conn.fetchrow(
            "SELECT username, email, is_active FROM users WHERE username = $1",
            "bperak"
        )
        
        if user:
            print(f"✅ User 'bperak' found:")
            print(f"   - Username: {user['username']}")
            print(f"   - Email: {user['email']}")
            print(f"   - Is Active: {user['is_active']}")
        else:
            print("❌ User 'bperak' NOT found")
        
        await conn.close()
        return True
        
    except asyncpg.exceptions.InvalidPasswordError as e:
        print(f"❌ Password authentication failed: {e}")
        print("\nPossible causes:")
        print("  1. Wrong password in connection string")
        print("  2. Connecting to wrong PostgreSQL instance")
        print("  3. Local PostgreSQL instance interfering")
        return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    sys.exit(0 if success else 1)

