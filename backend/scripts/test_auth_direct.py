"""Test authentication directly."""
import asyncio
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db import init_postgresql, get_postgresql_session
from app.services.auth_service import AuthService

async def test():
    print("Testing authentication...")
    init_postgresql()
    
    async for db in get_postgresql_session():
        try:
            user = await AuthService.authenticate_user(db, "bperak", "Teachable1A")
            if user:
                print("SUCCESS: User authenticated!")
                print(f"Username: {user.username}")
                print(f"Email: {user.email}")
                print(f"Is Active: {user.is_active}")
                return True
            else:
                print("FAILED: User not authenticated")
                return False
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            await db.close()

if __name__ == "__main__":
    result = asyncio.run(test())
    sys.exit(0 if result else 1)

