#!/usr/bin/env python3
"""Quick script to compile 10 A1 lessons via API"""
import requests
import time

# Get A1 CanDo IDs
candos = [
    "JF:1", "JF:2", "JF:3", "JF:4", "JF:5", 
    "JF:6", "JF:7", "JF:8", "JF:9", "JF:10"
]

print("Compiling 10 A1 Lessons")
print("=" * 60)

results = []
for idx, can_do_id in enumerate(candos, 1):
    print(f"[{idx}/10] Compiling {can_do_id}...", end=" ", flush=True)
    start = time.time()
    
    try:
        response = requests.post(
            f"http://localhost:8000/api/v1/cando/lessons/compile_v2",
            params={
                "can_do_id": can_do_id,
                "metalanguage": "en",
                "model": "gpt-4o"
            },
            timeout=180
        )
        
        duration = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ ({duration:.1f}s) - v{data.get('version', '?')}")
            results.append({"can_do_id": can_do_id, "status": "success", "duration": duration})
        else:
            print(f"✗ HTTP {response.status_code}")
            results.append({"can_do_id": can_do_id, "status": "failed", "error": response.text[:100]})
            
    except Exception as e:
        duration = time.time() - start
        print(f"✗ Error: {str(e)[:50]}")
        results.append({"can_do_id": can_do_id, "status": "failed", "error": str(e)})

print()
print("=" * 60)
success = sum(1 for r in results if r['status'] == 'success')
print(f"Success: {success}/10")
print(f"Total time: {sum(r.get('duration', 0) for r in results):.1f}s")

