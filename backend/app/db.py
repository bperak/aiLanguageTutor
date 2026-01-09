"""
Database connection management for PostgreSQL and Neo4j.

This module handles the initialization and management of database
connections for both the relational database (PostgreSQL) and graph database (Neo4j).
"""

import structlog
from neo4j import AsyncGraphDatabase, AsyncDriver
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.migrations.postgres_migrator import apply_postgres_sql_migrations


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
            max_connection_pool_size=settings.NEO4J_MAX_CONNECTION_POOL_SIZE,
            # Keep it simple, but set sane defaults for production stability.
            # Reason: prevents request spikes from stalling indefinitely.
            connection_acquisition_timeout=30.0,
            # Reason: recycle connections periodically to avoid stale/broken sockets.
            max_connection_lifetime=60.0 * 60.0,
            # Reason: proactively detect dead connections.
            keep_alive=True,
        )
        # Verify connectivity (with a short retry to handle first-boot race)
        last_err: Exception | None = None
        for _ in range(3):
            try:
                await neo4j_driver.verify_connectivity()
                last_err = None
                break
            except Exception as e:  # noqa: BLE001
                last_err = e
                await asyncio.sleep(0.5)
        if last_err:
            raise last_err
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
        # Ensure DATABASE_URL uses an async driver
        database_url = settings.DATABASE_URL
        if database_url.startswith("postgresql://"):
            # Convert to asyncpg driver for async operations
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif database_url.startswith("postgres://"):
            # Also handle postgres:// alias
            database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
        # If already using async driver (postgresql+asyncpg:// or postgresql+psycopg://), keep it
        
        # Log the actual database URL being used (hide password)
        safe_url = database_url.split('@')[1] if '@' in database_url else database_url
        logger.info("PostgreSQL connection URL", original=settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL, converted=safe_url)
        
        postgresql_engine = create_async_engine(
            database_url,
            echo=settings.DEBUG,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=False,  # Disable to avoid greenlet issues in background tasks
        )
        
        AsyncSessionLocal = sessionmaker(
            postgresql_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        logger.info("PostgreSQL connection established", url=safe_url)
        return postgresql_engine
        
    except Exception as e:
        logger.error("Failed to connect to PostgreSQL", error=str(e))
        raise


async def init_db_connections() -> None:
    """Initialize all database connections."""
    # Initialize PostgreSQL
    try:
        init_postgresql()
        # Reason: `docker-entrypoint-initdb.d/init.sql` only runs on first DB init.
        # For persistent production volumes, apply curated SQL migrations at startup.
        if postgresql_engine is not None:
            await apply_postgres_sql_migrations(engine=postgresql_engine)
    except Exception as e:
        logger.error("PostgreSQL connection failed", error=str(e))
        raise
    
    # Initialize Neo4j with retries to avoid transient boot issues
    for attempt in range(1, 6):
        try:
            await init_neo4j()
            break
        except Exception as e:  # noqa: BLE001
            if attempt == 5:
                logger.warning("Neo4j connection failed after retries, continuing without it", error=str(e))
            else:
                await asyncio.sleep(1.0)


async def close_db_connections() -> None:
    """Close all database connections."""
    global neo4j_driver, postgresql_engine, AsyncSessionLocal
    
    if neo4j_driver:
        await neo4j_driver.close()
        neo4j_driver = None
        logger.info("Neo4j connection closed")
    
    if postgresql_engine:
        await postgresql_engine.dispose()
        postgresql_engine = None
        AsyncSessionLocal = None
        logger.info("PostgreSQL connection closed")


async def get_neo4j_session():
    """
    Get Neo4j database session.

    IMPORTANT: Do not catch exceptions after yielding; FastAPI expects the
    generator to stop on errors (avoids "generator didn't stop after athrow()").
    """
    global neo4j_driver
    if neo4j_driver is None:
        await init_neo4j()
    if neo4j_driver is None:
        raise RuntimeError("Neo4j driver not initialized")

    session = neo4j_driver.session()
    try:
        yield session
    finally:
        try:
            await session.close()
        except Exception:
            # Best-effort close; avoid masking original exceptions
            pass


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
            # Check if session is in a valid state before committing
            # If there's a pending rollback, rollback first
            try:
                await session.commit()
            except Exception as commit_error:
                # Check if it's a PendingRollbackError or similar
                error_type = type(commit_error).__name__
                if "PendingRollback" in error_type or "Rollback" in error_type:
                    # Session needs rollback before commit, rollback and re-raise
                    await session.rollback()
                raise
        except Exception:
            # Rollback on any exception during yield
            try:
                await session.rollback()
            except Exception:
                # Best effort rollback; session may already be rolled back
                pass
            raise
        finally:
            await session.close()