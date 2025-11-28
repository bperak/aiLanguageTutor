#!/usr/bin/env python3
"""Test script to check environment variables"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from root directory
env_path = Path(__file__).parent.parent / '.env'
print(f"Loading environment from: {env_path}")
print(f"Environment file exists: {env_path.exists()}")

load_dotenv(env_path)

# Check Neo4j environment variables
print("\nNeo4j Environment Variables:")
print(f"NEO4J_URI: {os.getenv('NEO4J_URI', 'NOT SET')}")
print(f"NEO4J_USER: {os.getenv('NEO4J_USER', 'NOT SET')}")
print(f"NEO4J_PASSWORD: {'SET' if os.getenv('NEO4J_PASSWORD') else 'NOT SET'}")
print(f"NEO4J_PASSWORD length: {len(os.getenv('NEO4J_PASSWORD', ''))}")

# Check all environment variables that start with NEO4J
print("\nAll NEO4J variables:")
for key, value in os.environ.items():
    if key.startswith('NEO4J'):
        if 'PASSWORD' in key:
            print(f"{key}: {'SET' if value else 'NOT SET'} (length: {len(value)})")
        else:
            print(f"{key}: {value}")


