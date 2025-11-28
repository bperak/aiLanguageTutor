#!/usr/bin/env python
"""Check which OpenAI models are actually available via API."""
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

print("=" * 60)
print("AVAILABLE OPENAI MODELS")
print("=" * 60)

try:
    models = client.models.list()
    
    # Filter for GPT models
    gpt_models = [m for m in models.data if 'gpt' in m.id.lower()]
    gpt_models.sort(key=lambda x: x.id)
    
    print(f"\nFound {len(gpt_models)} GPT models:\n")
    
    for model in gpt_models:
        print(f"  • {model.id}")
        
    print("\n" + "=" * 60)
    
    # Check for specific models
    print("\nCHECKING SPECIFIC MODELS:")
    print("=" * 60)
    
    models_to_check = ["gpt-5", "gpt-5-mini", "gpt-4.1", "gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]
    
    for model_name in models_to_check:
        exists = any(m.id == model_name for m in models.data)
        status = "✅ EXISTS" if exists else "❌ NOT FOUND"
        print(f"{model_name:20s} {status}")
        
except Exception as e:
    print(f"❌ Error: {e}")

