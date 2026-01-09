#!/usr/bin/env python3
"""
Script to create an admin user in the database.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import init_postgresql, get_postgresql_session
from app.models.database_models import User
from app.services.auth_service import AuthService
from sqlalchemy import select


async def create_admin_user():
    """Create admin user if it doesn't exist."""
    init_postgresql()
    async for db in get_postgresql_session():
        try:
            # Check if user already exists
            result = await db.execute(
                select(User).where(User.username == "bperak_admin")
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                print(f"User 'bperak_admin' already exists (ID: {existing_user.id})")
                # Update password in case it changed
                existing_user.hashed_password = AuthService.get_password_hash("Teachable1A")
                existing_user.is_active = True
                existing_user.is_superuser = True
                await db.commit()
                print("Password updated and user activated.")
                return
            
            # Create new user
            new_user = User(
                username="bperak_admin",
                email="bperak_admin@example.com",
                hashed_password=AuthService.get_password_hash("Teachable1A"),
                is_active=True,
                is_superuser=True,
            )
            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)
            print(f"User 'bperak_admin' created successfully (ID: {new_user.id})")
            break
        except Exception as e:
            print(f"Error creating user: {e}")
            await db.rollback()
            raise
        finally:
            await db.close()


if __name__ == "__main__":
    asyncio.run(create_admin_user())
