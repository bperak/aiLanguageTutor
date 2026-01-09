"""
Simple integration test script to verify the User Path Module.

This script checks:
1. All services can be imported
2. Service initialization works
3. Configuration is accessible
4. Service dependencies are correct
"""

import sys
import os

# Add app to path
sys.path.insert(0, os.path.dirname(__file__))

def test_imports():
    """Test that all services can be imported."""
    print("Testing imports...")
    
    try:
        from app.services.cando_complexity_service import CanDoComplexityService, cando_complexity_service
        print("✓ CanDoComplexityService imported")
    except Exception as e:
        print(f"✗ CanDoComplexityService import failed: {e}")
        return False
    
    try:
        from app.services.cando_selector_service import CanDoSelectorService, cando_selector_service
        print("✓ CanDoSelectorService imported")
    except Exception as e:
        print(f"✗ CanDoSelectorService import failed: {e}")
        return False
    
    try:
        from app.services.path_builder import PathBuilder, path_builder
        print("✓ PathBuilder imported")
    except Exception as e:
        print(f"✗ PathBuilder import failed: {e}")
        return False
    
    try:
        from app.services.user_path_service import UserPathService, user_path_service
        print("✓ UserPathService imported")
    except Exception as e:
        print(f"✗ UserPathService import failed: {e}")
        return False
    
    try:
        from app.services.learning_path_service import LearningPathService, learning_path_service
        print("✓ LearningPathService imported")
    except Exception as e:
        print(f"✗ LearningPathService import failed: {e}")
        return False
    
    return True


def test_service_initialization():
    """Test that services can be initialized."""
    print("\nTesting service initialization...")
    
    try:
        from app.services.cando_complexity_service import cando_complexity_service
        assert cando_complexity_service is not None
        print("✓ CanDoComplexityService initialized")
    except Exception as e:
        print(f"✗ CanDoComplexityService initialization failed: {e}")
        return False
    
    try:
        from app.services.cando_selector_service import cando_selector_service
        assert cando_selector_service is not None
        print("✓ CanDoSelectorService initialized")
    except Exception as e:
        print(f"✗ CanDoSelectorService initialization failed: {e}")
        return False
    
    try:
        from app.services.path_builder import path_builder
        assert path_builder is not None
        print("✓ PathBuilder initialized")
    except Exception as e:
        print(f"✗ PathBuilder initialization failed: {e}")
        return False
    
    try:
        from app.services.user_path_service import user_path_service
        assert user_path_service is not None
        assert user_path_service.selector_service is not None
        assert user_path_service.path_builder is not None
        assert user_path_service.complexity_service is not None
        print("✓ UserPathService initialized with dependencies")
    except Exception as e:
        print(f"✗ UserPathService initialization failed: {e}")
        return False
    
    try:
        from app.services.learning_path_service import learning_path_service
        assert learning_path_service is not None
        assert learning_path_service.user_path_service is not None
        print("✓ LearningPathService initialized with UserPathService")
    except Exception as e:
        print(f"✗ LearningPathService initialization failed: {e}")
        return False
    
    return True


def test_configuration():
    """Test that configuration settings are accessible."""
    print("\nTesting configuration...")
    
    try:
        from app.core.config import settings
        assert hasattr(settings, 'PATH_MAX_STEPS')
        assert hasattr(settings, 'PATH_COMPLEXITY_INCREMENT')
        assert hasattr(settings, 'PATH_SEMANTIC_THRESHOLD')
        assert hasattr(settings, 'PATH_COMPLEXITY_MODEL')
        print(f"✓ Configuration settings accessible:")
        print(f"  - PATH_MAX_STEPS: {settings.PATH_MAX_STEPS}")
        print(f"  - PATH_COMPLEXITY_INCREMENT: {settings.PATH_COMPLEXITY_INCREMENT}")
        print(f"  - PATH_SEMANTIC_THRESHOLD: {settings.PATH_SEMANTIC_THRESHOLD}")
        print(f"  - PATH_COMPLEXITY_MODEL: {settings.PATH_COMPLEXITY_MODEL}")
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False
    
    return True


def test_method_signatures():
    """Test that key methods exist with correct signatures."""
    print("\nTesting method signatures...")
    
    try:
        from app.services.user_path_service import user_path_service
        assert hasattr(user_path_service, 'generate_user_path')
        assert hasattr(user_path_service, 'analyze_profile_for_path')
        print("✓ UserPathService methods exist")
    except Exception as e:
        print(f"✗ Method signature test failed: {e}")
        return False
    
    try:
        from app.services.path_builder import path_builder
        assert hasattr(path_builder, 'build_semantic_path')
        assert hasattr(path_builder, 'find_next_semantic_cando')
        assert hasattr(path_builder, 'ensure_continuity')
        print("✓ PathBuilder methods exist")
    except Exception as e:
        print(f"✗ Method signature test failed: {e}")
        return False
    
    try:
        from app.services.cando_complexity_service import cando_complexity_service
        assert hasattr(cando_complexity_service, 'assess_complexity')
        assert hasattr(cando_complexity_service, 'compare_complexity')
        assert hasattr(cando_complexity_service, 'rank_by_complexity')
        print("✓ CanDoComplexityService methods exist")
    except Exception as e:
        print(f"✗ Method signature test failed: {e}")
        return False
    
    try:
        from app.services.cando_selector_service import cando_selector_service
        assert hasattr(cando_selector_service, 'select_initial_candos')
        assert hasattr(cando_selector_service, 'filter_by_profile')
        print("✓ CanDoSelectorService methods exist")
    except Exception as e:
        print(f"✗ Method signature test failed: {e}")
        return False
    
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("User Path Module Integration Test")
    print("=" * 60)
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Service Initialization", test_service_initialization()))
    results.append(("Configuration", test_configuration()))
    results.append(("Method Signatures", test_method_signatures()))
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

