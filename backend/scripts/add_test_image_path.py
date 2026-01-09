# Quick test script to add test image path to lesson JSON
import json
from pathlib import Path

script_dir = Path(__file__).resolve().parent
repo_root = script_dir.parents[1]
lesson_file = repo_root / "backend" / "lessons_v2" / "canDo_JF_105_v1.json"
with open(lesson_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Add path to first word image
if 'lesson' in data and 'cards' in data['lesson']:
    words = data['lesson']['cards'].get('words', {}).get('items', [])
    if words and words[0].get('image'):
        words[0]['image']['path'] = 'images/lessons/cando/JF_105/test-image.png'
        print(f"Added path to first word image: {words[0]['image']['path']}")

with open(lesson_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Updated {lesson_file}")

