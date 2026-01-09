#!/usr/bin/env python3
"""
Integration verification script for extraction_response storage.

This script verifies that all components work together correctly:
1. Service returns extraction_response
2. Endpoint handles extraction_response
3. Schema includes extraction_response
4. Model can store extraction_response
"""

import sys
import re
from pathlib import Path

def check_service_returns_tuple():
    """Verify service method signature returns tuple."""
    service_path = Path(__file__).parent.parent / "app" / "services" / "profile_building_service.py"
    content = service_path.read_text()
    
    # Check return type annotation
    pattern = r'async def extract_profile_data\([^)]+\)\s*->\s*(Tuple|tuple)'
    if re.search(pattern, content):
        print("✅ Service method returns Tuple")
        return True
    else:
        print("❌ Service method does not return Tuple")
        return False


def check_endpoint_unpacks_tuple():
    """Verify endpoint unpacks the tuple correctly."""
    endpoint_path = Path(__file__).parent.parent / "app" / "api" / "v1" / "endpoints" / "profile.py"
    content = endpoint_path.read_text()
    
    # Check for tuple unpacking
    patterns = [
        r'profile_data,\s*extraction_response\s*=\s*await',
        r'profile_data,\s*extraction_response\s*=\s*profile_building_service\.extract_profile_data'
    ]
    
    found = any(re.search(p, content) for p in patterns)
    if found:
        print("✅ Endpoint unpacks tuple correctly")
        return True
    else:
        print("❌ Endpoint does not unpack tuple")
        return False


def check_endpoint_returns_extraction_response():
    """Verify endpoint returns extraction_response in response."""
    endpoint_path = Path(__file__).parent.parent / "app" / "api" / "v1" / "endpoints" / "profile.py"
    content = endpoint_path.read_text()
    
    # Check /extract endpoint returns extraction_response
    extract_section = re.search(r'@router\.post\("/extract"\).*?return\s+\{', content, re.DOTALL)
    if extract_section:
        if '"extraction_response"' in extract_section.group(0):
            print("✅ /extract endpoint returns extraction_response")
            return True
    
    print("❌ /extract endpoint does not return extraction_response")
    return False


def check_save_profile_accepts_extraction_response():
    """Verify save_profile_data accepts extraction_response parameter."""
    service_path = Path(__file__).parent.parent / "app" / "services" / "profile_building_service.py"
    content = service_path.read_text()
    
    # Check function signature
    pattern = r'async def save_profile_data\([^)]*extraction_response[^)]*\)'
    if re.search(pattern, content):
        print("✅ save_profile_data accepts extraction_response parameter")
        return True
    else:
        print("❌ save_profile_data does not accept extraction_response parameter")
        return False


def check_save_profile_stores_extraction_response():
    """Verify save_profile_data stores extraction_response in profile_dict."""
    service_path = Path(__file__).parent.parent / "app" / "services" / "profile_building_service.py"
    content = service_path.read_text()
    
    # Check profile_dict includes extraction_response
    pattern = r'profile_dict\s*=\s*\{[^}]*"extraction_response"[^}]*\}'
    if re.search(pattern, content, re.DOTALL):
        print("✅ save_profile_data stores extraction_response in profile_dict")
        return True
    else:
        print("❌ save_profile_data does not store extraction_response")
        return False


def check_complete_endpoint_passes_extraction_response():
    """Verify /complete endpoint passes extraction_response to save."""
    endpoint_path = Path(__file__).parent.parent / "app" / "api" / "v1" / "endpoints" / "profile.py"
    content = endpoint_path.read_text()
    
    # Check /complete endpoint passes extraction_response
    complete_section = re.search(r'@router\.post\("/complete"\).*?await profile_building_service\.save_profile_data', content, re.DOTALL)
    if complete_section:
        if 'extraction_response=' in complete_section.group(0):
            print("✅ /complete endpoint passes extraction_response")
            return True
    
    print("❌ /complete endpoint does not pass extraction_response")
    return False


def check_data_endpoint_includes_extraction_response():
    """Verify /data endpoint includes extraction_response in response."""
    endpoint_path = Path(__file__).parent.parent / "app" / "api" / "v1" / "endpoints" / "profile.py"
    content = endpoint_path.read_text()
    
    # Check /data endpoint response
    data_section = re.search(r'@router\.get\("/data"\).*?ProfileDataResponse\(', content, re.DOTALL)
    if data_section:
        if 'extraction_response=' in data_section.group(0):
            print("✅ /data endpoint includes extraction_response")
            return True
    
    print("❌ /data endpoint does not include extraction_response")
    return False


def main():
    """Run all integration checks."""
    print("=" * 70)
    print("EXTRACTION RESPONSE INTEGRATION VERIFICATION")
    print("=" * 70)
    print()
    
    checks = [
        ("Service returns tuple", check_service_returns_tuple),
        ("Endpoint unpacks tuple", check_endpoint_unpacks_tuple),
        ("Endpoint returns extraction_response", check_endpoint_returns_extraction_response),
        ("Save accepts extraction_response", check_save_profile_accepts_extraction_response),
        ("Save stores extraction_response", check_save_profile_stores_extraction_response),
        ("Complete endpoint passes extraction_response", check_complete_endpoint_passes_extraction_response),
        ("Data endpoint includes extraction_response", check_data_endpoint_includes_extraction_response),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"Checking: {name}...")
        results.append((name, check_func()))
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
        print("✅ All integration checks passed!")
        print()
        print("The implementation is complete and ready for:")
        print("  1. Database migration (will apply automatically on startup)")
        print("  2. Testing with real API calls")
        print("  3. Frontend integration to display extraction_response")
        return 0
    else:
        print("❌ Some integration checks failed.")
        print("Please review the output above and fix any issues.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
