from __future__ import annotations

import asyncio
import json
import sys
import time

from app.services.ai_chat_service import AIChatService


async def main() -> int:
    chat = AIChatService()
    t0 = time.time()
    try:
        resp = await chat.generate_reply(
            provider="gemini",
            model="gemini-2.5-pro",
            messages=[{"role": "user", "content": "Return the word pong."}],
            system_prompt="Return pong only.",
        )
        dt = time.time() - t0
        print(json.dumps({"ok": True, "latency_s": round(dt, 2), "content": resp.get("content")}, ensure_ascii=False))
        return 0
    except Exception as e:
        dt = time.time() - t0
        print(json.dumps({"ok": False, "latency_s": round(dt, 2), "error": str(e)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))


