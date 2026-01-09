#!/usr/bin/env python3
"""
Simple script to verify extraction_response storage implementation.

This script checks:
1. Migration file exists and is valid SQL
2. Model includes extraction_response field
3. Service method signature is correct
4. Schema includes extraction_response field
"""

import sys
from pathlib import Path

def check_migration_file():
    """Check that migration file exists and has correct SQL."""
    migration_path = Path(__file__).parent.parent / "migrations" / "versions" / "add_profile_extraction_response.sql"
    
    if not migration_path.exists():
        print("❌ Migration file not found:", migration_path)
        return False
    
    content = migration_path.read_text()
    
    checks = [
        ("ALTER TABLE user_profiles" in content, "Has ALTER TABLE statement"),
        ("extraction_response" in content, "Has extraction_response column"),
        ("JSONB" in content, "Uses JSONB type"),
        ("COMMENT ON COLUMN" in content, "Has documentation comment"),
    ]
    
    all_pass = True
    for check, desc in checks:
        if check:
            print(f"✅ {desc}")
        else:
            print(f"❌ {desc}")
            all_pass = False
    
    return all_pass


def check_model_file():
    """Check that model file includes extraction_response."""
    model_path = Path(__file__).parent.parent / "app" / "models" / "database_models.py"
    
    if not model_path.exists():
        print("❌ Model file not found:", model_path)
        return False
    
    content = model_path.read_text()
    
    checks = [
        ("extraction_response" in content, "Model includes extraction_response field"),
        ("Column(JSON" in content or "JSONB" in content, "Uses JSON/JSONB type"),
    ]
    
    all_pass = True
    for check, desc in checks:
        if check:
            print(f"✅ {desc}")
        else:
            print(f"❌ {desc}")
            all_pass = False
    
    return all_pass


def check_service_file():
    """Check that service file has correct return type."""
    service_path = Path(__file__).parent.parent / "app" / "services" / "profile_building_service.py"
    
    if not service_path.exists():
        print("❌ Service file not found:", service_path)
        return False
    
    content = service_path.read_text()
    
    checks = [
        ("Tuple[ProfileData, Dict[str, Any]]" in content or "tuple[ProfileData, Dict[str, Any]]" in content, 
         "extract_profile_data returns tuple"),
        ("extraction_response" in content, "Service handles extraction_response"),
        ("raw_ai_response" in content, "Includes raw_ai_response in response"),
        ("assessment" in content, "Includes assessment in response"),
        ("model_used" in content, "Includes model_used in response"),
    ]
    
    all_pass = True
    for check, desc in checks:
        if check:
            print(f"✅ {desc}")
        else:
            print(f"❌ {desc}")
            all_pass = False
    
    return all_pass


def check_schema_file():
    """Check that schema includes extraction_response."""
    schema_path = Path(__file__).parent.parent / "app" / "schemas" / "profile.py"
    
    if not schema_path.exists():
        print("❌ Schema file not found:", schema_path)
        return False
    
    content = schema_path.read_text()
    
    checks = [
        ("extraction_response" in content, "Schema includes extraction_response field"),
        ("Optional[Dict[str, Any]]" in content, "Uses Optional Dict type"),
    ]
    
    all_pass = True
    for check, desc in checks:
        if check:
            print(f"✅ {desc}")
        else:
            print(f"❌ {desc}")
            all_pass = False
    
    return all_pass


def check_endpoint_file():
    """Check that endpoint handles extraction_response."""
    endpoint_path = Path(__file__).parent.parent / "app" / "api" / "v1" / "endpoints" / "profile.py"
    
    if not endpoint_path.exists():
        print("❌ Endpoint file not found:", endpoint_path)
        return False
    
    content = endpoint_path.read_text()
    
    checks = [
        ("extraction_response" in content, "Endpoint handles extraction_response"),
        ("profile_data, extraction_response" in content, "Unpacks tuple from extract"),
    ]
    
    all_pass = True
    for check, desc in checks:
        if check:
            print(f"✅ {desc}")
        else:
            print(f"❌ {desc}")
            all_pass = False
    
    return all_pass


def main():
    """Run all checks."""
    print("=" * 70)
    print("EXTRACTION RESPONSE STORAGE VERIFICATION")
    print("=" * 70)
    print()
    
    results = []
    
    print("1. Checking migration file...")
    results.append(("Migration", check_migration_file()))
    print()
    
    print("2. Checking model file...")
    results.append(("Model", check_model_file()))
    print()
    
    print("3. Checking service file...")
    results.append(("Service", check_service_file()))
    print()
    
    print("4. Checking schema file...")
    results.append(("Schema", check_schema_file()))
    print()
    
    print("5. Checking endpoint file...")
    results.append(("Endpoint", check_endpoint_file()))
    print()
    
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    all_pass = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_pass = False
    
    print()
    if all_pass:
        print("✅ All checks passed! Implementation looks correct.")
        return 0
    else:
        print("❌ Some checks failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
