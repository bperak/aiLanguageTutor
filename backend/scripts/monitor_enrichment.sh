#!/bin/bash
# Monitor enrichment progress

echo "Monitoring UniDic enrichment progress..."
echo "Press Ctrl+C to stop monitoring (enrichment will continue in background)"
echo ""

while true; do
    clear
    echo "=== $(date) ==="
    docker exec ai-tutor-backend bash -c "cd /app && PYTHONPATH=/app poetry run python scripts/check_pos_progress.py" 2>/dev/null
    
    # Check if process is still running
    if docker exec ai-tutor-backend pgrep -f run_enrichment_until_complete > /dev/null 2>&1; then
        echo ""
        echo "✓ Enrichment process is running"
    else
        echo ""
        echo "⚠ Enrichment process not found (may have completed)"
    fi
    
    echo ""
    echo "Refreshing in 30 seconds... (Ctrl+C to stop monitoring)"
    sleep 30
done
