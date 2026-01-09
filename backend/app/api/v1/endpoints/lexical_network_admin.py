"""
Lexical Network Admin API Endpoints

Provides control interface for lexical network building operations.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from neo4j import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db import get_neo4j_session
from app.schemas.lexical_network import (
    BuildResult,
    JobConfig,
    JobResult,
    JobStatus,
    ModelInfo,
    NetworkStats,
)
from app.services.lexical_network.ai_provider_config import (
    list_available_models as get_available_models,
)
from app.services.lexical_network.job_manager_service import job_manager
from app.services.lexical_network.relation_builder_service import (
    RelationBuilderService,
)

router = APIRouter()

relation_builder = RelationBuilderService()


# ============ Dashboard ============


@router.get("/stats", response_model=NetworkStats)
async def get_network_stats(
    session: AsyncSession = Depends(get_neo4j_session),
) -> NetworkStats:
    """Get overall lexical network statistics."""
    
    # Categorize relationship types
    LEXICAL_TYPES = {"LEXICAL_RELATION", "SYNONYM_OF", "SIMILAR_TO"}
    LEARNING_TYPES = {"PREREQUISITE_FOR", "SAME_LEVEL", "SAME_SKILLDOMAIN"}
    SEMANTIC_TYPES = {"SAME_TYPE", "SAME_TOPIC", "SEMANTICALLY_SIMILAR"}
    
    # Total words
    result = await session.run("MATCH (w:Word) RETURN count(w) AS count")
    total_words = (await result.single())["count"]
    
    # ========== ALL Relationship Types ==========
    result = await session.run(
        """
        MATCH ()-[r]->()
        RETURN type(r) AS rel_type, count(r) AS count
        ORDER BY count DESC
        """
    )
    all_relations_by_type: Dict[str, int] = {}
    for record in await result.data():
        rel_type = record["rel_type"]
        count = record["count"]
        if rel_type:
            all_relations_by_type[rel_type] = count
    
    # Categorize relationships
    relations_by_category: Dict[str, int] = {
        "lexical": 0,
        "learning": 0,
        "semantic": 0,
        "other": 0,
    }
    for rel_type, count in all_relations_by_type.items():
        if rel_type in LEXICAL_TYPES:
            relations_by_category["lexical"] += count
        elif rel_type in LEARNING_TYPES:
            relations_by_category["learning"] += count
        elif rel_type in SEMANTIC_TYPES:
            relations_by_category["semantic"] += count
        else:
            relations_by_category["other"] += count
    
    # Lexical relations only (what we're building)
    lexical_relations: Dict[str, int] = {
        k: v for k, v in all_relations_by_type.items() if k in LEXICAL_TYPES
    }
    total_relations = sum(lexical_relations.values())
    
    # ========== POS Distribution (use canonical if available, fallback to pos_primary) ==========
    result = await session.run(
        """
        MATCH (w:Word)
        WHERE coalesce(w.pos_primary_norm, w.pos_primary) IS NOT NULL
        RETURN coalesce(w.pos_primary_norm, w.pos_primary) AS pos, count(*) AS count
        ORDER BY count DESC
        """
    )
    pos_distribution = {r["pos"]: r["count"] for r in await result.data() if r["pos"]}
    
    # ========== Difficulty Distribution ==========
    result = await session.run(
        """
        MATCH (w:Word)
        WHERE w.difficulty IS NOT NULL OR w.difficulty_numeric IS NOT NULL
        RETURN coalesce(w.difficulty, 'Unknown') AS difficulty, count(*) AS count
        ORDER BY count DESC
        """
    )
    difficulty_distribution = {r["difficulty"]: r["count"] for r in await result.data()}
    
    # ========== Lexical Relations by POS (use canonical) ==========
    result = await session.run(
        """
        MATCH (w:Word)-[r:LEXICAL_RELATION|SYNONYM_OF|SIMILAR_TO]-()
        WHERE coalesce(w.pos_primary_norm, w.pos_primary) IS NOT NULL
        RETURN coalesce(w.pos_primary_norm, w.pos_primary) AS pos, type(r) AS rel_type, count(r) AS count
        ORDER BY count DESC
        """
    )
    relations_by_pos: Dict[str, Dict[str, int]] = {}
    for record in await result.data():
        pos = record["pos"]
        rel_type = record["rel_type"]
        count = record["count"]
        if pos not in relations_by_pos:
            relations_by_pos[pos] = {}
        relations_by_pos[pos][rel_type] = count
    
    # ========== Words without lexical relations ==========
    result = await session.run(
        """
        MATCH (w:Word)
        WHERE NOT (w)-[:LEXICAL_RELATION|SYNONYM_OF|SIMILAR_TO]-()
        RETURN count(w) AS count
        """
    )
    words_without_relations = (await result.single())["count"]
    
    # ========== Most Connected Words (lexical) ==========
    result = await session.run(
        """
        MATCH (w:Word)-[r:LEXICAL_RELATION|SYNONYM_OF|SIMILAR_TO]-()
        WITH w, count(r) AS rel_count
        RETURN coalesce(w.standard_orthography, w.kanji) AS word,
               w.translation AS translation,
               coalesce(w.pos_primary_norm, w.pos_primary) AS pos,
               rel_count
        ORDER BY rel_count DESC
        LIMIT 10
        """
    )
    most_connected_words = [dict(r) for r in await result.data()]
    
    # Legacy: relations_by_type (for backwards compatibility)
    result = await session.run(
        """
        MATCH ()-[r:LEXICAL_RELATION]->()
        RETURN r.relation_type AS type, count(*) AS count
        """
    )
    relations_by_type = {r["type"]: r["count"] for r in await result.data() if r["type"]}
    
    return NetworkStats(
        total_words=total_words,
        total_relations=total_relations,
        lexical_relations=lexical_relations,
        relations_by_pos=relations_by_pos,
        all_relations_by_type=all_relations_by_type,
        relations_by_category=relations_by_category,
        pos_distribution=pos_distribution,
        difficulty_distribution=difficulty_distribution,
        avg_relations_per_word=total_relations / max(total_words, 1),
        words_without_relations=words_without_relations,
        most_connected_words=most_connected_words,
        relations_by_type=relations_by_type,
    )


# ============ Jobs ============


@router.post("/jobs", response_model=Dict[str, str])
async def create_job(
    config: JobConfig,
    current_user=Depends(get_current_user),
) -> Dict[str, str]:
    """Create a new lexical network job."""
    
    job_id = await job_manager.create_job(config)
    return {"job_id": job_id, "status": "pending"}


@router.post("/jobs/{job_id}/start", response_model=Dict[str, str])
async def start_job(
    job_id: str,
    current_user=Depends(get_current_user),
) -> Dict[str, str]:
    """Start a pending job."""
    
    success = await job_manager.start_job(job_id)
    if not success:
        raise HTTPException(400, "Job not found or already started")
    return {"job_id": job_id, "status": "running"}


@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str) -> JobStatus:
    """Get job status and progress."""
    
    job_status = await job_manager.get_job_status(job_id)
    if not job_status:
        raise HTTPException(404, "Job not found")
    return job_status


@router.get("/relations/sample")
async def relations_sample(
    limit: int = Query(20, ge=1, le=200),
    source: Optional[str] = Query(None, description="Filter by source standard_orthography"),
    pos: Optional[str] = Query(None, description="Filter by source POS (canonical: pos_primary_norm/pos1, fallback: pos_primary)"),
    pos_list: Optional[str] = Query(None, description="Comma-separated POS list"),
    rel_type: Optional[str] = Query(None, description="Filter by relation_type (single)"),
    rel_types: Optional[str] = Query(None, description="Comma-separated relation_type list"),
    session: AsyncSession = Depends(get_neo4j_session),
    current_user=Depends(get_current_user),
):
    """
    Return a sample of LEXICAL_RELATION edges with optional filters.
    Supports single pos/rel_type or comma-separated lists via pos_list/rel_types.
    """
    query = """
    WITH
      (CASE WHEN $pos_list IS NOT NULL THEN [p IN split($pos_list, ',') WHERE trim(p) <> ''] ELSE [] END) AS posList,
      (CASE WHEN $rel_types IS NOT NULL THEN [r IN split($rel_types, ',') WHERE trim(r) <> ''] ELSE [] END) AS relList
    MATCH (s:Word)-[r:LEXICAL_RELATION]->(t:Word)
    WHERE ($source IS NULL OR s.standard_orthography = $source)
      AND (
        ($pos IS NULL AND size(posList)=0)
        OR coalesce(s.pos_primary_norm, s.pos_primary) = $pos
        OR coalesce(s.pos_primary_norm, s.pos_primary) IN posList
      )
      AND (
        ($rel_type IS NULL AND size(relList)=0)
        OR r.relation_type = $rel_type
        OR r.relation_type IN relList
      )
    RETURN
      s.standard_orthography AS source,
      coalesce(s.pos_primary_norm, s.pos1, s.pos_primary) AS source_pos,
      t.standard_orthography AS target,
      coalesce(t.pos_primary_norm, t.pos1, t.pos_primary) AS target_pos,
      r.relation_type AS rel_type,
      r.relation_category AS rel_category,
      r.weight AS weight,
      r.confidence AS confidence,
      r.is_symmetric AS is_symmetric,
      r.domain_tags AS domain_tags,
      r.domain_weights AS domain_weights,
      r.context_tags AS context_tags,
      r.context_weights AS context_weights,
      r.register_source AS register_source,
      r.register_target AS register_target,
      r.formality_difference AS formality_difference,
      r.target_orthography_raw AS raw_orth,
      r.target_reading_raw AS raw_reading,
      r.resolution_method AS resolution,
      r.resolution_confidence AS res_conf,
      r.ai_provider AS ai_provider,
      r.ai_model AS ai_model,
      r.ai_temperature AS ai_temperature,
      r.ai_request_id AS ai_request_id,
      r.created_utc AS created_utc,
      r.updated_utc AS updated_utc,
      properties(r) AS edge_properties
    ORDER BY r.created_utc DESC
    LIMIT $limit
    """
    result = await session.run(
        query,
        limit=limit,
        source=source,
        pos=pos,
        pos_list=pos_list,
        rel_type=rel_type,
        rel_types=rel_types,
    )
    return await result.data()


@router.post("/jobs/preview", response_model=Dict[str, Any])
async def preview_job_words(
    config: JobConfig,
    session: AsyncSession = Depends(get_neo4j_session),
    current_user=Depends(get_current_user),
) -> Dict[str, Any]:
    """Preview the words that would be processed for a given job config."""
    
    words = await job_manager.get_words_for_job(session, config)
    return {
        "words": words,
        "count": len(words),
        "source": config.source,
        "max_words": config.max_words,
    }


@router.get("/jobs", response_model=List[JobStatus])
async def list_jobs(
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> List[JobStatus]:
    """List all jobs."""
    
    return await job_manager.list_jobs(status=status, limit=limit)


@router.post("/jobs/{job_id}/cancel", response_model=Dict[str, str])
async def cancel_job(
    job_id: str,
    current_user=Depends(get_current_user),
) -> Dict[str, str]:
    """Cancel a running job."""
    
    success = await job_manager.cancel_job(job_id)
    if not success:
        raise HTTPException(400, "Job not found or not running")
    return {"job_id": job_id, "status": "cancelled"}


# ============ Quick Actions ============


@router.post("/build-relations", response_model=BuildResult)
async def build_relations_for_word(
    word: str = Query(..., description="Target word"),
    relation_types: List[str] = Query(["SYNONYM"]),
    model: str = Query("gpt-4o-mini"),
    session: AsyncSession = Depends(get_neo4j_session),
    current_user=Depends(get_current_user),
) -> BuildResult:
    """Build relations for a single word (immediate execution)."""
    
    from app.schemas.lexical_network import JobConfig
    
    config = JobConfig(
        job_type="relation_building",
        source="word_list",
        word_list=[word],
        relation_types=relation_types,
        model=model,
        max_words=1,
        batch_size=20,
    )
    
    result = await relation_builder.build_relations_for_word(session, word, config)
    return result


# ============ POS-based Operations ============


@router.get("/words-by-pos")
async def get_words_by_pos(
    pos: str = Query(..., description="POS tag: 形容詞, 名詞, 動詞, etc."),
    limit: int = Query(50, ge=1, le=500),
    has_relations: Optional[bool] = Query(None),
    session: AsyncSession = Depends(get_neo4j_session),
) -> Dict[str, Any]:
    """Get words filtered by POS."""
    
    if has_relations is None:
        query = """
        MATCH (w:Word)
        WHERE coalesce(w.pos_primary_norm, w.pos1, w.pos_primary) = $pos
        OPTIONAL MATCH (w)-[r:LEXICAL_RELATION|SYNONYM_OF|SIMILAR_TO]-()
        RETURN coalesce(w.standard_orthography, w.kanji) AS word,
               w.translation AS translation,
               count(r) AS relation_count
        ORDER BY relation_count DESC
        LIMIT $limit
        """
    elif has_relations:
        query = """
        MATCH (w:Word)-[r:LEXICAL_RELATION|SYNONYM_OF|SIMILAR_TO]-()
        WHERE coalesce(w.pos_primary_norm, w.pos1, w.pos_primary) = $pos
        RETURN coalesce(w.standard_orthography, w.kanji) AS word,
               w.translation AS translation,
               count(r) AS relation_count
        ORDER BY relation_count DESC
        LIMIT $limit
        """
    else:
        query = """
        MATCH (w:Word)
        WHERE coalesce(w.pos_primary_norm, w.pos1, w.pos_primary) = $pos
        AND NOT (w)-[:LEXICAL_RELATION|SYNONYM_OF|SIMILAR_TO]-()
        RETURN coalesce(w.standard_orthography, w.kanji) AS word,
               w.translation AS translation,
               0 AS relation_count
        LIMIT $limit
        """
    
    result = await session.run(query, pos=pos, limit=limit)
    words = await result.data()
    
    return {"pos": pos, "count": len(words), "words": words}


# ============ Centrality Analysis ============


@router.get("/centrality")
async def get_centrality_analysis(
    metric: str = Query("degree", description="degree, betweenness, pagerank"),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_neo4j_session),
) -> Dict[str, Any]:
    """Get words ranked by centrality measures."""
    
    if metric == "degree":
        query = """
        MATCH (w:Word)
        OPTIONAL MATCH (w)-[r:LEXICAL_RELATION|SYNONYM_OF]-()
        WITH w, count(r) AS degree
        RETURN coalesce(w.standard_orthography, w.kanji) AS word,
               w.translation AS translation,
               coalesce(w.pos_primary_norm, w.pos1, w.pos_primary) AS pos,
               degree
        ORDER BY degree DESC
        LIMIT $limit
        """
    else:
        raise HTTPException(400, f"Unknown metric: {metric}")
    
    result = await session.run(query, limit=limit)
    words = await result.data()
    
    return {"metric": metric, "count": len(words), "words": words}


# ============ Model Information ============


@router.get("/models", response_model=List[ModelInfo])
async def list_available_models() -> List[ModelInfo]:
    """List all available AI models."""
    
    models = get_available_models()
    return [
        ModelInfo(
            model_key=model.model_id,
            provider=model.provider,
            display_name=model.display_name,
            input_cost_per_1k=model.input_cost_per_1k,
            output_cost_per_1k=model.output_cost_per_1k,
            max_tokens=model.max_tokens,
            supports_json_mode=model.supports_json_mode,
            recommended_for=model.recommended_for,
        )
        for model in models
    ]


# ============ Dictionary Import ============


@router.post("/import/lee-dict")
async def import_lee_dict(
    session: AsyncSession = Depends(get_neo4j_session),
    current_user=Depends(get_current_user),
) -> Dict[str, Any]:
    """Import Lee dictionary from Google Sheets."""
    from app.services.lexical_network.dictionary_import_service import DictionaryImportService
    from app.services.lexical_network.column_mappings import LEE_DICT_MAPPING, LEE_DICT_URL
    
    dictionary_import = DictionaryImportService()
    stats = await dictionary_import.import_from_google_sheets(
        session, LEE_DICT_URL, "lee", LEE_DICT_MAPPING
    )
    return stats


@router.post("/import/matsushita-dict")
async def import_matsushita_dict(
    session: AsyncSession = Depends(get_neo4j_session),
    current_user=Depends(get_current_user),
) -> Dict[str, Any]:
    """Import Matsushita dictionary from Google Sheets."""
    from app.services.lexical_network.dictionary_import_service import DictionaryImportService
    from app.services.lexical_network.column_mappings import (
        MATSUSHITA_DICT_MAPPING,
        MATSUSHITA_DICT_URL,
    )
    
    dictionary_import = DictionaryImportService()
    stats = await dictionary_import.import_from_google_sheets(
        session, MATSUSHITA_DICT_URL, "matsushita", MATSUSHITA_DICT_MAPPING
    )
    return stats


# ============ UNIDIC Enrichment ============


@router.post("/enrich/unidic")
async def enrich_unidic(
    limit: int = Query(1000, ge=1, le=10000, description="Maximum words to process"),
    pos_filter: Optional[str] = Query(None, description="Optional POS filter"),
    session: AsyncSession = Depends(get_neo4j_session),
    current_user=Depends(get_current_user),
) -> Dict[str, Any]:
    """Enrich Word nodes with UNIDIC morphological data."""
    from app.services.lexical_network.unidic_enrichment_service import UnidicEnrichmentService
    
    service = UnidicEnrichmentService()
    if not service.is_available:
        raise HTTPException(503, "UNIDIC not available - fugashi not installed")
    
    stats = await service.batch_enrich(session, limit, pos_filter)
    return stats


# ============ AI Gap-Fill ============


@router.post("/gap-fill/batch")
async def gap_fill_batch(
    limit: int = Query(100, ge=1, le=1000, description="Maximum words to process"),
    model: str = Query("gpt-4o-mini", description="AI model to use"),
    min_confidence: float = Query(0.7, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    pos_filter: Optional[str] = Query(None, description="Optional POS filter"),
    session: AsyncSession = Depends(get_neo4j_session),
    current_user=Depends(get_current_user),
) -> Dict[str, Any]:
    """Batch fill missing attributes using AI."""
    from app.services.lexical_network.ai_gap_fill_service import AIGapFillService
    
    service = AIGapFillService(default_model=model)
    stats = await service.batch_fill_gaps(session, limit, model, min_confidence, pos_filter)
    return stats


@router.get("/gap-fill/stats")
async def gap_fill_stats(
    session: AsyncSession = Depends(get_neo4j_session),
) -> Dict[str, Any]:
    """Get statistics on attribute coverage and AI gap-fill usage."""
    
    # Count words by source
    result = await session.run("""
        MATCH (w:Word)
        UNWIND w.sources AS source
        RETURN source, count(*) AS count
        ORDER BY count DESC
    """)
    sources = await result.data()
    
    # Count words with/without AI gap-fill
    result = await session.run("""
        MATCH (w:Word)
        RETURN 
            count(*) AS total_words,
            sum(CASE WHEN w.ai_gap_filled = true THEN 1 ELSE 0 END) AS ai_filled_count,
            sum(CASE WHEN w.translation IS NULL THEN 1 ELSE 0 END) AS missing_translation,
            sum(CASE WHEN w.etymology IS NULL THEN 1 ELSE 0 END) AS missing_etymology,
            sum(CASE WHEN coalesce(w.pos_primary_norm, w.pos_primary) IS NULL THEN 1 ELSE 0 END) AS missing_pos,
            sum(CASE WHEN w.bunrui_class IS NULL THEN 1 ELSE 0 END) AS missing_bunrui_class
    """)
    coverage = await result.single()
    
    return {
        "sources": sources,
        "coverage": dict(coverage) if coverage else {},
    }


# ============ Coverage Report ============


@router.get("/coverage-report")
async def coverage_report(
    session: AsyncSession = Depends(get_neo4j_session),
) -> Dict[str, Any]:
    """Get detailed coverage report showing which sources cover which attributes."""
    
    result = await session.run("""
        MATCH (w:Word)
        RETURN 
            count(*) AS total_words,
            sum(CASE WHEN 'lee' IN w.sources THEN 1 ELSE 0 END) AS has_lee,
            sum(CASE WHEN 'matsushita' IN w.sources THEN 1 ELSE 0 END) AS has_matsushita,
            sum(CASE WHEN 'unidic' IN w.sources THEN 1 ELSE 0 END) AS has_unidic,
            sum(CASE WHEN 'ai_gap_fill' IN w.sources THEN 1 ELSE 0 END) AS has_ai_fill,
            sum(CASE WHEN w.lee_difficulty_numeric IS NOT NULL THEN 1 ELSE 0 END) AS has_lee_difficulty,
            sum(CASE WHEN w.matsushita_difficulty_numeric IS NOT NULL THEN 1 ELSE 0 END) AS has_matsushita_difficulty,
            sum(CASE WHEN w.bunrui_number IS NOT NULL THEN 1 ELSE 0 END) AS has_bunrui,
            sum(CASE WHEN w.translation IS NOT NULL THEN 1 ELSE 0 END) AS has_translation,
            sum(CASE WHEN w.etymology IS NOT NULL THEN 1 ELSE 0 END) AS has_etymology,
            sum(CASE WHEN coalesce(w.pos_primary_norm, w.pos_primary) IS NOT NULL THEN 1 ELSE 0 END) AS has_pos,
            sum(CASE WHEN w.pos1 IS NOT NULL THEN 1 ELSE 0 END) AS has_canonical_pos,
            sum(CASE WHEN w.pos_source IS NOT NULL THEN 1 ELSE 0 END) AS has_pos_source,
            sum(CASE WHEN w.unidic_lemma IS NOT NULL THEN 1 ELSE 0 END) AS has_unidic_data
    """)
    report = await result.single()
    
    return dict(report) if report else {}


# ============ POS Coverage Stats ============


@router.get("/pos-coverage")
async def pos_coverage_stats(
    session: AsyncSession = Depends(get_neo4j_session),
) -> Dict[str, Any]:
    """Get POS coverage statistics showing canonical POS distribution and sources."""
    
    # Total words and POS coverage
    result = await session.run("""
        MATCH (w:Word)
        RETURN 
            count(*) AS total_words,
            sum(CASE WHEN w.pos1 IS NOT NULL THEN 1 ELSE 0 END) AS has_canonical_pos,
            sum(CASE WHEN w.pos_primary_norm IS NOT NULL THEN 1 ELSE 0 END) AS has_pos_primary_norm,
            sum(CASE WHEN w.pos_primary IS NOT NULL THEN 1 ELSE 0 END) AS has_pos_primary,
            sum(CASE WHEN w.pos_source IS NOT NULL THEN 1 ELSE 0 END) AS has_pos_source
    """)
    coverage = await result.single()
    
    # POS source distribution
    result = await session.run("""
        MATCH (w:Word)
        WHERE w.pos_source IS NOT NULL
        RETURN w.pos_source AS source, count(*) AS count
        ORDER BY count DESC
    """)
    source_distribution = {r["source"]: r["count"] for r in await result.data()}
    
    # Canonical POS distribution (pos_primary_norm)
    result = await session.run("""
        MATCH (w:Word)
        WHERE w.pos_primary_norm IS NOT NULL
        RETURN w.pos_primary_norm AS pos, count(*) AS count
        ORDER BY count DESC
    """)
    canonical_pos_distribution = {r["pos"]: r["count"] for r in await result.data()}
    
    # POS hierarchy coverage (pos1-pos4)
    result = await session.run("""
        MATCH (w:Word)
        RETURN 
            sum(CASE WHEN w.pos1 IS NOT NULL THEN 1 ELSE 0 END) AS has_pos1,
            sum(CASE WHEN w.pos2 IS NOT NULL THEN 1 ELSE 0 END) AS has_pos2,
            sum(CASE WHEN w.pos3 IS NOT NULL THEN 1 ELSE 0 END) AS has_pos3,
            sum(CASE WHEN w.pos4 IS NOT NULL THEN 1 ELSE 0 END) AS has_pos4
    """)
    hierarchy_coverage = await result.single()
    
    return {
        "coverage": dict(coverage) if coverage else {},
        "source_distribution": source_distribution,
        "canonical_pos_distribution": canonical_pos_distribution,
        "hierarchy_coverage": dict(hierarchy_coverage) if hierarchy_coverage else {},
    }
