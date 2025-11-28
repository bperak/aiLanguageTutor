"""
Authentication service for JWT-based user authentication.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import structlog
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.core.config import settings
from app.models.database_models import User
from app.schemas.user import UserCreate, TokenData

logger = structlog.get_logger()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
ALGORITHM = settings.JWT_ALGORITHM
SECRET_KEY = settings.JWT_SECRET_KEY
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days


class AuthService:
    """Authentication service for user management."""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash a password."""
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Optional[TokenData]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id: str = payload.get("sub")
            username: str = payload.get("username")
            
            if user_id is None:
                return None
                
            token_data = TokenData(user_id=user_id, username=username)
            return token_data
            
        except JWTError as e:
            logger.warning("JWT verification failed", error=str(e))
            return None
    
    @staticmethod
    async def authenticate_user(
        db: AsyncSession, 
        username: str, 
        password: str
    ) -> Optional[User]:
        """Authenticate a user with username/email and password."""
        try:
            # Try to find user by username or email
            result = await db.execute(
                select(User).where(
                    (User.username == username) | (User.email == username)
                )
            )
            user = result.scalar_one_or_none()
            
            if not user:
                logger.info("User not found", username=username)
                return None
            
            if not AuthService.verify_password(password, user.hashed_password):
                logger.info("Invalid password", username=username)
                return None
            
            if not user.is_active:
                logger.info("User account is inactive", username=username)
                return None
            
            logger.info("User authenticated successfully", 
                       user_id=str(user.id), 
                       username=user.username)
            return user
            
        except Exception as e:
            logger.error("Authentication error", 
                        username=username, 
                        error=str(e))
            return None
    
    @staticmethod
    async def get_current_user(db: AsyncSession, token: str) -> User:
        """Get current user from JWT token."""
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        token_data = AuthService.verify_token(token)
        if token_data is None:
            raise credentials_exception
        
        try:
            result = await db.execute(
                select(User).where(User.id == token_data.user_id)
            )
            user = result.scalar_one_or_none()
            
            if user is None:
                raise credentials_exception
                
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User account is inactive"
                )
            
            return user
            
        except Exception as e:
            logger.error("Error getting current user", 
                        user_id=str(token_data.user_id), 
                        error=str(e))
            raise credentials_exception
    
    @staticmethod
    async def create_user(db: AsyncSession, user_create: UserCreate) -> User:
        """Create a new user account."""
        try:
            # Check if username already exists
            result = await db.execute(
                select(User).where(User.username == user_create.username)
            )
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already registered"
                )
            
            # Check if email already exists
            result = await db.execute(
                select(User).where(User.email == user_create.email)
            )
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            
            # Create new user
            hashed_password = AuthService.get_password_hash(user_create.password)
            
            # Apply safe defaults for columns that may not have DB defaults
            db_user = User(
                email=user_create.email,
                username=user_create.username,
                hashed_password=hashed_password,
                full_name=user_create.full_name,
                native_language=user_create.native_language or "en",
                target_languages=user_create.target_languages or ["ja"],
                current_level=user_create.current_level or "beginner",
                learning_goals=user_create.learning_goals or [],
                study_time_preference=(
                    user_create.study_time_preference if user_create.study_time_preference is not None else 30
                ),
                difficulty_preference=user_create.difficulty_preference or "adaptive",
                preferred_ai_provider=user_create.preferred_ai_provider or "openai",
                conversation_style=user_create.conversation_style or "balanced",
                max_conversation_length=(
                    user_create.max_conversation_length if user_create.max_conversation_length is not None else 50
                ),
                auto_save_conversations=(
                    user_create.auto_save_conversations if user_create.auto_save_conversations is not None else True
                ),
                is_active=True,
                is_verified=False,
                profile_completed=False,
                profile_skipped=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            
            db.add(db_user)
            await db.commit()
            await db.refresh(db_user)
            
            logger.info("User created successfully", 
                       user_id=str(db_user.id), 
                       username=db_user.username,
                       email=db_user.email)
            
            return db_user
            
        except HTTPException:
            raise
        except Exception as e:
            await db.rollback()
            logger.error("Error creating user", 
                        username=user_create.username,
                        email=user_create.email,
                        error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user account"
            )
    
    @staticmethod
    async def update_user(
        db: AsyncSession, 
        user: User, 
        user_update: Dict[str, Any]
    ) -> User:
        """Update user information."""
        try:
            # Update user fields
            for field, value in user_update.items():
                if hasattr(user, field) and value is not None:
                    setattr(user, field, value)
            
            user.updated_at = datetime.utcnow()
            
            await db.commit()
            await db.refresh(user)
            
            logger.info("User updated successfully", 
                       user_id=str(user.id),
                       updated_fields=list(user_update.keys()))
            
            return user
            
        except Exception as e:
            await db.rollback()
            logger.error("Error updating user", 
                        user_id=str(user.id),
                        error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user"
            )
    
    @staticmethod
    async def change_password(
        db: AsyncSession, 
        user: User, 
        current_password: str, 
        new_password: str
    ) -> bool:
        """Change user password."""
        try:
            # Verify current password
            if not AuthService.verify_password(current_password, user.hashed_password):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Current password is incorrect"
                )
            
            # Hash new password
            user.hashed_password = AuthService.get_password_hash(new_password)
            user.updated_at = datetime.utcnow()
            
            await db.commit()
            
            logger.info("Password changed successfully", user_id=str(user.id))
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            await db.rollback()
            logger.error("Error changing password", 
                        user_id=str(user.id),
                        error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to change password"
            )
    
    @staticmethod
    async def deactivate_user(db: AsyncSession, user: User) -> bool:
        """Deactivate user account."""
        try:
            user.is_active = False
            user.updated_at = datetime.utcnow()
            
            await db.commit()
            
            logger.info("User deactivated", user_id=str(user.id))
            return True
            
        except Exception as e:
            await db.rollback()
            logger.error("Error deactivating user", 
                        user_id=str(user.id),
                        error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to deactivate user"
            )


# Utility functions for dependency injection
async def get_current_active_user(
    db: AsyncSession,
    token: str
) -> User:
    """Dependency to get current active user."""
    user = await AuthService.get_current_user(db, token)
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return user
