"""
API v1 router aggregation.

This module combines all v1 API endpoints into a single router
for inclusion in the main FastAPI application.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import health, knowledge, auth, conversations, content, learning, srs, admin, analytics, grammar


api_router = APIRouter()

# Include endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
api_router.include_router(content.router, prefix="/content", tags=["content-analysis"])
api_router.include_router(learning.router, prefix="/learning", tags=["learning"])
api_router.include_router(srs.router, prefix="/srs", tags=["srs"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(grammar.router, prefix="/grammar", tags=["grammar"])

# Future endpoint routers will be added here:
# api_router.include_router(users.router, prefix="/users", tags=["users"])
# api_router.include_router(learning.router, prefix="/learning", tags=["learning"])