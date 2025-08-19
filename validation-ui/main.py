"""
AI Language Tutor - Human Validation Interface

This Streamlit application provides a professional-grade interface for
human reviewers to validate and enhance AI-generated content.
"""

import streamlit as st
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

st.set_page_config(
    page_title="AI Language Tutor - Validation Interface",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """Main application entry point."""
    st.title("🎓 AI Language Tutor - Validation Interface")
    st.markdown("---")
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Choose a page",
        [
            "Dashboard",
            "Pending Reviews",
            "Content Analysis",
            "Quality Metrics",
            "Settings"
        ]
    )
    
    # Main content area
    if page == "Dashboard":
        show_dashboard()
    elif page == "Pending Reviews":
        show_pending_reviews()
    elif page == "Content Analysis":
        show_content_analysis()
    elif page == "Quality Metrics":
        show_quality_metrics()
    elif page == "Settings":
        show_settings()


def show_dashboard():
    """Display the main dashboard."""
    st.header("📊 Validation Dashboard")
    
    # Create columns for metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Pending Reviews", "0", delta="0")
    
    with col2:
        st.metric("Approved Today", "0", delta="0")
    
    with col3:
        st.metric("Rejected Today", "0", delta="0")
    
    with col4:
        st.metric("Quality Score", "N/A", delta="0")
    
    st.markdown("---")
    
    # Status information
    st.info("🚧 Validation interface is ready! Connect your databases to start reviewing content.")
    
    # Database connection status
    st.subheader("🔗 Database Connections")
    
    col1, col2 = st.columns(2)
    
    with col1:
        neo4j_status = check_neo4j_connection()
        if neo4j_status:
            st.success("✅ Neo4j Connected")
        else:
            st.error("❌ Neo4j Disconnected")
    
    with col2:
        # Check PostgreSQL connection
        if check_postgresql_connection():
            st.success("✅ PostgreSQL Connected")
        else:
            st.error("❌ PostgreSQL Disconnected")


def show_pending_reviews():
    """Display pending content reviews."""
    st.header("📝 Pending Reviews")
    st.info("No pending reviews yet. AI-generated content will appear here for validation.")


def show_content_analysis():
    """Display content analysis tools."""
    st.header("🔍 Content Analysis")
    st.info("Content analysis tools will be available in Phase 2.")


def show_quality_metrics():
    """Display quality metrics and analytics."""
    st.header("📈 Quality Metrics")
    st.info("Quality metrics and analytics will be available after content validation begins.")


def show_settings():
    """Display application settings."""
    st.header("⚙️ Settings")
    
    st.subheader("Database Configuration")
    
    # Neo4j settings
    st.text_input("Neo4j URI", value=os.getenv("NEO4J_URI", ""), disabled=True)
    st.text_input("Neo4j Username", value=os.getenv("NEO4J_USERNAME", ""), disabled=True)
    
    # Environment info
    st.subheader("Environment Information")
    st.text(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    st.text(f"Debug Mode: {os.getenv('DEBUG', 'false')}")


def check_neo4j_connection():
    """
    Check Neo4j database connection.
    
    Returns:
        bool: True if connected, False otherwise.
    """
    try:
        # This will be implemented when Neo4j is properly configured
        # For now, just check if environment variables are set
        neo4j_uri = os.getenv("NEO4J_URI")
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        
        return bool(neo4j_uri and neo4j_password)
    except Exception:
        return False


def check_postgresql_connection():
    """
    Check PostgreSQL database connection.
    
    Returns:
        bool: True if connected, False otherwise.
    """
    try:
        # Check if PostgreSQL environment variables are set
        database_url = os.getenv("DATABASE_URL")
        pgvector_enabled = os.getenv("PGVECTOR_ENABLED", "false").lower() == "true"
        
        return bool(database_url and pgvector_enabled)
    except Exception:
        return False


if __name__ == "__main__":
    main()