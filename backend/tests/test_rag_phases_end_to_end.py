"""
End-to-end test script for RAG implementation phases 1, 2, and 3.

This script tests:
- Phase 1: Database schema updates (textsearch column, HNSW index)
- Phase 2: Embedding generation for chat messages
- Phase 3: Semantic search and RAG integration
"""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import text, select
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.database_models import User, ConversationSession, ConversationMessage
from app.services.embedding_service import EmbeddingService
from app.services.conversation_service import ConversationService
from app.db import init_postgresql
import app.db as db_module


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_status(phase: str, message: str, status: str = "INFO"):
    """Print colored status message."""
    color = Colors.GREEN if status == "PASS" else Colors.RED if status == "FAIL" else Colors.YELLOW if status == "WARN" else Colors.BLUE
    print(f"{color}[{status}]{Colors.RESET} {Colors.BOLD}Phase {phase}:{Colors.RESET} {message}")


async def test_phase1_database_schema(db: AsyncSession):
    """Test Phase 1: Database schema updates."""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}PHASE 1: Database Schema Updates{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")
    
    results = {
        "textsearch_column": False,
        "textsearch_index": False,
        "hnsw_index": False,
        "textsearch_trigger": False
    }
    
    try:
        # Check if textsearch column exists
        result = await db.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'conversation_messages' 
                AND column_name = 'textsearch'
            )
        """))
        results["textsearch_column"] = result.scalar()
        print_status("1", f"textsearch column exists: {results['textsearch_column']}", 
                    "PASS" if results["textsearch_column"] else "FAIL")
        
        # Check if textsearch GIN index exists
        result = await db.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM pg_indexes 
                WHERE tablename = 'conversation_messages' 
                AND indexname = 'idx_conversation_messages_textsearch'
            )
        """))
        results["textsearch_index"] = result.scalar()
        print_status("1", f"textsearch GIN index exists: {results['textsearch_index']}", 
                    "PASS" if results["textsearch_index"] else "FAIL")
        
        # Check if HNSW index exists (or ivfflat as fallback)
        result = await db.execute(text("""
            SELECT indexname FROM pg_indexes 
            WHERE tablename = 'conversation_messages' 
            AND indexname LIKE '%embedding%'
        """))
        index_names = [row[0] for row in result.fetchall()]
        results["hnsw_index"] = any('hnsw' in name.lower() for name in index_names) or any('embedding' in name.lower() for name in index_names)
        print_status("1", f"Vector index exists: {index_names}", 
                    "PASS" if results["hnsw_index"] else "WARN")
        
        # Check if trigger exists
        result = await db.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM pg_trigger 
                WHERE tgname = 'trigger_update_conversation_message_textsearch'
            )
        """))
        results["textsearch_trigger"] = result.scalar()
        print_status("1", f"textsearch trigger exists: {results['textsearch_trigger']}", 
                    "PASS" if results["textsearch_trigger"] else "WARN")
        
        # Test trigger functionality
        if results["textsearch_column"]:
            test_message_id = uuid4()
            await db.execute(text("""
                INSERT INTO conversation_messages 
                (id, session_id, role, content, message_order, created_at)
                VALUES (:id, :session_id, 'user', 'Test message', 1, NOW())
                ON CONFLICT DO NOTHING
            """), {
                'id': test_message_id,
                'session_id': uuid4()  # Dummy session ID
            })
            
            result = await db.execute(text("""
                SELECT textsearch FROM conversation_messages WHERE id = :id
            """), {'id': test_message_id})
            textsearch_value = result.scalar()
            trigger_works = textsearch_value is not None
            print_status("1", f"Trigger auto-populates textsearch: {trigger_works}", 
                        "PASS" if trigger_works else "FAIL")
            
            # Cleanup
            await db.execute(text("DELETE FROM conversation_messages WHERE id = :id"), {'id': test_message_id})
            await db.commit()
        
        phase1_passed = all([results["textsearch_column"], results["textsearch_index"]])
        return phase1_passed, results
        
    except Exception as e:
        print_status("1", f"Error testing schema: {str(e)}", "FAIL")
        return False, results


async def test_phase2_embedding_generation(db: AsyncSession):
    """Test Phase 2: Embedding generation for messages."""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}PHASE 2: Embedding Generation{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")
    
    try:
        # Create a test user if needed
        test_user_result = await db.execute(
            select(User).where(User.email == "test_rag@example.com").limit(1)
        )
        test_user = test_user_result.scalar_one_or_none()
        
        if not test_user:
            test_user = User(
                id=uuid4(),
                email="test_rag@example.com",
                username="test_rag_user",
                hashed_password="test_hash",
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.add(test_user)
            await db.commit()
            await db.refresh(test_user)
        
        # Create a test session
        test_session = ConversationSession(
            id=uuid4(),
            user_id=test_user.id,
            language_code="ja",
            session_type="home",
            ai_provider="openai",
            ai_model="gpt-4o-mini",
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(test_session)
        await db.commit()
        await db.refresh(test_session)
        
        print_status("2", f"Created test session: {test_session.id}")
        
        # Create a test message
        test_content = "こんにちは、元気ですか？"  # "Hello, how are you?" in Japanese
        test_message = ConversationMessage(
            id=uuid4(),
            session_id=test_session.id,
            role="user",
            content=test_content,
            message_order=1,
            created_at=datetime.utcnow()
        )
        db.add(test_message)
        await db.commit()
        await db.refresh(test_message)
        
        print_status("2", f"Created test message: {test_message.id}")
        
        # Generate embedding
        embedding_service = EmbeddingService()
        try:
            embedding = await embedding_service.generate_and_store_message_embedding(
                message_id=str(test_message.id),
                content=test_content,
                postgresql_session=db,
                provider="openai"
            )
            
            if embedding and len(embedding) == 1536:
                print_status("2", f"Embedding generated successfully (dimensions: {len(embedding)})", "PASS")
                
                # Verify embedding is stored
                result = await db.execute(text("""
                    SELECT content_embedding FROM conversation_messages WHERE id = :id
                """), {'id': test_message.id})
                stored_embedding = result.scalar()
                
                if stored_embedding:
                    print_status("2", "Embedding stored in database", "PASS")
                    phase2_passed = True
                else:
                    print_status("2", "Embedding not found in database", "FAIL")
                    phase2_passed = False
            else:
                print_status("2", f"Invalid embedding generated: {len(embedding) if embedding else 0} dimensions", "FAIL")
                phase2_passed = False
                
        except Exception as e:
            print_status("2", f"Error generating embedding: {str(e)}", "FAIL")
            phase2_passed = False
            
        # Cleanup
        await db.execute(text("DELETE FROM conversation_messages WHERE id = :id"), {'id': test_message.id})
        await db.execute(text("DELETE FROM conversation_sessions WHERE id = :id"), {'id': test_session.id})
        await db.commit()
        
        return phase2_passed
        
    except Exception as e:
        print_status("2", f"Error testing embedding generation: {str(e)}", "FAIL")
        import traceback
        traceback.print_exc()
        return False


async def test_phase3_semantic_search(db: AsyncSession):
    """Test Phase 3: Semantic search and RAG integration."""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}PHASE 3: Semantic Search & RAG{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")
    
    try:
        # Create test user
        test_user_result = await db.execute(
            select(User).where(User.email == "test_rag_search@example.com").limit(1)
        )
        test_user = test_user_result.scalar_one_or_none()
        
        if not test_user:
            test_user = User(
                id=uuid4(),
                email="test_rag_search@example.com",
                username="test_rag_search",
                hashed_password="test_hash",
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.add(test_user)
            await db.commit()
            await db.refresh(test_user)
        
        # Create test session
        test_session = ConversationSession(
            id=uuid4(),
            user_id=test_user.id,
            language_code="ja",
            session_type="home",
            ai_provider="openai",
            ai_model="gpt-4o-mini",
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(test_session)
        await db.commit()
        await db.refresh(test_session)
        
        # Create multiple test messages with embeddings
        test_messages = [
            ("私は日本語を勉強しています", "I am studying Japanese"),
            ("今日は天気がいいです", "The weather is nice today"),
            ("お寿司を食べたいです", "I want to eat sushi"),
        ]
        
        message_ids = []
        embedding_service = EmbeddingService()
        
        for i, (content_ja, content_en) in enumerate(test_messages, 1):
            msg = ConversationMessage(
                id=uuid4(),
                session_id=test_session.id,
                role="user",
                content=content_ja,
                message_order=i,
                created_at=datetime.utcnow()
            )
            db.add(msg)
            await db.commit()
            await db.refresh(msg)
            message_ids.append(msg.id)
            
            # Generate embedding
            try:
                await embedding_service.generate_and_store_message_embedding(
                    message_id=str(msg.id),
                    content=content_ja,
                    postgresql_session=db,
                    provider="openai"
                )
            except Exception as e:
                print_status("3", f"Warning: Could not generate embedding for message {i}: {str(e)}", "WARN")
        
        print_status("3", f"Created {len(message_ids)} test messages with embeddings")
        
        # Test vector search
        query_text = "日本語の勉強"  # "Japanese study"
        query_embedding = await embedding_service.generate_content_embedding(query_text, "openai")
        
        similar_messages = await ConversationService.search_similar_past_conversations(
            db=db,
            user_id=test_user.id,
            query_embedding=query_embedding,
            limit=5
        )
        
        if similar_messages:
            print_status("3", f"Vector search found {len(similar_messages)} similar messages", "PASS")
            for i, msg in enumerate(similar_messages[:3], 1):
                print_status("3", f"  {i}. Similarity: {msg['similarity']:.3f} - {msg['content'][:50]}...")
        else:
            print_status("3", "Vector search returned no results", "WARN")
        
        # Test hybrid search
        hybrid_results = await ConversationService.hybrid_search_past_conversations(
            db=db,
            user_id=test_user.id,
            query_text=query_text,
            query_embedding=query_embedding,
            limit=5
        )
        
        if hybrid_results:
            print_status("3", f"Hybrid search found {len(hybrid_results)} results", "PASS")
            for i, result in enumerate(hybrid_results[:3], 1):
                print_status("3", f"  {i}. Score: {result['score']:.3f} - {result['content'][:50]}...")
        else:
            print_status("3", "Hybrid search returned no results (may be expected if textsearch not populated)", "WARN")
        
        # Test user profile building
        profile = await ConversationService.build_user_conversation_profile(
            db=db,
            user_id=test_user.id,
            days_back=90
        )
        
        if profile.get('has_profile'):
            print_status("3", f"User profile built: {profile['message_count']} messages analyzed", "PASS")
            print_status("3", f"  Session types: {profile.get('session_types', [])}")
            print_status("3", f"  Topics: {len(profile.get('topics', []))} topics")
        else:
            print_status("3", "User profile could not be built", "WARN")
        
        # Cleanup
        for msg_id in message_ids:
            await db.execute(text("DELETE FROM conversation_messages WHERE id = :id"), {'id': msg_id})
        await db.execute(text("DELETE FROM conversation_sessions WHERE id = :id"), {'id': test_session.id})
        await db.commit()
        
        phase3_passed = len(similar_messages) > 0 or len(hybrid_results) > 0
        return phase3_passed
        
    except Exception as e:
        print_status("3", f"Error testing semantic search: {str(e)}", "FAIL")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all phase tests."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}RAG Implementation End-to-End Test Suite{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")
    
    # Initialize database connection
    print_status("INIT", "Initializing database connection...")
    try:
        init_postgresql()
        if not db_module.AsyncSessionLocal:
            print_status("INIT", "Failed to initialize database session", "FAIL")
            return 1
        print_status("INIT", "Database connection initialized", "PASS")
    except Exception as e:
        print_status("INIT", f"Failed to initialize database: {str(e)}", "FAIL")
        import traceback
        traceback.print_exc()
        return 1
    
    async with db_module.AsyncSessionLocal() as db:
        try:
            # Phase 1: Database Schema
            phase1_passed, phase1_results = await test_phase1_database_schema(db)
            
            # Phase 2: Embedding Generation
            phase2_passed = await test_phase2_embedding_generation(db)
            
            # Phase 3: Semantic Search
            phase3_passed = await test_phase3_semantic_search(db)
            
            # Summary
            print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
            print(f"{Colors.BOLD}TEST SUMMARY{Colors.RESET}")
            print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")
            
            print_status("1", f"Database Schema: {'PASS' if phase1_passed else 'FAIL'}", 
                        "PASS" if phase1_passed else "FAIL")
            print_status("2", f"Embedding Generation: {'PASS' if phase2_passed else 'FAIL'}", 
                        "PASS" if phase2_passed else "FAIL")
            print_status("3", f"Semantic Search: {'PASS' if phase3_passed else 'FAIL'}", 
                        "PASS" if phase3_passed else "FAIL")
            
            all_passed = phase1_passed and phase2_passed and phase3_passed
            
            print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
            if all_passed:
                print(f"{Colors.GREEN}{Colors.BOLD}✓ ALL PHASES PASSED{Colors.RESET}")
            else:
                print(f"{Colors.RED}{Colors.BOLD}✗ SOME PHASES FAILED{Colors.RESET}")
            print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")
            
            return 0 if all_passed else 1
            
        except Exception as e:
            print_status("ERROR", f"Test suite failed: {str(e)}", "FAIL")
            import traceback
            traceback.print_exc()
            return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

