"""
Health check endpoints.

This module provides endpoints for checking the health and status
of the API and its dependencies.
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text

from app.db import get_neo4j_session, get_postgresql_session

logger = structlog.get_logger()
router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    service: str
    version: str
    dependencies: dict[str, str]


@router.get("/", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Basic health check endpoint.

    Returns:
        HealthResponse: Basic health status.
    """
    return HealthResponse(
        status="healthy",
        service="ai-language-tutor-backend",
        version="0.1.0",
        dependencies={},
    )


@router.get("/detailed", response_model=HealthResponse)
async def detailed_health_check(
    neo4j_session=Depends(get_neo4j_session),
    postgresql_session=Depends(get_postgresql_session),
) -> HealthResponse:
    """
    Detailed health check with dependency verification.

    Args:
        neo4j_session: Neo4j database session.
        postgresql_session: PostgreSQL database session.

    Returns:
        HealthResponse: Detailed health status including dependencies.

    Raises:
        HTTPException: If any dependency is unhealthy.
    """
    dependencies = {}

    # Check Neo4j connectivity
    try:
        result = await neo4j_session.run("RETURN 1 as health_check")
        record = await result.single()
        if record and record["health_check"] == 1:
            dependencies["neo4j"] = "healthy"
        else:
            dependencies["neo4j"] = "unhealthy"
    except Exception as e:
        logger.error("Neo4j health check failed", error=str(e))
        dependencies["neo4j"] = "unhealthy"

    # Check PostgreSQL connectivity
    try:
        result = await postgresql_session.execute(text("SELECT 1 as health_check"))
        row = result.fetchone()
        if row and row[0] == 1:
            dependencies["postgresql"] = "healthy"
        else:
            dependencies["postgresql"] = "unhealthy"
    except Exception as e:
        logger.error("PostgreSQL health check failed", error=str(e))
        dependencies["postgresql"] = "unhealthy"

    # Determine overall status
    overall_status = (
        "healthy"
        if all(status == "healthy" for status in dependencies.values())
        else "unhealthy"
    )

    if overall_status == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="One or more dependencies are unhealthy",
        )

    return HealthResponse(
        status=overall_status,
        service="ai-language-tutor-backend",
        version="0.1.0",
        dependencies=dependencies,
    )
