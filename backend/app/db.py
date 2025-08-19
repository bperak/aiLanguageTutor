"""
Database connection management for PostgreSQL and Neo4j.

This module handles the initialization and management of database
connections for both the relational database (PostgreSQL) and graph database (Neo4j).
"""

import structlog
from neo4j import AsyncGraphDatabase, AsyncDriver
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


logger = structlog.get_logger()

# Global database clients
neo4j_driver: AsyncDriver | None = None
postgresql_engine: AsyncEngine | None = None
AsyncSessionLocal: sessionmaker | None = None


async def init_neo4j() -> AsyncDriver:
    """
    Initialize Neo4j database connection.
    
    Returns:
        AsyncDriver: Neo4j async driver instance.
        
    Raises:
        Exception: If connection fails.
    """
    global neo4j_driver
    
    try:
        neo4j_driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
            max_connection_pool_size=10,
        )
        
        # Verify connectivity
        await neo4j_driver.verify_connectivity()
        logger.info("Neo4j connection established", uri=settings.NEO4J_URI)
        
        return neo4j_driver
        
    except Exception as e:
        logger.error("Failed to connect to Neo4j", error=str(e))
        raise


def init_postgresql() -> AsyncEngine:
    """
    Initialize PostgreSQL database connection.
    
    Returns:
        AsyncEngine: SQLAlchemy async engine instance.
        
    Raises:
        Exception: If connection fails.
    """
    global postgresql_engine, AsyncSessionLocal
    
    try:
        postgresql_engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
        )
        
        AsyncSessionLocal = sessionmaker(
            postgresql_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        logger.info("PostgreSQL connection established", url=settings.DATABASE_URL.split('@')[1])
        return postgresql_engine
        
    except Exception as e:
        logger.error("Failed to connect to PostgreSQL", error=str(e))
        raise


async def init_db_connections() -> None:
    """Initialize all database connections."""
    # Initialize PostgreSQL
    try:
        init_postgresql()
    except Exception as e:
        logger.error("PostgreSQL connection failed", error=str(e))
        raise
    
    # Initialize Neo4j
    try:
        await init_neo4j()
    except Exception as e:
        logger.warning("Neo4j connection failed, continuing without it", error=str(e))


async def close_db_connections() -> None:
    """Close all database connections."""
    global neo4j_driver, postgresql_engine
    
    if neo4j_driver:
        await neo4j_driver.close()
        neo4j_driver = None
        logger.info("Neo4j connection closed")
    
    if postgresql_engine:
        await postgresql_engine.dispose()
        postgresql_engine = None
        logger.info("PostgreSQL connection closed")


async def get_neo4j_session():
    """
    Get Neo4j database session.
    
    Dependency for FastAPI endpoints.
    
    Returns:
        AsyncSession: Neo4j async session.
        
    Raises:
        RuntimeError: If Neo4j driver is not initialized.
    """
    if not neo4j_driver:
        raise RuntimeError("Neo4j driver not initialized")
    
    async with neo4j_driver.session() as session:
        yield session


async def get_postgresql_session() -> AsyncSession:
    """
    Get PostgreSQL database session.
    
    Dependency for FastAPI endpoints.
    
    Returns:
        AsyncSession: SQLAlchemy async session.
        
    Raises:
        RuntimeError: If PostgreSQL engine is not initialized.
    """
    if not AsyncSessionLocal:
        raise RuntimeError("PostgreSQL session maker not initialized")
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()