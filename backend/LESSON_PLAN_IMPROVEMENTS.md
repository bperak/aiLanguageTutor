# Lesson Plan Creation - Potential Improvements

**Date:** 2025-12-30  
**Status:** 📋 **ANALYSIS** - Identified improvement opportunities

## Executive Summary

The lesson plan creation flow is functional but has several opportunities for improvement:
1. **No caching** - Plans are regenerated every time (even for same CanDo + profile)
2. **No plan reuse** - Cannot reuse existing plans when regenerating stages
3. **Limited error recovery** - Basic retry logic but could be enhanced
4. **No plan versioning** - Cannot track plan changes over time
5. **Synchronous generation** - Plan blocks compilation start (could be optimized)

## Identified Improvements

### 1. Plan Caching ⭐ **HIGH PRIORITY**

**Current State**:
- Plan is regenerated every time `compile_lessonroot()` is called
- Same CanDo + same profile = same plan (wasteful LLM call)
- No caching mechanism exists

**Improvement**:
```python
# Add plan caching by (can_do_id, profile_hash, kit_hash)
async def _get_cached_plan(
    pg: PgSession,
    can_do_id: str,
    profile_context_hash: str,
    kit_context_hash: str,
) -> Optional[DomainPlan]:
    """Check if plan exists in cache."""
    # Query plan_cache table
    # Return cached plan if found and not expired
    
async def _cache_plan(
    pg: PgSession,
    can_do_id: str,
    profile_context_hash: str,
    kit_context_hash: str,
    plan: DomainPlan,
    ttl_hours: int = 24,
) -> None:
    """Cache generated plan."""
    # Store in plan_cache table with expiration
```

**Benefits**:
- ⚡ Faster compilation (skip LLM call if plan cached)
- 💰 Cost savings (fewer LLM API calls)
- 🔄 Consistent plans for same inputs

**Implementation**:
- Create `plan_cache` table with columns: `can_do_id`, `profile_hash`, `kit_hash`, `plan_json`, `created_at`, `expires_at`
- Hash profile_context and kit_context to create cache keys
- Check cache before calling `gen_domain_plan()`
- Store plan after successful generation

### 2. Plan Reuse for Stage Regeneration ⭐ **HIGH PRIORITY**

**Current State**:
- When regenerating a stage (e.g., Content), plan is regenerated
- `regenerate_lesson_stage()` doesn't reuse existing plan

**Improvement**:
```python
async def regenerate_lesson_stage(
    ...,
    reuse_plan: bool = True,  # New parameter
) -> Dict[str, Any]:
    """Regenerate a specific lesson stage."""
    if reuse_plan:
        # Load existing plan from lesson JSON
        plan = _extract_plan_from_lesson(lesson_json)
    else:
        # Regenerate plan (current behavior)
        plan = await _generate_plan(...)
```

**Benefits**:
- ⚡ Faster stage regeneration
- 🎯 Consistent plan across regenerations
- 💰 Cost savings

### 3. Enhanced Error Handling ⭐ **MEDIUM PRIORITY**

**Current State**:
- Basic `validate_or_repair()` with max_repair=2
- No specific error types handled
- No fallback strategies

**Improvement**:
```python
async def gen_domain_plan_with_fallback(
    ...,
    fallback_plan: Optional[DomainPlan] = None,
) -> DomainPlan:
    """Generate plan with enhanced error handling."""
    try:
        return await gen_domain_plan(...)
    except ValidationError as e:
        if fallback_plan:
            logger.warning("Using fallback plan", error=str(e))
            return fallback_plan
        # Try simplified prompt
        return await gen_domain_plan_simplified(...)
    except LLMTimeoutError:
        # Use cached plan if available
        cached = await _get_cached_plan(...)
        if cached:
            return cached
        raise
```

**Benefits**:
- 🛡️ Better resilience to LLM failures
- 🔄 Graceful degradation
- 📊 Better error tracking

### 4. Plan Versioning 📋 **MEDIUM PRIORITY**

**Current State**:
- Plans are not versioned
- Cannot track plan changes over time
- Cannot rollback to previous plan

**Improvement**:
```python
# Add plan_version to DomainPlan model
class DomainPlan(BaseModel):
    plan_version: int = 1  # Increment on changes
    created_at: datetime
    # ... existing fields

# Store plan versions in database
CREATE TABLE plan_versions (
    id UUID PRIMARY KEY,
    can_do_id VARCHAR(255),
    profile_hash VARCHAR(64),
    plan_version INTEGER,
    plan_json JSONB,
    created_at TIMESTAMP,
    ...
);
```

**Benefits**:
- 📊 Track plan evolution
- 🔄 Rollback capability
- 🔍 Debugging plan changes

### 5. Async Plan Generation Optimization 📋 **LOW PRIORITY**

**Current State**:
- Plan generation uses `asyncio.to_thread()` (good)
- But still blocks compilation start

**Improvement**:
```python
# Generate plan in parallel with other prep work
async def compile_lessonroot(...):
    # Start plan generation early
    plan_task = asyncio.create_task(
        asyncio.to_thread(pipeline.gen_domain_plan, ...)
    )
    
    # Do other prep work in parallel
    kit_task = asyncio.create_task(_fetch_prelesson_kit(...))
    profile_task = asyncio.create_task(_build_user_profile_context(...))
    
    # Wait for all
    plan, kit, profile = await asyncio.gather(
        plan_task, kit_task, profile_task
    )
```

**Benefits**:
- ⚡ Slightly faster compilation start
- 🔄 Better resource utilization

### 6. Plan Validation Enhancement 📋 **LOW PRIORITY**

**Current State**:
- Basic Pydantic validation
- Generic repair prompts

**Improvement**:
```python
def validate_plan_quality(plan: DomainPlan) -> List[str]:
    """Validate plan quality beyond schema."""
    issues = []
    
    # Check scenario count
    if len(plan.scenarios) < 1:
        issues.append("Too few scenarios")
    
    # Check vocabulary coverage
    total_vocab = sum(len(b.items) for b in plan.lex_buckets)
    if total_vocab < 20:
        issues.append("Insufficient vocabulary")
    
    # Check grammar alignment
    if len(plan.grammar_functions) < 2:
        issues.append("Too few grammar functions")
    
    return issues
```

**Benefits**:
- ✅ Better plan quality assurance
- 🎯 Catch issues before content generation
- 📊 Quality metrics

### 7. Plan Prompt Optimization 📋 **LOW PRIORITY**

**Current State**:
- Prompt includes all context (good for personalization)
- But could be optimized for token efficiency

**Improvement**:
```python
def build_planner_prompt_optimized(
    ...,
    include_full_profile: bool = True,
) -> Tuple[str, str]:
    """Optimized prompt with selective context inclusion."""
    if not include_full_profile:
        # Include only essential profile fields
        profile_context = _build_minimal_profile_context(profile)
    else:
        profile_context = _build_full_profile_context(profile)
    
    # Use shorter kit context if possible
    kit_context = _summarize_kit_context(kit) if kit else ""
    
    # ... rest of prompt
```

**Benefits**:
- 💰 Lower token costs
- ⚡ Faster LLM response
- 🎯 Focus on essential information

## Recommended Implementation Order

### Phase 1: Quick Wins (1-2 days)
1. ✅ **Plan Reuse for Stage Regeneration** - Simple parameter addition
2. ✅ **Enhanced Error Handling** - Add fallback logic

### Phase 2: High Impact (3-5 days)
3. ✅ **Plan Caching** - Database table + cache logic
4. ✅ **Plan Validation Enhancement** - Quality checks

### Phase 3: Nice to Have (1-2 weeks)
5. ✅ **Plan Versioning** - Track plan history
6. ✅ **Async Optimization** - Parallel generation
7. ✅ **Prompt Optimization** - Token efficiency

## Implementation Details

### Plan Caching Schema

```sql
CREATE TABLE plan_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    can_do_id VARCHAR(255) NOT NULL,
    profile_hash VARCHAR(64) NOT NULL,
    kit_hash VARCHAR(64) NOT NULL,
    plan_json JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    hits INTEGER DEFAULT 0,
    
    UNIQUE(can_do_id, profile_hash, kit_hash)
);

CREATE INDEX idx_plan_cache_lookup ON plan_cache(can_do_id, profile_hash, kit_hash);
CREATE INDEX idx_plan_cache_expires ON plan_cache(expires_at) WHERE expires_at > NOW();
```

### Cache Key Generation

```python
import hashlib
import json

def _hash_profile_context(profile_context: str) -> str:
    """Generate hash for profile context."""
    return hashlib.sha256(profile_context.encode()).hexdigest()[:16]

def _hash_kit_context(kit_context: str, kit_requirements: str) -> str:
    """Generate hash for kit context."""
    combined = f"{kit_context}|{kit_requirements}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]
```

### Plan Reuse Logic

```python
def _extract_plan_from_lesson(lesson_json: Dict[str, Any]) -> Optional[DomainPlan]:
    """Extract DomainPlan from compiled lesson JSON."""
    # Lesson JSON structure includes plan data
    if "plan" in lesson_json:
        return DomainPlan.model_validate(lesson_json["plan"])
    # Or reconstruct from lesson structure
    return None
```

## Metrics to Track

After implementing improvements, track:
- **Cache hit rate**: % of compilations using cached plans
- **Plan generation time**: Average time to generate plan
- **Cost savings**: Reduction in LLM API calls
- **Error rate**: Plan generation failures
- **Plan quality**: Validation issues found

## Conclusion

The lesson plan creation flow is solid but can be significantly improved with:
1. **Caching** (biggest impact on cost and speed)
2. **Plan reuse** (improves regeneration efficiency)
3. **Enhanced error handling** (better resilience)

These improvements would make the system more efficient, cost-effective, and reliable.

