#!/bin/bash
# Watch POS progress - updates every 10 seconds

echo "Watching POS resolution progress (Ctrl+C to stop)..."
echo ""

while true; do
    clear
    docker exec ai-tutor-backend bash -c "cd /app && PYTHONPATH=/app poetry run python scripts/check_pos_progress.py" 2>/dev/null
    echo ""
    echo "Refreshing in 10 seconds... (Ctrl+C to stop)"
    sleep 10
done
