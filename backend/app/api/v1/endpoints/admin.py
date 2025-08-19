"""
Admin endpoints (minimal RBAC): require username to start with 'admin_'.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db import get_postgresql_session
from app.models.database_models import User


router = APIRouter()


class AdminHealth(BaseModel):
    status: str
    user: str


def require_admin(current_user: User) -> None:
    if not current_user.username.lower().startswith("admin_"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )


@router.get("/health", response_model=AdminHealth)
async def admin_health(
    db: AsyncSession = Depends(get_postgresql_session),
    current_user: User = Depends(get_current_user),
) -> AdminHealth:
    require_admin(current_user)
    return AdminHealth(status="ok", user=current_user.username)


