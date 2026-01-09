"""
PHASE 1.1: Database Connection Tests

Tests for verifying PostgreSQL and Neo4j database connections,
required tables, and CanDo descriptor queries.
"""

import pytest
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import text
from neo4j import AsyncSession

# Load .env file
backend_path = Path(__file__).resolve().parent.parent
env_path = backend_path.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # Try to find .env in parent directories
    for parent in backend_path.parents:
        candidate = parent / ".env"
        if candidate.exists():
            load_dotenv(candidate)
            break

from app.db import init_db_connections, close_db_connections, get_neo4j_session, get_postgresql_session
from app.core.config import settings


@pytest.mark.asyncio
async def test_postgresql_connection():
    """
    Test: Connection to PostgreSQL succeeds.
    
    Verifies that PostgreSQL connection can be established
    and basic queries can be executed.
    """
    await init_db_connections()
    try:
        async for pg_session in get_postgresql_session():
            # Test basic query
            result = await pg_session.execute(text("SELECT 1 as test"))
            row = result.scalar()
            assert row == 1, "PostgreSQL connection test query failed"
            
            # Test database version
            result = await pg_session.execute(text("SELECT version()"))
            version = result.scalar()
            assert version is not None, "Could not retrieve PostgreSQL version"
            assert "PostgreSQL" in str(version), "Invalid PostgreSQL version string"
            break
    finally:
        await close_db_connections()


@pytest.mark.asyncio
async def test_neo4j_connection():
    """
    Test: Connection to Neo4j succeeds.
    
    Verifies that Neo4j connection can be established
    and basic queries can be executed.
    """
    await init_db_connections()
    try:
        async for neo_session in get_neo4j_session():
            # Test basic query
            result = await neo_session.run("RETURN 1 as test")
            record = await result.single()
            assert record is not None, "Neo4j connection test query returned no result"
            assert record["test"] == 1, "Neo4j connection test query failed"
            
            # Test database version/info
            result = await neo_session.run("CALL dbms.components() YIELD name, versions, edition")
            record = await result.single()
            assert record is not None, "Could not retrieve Neo4j version info"
            break
    finally:
        await close_db_connections()


@pytest.mark.asyncio
async def test_postgresql_required_tables():
    """
    Test: Required tables exist in PostgreSQL.
    
    Verifies that essential tables (users, user_profiles, learning_paths)
    exist in the database.
    """
    await init_db_connections()
    try:
        async for pg_session in get_postgresql_session():
            # Check users table
            result = await pg_session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'users'
                )
            """))
            assert result.scalar() is True, "users table does not exist"
            
            # Check user_profiles table
            result = await pg_session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'user_profiles'
                )
            """))
            assert result.scalar() is True, "user_profiles table does not exist"
            
            # Check learning_paths table
            result = await pg_session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'learning_paths'
                )
            """))
            assert result.scalar() is True, "learning_paths table does not exist"
            break
    finally:
        await close_db_connections()


@pytest.mark.asyncio
async def test_neo4j_cando_descriptors():
    """
    Test: CanDo descriptors can be queried from Neo4j.
    
    Verifies that CanDo descriptors exist in Neo4j and can be queried
    with the expected structure.
    """
    await init_db_connections()
    try:
        async for neo_session in get_neo4j_session():
            # Query for CanDo descriptors
            query = """
                MATCH (c:CanDoDescriptor)
                RETURN c.uid AS uid, toString(c.level) AS level
                LIMIT 5
            """
            result = await neo_session.run(query)
            records = [record async for record in result]
            
            assert len(records) > 0, "No CanDo descriptors found in Neo4j"
            
            # Verify structure of first record
            first_record = records[0]
            record_keys = first_record.keys()
            assert "uid" in record_keys, "CanDo descriptor missing 'uid' field"
            assert "level" in record_keys, "CanDo descriptor missing 'level' field"
            assert first_record["uid"] is not None, "CanDo descriptor uid is None"
            assert first_record["level"] is not None, "CanDo descriptor level is None"
            
            # Test querying specific CanDo (if JFまるごと:1 exists)
            specific_query = """
                MATCH (c:CanDoDescriptor {uid: $id})
                RETURN c.uid AS uid, toString(c.level) AS level,
                       toString(c.primaryTopic) AS primaryTopic,
                       toString(c.descriptionEn) AS descriptionEn
                LIMIT 1
            """
            result = await neo_session.run(specific_query, id="JFまるごと:1")
            record = await result.single()
            
            # This might not exist, so we just verify the query works
            # If it exists, verify structure
            if record:
                assert "uid" in record, "Specific CanDo query missing 'uid' field"
                assert "level" in record, "Specific CanDo query missing 'level' field"
            break
    finally:
        await close_db_connections()


@pytest.mark.asyncio
async def test_database_connection_pooling():
    """
    Test: Database connections are properly pooled.
    
    Verifies that multiple concurrent connections can be established
    without issues (basic connection pool test).
    """
    await init_db_connections()
    try:
        import asyncio
        
        # Test multiple concurrent PostgreSQL connections
        async def test_pg_connection():
            async for pg_session in get_postgresql_session():
                result = await pg_session.execute(text("SELECT 1"))
                assert result.scalar() == 1
                break
        
        # Test multiple concurrent Neo4j connections
        async def test_neo_connection():
            async for neo_session in get_neo4j_session():
                result = await neo_session.run("RETURN 1 as test")
                record = await result.single()
                assert record["test"] == 1
                break
        
        # Run multiple concurrent connections
        tasks = [test_pg_connection() for _ in range(3)] + [test_neo_connection() for _ in range(3)]
        await asyncio.gather(*tasks)
    finally:
        await close_db_connections()

