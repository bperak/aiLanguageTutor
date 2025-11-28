"""
Authentication endpoints for user registration, login, and management.
"""

from datetime import timedelta
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_postgresql_session
from app.services.auth_service import AuthService, get_current_active_user
from app.schemas.user import (
    UserCreate, UserResponse, UserLogin, Token, 
    UserUpdate, UserProfile, TokenData
)
from app.models.database_models import User

router = APIRouter()

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/token")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_postgresql_session)
) -> User:
    """Dependency to get current authenticated user."""
    return await AuthService.get_current_user(db, token)


async def get_current_active_user_dep(
    current_user: User = Depends(get_current_user)
) -> User:
    """Dependency to get current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


async def get_optional_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_postgresql_session)
) -> User | None:
    """Return the user if a valid Bearer token is present, otherwise None.

    This lets public endpoints glean user context for analytics without enforcing auth.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    try:
        user = await AuthService.get_current_user(db, token)
        return user
    except Exception:
        return None


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_create: UserCreate,
    db: AsyncSession = Depends(get_postgresql_session)
):
    """
    Register a new user account.
    
    Creates a new user with the provided information and returns the user data.
    Passwords are securely hashed using bcrypt.
    """
    try:
        user = await AuthService.create_user(db, user_create)
        response = UserResponse.from_orm(user)
        # Add profile_completed flag to response
        response_dict = response.dict()
        response_dict["profile_completed"] = False
        response_dict["profile_skipped"] = False
        return response_dict
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_postgresql_session)
):
    """
    Login endpoint that returns a JWT access token.
    
    Accepts username/email and password, returns JWT token on successful authentication.
    Token expires after 7 days by default.
    """
    user = await AuthService.authenticate_user(
        db, form_data.username, form_data.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=60 * 24 * 7)  # 7 days
    access_token = AuthService.create_access_token(
        data={"sub": str(user.id), "username": user.username},
        expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=int(access_token_expires.total_seconds()),
        user_id=user.id
    )


@router.post("/login", response_model=Token)
async def login_user(
    user_login: UserLogin,
    db: AsyncSession = Depends(get_postgresql_session)
):
    """
    Alternative login endpoint accepting JSON payload.
    
    Same functionality as /token but accepts JSON instead of form data.
    """
    user = await AuthService.authenticate_user(
        db, user_login.username, user_login.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    access_token_expires = timedelta(minutes=60 * 24 * 7)  # 7 days
    access_token = AuthService.create_access_token(
        data={"sub": str(user.id), "username": user.username},
        expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=int(access_token_expires.total_seconds()),
        user_id=user.id
    )


@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: User = Depends(get_current_active_user_dep)
):
    """
    Get current user information.
    
    Returns the authenticated user's profile information.
    """
    return UserResponse.from_orm(current_user)


@router.get("/profile-status")
async def get_profile_status(
    current_user: User = Depends(get_current_active_user_dep),
    db: AsyncSession = Depends(get_postgresql_session)
):
    """Get profile completion status for guards."""
    from app.services.profile_building_service import profile_building_service
    status_data = await profile_building_service.check_profile_completion(
        db, current_user.id
    )
    return {
        "profile_completed": status_data["completed"],
        "profile_skipped": status_data["skipped"]
    }


@router.get("/profile", response_model=UserProfile)
async def get_user_profile(
    current_user: User = Depends(get_current_active_user_dep),
    db: AsyncSession = Depends(get_postgresql_session)
):
    """
    Get extended user profile with learning statistics.
    
    Returns user information along with learning progress data.
    """
    # Get learning progress (if exists)
    from sqlalchemy import select
    from app.models.database_models import UserLearningProgress
    
    result = await db.execute(
        select(UserLearningProgress).where(
            UserLearningProgress.user_id == current_user.id
        )
    )
    progress = result.scalar_one_or_none()
    
    # Create profile response
    profile_data = UserProfile.from_orm(current_user)
    
    if progress:
        profile_data.total_study_time_minutes = progress.total_study_time_minutes
        profile_data.total_conversations = progress.total_conversations
        profile_data.total_words_learned = progress.total_words_learned
        profile_data.current_streak_days = progress.current_streak_days
        profile_data.assessed_level = progress.assessed_level
    
    return profile_data


@router.put("/profile", response_model=UserResponse)
async def update_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user_dep),
    db: AsyncSession = Depends(get_postgresql_session)
):
    """
    Update user profile information.
    
    Updates the authenticated user's profile with the provided data.
    Only non-null fields in the request will be updated.
    """
    # Convert Pydantic model to dict, excluding None values
    update_data = user_update.dict(exclude_unset=True)
    
    if not update_data:
        return UserResponse.from_orm(current_user)
    
    updated_user = await AuthService.update_user(db, current_user, update_data)
    return UserResponse.from_orm(updated_user)


@router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: User = Depends(get_current_active_user_dep),
    db: AsyncSession = Depends(get_postgresql_session)
):
    """
    Change user password.
    
    Requires the current password for verification before setting the new password.
    """
    success = await AuthService.change_password(
        db, current_user, current_password, new_password
    )
    
    if success:
        return {"message": "Password changed successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to change password"
        )


@router.post("/deactivate")
async def deactivate_account(
    current_user: User = Depends(get_current_active_user_dep),
    db: AsyncSession = Depends(get_postgresql_session)
):
    """
    Deactivate user account.
    
    Marks the user account as inactive. The user will no longer be able to log in.
    """
    success = await AuthService.deactivate_user(db, current_user)
    
    if success:
        return {"message": "Account deactivated successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to deactivate account"
        )


@router.get("/verify-token")
async def verify_token(
    current_user: User = Depends(get_current_active_user_dep)
):
    """
    Verify JWT token validity.
    
    Returns user information if the token is valid and the user is active.
    """
    return {
        "valid": True,
        "user_id": str(current_user.id),
        "username": current_user.username,
        "is_active": current_user.is_active
    }


@router.get("/health")
async def auth_health_check():
    """Health check for authentication service."""
    return {
        "status": "healthy",
        "service": "authentication",
        "features": {
            "registration": "available",
            "login": "available",
            "jwt_tokens": "available",
            "password_hashing": "bcrypt",
            "token_expiry": "7_days"
        }
    }
