"""
Minimal test runner that verifies test structure and logic
without requiring all dependencies to be installed.
"""

import sys
import os
import importlib.util
import ast

# Add app to path
sys.path.insert(0, os.path.dirname(__file__))

def check_test_file_structure(filepath):
    """Check if test file has correct structure."""
    print(f"\nChecking {filepath}...")
    
    if not os.path.exists(filepath):
        print(f"  ✗ File not found")
        return False
    
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Parse AST to check structure
        tree = ast.parse(content, filename=filepath)
        
        # Check for test functions
        test_functions = []
        fixtures = []
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name.startswith('test_'):
                    test_functions.append(node.name)
                elif 'fixture' in [d.id for d in node.decorator_list if isinstance(d, ast.Name)]:
                    fixtures.append(node.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
        
        print(f"  ✓ File parsed successfully")
        print(f"    - Test functions: {len(test_functions)}")
        for func in test_functions:
            print(f"      • {func}")
        print(f"    - Fixtures: {len(fixtures)}")
        for fix in fixtures:
            print(f"      • {fix}")
        print(f"    - Imports: {len(imports)}")
        
        return True
        
    except SyntaxError as e:
        print(f"  ✗ Syntax error: {e}")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def verify_test_imports():
    """Verify that test imports are correct."""
    print("\nVerifying test imports...")
    
    test_files = [
        'tests/services/test_user_path_service.py',
        'tests/services/test_path_builder.py',
        'tests/services/test_cando_complexity_service.py'
    ]
    
    all_ok = True
    for test_file in test_files:
        filepath = os.path.join(os.path.dirname(__file__), test_file)
        if not os.path.exists(filepath):
            print(f"  ✗ {test_file} not found")
            all_ok = False
            continue
        
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            
            # Check for common test imports
            has_pytest = 'import pytest' in content or 'from pytest' in content
            has_unittest_mock = 'from unittest.mock' in content or 'import unittest.mock' in content
            
            if has_pytest:
                print(f"  ✓ {test_file} has pytest imports")
            else:
                print(f"  ⚠ {test_file} missing pytest imports")
            
            if has_unittest_mock:
                print(f"  ✓ {test_file} has mock imports")
            else:
                print(f"  ⚠ {test_file} missing mock imports")
                
        except Exception as e:
            print(f"  ✗ Error reading {test_file}: {e}")
            all_ok = False
    
    return all_ok


def check_service_files():
    """Check that service files have correct structure."""
    print("\nChecking service files...")
    
    service_files = [
        'app/services/user_path_service.py',
        'app/services/path_builder.py',
        'app/services/cando_complexity_service.py',
        'app/services/cando_selector_service.py'
    ]
    
    all_ok = True
    for service_file in service_files:
        filepath = os.path.join(os.path.dirname(__file__), service_file)
        if not os.path.exists(filepath):
            print(f"  ✗ {service_file} not found")
            all_ok = False
            continue
        
        try:
            # Try to compile
            with open(filepath, 'r') as f:
                code = f.read()
            
            compile(code, filepath, 'exec')
            print(f"  ✓ {service_file} compiles successfully")
            
            # Check for singleton instance
            if 'Singleton instance' in code or '# Singleton' in code:
                print(f"    - Has singleton instance")
            
        except SyntaxError as e:
            print(f"  ✗ {service_file} has syntax error: {e}")
            all_ok = False
        except Exception as e:
            print(f"  ✗ Error checking {service_file}: {e}")
            all_ok = False
    
    return all_ok


def main():
    """Run minimal tests."""
    print("=" * 70)
    print("Minimal Test Runner - Structure and Syntax Verification")
    print("=" * 70)
    
    results = []
    
    # Check test files
    test_files = [
        'tests/services/test_user_path_service.py',
        'tests/services/test_path_builder.py',
        'tests/services/test_cando_complexity_service.py'
    ]
    
    print("\n" + "=" * 70)
    print("Test File Structure Check")
    print("=" * 70)
    
    for test_file in test_files:
        filepath = os.path.join(os.path.dirname(__file__), test_file)
        results.append((test_file, check_test_file_structure(filepath)))
    
    # Verify imports
    results.append(("Test imports verification", verify_test_imports()))
    
    # Check service files
    results.append(("Service files check", check_service_files()))
    
    # Summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False
    
    print("=" * 70)
    if all_passed:
        print("✓ All structure checks passed!")
        print("\nNote: Full runtime tests require dependencies to be installed.")
        print("To run full tests, use: pytest tests/services/")
        return 0
    else:
        print("✗ Some checks failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

