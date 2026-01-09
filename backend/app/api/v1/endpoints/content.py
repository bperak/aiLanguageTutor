"""
Content analysis endpoint (Phase 2 minimal version).

Provides a simple text-based analysis stub that returns a structured
response. This keeps the API contract stable while we iterate on
the underlying analysis pipeline.
"""

from datetime import datetime
from typing import List, Optional

import httpx
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks, Query
from pydantic import BaseModel, Field, HttpUrl
from app.db import neo4j_driver


router = APIRouter()


class SourceMetadata(BaseModel):
    """Minimal source metadata for attribution."""

    title: str
    author: Optional[str] = None
    url: Optional[str] = None
    language: str = Field(default="ja", max_length=10)


class ContentSubmission(BaseModel):
    """Content submission payload for analysis."""

    text: str = Field(min_length=1, description="Raw text to analyze")
    source: SourceMetadata


class ExtractedItem(BaseModel):
    """A minimal representation of an extracted knowledge item."""

    kind: str  # e.g., "vocabulary", "grammar_point"
    value: str
    confidence: float = Field(ge=0.0, le=1.0)


class AnalysisResponse(BaseModel):
    """Structured response for a content analysis request."""

    status: str
    processed_chars: int
    items: List[ExtractedItem]
    source: SourceMetadata
    analyzed_at: datetime
    persisted: Optional[bool] = None
    persisted_count: int = 0


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_content(request: ContentSubmission) -> AnalysisResponse:
    """
    Analyze submitted text and return a minimal structured result.

    This is a simple, deterministic implementation to unblock
    Phase 2 integration and testing. It does not call external AI
    providers yet.
    """

    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text must not be empty")

    # Minimal heuristic: extract the first token-like unit as a demo item
    items = _extract_items(text, max_items=5)
    return AnalysisResponse(
        status="ok",
        processed_chars=len(text),
        items=items,
        source=request.source,
        analyzed_at=datetime.utcnow(),
    )


class UrlSubmission(BaseModel):
    url: HttpUrl
    source: SourceMetadata


def _analyze_text(text: str, source: SourceMetadata) -> AnalysisResponse:
    text = text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text must not be empty")
    items = _extract_items(text, max_items=5)
    return AnalysisResponse(
        status="ok",
        processed_chars=len(text),
        items=items,
        source=source,
        analyzed_at=datetime.utcnow(),
    )


@router.post("/analyze-url", response_model=AnalysisResponse)
async def analyze_url(payload: UrlSubmission, background_tasks: BackgroundTasks = None) -> AnalysisResponse:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(str(payload.url))
            resp.raise_for_status()
            content = resp.text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {e}")
    return _analyze_text(content, payload.source)


@router.post("/analyze-upload", response_model=AnalysisResponse)
async def analyze_upload(
    file: UploadFile = File(...),
    title: str = Form(...),
    language: str = Form("ja"),
    author: Optional[str] = Form(None),
    url: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = None,
) -> AnalysisResponse:
    try:
        raw = await file.read()
        text = raw.decode("utf-8", errors="ignore")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read upload: {e}")
    source = SourceMetadata(title=title, author=author, url=url, language=language)
    return _analyze_text(text, source)


@router.post("/analyze-persist", response_model=AnalysisResponse)
async def analyze_and_persist(
    request: ContentSubmission,
    min_confidence: float = Query(0.7, ge=0.0, le=1.0),
) -> AnalysisResponse:
    """Analyze text then persist a minimal node and source in Neo4j if available."""
    result = await analyze_content(request)
    persisted_flag = False
    persisted_count = 0
    try:
        if neo4j_driver is not None and result.items:
            async with neo4j_driver.session() as session:
                source = request.source
                cypher = (
                    "MERGE (s:Source {title: $title}) "
                    "SET s.author = $author, s.url = $url, s.language = $language "
                    "WITH s, $value as value "
                    "MERGE (t:ExtractedTerm {value: value}) "
                    "MERGE (t)-[:SOURCED_FROM]->(s) "
                    "RETURN t.value AS value"
                )
                for item in result.items:
                    if item.confidence < min_confidence:
                        continue
                    rec = await (await session.run(
                        cypher,
                        {
                            "title": source.title,
                            "author": source.author,
                            "url": source.url,
                            "language": source.language,
                            "value": item.value,
                        },
                    )).single()
                    if rec is not None:
                        persisted_count += 1
                persisted_flag = persisted_count > 0
    except Exception:
        persisted_flag = False
    result.persisted = persisted_flag
    result.persisted_count = persisted_count
    return result


@router.get("/term")
async def get_term(value: str, title: Optional[str] = None) -> dict:
    """Verify if a persisted term (and optionally its source) exists in Neo4j."""
    if neo4j_driver is None:
        return {"found": False, "reason": "neo4j_unavailable"}
    try:
        async with neo4j_driver.session() as session:
            if title:
                cypher = (
                    "MATCH (t:ExtractedTerm {value: $value})-[:SOURCED_FROM]->(s:Source {title: $title})"
                    " RETURN t.value AS value LIMIT 1"
                )
                rec = await (await session.run(cypher, {"value": value, "title": title})).single()
            else:
                cypher = "MATCH (t:ExtractedTerm {value: $value}) RETURN t.value AS value LIMIT 1"
                rec = await (await session.run(cypher, {"value": value})).single()
            return {"found": rec is not None}
    except Exception as e:
        return {"found": False, "error": str(e)}


def _extract_items(text: str, max_items: int = 5) -> List[ExtractedItem]:
    """Very simple token extraction with naive confidence."""
    import re

    # Split on whitespace, keep tokens with letters/numbers or CJK
    raw_tokens = re.findall(r"[\w\u3040-\u30ff\u4e00-\u9fff]+", text)
    seen: set[str] = set()
    items: List[ExtractedItem] = []
    for tok in raw_tokens:
        token = tok.strip()
        if not token:
            continue
        if token in seen:
            continue
        seen.add(token)
        # Confidence heuristic
        is_cjk = re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", token) is not None
        if len(token) >= 3 or is_cjk:
            conf = 0.9
        else:
            conf = 0.5
        items.append(ExtractedItem(kind="vocabulary", value=token, confidence=conf))
        if len(items) >= max_items:
            break
    if not items:
        # Fallback to first word
        first = text.split()[0]
        items.append(ExtractedItem(kind="vocabulary", value=first, confidence=0.5))
    return items


