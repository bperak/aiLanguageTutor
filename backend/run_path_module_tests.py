#!/usr/bin/env python3
"""
Test runner for User Path Module.

This script runs all tests for the User Path Module.
It loads environment variables from .env file and runs pytest.

Usage:
    python run_path_module_tests.py
    python run_path_module_tests.py -v  # verbose
    python run_path_module_tests.py -k test_complexity  # run specific tests
"""

import sys
import os
import subprocess
from pathlib import Path

# Add parent directory to path to find .env
backend_dir = Path(__file__).parent
project_root = backend_dir.parent
env_file = project_root / ".env"

def load_env_file():
    """Load environment variables from .env file."""
    if env_file.exists():
        print(f"✓ Loading environment from {env_file}")
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
        return True
    else:
        print(f"⚠ .env file not found at {env_file}")
        return False

def check_dependencies():
    """Check if required dependencies are available."""
    print("\nChecking dependencies...")
    missing = []
    
    try:
        import pytest
        print("  ✓ pytest available")
    except ImportError:
        missing.append("pytest")
        print("  ✗ pytest not available")
    
    try:
        import pytest_asyncio
        print("  ✓ pytest-asyncio available")
    except ImportError:
        missing.append("pytest-asyncio")
        print("  ✗ pytest-asyncio not available")
    
    try:
        import structlog
        print("  ✓ structlog available")
    except ImportError:
        missing.append("structlog")
        print("  ✗ structlog not available")
    
    try:
        from app.core.config import settings
        print("  ✓ app.core.config available")
    except ImportError as e:
        missing.append("app dependencies")
        print(f"  ✗ app.core.config: {e}")
    
    return missing

def run_tests(test_args=None):
    """Run pytest with the test files."""
    if test_args is None:
        test_args = []
    
    test_files = [
        "tests/services/test_user_path_service.py",
        "tests/services/test_path_builder.py",
        "tests/services/test_cando_complexity_service.py"
    ]
    
    # Build pytest command
    cmd = [
        sys.executable, "-m", "pytest",
        *test_files,
        "-v",
        "--tb=short",
        *test_args
    ]
    
    print(f"\nRunning tests with: {' '.join(cmd)}")
    print("=" * 70)
    
    try:
        result = subprocess.run(cmd, cwd=backend_dir)
        return result.returncode
    except FileNotFoundError:
        print("✗ pytest not found. Please install dependencies:")
        print("  pip install pytest pytest-asyncio")
        return 1
    except Exception as e:
        print(f"✗ Error running tests: {e}")
        return 1

def main():
    """Main test runner."""
    print("=" * 70)
    print("User Path Module Test Runner")
    print("=" * 70)
    
    # Load environment
    env_loaded = load_env_file()
    
    # Check dependencies
    missing = check_dependencies()
    
    if missing:
        print(f"\n⚠ Missing dependencies: {', '.join(missing)}")
        print("Please install them with:")
        print("  pip install pytest pytest-asyncio structlog")
        print("  or")
        print("  poetry install")
        print("\nContinuing anyway...")
    
    # Get additional test arguments from command line
    test_args = sys.argv[1:] if len(sys.argv) > 1 else []
    
    # Run tests
    return_code = run_tests(test_args)
    
    print("\n" + "=" * 70)
    if return_code == 0:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed")
    print("=" * 70)
    
    return return_code

if __name__ == "__main__":
    sys.exit(main())

