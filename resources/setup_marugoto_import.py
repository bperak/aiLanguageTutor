#!/usr/bin/env python3
"""
Setup script for Marugoto Grammar Import
Helps configure environment variables and test connections
"""

import os
import sys
from pathlib import Path

def setup_environment():
    """Setup environment variables for the import"""
    
    print("🔧 Marugoto Grammar Import Setup")
    print("=" * 40)
    
    # Check if .env file exists
    env_file = Path(".env")
    if env_file.exists():
        print("✅ Found .env file")
        # Load existing .env
        with open(env_file, 'r') as f:
            env_content = f.read()
    else:
        print("⚠️  No .env file found, will create one")
        env_content = ""
    
    # Check required environment variables
    required_vars = {
        'GEMINI_API_KEY': 'Your Google Gemini API key (for AI validation)',
        'NEO4J_URI': 'Neo4j connection URI (default: bolt://localhost:7687)',
        'NEO4J_USER': 'Neo4j username (default: neo4j)',
        'NEO4J_PASSWORD': 'Neo4j password'
    }
    
    missing_vars = []
    
    for var_name, description in required_vars.items():
        current_value = os.getenv(var_name)
        if not current_value and var_name not in env_content:
            missing_vars.append((var_name, description))
        elif current_value:
            print(f"✅ {var_name}: {'*' * min(len(current_value), 8)}")
        else:
            print(f"📝 {var_name}: Found in .env file")
    
    if missing_vars:
        print(f"\n❌ Missing {len(missing_vars)} required environment variables:")
        for var_name, description in missing_vars:
            print(f"   {var_name}: {description}")
        
        print("\n💡 Please set these environment variables:")
        print("   Option 1: Add to your .env file")
        print("   Option 2: Set in your shell:")
        
        for var_name, _ in missing_vars:
            if var_name == 'NEO4J_URI':
                print(f"   export {var_name}=bolt://localhost:7687")
            elif var_name == 'NEO4J_USER':
                print(f"   export {var_name}=neo4j")
            else:
                print(f"   export {var_name}=your_value_here")
        
        return False
    
    print("\n✅ All environment variables are configured!")
    return True

def test_dependencies():
    """Test if required Python packages are installed"""
    
    print("\n🧪 Testing Dependencies")
    print("=" * 25)
    
    required_packages = [
        'pandas',
        'pykakasi', 
        'neo4j',
        'google.generativeai'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package}")
    
    if missing_packages:
        print(f"\n❌ Missing {len(missing_packages)} required packages:")
        for package in missing_packages:
            print(f"   {package}")
        
        print("\n💡 Install missing packages:")
        print("   pip install " + " ".join(missing_packages))
        return False
    
    print("\n✅ All dependencies are installed!")
    return True

def test_connections():
    """Test connections to external services"""
    
    print("\n🔗 Testing Connections")
    print("=" * 22)
    
    # Test Neo4j connection
    try:
        from neo4j import GraphDatabase
        
        neo4j_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
        neo4j_password = os.getenv('NEO4J_PASSWORD', 'password')
        
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            result.single()
        driver.close()
        
        print("✅ Neo4j connection successful")
        neo4j_ok = True
        
    except Exception as e:
        print(f"❌ Neo4j connection failed: {e}")
        neo4j_ok = False
    
    # Test Gemini API
    try:
        import google.generativeai as genai
        
        api_key = os.getenv('GEMINI_API_KEY')
        if api_key:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            # Simple test
            response = model.generate_content("Test")
            print("✅ Gemini AI connection successful")
            gemini_ok = True
        else:
            print("⚠️  Gemini API key not set (AI validation will be disabled)")
            gemini_ok = False
            
    except Exception as e:
        print(f"❌ Gemini AI connection failed: {e}")
        gemini_ok = False
    
    return neo4j_ok, gemini_ok

def main():
    """Main setup function"""
    
    print("🚀 Setting up Marugoto Grammar Import Environment")
    print("=" * 50)
    
    # Step 1: Check environment variables
    env_ok = setup_environment()
    
    # Step 2: Check dependencies
    deps_ok = test_dependencies()
    
    # Step 3: Test connections (if env vars are set)
    if env_ok and deps_ok:
        neo4j_ok, gemini_ok = test_connections()
    else:
        neo4j_ok = gemini_ok = False
    
    # Summary
    print("\n📋 Setup Summary")
    print("=" * 16)
    print(f"Environment Variables: {'✅' if env_ok else '❌'}")
    print(f"Python Dependencies: {'✅' if deps_ok else '❌'}")
    print(f"Neo4j Connection: {'✅' if neo4j_ok else '❌'}")
    print(f"Gemini AI: {'✅' if gemini_ok else '⚠️ '}")
    
    if env_ok and deps_ok and neo4j_ok:
        print("\n🎉 Setup complete! You can now run:")
        print("   python scripts/run_marugoto_import.py")
    else:
        print("\n❌ Setup incomplete. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
