#!/usr/bin/env python3
"""Test different ways to import google-genai"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

print("Testing import methods...")

# Method 1: from google import genai
try:
    from google import genai
    print("✓ Method 1 SUCCESS: from google import genai")
    print(f"  Client available: {hasattr(genai, 'Client')}")
except Exception as e:
    print(f"✗ Method 1 FAILED: from google import genai")
    print(f"  Error: {e}")

# Method 2: import genai
try:
    import genai
    print("✓ Method 2 SUCCESS: import genai")
    print(f"  Client available: {hasattr(genai, 'Client')}")
except Exception as e:
    print(f"✗ Method 2 FAILED: import genai")
    print(f"  Error: {e}")

# Method 3: from google.genai import Client
try:
    from google.genai import Client
    print("✓ Method 3 SUCCESS: from google.genai import Client")
except Exception as e:
    print(f"✗ Method 3 FAILED: from google.genai import Client")
    print(f"  Error: {e}")

# Method 4: Check what's in google
try:
    import google
    print(f"\nGoogle package contents: {dir(google)}")
    print(f"Google __path__: {google.__path__}")
except Exception as e:
    print(f"Could not inspect google: {e}")

