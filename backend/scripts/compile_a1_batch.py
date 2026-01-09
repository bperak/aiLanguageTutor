#!/usr/bin/env python3
"""Compile 10 specific A1 lessons"""
import requests
import time

# Actual A1 CanDo IDs from Neo4j
candos = [
    "JF:105", "JF:106", "JF:107", "JF:108", "JF:109", 
    "JF:110", "JF:126", "JF:127", "JF:145", "JF:147"
]

print("Compiling 10 A1 Lessons")
print("=" * 60)

results = []
for idx, can_do_id in enumerate(candos, 1):
    print(f"[{idx}/10] {can_do_id}...", end=" ", flush=True)
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
            print(f"✓ ({duration:.1f}s) v{data.get('version', '?')}")
            results.append({"can_do_id": can_do_id, "status": "success", "duration": duration, "version": data.get('version')})
        else:
            print(f"✗ HTTP {response.status_code}")
            results.append({"can_do_id": can_do_id, "status": "failed", "error": f"HTTP {response.status_code}"})
            
    except Exception as e:
        duration = time.time() - start
        print(f"✗ {str(e)[:60]}")
        results.append({"can_do_id": can_do_id, "status": "failed", "error": str(e)})

print()
print("=" * 60)
success = sum(1 for r in results if r['status'] == 'success')
print(f"Success: {success}/10")
if success > 0:
    avg_time = sum(r.get('duration', 0) for r in results if r['status'] == 'success') / success
    print(f"Average time: {avg_time:.1f}s per lesson")
    print(f"Total time: {sum(r.get('duration', 0) for r in results):.1f}s")

# Show failures
failed = [r for r in results if r['status'] == 'failed']
if failed:
    print(f"\nFailed ({len(failed)}):")
    for f in failed:
        print(f"  - {f['can_do_id']}: {f['error']}")

