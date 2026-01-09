#!/usr/bin/env python3
"""
Verification script for Lexical Network Builder implementation.

Checks that all components are properly imported and configured.
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

def check_imports():
    """Check that all modules can be imported."""
    print("Checking imports...")
    
    try:
        from app.services.lexical_network.relation_types import (
            get_valid_relations_for_pos,
            is_symmetric_relation,
        )
        print("✓ relation_types imported")
        
        from app.services.lexical_network.vocabularies import (
            validate_domain_tag,
            validate_register_tag,
        )
        print("✓ vocabularies imported")
        
        from app.services.lexical_network.ai_provider_config import (
            list_available_models,
            get_model_config,
        )
        print("✓ ai_provider_config imported")
        
        from app.services.lexical_network.ai_providers import (
            AIProviderManager,
            OpenAIProvider,
        )
        print("✓ ai_providers imported")
        
        from app.services.lexical_network.prompts import LexicalPromptBuilder
        print("✓ prompts imported")
        
        from app.services.lexical_network.relation_builder_service import (
            RelationBuilderService,
        )
        print("✓ relation_builder_service imported")
        
        from app.services.lexical_network.job_manager_service import (
            LexicalNetworkJobManager,
        )
        print("✓ job_manager_service imported")
        
        from app.services.lexical_network.dictionary_import_service import (
            DictionaryImportService,
        )
        print("✓ dictionary_import_service imported")
        
        from app.schemas.lexical_network import (
            JobConfig,
            RelationCandidate,
            JobStatus,
        )
        print("✓ schemas imported")
        
        from app.api.v1.endpoints.lexical_network_admin import router
        print("✓ API endpoints imported")
        
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False


def check_relation_types():
    """Check relation type functionality."""
    print("\nChecking relation types...")
    
    from app.services.lexical_network.relation_types import (
        get_valid_relations_for_pos,
        is_symmetric_relation,
        validate_relation_for_pos,
    )
    
    # Test POS-to-relations mapping
    noun_rels = get_valid_relations_for_pos("名詞")
    assert "HYPERNYM" in noun_rels, "Noun should have HYPERNYM"
    print(f"✓ Noun relations: {len(noun_rels)} types")
    
    adj_rels = get_valid_relations_for_pos("形容詞")
    assert "GRADABLE_ANTONYM" in adj_rels, "Adjective should have GRADABLE_ANTONYM"
    print(f"✓ Adjective relations: {len(adj_rels)} types")
    
    # Test symmetry
    assert is_symmetric_relation("SYNONYM") is True
    assert is_symmetric_relation("HYPERNYM") is False
    print("✓ Symmetry detection works")
    
    # Test validation
    assert validate_relation_for_pos("HYPERNYM", "名詞") is True
    assert validate_relation_for_pos("HYPERNYM", "形容詞") is False
    print("✓ POS validation works")
    
    return True


def check_ai_providers():
    """Check AI provider configuration."""
    print("\nChecking AI providers...")
    
    from app.services.lexical_network.ai_provider_config import (
        list_available_models,
        get_model_config,
    )
    
    models = list_available_models()
    assert len(models) >= 6, f"Expected at least 6 models, got {len(models)}"
    print(f"✓ Found {len(models)} available models")
    
    # Check each provider
    config = get_model_config("gpt-4o-mini")
    assert config.provider == "openai"
    assert config.supports_json_mode is True
    print("✓ OpenAI model config correct")
    
    config = get_model_config("gemini-2.5-flash")
    assert config.provider == "gemini"
    print("✓ Gemini model config correct")
    
    config = get_model_config("deepseek-chat")
    assert config.provider == "deepseek"
    print("✓ DeepSeek model config correct")
    
    return True


def check_vocabularies():
    """Check controlled vocabularies."""
    print("\nChecking vocabularies...")
    
    from app.services.lexical_network.vocabularies import (
        validate_domain_tag,
        validate_context_tag,
        validate_register_tag,
        validate_aligned_arrays,
    )
    
    assert validate_domain_tag("aesthetics") is True
    assert validate_domain_tag("invalid") is False
    print("✓ Domain validation works")
    
    assert validate_register_tag("neutral") is True
    assert validate_register_tag("invalid") is False
    print("✓ Register validation works")
    
    assert validate_aligned_arrays(["a", "b"], [0.8, 0.5]) is True
    assert validate_aligned_arrays(["a"], [0.8, 0.5]) is False
    print("✓ Array alignment validation works")
    
    return True


def check_schemas():
    """Check Pydantic schemas."""
    print("\nChecking schemas...")
    
    try:
        from app.schemas.lexical_network import JobConfig, RelationCandidate
        
        # Test JobConfig
        config = JobConfig(
            job_type="relation_building",
            source="pos_filter",
            pos_filter="形容詞",
            relation_types=["SYNONYM"],
            model="gpt-4o-mini",
        )
        assert config.model == "gpt-4o-mini"
        print("✓ JobConfig schema works")
        
        # Test RelationCandidate
        candidate = RelationCandidate(
            source_word="test",
            target_word="test2",
            relation_type="SYNONYM",
            relation_category="noun",
            weight=0.8,
            confidence=0.9,
            is_symmetric=True,
            shared_meaning_en="test",
            distinction_en="test",
            usage_context_en="test",
            register_source="neutral",
            register_target="neutral",
            formality_difference="same",
            domain_tags=["aesthetics"],
            domain_weights=[0.9],
            context_tags=[],
            context_weights=[],
        )
        assert candidate.ai_temperature == 0.0
        print("✓ RelationCandidate schema works")
        
        return True
    except Exception as e:
        print(f"✗ Schema check failed: {e}")
        return False


def main():
    """Run all checks."""
    print("=" * 60)
    print("Lexical Network Builder - Build Status Check")
    print("=" * 60)
    
    checks = [
        ("Imports", check_imports),
        ("Relation Types", check_relation_types),
        ("AI Providers", check_ai_providers),
        ("Vocabularies", check_vocabularies),
        ("Schemas", check_schemas),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"✗ {name} check failed: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {name}")
    
    all_passed = all(result for _, result in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All checks passed! Build is ready.")
        return 0
    else:
        print("✗ Some checks failed. Please review errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
