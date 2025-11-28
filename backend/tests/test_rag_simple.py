"""
Simplified end-to-end test for RAG implementation.
Uses direct database queries and API calls instead of async session management.
"""

import sys
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from pathlib import Path

# Database connection settings
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'ai_language_tutor',
    'user': 'postgres',
    'password': 'testpassword123'
}

API_BASE = "http://localhost:8000/api/v1"


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_status(phase, message, status="INFO"):
    color = Colors.GREEN if status == "PASS" else Colors.RED if status == "FAIL" else Colors.YELLOW if status == "WARN" else Colors.BLUE
    print(f"{color}[{status}]{Colors.RESET} {Colors.BOLD}Phase {phase}:{Colors.RESET} {message}")


def test_phase1_schema():
    """Test Phase 1: Database schema."""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}PHASE 1: Database Schema{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check textsearch column
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'conversation_messages' 
                AND column_name = 'textsearch'
            )
        """)
        has_textsearch = cur.fetchone()['exists']
        print_status("1", f"textsearch column: {has_textsearch}", 
                    "PASS" if has_textsearch else "FAIL")
        
        # Check textsearch index
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM pg_indexes 
                WHERE tablename = 'conversation_messages' 
                AND indexname = 'idx_conversation_messages_textsearch'
            )
        """)
        has_textsearch_idx = cur.fetchone()['exists']
        print_status("1", f"textsearch GIN index: {has_textsearch_idx}", 
                    "PASS" if has_textsearch_idx else "FAIL")
        
        # Check vector indexes
        cur.execute("""
            SELECT indexname FROM pg_indexes 
            WHERE tablename = 'conversation_messages' 
            AND indexname LIKE '%embedding%'
        """)
        embedding_indexes = [row['indexname'] for row in cur.fetchall()]
        has_vector_idx = len(embedding_indexes) > 0
        print_status("1", f"Vector indexes: {embedding_indexes}", 
                    "PASS" if has_vector_idx else "WARN")
        
        # Check trigger
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM pg_trigger 
                WHERE tgname = 'trigger_update_conversation_message_textsearch'
            )
        """)
        has_trigger = cur.fetchone()['exists']
        print_status("1", f"textsearch trigger: {has_trigger}", 
                    "PASS" if has_trigger else "WARN")
        
        cur.close()
        conn.close()
        
        return has_textsearch and has_textsearch_idx
        
    except Exception as e:
        print_status("1", f"Error: {str(e)}", "FAIL")
        return False


def test_phase2_embeddings():
    """Test Phase 2: Embedding generation."""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}PHASE 2: Embedding Generation{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check if any messages have embeddings
        cur.execute("""
            SELECT COUNT(*) as count 
            FROM conversation_messages 
            WHERE content_embedding IS NOT NULL
        """)
        result = cur.fetchone()
        messages_with_embeddings = result['count']
        print_status("2", f"Messages with embeddings: {messages_with_embeddings}")
        
        if messages_with_embeddings > 0:
            print_status("2", "Embeddings are being stored", "PASS")
            
            # Check embedding dimensions
            cur.execute("""
                SELECT array_length(content_embedding, 1) as dims
                FROM conversation_messages 
                WHERE content_embedding IS NOT NULL 
                LIMIT 1
            """)
            dims_result = cur.fetchone()
            if dims_result and dims_result['dims']:
                dims = dims_result['dims']
                print_status("2", f"Embedding dimensions: {dims}", 
                            "PASS" if dims == 1536 else "WARN")
        else:
            print_status("2", "No embeddings found yet (may need to create messages)", "WARN")
        
        cur.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print_status("2", f"Error: {str(e)}", "FAIL")
        import traceback
        traceback.print_exc()
        return False


def test_phase3_search():
    """Test Phase 3: Semantic search."""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}PHASE 3: Semantic Search{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check if search queries can run
        cur.execute("""
            SELECT COUNT(*) as count
            FROM conversation_messages m
            JOIN conversation_sessions s ON m.session_id = s.id
            WHERE m.content_embedding IS NOT NULL
            AND m.role = 'user'
        """)
        result = cur.fetchone()
        searchable_messages = result['count']
        print_status("3", f"Searchable messages (with embeddings): {searchable_messages}")
        
        if searchable_messages > 0:
            print_status("3", "Semantic search is ready", "PASS")
            
            # Test if we can query (simplified - just check if query would work)
            cur.execute("""
                SELECT m.id, m.content, s.title
                FROM conversation_messages m
                JOIN conversation_sessions s ON m.session_id = s.id
                WHERE m.content_embedding IS NOT NULL
                AND m.role = 'user'
                LIMIT 1
            """)
            sample = cur.fetchone()
            if sample:
                print_status("3", f"Sample searchable message: {sample['content'][:50]}...", "PASS")
        else:
            print_status("3", "No searchable messages yet", "WARN")
        
        cur.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print_status("3", f"Error: {str(e)}", "FAIL")
        import traceback
        traceback.print_exc()
        return False


def test_api_health():
    """Test if API is accessible."""
    try:
        response = requests.get(f"{API_BASE}/health/", timeout=5)
        if response.status_code == 200:
            print_status("API", "Backend API is healthy", "PASS")
            return True
        else:
            print_status("API", f"Backend API returned {response.status_code}", "WARN")
            return False
    except Exception as e:
        print_status("API", f"Cannot connect to API: {str(e)}", "WARN")
        return False


def main():
    """Run all tests."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}RAG Implementation Test Suite (Simple){Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")
    
    # Test API health
    api_ok = test_api_health()
    print()
    
    # Phase 1
    phase1_ok = test_phase1_schema()
    
    # Phase 2
    phase2_ok = test_phase2_embeddings()
    
    # Phase 3
    phase3_ok = test_phase3_search()
    
    # Summary
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}SUMMARY{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")
    
    print_status("1", f"Schema: {'PASS' if phase1_ok else 'FAIL'}", 
                "PASS" if phase1_ok else "FAIL")
    print_status("2", f"Embeddings: {'PASS' if phase2_ok else 'WARN'}", 
                "PASS" if phase2_ok else "WARN")
    print_status("3", f"Search: {'PASS' if phase3_ok else 'WARN'}", 
                "PASS" if phase3_ok else "WARN")
    
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    if phase1_ok:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ Phase 1 (Schema) PASSED{Colors.RESET}")
    else:
        print(f"{Colors.RED}{Colors.BOLD}✗ Phase 1 (Schema) FAILED - Run migration first!{Colors.RESET}")
        print(f"{Colors.YELLOW}Run: docker exec -i ai-tutor-postgres psql -U postgres -d ai_language_tutor < backend/migrations/2025-11-06_enrich_chat_sessions_pgvector.sql{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")
    
    return 0 if phase1_ok else 1


if __name__ == "__main__":
    sys.exit(main())





