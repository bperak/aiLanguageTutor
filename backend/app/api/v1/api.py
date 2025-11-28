"""
API v1 router aggregation.

This module combines all v1 API endpoints into a single router
for inclusion in the main FastAPI application.
"""

from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    health,
    grammar,
    conversations,
    knowledge,
    content,
    ai_content,
    learning,
    srs,
    analytics,
    admin,
    lexical,
    cando as cando_alias,
    profile,
    home_chat,
)

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(grammar.router, prefix="/grammar", tags=["grammar"])
api_router.include_router(
    conversations.router, prefix="/conversations", tags=["conversations"]
)
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(content.router, prefix="/content", tags=["content"])
api_router.include_router(ai_content.router, prefix="/ai-content", tags=["ai-content"])
api_router.include_router(learning.router, prefix="/learning", tags=["learning"])
api_router.include_router(srs.router, prefix="/srs", tags=["srs"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(lexical.router, prefix="/lexical", tags=["lexical"])
# Clean CanDo namespace (aliasing selected lexical endpoints)
api_router.include_router(cando_alias.router, prefix="/cando", tags=["cando"])
api_router.include_router(profile.router, prefix="/profile", tags=["profile"])
api_router.include_router(home_chat.router, prefix="/home", tags=["home"])
