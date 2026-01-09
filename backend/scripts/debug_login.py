"""Debug script to test login authentication."""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db import get_postgresql_session, init_postgresql
from app.services.auth_service import AuthService
from sqlalchemy import select
from app.models.database_models import User


async def debug_login(username: str, password: str):
    """Debug login process."""
    print(f"🔍 Debugging login for user: {username}")
    print("=" * 60)
    
    # Initialize database
    print("\n1. Initializing database connection...")
    init_postgresql()
    print("   ✅ Database initialized")
    
    async for session in get_postgresql_session():
        try:
            print("\n2. Searching for user in database...")
            result = await session.execute(
                select(User).where(User.username == username)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                print(f"   ❌ User '{username}' NOT FOUND in database")
                return False
            
            print(f"   ✅ User found:")
            print(f"      - ID: {user.id}")
            print(f"      - Username: {user.username}")
            print(f"      - Email: {user.email}")
            print(f"      - Is Active: {user.is_active}")
            print(f"      - Password hash: {user.hashed_password[:30]}...")
            
            print("\n3. Verifying password...")
            password_match = AuthService.verify_password(password, user.hashed_password)
            print(f"   Password match: {'✅ YES' if password_match else '❌ NO'}")
            
            if not password_match:
                print("\n   ❌ Password verification failed!")
                print("   Testing with bcrypt directly...")
                import bcrypt
                direct_check = bcrypt.checkpw(
                    password.encode('utf-8'),
                    user.hashed_password.encode('utf-8')
                )
                print(f"   Direct bcrypt check: {'✅ YES' if direct_check else '❌ NO'}")
                return False
            
            if not user.is_active:
                print("\n   ❌ User account is INACTIVE")
                return False
            
            print("\n4. Creating access token...")
            from datetime import timedelta
            access_token = AuthService.create_access_token(
                data={"sub": str(user.id), "username": user.username},
                expires_delta=timedelta(minutes=60 * 24 * 7)
            )
            print(f"   ✅ Token created: {access_token[:40]}...")
            
            print("\n✅✅✅ AUTHENTICATION SUCCESSFUL! ✅✅✅")
            return True
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            await session.close()


if __name__ == "__main__":
    username = "bperak"
    password = "Teachable1A"
    
    print("🔐 LOGIN DEBUG SCRIPT")
    print("=" * 60)
    
    success = asyncio.run(debug_login(username, password))
    
    if success:
        print("\n✅ Login should work!")
        sys.exit(0)
    else:
        print("\n❌ Login will fail - check errors above")
        sys.exit(1)

