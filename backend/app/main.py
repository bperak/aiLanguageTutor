"""
AI Language Tutor Backend API - Main FastAPI application.

This module initializes the FastAPI application with all necessary middleware,
routers, and configuration for the AI Language Tutor platform.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Any

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.api import api_router
from app.core.config import settings
from app.db import close_db_connections, init_db_connections
from app.services.lexical_lessons_service import lexical_lessons


logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    
    Handles startup and shutdown events for database connections
    and other resources.
    """
    # Startup
    logger.info("Starting AI Language Tutor Backend API")
    await init_db_connections()
    logger.info("Database connections initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Language Tutor Backend API")
    await close_db_connections()
    logger.info("Database connections closed")


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        FastAPI: The configured FastAPI application instance.
    """
    app = FastAPI(
        title="AI Language Tutor API",
        description="Intelligent, personalized multi-language learning platform",
        version="0.1.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )
    
    # Configure CORS (widen in DEBUG to simplify Docker-based E2E tests)
    if settings.DEBUG:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Specific origins when credentials are used
            allow_origin_regex=r"https?://localhost(:\d+)?",
            allow_credentials=True,  # Allow credentials for cookie-based auth
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_origin_regex=r"https?://localhost(:\d+)?",
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    # Include API router
    app.include_router(api_router, prefix="/api/v1")
    
    return app


app = create_application()


@app.get("/health")
async def health_check() -> JSONResponse:
    """
    Health check endpoint.
    
    Returns:
        JSONResponse: Application health status.
    """
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "ai-language-tutor-backend",
            "version": "0.1.0",
        }
    )


@app.get("/")
async def root() -> dict[str, str]:
    """
    Root endpoint.
    
    Returns:
        dict: Welcome message and API information.
    """
    return {
        "message": "Welcome to AI Language Tutor API",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/api/lessons/activate")
async def activate_lesson_compat(can_do_id: str) -> Dict[str, Any]:
    """
    Compatibility endpoint expected by MCP scenarios:
    /api/lessons/activate?can_do_id=...

    Internally delegates to lexical_lessons.activate_cando.
    """
    return await lexical_lessons.activate_cando(can_do_id=can_do_id)