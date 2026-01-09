"""
Job Manager Service

Manages background jobs for continuous lexical network building.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

import structlog

from app.db import get_neo4j_session
from app.schemas.lexical_network import JobConfig, JobResult, JobStatus, WordProcessingResult
from app.services.lexical_network.relation_builder_service import (
    RelationBuilderService,
)

logger = structlog.get_logger()


class JobStatusEnum(str, Enum):
    """Job status enumeration."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class LexicalNetworkJob:
    """Internal job representation."""
    
    id: str
    job_type: str
    status: JobStatusEnum
    config: JobConfig
    progress: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Optional[JobResult] = None
    source_words: Optional[List[str]] = None
    
    # Real-time progress tracking
    current_word: Optional[str] = None
    current_word_index: int = 0
    total_words: int = 0
    recent_results: List[WordProcessingResult] = field(default_factory=list)


class LexicalNetworkJobManager:
    """Manages background jobs for lexical network building."""
    
    def __init__(self):
        self.jobs: Dict[str, LexicalNetworkJob] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.relation_builder = RelationBuilderService()
    
    async def create_job(self, config: JobConfig) -> str:
        """
        Create a new lexical network job.
        
        Args:
            config: Job configuration
            
        Returns:
            Job ID
        """
        job_id = f"job_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{len(self.jobs)}"
        
        job = LexicalNetworkJob(
            id=job_id,
            job_type=config.job_type,
            status=JobStatusEnum.PENDING,
            config=config,
        )
        
        self.jobs[job_id] = job
        logger.info("Job created", job_id=job_id, job_type=config.job_type)
        
        return job_id
    
    async def start_job(self, job_id: str) -> bool:
        """
        Start a pending job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if started, False otherwise
        """
        job = self.jobs.get(job_id)
        if not job or job.status != JobStatusEnum.PENDING:
            return False
        
        # Fetch word list before starting (for relation_building jobs)
        if job.job_type == "relation_building" and not job.source_words:
            async for neo4j_session in get_neo4j_session():
                job.source_words = await self.get_words_for_job(neo4j_session, job.config)
                break
        
        job.status = JobStatusEnum.RUNNING
        job.started_at = datetime.utcnow()
        
        # Create async task
        task = asyncio.create_task(self._run_job(job_id))
        self.running_tasks[job_id] = task
        
        logger.info("Job started", job_id=job_id, word_count=len(job.source_words) if job.source_words else 0)
        return True
    
    async def get_job_status(self, job_id: str) -> Optional[JobStatus]:
        """
        Get job status.
        
        Args:
            job_id: Job identifier
            
        Returns:
            JobStatus or None if not found
        """
        job = self.jobs.get(job_id)
        if not job:
            return None
        
        # Convert config to dict for serialization
        config_dict = None
        if job.config:
            config_dict = job.config.dict(exclude_none=True)
        
        return JobStatus(
            id=job.id,
            job_type=job.job_type,
            status=job.status.value,
            progress=job.progress,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error=job.error,
            result=job.result,
            source_words=job.source_words,
            config=config_dict,
            current_word=job.current_word,
            current_word_index=job.current_word_index,
            total_words=job.total_words,
            recent_results=job.recent_results,
        )
    
    async def list_jobs(
        self, status: Optional[str] = None, limit: int = 20
    ) -> List[JobStatus]:
        """
        List jobs.
        
        Args:
            status: Optional status filter
            limit: Maximum number of jobs to return
            
        Returns:
            List of JobStatus
        """
        jobs = list(self.jobs.values())
        
        if status:
            jobs = [j for j in jobs if j.status.value == status]
        
        jobs = sorted(jobs, key=lambda j: j.created_at, reverse=True)[:limit]
        
        return [
            JobStatus(
                id=j.id,
                job_type=j.job_type,
                status=j.status.value,
                progress=j.progress,
                created_at=j.created_at,
                started_at=j.started_at,
                completed_at=j.completed_at,
                error=j.error,
                result=j.result,
                source_words=j.source_words,
                config=j.config.dict(exclude_none=True) if j.config else None,
                current_word=j.current_word,
                current_word_index=j.current_word_index,
                total_words=j.total_words,
                recent_results=j.recent_results,
            )
            for j in jobs
        ]
    
    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a running job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if cancelled, False otherwise
        """
        job = self.jobs.get(job_id)
        if not job or job.status != JobStatusEnum.RUNNING:
            return False
        
        job.status = JobStatusEnum.CANCELLED
        job.completed_at = datetime.utcnow()
        
        # Cancel task
        task = self.running_tasks.pop(job_id, None)
        if task:
            task.cancel()
        
        logger.info("Job cancelled", job_id=job_id)
        return True
    
    async def _run_job(self, job_id: str):
        """Execute the job."""
        job = self.jobs[job_id]
        
        try:
            if job.job_type == "relation_building":
                result = await self._run_relation_building_job(job)
            elif job.job_type == "dictionary_import":
                result = await self._run_dictionary_import_job(job)
            else:
                raise ValueError(f"Unknown job type: {job.job_type}")
            
            job.status = JobStatusEnum.COMPLETED
            job.result = result
            
        except asyncio.CancelledError:
            job.status = JobStatusEnum.CANCELLED
            job.error = "Job was cancelled"
            logger.info("Job cancelled", job_id=job_id)
        except Exception as e:
            job.status = JobStatusEnum.FAILED
            job.error = str(e)
            logger.error("Job failed", job_id=job_id, error=str(e))
        finally:
            job.completed_at = datetime.utcnow()
            self.running_tasks.pop(job_id, None)
    
    async def _run_relation_building_job(self, job: LexicalNetworkJob) -> JobResult:
        """Run relation building for words based on config."""
        config = job.config
        stats = {
            "processed": 0,
            "relations_created": 0,
            "relations_updated": 0,
            "errors": 0,
            "total_tokens_input": 0,
            "total_tokens_output": 0,
            "total_cost_usd": 0.0,
            "latency_ms_list": [],
            "models_used": {},
            # Resolution stats
            "total_targets_attempted": 0,
            "total_targets_resolved": 0,
            "total_targets_dropped_not_found": 0,
            "total_targets_dropped_ambiguous": 0,
            "dropped_not_found_samples": [],
            "dropped_ambiguous_samples": [],
        }
        
        # Get words to process
        async for neo4j_session in get_neo4j_session():
            words = await self.get_words_for_job(neo4j_session, config)
            break
        
        total_words = len(words)
        job.total_words = total_words
        logger.info("Starting relation building job", words=total_words, job_id=job.id)
        
        for i, word in enumerate(words):
            # Check if cancelled
            if job.status == JobStatusEnum.CANCELLED:
                break
            
            # Update current word tracking
            job.current_word = word
            job.current_word_index = i + 1
            
            word_result = WordProcessingResult(
                word=word,
                timestamp=datetime.utcnow()
            )
            
            try:
                async for neo4j_session in get_neo4j_session():
                    build_result = await self.relation_builder.build_relations_for_word(
                        neo4j_session, word, config
                    )
                    break
                
                stats["processed"] += 1
                stats["relations_created"] += build_result.relations_created
                stats["relations_updated"] += build_result.relations_updated
                stats["total_tokens_input"] += build_result.tokens_input
                stats["total_tokens_output"] += build_result.tokens_output
                stats["total_cost_usd"] += build_result.cost_usd
                stats["latency_ms_list"].append(build_result.latency_ms)
                stats["models_used"][build_result.model_used] = (
                    stats["models_used"].get(build_result.model_used, 0) + 1
                )
                
                # Aggregate resolution stats
                stats["total_targets_attempted"] += build_result.targets_attempted
                stats["total_targets_resolved"] += build_result.targets_resolved
                stats["total_targets_dropped_not_found"] += build_result.targets_dropped_not_found
                stats["total_targets_dropped_ambiguous"] += build_result.targets_dropped_ambiguous
                
                # Collect samples (bounded to avoid memory issues)
                for sample in build_result.dropped_not_found_samples:
                    if sample not in stats["dropped_not_found_samples"] and len(stats["dropped_not_found_samples"]) < 50:
                        stats["dropped_not_found_samples"].append(sample)
                for sample in build_result.dropped_ambiguous_samples:
                    if sample not in stats["dropped_ambiguous_samples"] and len(stats["dropped_ambiguous_samples"]) < 50:
                        stats["dropped_ambiguous_samples"].append(sample)
                
                # Update word result
                word_result.relations_created = build_result.relations_created
                word_result.relations_updated = build_result.relations_updated
                word_result.targets_found = build_result.targets_attempted
                word_result.targets_resolved = build_result.targets_resolved
                
            except Exception as e:
                stats["errors"] += 1
                word_result.error = str(e)
                logger.error("Error processing word", word=word, error=str(e))
            
            # Add to recent results (keep last 20)
            job.recent_results.append(word_result)
            if len(job.recent_results) > 20:
                job.recent_results = job.recent_results[-20:]
            
            # Update progress
            job.progress = (i + 1) / total_words if total_words > 0 else 0.0
        
        # Clear current word when done
        job.current_word = None
        
        avg_latency = (
            sum(stats["latency_ms_list"]) / len(stats["latency_ms_list"])
            if stats["latency_ms_list"]
            else 0.0
        )
        
        # Calculate resolution rate
        resolution_rate = (
            stats["total_targets_resolved"] / stats["total_targets_attempted"]
            if stats["total_targets_attempted"] > 0
            else 0.0
        )
        
        return JobResult(
            processed=stats["processed"],
            relations_created=stats["relations_created"],
            relations_updated=stats["relations_updated"],
            errors=stats["errors"],
            total_tokens_input=stats["total_tokens_input"],
            total_tokens_output=stats["total_tokens_output"],
            total_cost_usd=stats["total_cost_usd"],
            avg_latency_ms=avg_latency,
            models_used=stats["models_used"],
            total_targets_attempted=stats["total_targets_attempted"],
            total_targets_resolved=stats["total_targets_resolved"],
            total_targets_dropped_not_found=stats["total_targets_dropped_not_found"],
            total_targets_dropped_ambiguous=stats["total_targets_dropped_ambiguous"],
            resolution_rate=resolution_rate,
        )
    
    async def _run_dictionary_import_job(self, job: LexicalNetworkJob) -> JobResult:
        """Run dictionary import job."""
        # This would call dictionary_import_service
        # For now, return placeholder
        return JobResult(
            processed=0,
            relations_created=0,
            relations_updated=0,
            errors=0,
            total_tokens_input=0,
            total_tokens_output=0,
            total_cost_usd=0.0,
            avg_latency_ms=0.0,
            models_used={},
        )
    
    async def get_words_for_job(self, session, config: JobConfig) -> List[str]:
        """Get words to process based on job config with combined filters."""
        max_words = config.max_words
        
        # Word list source - just return the list
        if config.source == "word_list":
            return config.word_list[:max_words] if config.word_list else []
        
        # Database source - build dynamic query with combined filters
        # Build WHERE clauses
        where_clauses = []
        params = {"limit": max_words}
        
        # POS filter (optional) - use canonical POS with fallback
        if config.pos_filter:
            where_clauses.append("coalesce(w.pos_primary_norm, w.pos1, w.pos_primary) = $pos")
            params["pos"] = config.pos_filter
        
        # Relation count filters
        if config.filter_no_relations:
            # No relations at all
            query = f"""
            MATCH (w:Word)
            WHERE NOT (w)-[:LEXICAL_RELATION|SYNONYM_OF|SIMILAR_TO]-()
            {' AND ' + ' AND '.join(where_clauses) if where_clauses else ''}
            RETURN DISTINCT coalesce(w.standard_orthography, w.kanji) AS word
            ORDER BY word
            LIMIT $limit
            """
            result = await session.run(query, **params)
            return [r["word"] for r in await result.data()]
        
        elif config.filter_few_relations and config.max_relations is not None:
            # Fewer than X relations
            params["max_rel_count"] = config.max_relations
            pos_where = f"AND {' AND '.join(where_clauses)}" if where_clauses else ""
            query = f"""
            MATCH (w:Word)
            WHERE true {pos_where}
            OPTIONAL MATCH (w)-[r:LEXICAL_RELATION|SYNONYM_OF|SIMILAR_TO]-()
            WITH w, count(r) AS rel_count
            WHERE rel_count < $max_rel_count
            RETURN DISTINCT coalesce(w.standard_orthography, w.kanji) AS word
            ORDER BY word
            LIMIT $limit
            """
            result = await session.run(query, **params)
            return [r["word"] for r in await result.data()]
        
        else:
            # No relation filter - just POS or all
            where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            query = f"""
            MATCH (w:Word)
            {where_str}
            RETURN DISTINCT coalesce(w.standard_orthography, w.kanji) AS word
            ORDER BY word
            LIMIT $limit
            """
            result = await session.run(query, **params)
            return [r["word"] for r in await result.data()]


# Global job manager instance
job_manager = LexicalNetworkJobManager()
