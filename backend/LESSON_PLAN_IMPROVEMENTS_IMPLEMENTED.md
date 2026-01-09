# Lesson Plan Improvements - Implementation Summary

**Date:** 2025-12-30  
**Status:** ✅ **IMPLEMENTED** - All high-priority improvements completed

## Implemented Improvements

### 1. ✅ Plan Caching ⭐ **HIGH PRIORITY**

**Implementation**:
- Created `plan_cache` database table with migration (`migrations/versions/create_plan_cache_table.sql`)
- Added `_hash_profile_context()` and `_hash_kit_context()` functions for cache key generation
- Added `_get_cached_plan()` function to retrieve cached plans
- Added `_cache_plan()` function to store generated plans
- Integrated caching into `compile_lessonroot()` - checks cache before generating, stores after generation
- Cache TTL: 24 hours (configurable)
- Cache key: `(can_do_id, profile_hash, kit_hash)`

**Benefits**:
- ⚡ Faster compilation (skip LLM call if plan cached)
- 💰 Cost savings (fewer LLM API calls)
- 🔄 Consistent plans for same inputs

**Files Modified**:
- `app/services/cando_v2_compile_service.py` - Added caching functions and integration
- `migrations/versions/create_plan_cache_table.sql` - Database schema

### 2. ✅ Plan Reuse for Stage Regeneration ⭐ **HIGH PRIORITY**

**Implementation**:
- Modified `regenerate_lesson_stage()` to extract and reuse existing plan from lesson JSON
- Converts plan dict to `DomainPlan` object for type safety
- Falls back to cache lookup if plan extraction fails
- Falls back to regeneration if cache lookup fails
- Added quality validation for reused plans

**Benefits**:
- ⚡ Faster stage regeneration (no plan regeneration needed)
- 🎯 Consistent plan across regenerations
- 💰 Cost savings

**Files Modified**:
- `app/services/cando_v2_compile_service.py` - Enhanced `regenerate_lesson_stage()`

### 3. ✅ Enhanced Error Handling ⭐ **MEDIUM PRIORITY**

**Implementation**:
- Enhanced `validate_or_repair()` with optional `fallback_data` parameter
- Added fallback logic in `compile_lessonroot()` - uses expired cache as fallback if generation fails
- Added fallback logic in `regenerate_lesson_stage()` - uses cache if plan extraction fails
- Better error logging with context

**Benefits**:
- 🛡️ Better resilience to LLM failures
- 🔄 Graceful degradation
- 📊 Better error tracking

**Files Modified**:
- `scripts/cando_creation/generators/utils.py` - Enhanced `validate_or_repair()`
- `app/services/cando_v2_compile_service.py` - Added fallback logic

### 4. ✅ Plan Validation Enhancement ⭐ **MEDIUM PRIORITY**

**Implementation**:
- Added `_validate_plan_quality()` function to check plan quality beyond schema validation
- Validates:
  - Scenario count (1-2 expected)
  - Vocabulary coverage (20-100 items recommended)
  - Grammar functions count (2-5 expected)
  - Success criteria count (2-5 expected)
  - Cultural themes count (2-5 expected)
- Quality issues are logged as warnings (not errors)
- Applied to both generated and reused plans

**Benefits**:
- ✅ Better plan quality assurance
- 🎯 Catch issues before content generation
- 📊 Quality metrics

**Files Modified**:
- `app/services/cando_v2_compile_service.py` - Added `_validate_plan_quality()`

## Implementation Details

### Cache Key Generation

```python
def _hash_profile_context(profile_context: str) -> str:
    """Generate hash for profile context to use as cache key."""
    return hashlib.sha256(profile_context.encode()).hexdigest()[:16]

def _hash_kit_context(kit_context: str, kit_requirements: str) -> str:
    """Generate hash for kit context to use as cache key."""
    combined = f"{kit_context}|{kit_requirements}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]
```

### Cache Lookup Flow

1. **During Compilation** (`compile_lessonroot()`):
   - Hash profile and kit contexts
   - Check cache for existing plan
   - If found and not expired: use cached plan
   - If not found or expired: generate new plan
   - Cache newly generated plan

2. **During Stage Regeneration** (`regenerate_lesson_stage()`):
   - Extract plan from lesson JSON
   - If extraction fails: check cache
   - If cache miss: regenerate plan
   - Cache newly generated plan

### Plan Quality Validation

```python
def _validate_plan_quality(plan: DomainPlan) -> List[str]:
    """Validate plan quality beyond schema validation."""
    issues = []
    
    # Check scenario count (1-2 expected)
    if len(plan.scenarios) < 1:
        issues.append("Too few scenarios (minimum 1 required)")
    elif len(plan.scenarios) > 2:
        issues.append(f"Too many scenarios ({len(plan.scenarios)}, expected 1-2)")
    
    # Check vocabulary coverage (20-100 items recommended)
    total_vocab = sum(len(bucket.items) for bucket in plan.lex_buckets)
    if total_vocab < 20:
        issues.append(f"Insufficient vocabulary ({total_vocab} items, minimum 20 recommended)")
    elif total_vocab > 100:
        issues.append(f"Excessive vocabulary ({total_vocab} items, may be overwhelming)")
    
    # Check grammar functions (2-5 expected)
    if len(plan.grammar_functions) < 2:
        issues.append("Too few grammar functions (minimum 2 required)")
    elif len(plan.grammar_functions) > 5:
        issues.append(f"Too many grammar functions ({len(plan.grammar_functions)}, expected 2-5)")
    
    # ... more validations
    
    return issues
```

## Database Schema

### plan_cache Table

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
    last_used_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(can_do_id, profile_hash, kit_hash)
);
```

**Indexes**:
- `idx_plan_cache_lookup` on `(can_do_id, profile_hash, kit_hash)`
- `idx_plan_cache_expires` on `expires_at` (partial, where `expires_at > NOW()`)
- `idx_plan_cache_last_used` on `last_used_at DESC`

## Usage Examples

### Compilation with Caching

```python
# First compilation - generates and caches plan
plan = await compile_lessonroot(
    neo=neo,
    pg=pg,
    can_do_id="JFまるごと:1",
    user_id=user_id
)
# Plan is generated and cached

# Second compilation (same CanDo + profile) - uses cached plan
plan = await compile_lessonroot(
    neo=neo,
    pg=pg,
    can_do_id="JFまるごと:1",
    user_id=user_id
)
# Plan is loaded from cache (faster, no LLM call)
```

### Stage Regeneration with Plan Reuse

```python
# Regenerate comprehension stage
result = await regenerate_lesson_stage(
    neo=neo,
    pg=pg,
    lesson_id=123,
    version=1,
    stage="comprehension"
)
# Plan is reused from lesson JSON (no regeneration needed)
```

## Metrics to Track

After deployment, track:
- **Cache hit rate**: % of compilations using cached plans
- **Plan generation time**: Average time to generate plan (vs cache lookup)
- **Cost savings**: Reduction in LLM API calls
- **Error rate**: Plan generation failures
- **Plan quality**: Validation issues found

## Next Steps (Optional)

### Phase 2: Nice to Have (Future)
1. **Plan Versioning** - Track plan history
2. **Async Optimization** - Parallel generation
3. **Prompt Optimization** - Token efficiency

## Conclusion

All high-priority improvements have been successfully implemented:
- ✅ Plan caching (biggest impact on cost and speed)
- ✅ Plan reuse (improves regeneration efficiency)
- ✅ Enhanced error handling (better resilience)
- ✅ Plan validation (quality assurance)

The system is now more efficient, cost-effective, and reliable.

