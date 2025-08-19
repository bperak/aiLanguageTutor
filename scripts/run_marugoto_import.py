#!/usr/bin/env python3
"""
Quick runner script for Marugoto Grammar Import
"""

import asyncio
import sys
from pathlib import Path

# Add the resources directory to the path
sys.path.append(str(Path(__file__).parent.parent / "resources"))

from marugoto_grammar_importer import main

if __name__ == "__main__":
    print("🚀 Starting Marugoto Grammar Patterns Import...")
    print("📋 This will:")
    print("   1. Generate romaji with pykakasi")
    print("   2. Validate romaji with Gemini AI")
    print("   3. Import to Neo4j with relationships")
    print("   4. Generate detailed report")
    print()
    
    asyncio.run(main())
