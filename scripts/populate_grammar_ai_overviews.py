#!/usr/bin/env python3
"""
Populate AI grammar overviews for missing GrammarPattern nodes.

- Finds patterns where `ai_overview` or `what_is` is missing
- Generates overview JSON using AI (OpenAI gpt-4.5 by default, or Gemini 2.5)
- Persists results back to Neo4j via GrammarAIContentService

Usage (examples):
  python scripts/populate_grammar_ai_overviews.py --dry-run --limit 10
  python scripts/populate_grammar_ai_overviews.py --limit 5 --provider openai --model gpt-4.5
  python scripts/populate_grammar_ai_overviews.py --provider gemini --model gemini-2.5-flash --delay 1.5

Notes:
  - Requires valid API keys in .env (OPENAI_API_KEY and/or GEMINI_API_KEY)
  - Uses project .env from repo root; does not modify it
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv


# Ensure UTF-8 console on Windows
if sys.platform == "win32":
    import codecs

    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())


# Resolve project root and load .env
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

# Make backend package importable
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db import init_neo4j  # type: ignore  # noqa: E402
import app.db as db  # type: ignore  # noqa: E402
from app.services.grammar_ai_content_service import (  # type: ignore  # noqa: E402
    GrammarAIContentService,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(PROJECT_ROOT / "ai_content_generation.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("grammar_ai_populator")


@dataclass
class RunStats:
    processed: int = 0
    generated: int = 0
    skipped: int = 0
    failed: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class GrammarAIPopulator:
    def __init__(self, provider: str, model: str, force: bool = False) -> None:
        self.provider = provider
        self.model = model
        self.force = force
        self.session = None
        self.stats = RunStats()
        self.service = GrammarAIContentService()

    async def initialize(self) -> None:
        await init_neo4j()
        # Create a long-lived session for this script lifecycle
        driver = getattr(db, "neo4j_driver", None)
        if driver is None:
            raise RuntimeError("Neo4j driver not initialized")
        self.session = driver.session()
        self.stats.start_time = datetime.utcnow()
        logger.info("Initialized Neo4j session")

    async def cleanup(self) -> None:
        if self.session:
            try:
                await self.session.close()
            except Exception:
                pass
        self.stats.end_time = datetime.utcnow()

    async def find_missing_patterns(self, limit: int, offset: int) -> List[Dict[str, Any]]:
        assert self.session is not None
        query = """
        MATCH (g:GrammarPattern)
        WHERE g.ai_overview IS NULL OR g.what_is IS NULL
        RETURN g.id AS id, g.sequence_number AS sequence_number, g.pattern AS pattern
        ORDER BY coalesce(g.sequence_number, 0)
        SKIP $offset
        LIMIT $limit
        """
        tx = await self.session.begin_transaction()
        try:
            result = await tx.run(query, offset=offset, limit=limit)
            data = await result.values("id", "sequence_number", "pattern")
        finally:
            await tx.commit()
        rows: List[Dict[str, Any]] = [
            {"id": id_, "sequence_number": seq, "pattern": pat}
            for id_, seq, pat in data
        ]
        return rows

    async def process_pattern(self, pattern_id: str) -> bool:
        assert self.session is not None
        try:
            logger.info("Generating overview", extra={"pattern_id": pattern_id, "provider": self.provider, "model": self.model})
            overview = await self.service.generate_overview(
                session=self.session,
                pattern_id=pattern_id,
                provider=self.provider,
                model=self.model,
                force=self.force,
            )
            ok = bool(overview and isinstance(overview, dict) and overview.get("what_is"))
            if ok:
                self.stats.generated += 1
                logger.info("Stored overview", extra={"pattern_id": pattern_id})
            else:
                # Stored anyway for caching; mark as processed
                self.stats.generated += 1
            return True
        except Exception as e:  # noqa: BLE001
            self.stats.failed += 1
            logger.error("Failed to generate overview", extra={"pattern_id": pattern_id, "error": str(e)})
            return False

    async def run(self, *, limit: int, offset: int, delay: float, dry_run: bool) -> None:
        items = await self.find_missing_patterns(limit=limit, offset=offset)
        if not items:
            logger.info("No GrammarPattern nodes need AI overviews. All set!")
            return

        logger.info("Found %d patterns missing AI overview/what_is", len(items))
        for i, item in enumerate(items, 1):
            pid = item["id"]
            self.stats.processed += 1
            if dry_run:
                logger.info("DRY RUN %d/%d - would process %s (%s)", i, len(items), pid, item.get("pattern") or "")
                continue
            ok = await self.process_pattern(pid)
            if i < len(items) and delay > 0:
                await asyncio.sleep(delay)

    def log_summary(self) -> None:
        elapsed = None
        if self.stats.start_time and self.stats.end_time:
            elapsed = (self.stats.end_time - self.stats.start_time).total_seconds()
        logger.info(
            "Summary | processed=%d generated=%d skipped=%d failed=%d elapsed=%ss",
            self.stats.processed,
            self.stats.generated,
            self.stats.skipped,
            self.stats.failed,
            f"{elapsed:.1f}" if elapsed is not None else "n/a",
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Populate AI overviews for GrammarPattern nodes")
    parser.add_argument("--limit", type=int, default=20, help="Max patterns to process")
    parser.add_argument("--offset", type=int, default=0, help="Offset for paging through patterns")
    parser.add_argument("--provider", choices=["openai", "gemini"], default="openai", help="AI provider")
    parser.add_argument(
        "--model",
        type=str,
        default=os.getenv("GRAMMAR_AI_DEFAULT_MODEL", "gpt-4.5"),
        help="Model name to use (e.g., gpt-4.5 or gemini-2.5-flash)",
    )
    parser.add_argument("--force", action="store_true", help="Regenerate even if overview exists")
    parser.add_argument("--delay", type=float, default=0.8, help="Delay between requests (seconds)")
    parser.add_argument("--dry-run", action="store_true", help="List targets without generating")
    return parser.parse_args()


async def main_async() -> int:
    args = parse_args()
    populator = GrammarAIPopulator(provider=args.provider, model=args.model, force=args.force)
    try:
        await populator.initialize()
        await populator.run(limit=args.limit, offset=args.offset, delay=args.delay, dry_run=args.dry_run)
    finally:
        await populator.cleanup()
        populator.log_summary()
    return 0


def main() -> None:
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("Interrupted")


if __name__ == "__main__":
    main()


