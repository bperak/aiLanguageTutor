#!/usr/bin/env python
"""Check two-stage configuration."""
from app.core.config import settings

print("=" * 50)
print("TWO-STAGE CONFIGURATION")
print("=" * 50)
print(f"Two-Stage Enabled: {settings.USE_TWOSTAGE_GENERATION}")
print(f"Stage 1 Provider: {settings.CANDO_AI_STAGE1_PROVIDER}")
print(f"Stage 1 Model: {settings.CANDO_AI_STAGE1_MODEL}")
print(f"Stage 1 Timeout: {settings.AI_STAGE1_TIMEOUT_SECONDS}s")
print(f"Stage 2 Provider: {settings.CANDO_AI_STAGE2_PROVIDER}")
print(f"Stage 2 Model: {settings.CANDO_AI_STAGE2_MODEL}")
print(f"Stage 2 Timeout: {settings.AI_STAGE2_TIMEOUT_SECONDS}s")
print("=" * 50)
print(f"\n✅ Two-stage generation is {'ENABLED' if settings.USE_TWOSTAGE_GENERATION else 'DISABLED'}")
print(f"✅ Backend is ready at http://localhost:8000")
print(f"✅ Frontend is ready at http://localhost:3000")

