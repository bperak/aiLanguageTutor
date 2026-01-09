"""Script to reset user password."""
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


async def reset_password(username: str, new_password: str):
    """Reset user password."""
    # Initialize database
    init_postgresql()
    
    async for session in get_postgresql_session():
        try:
            # Find user
            result = await session.execute(
                select(User).where(User.username == username)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                print(f"❌ User '{username}' not found")
                return False
            
            # Hash new password
            new_hash = AuthService.get_password_hash(new_password)
            user.hashed_password = new_hash
            
            await session.commit()
            print(f"✅ Password reset for user '{username}'")
            return True
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error: {e}")
            return False
        finally:
            await session.close()


if __name__ == "__main__":
    username = "bperak"
    password = "Teachable1A"
    
    print(f"Resetting password for user: {username}")
    success = asyncio.run(reset_password(username, password))
    if success:
        print("✅ Password reset successful!")
    else:
        print("❌ Password reset failed!")
        sys.exit(1)

