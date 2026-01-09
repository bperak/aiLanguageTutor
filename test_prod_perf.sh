#!/bin/bash
# Test production site performance using curl

PRODUCTION_URL="https://ailanguagetutor.syntagent.com"
LOG_FILE="/home/benedikt/.cursor/debug.log"

# Clear log file
> "$LOG_FILE"

echo "=================================================================================="
echo "PRODUCTION PERFORMANCE TEST"
echo "Testing: $PRODUCTION_URL"
echo "=================================================================================="

# Function to test endpoint and log results
test_endpoint() {
    local endpoint=$1
    local name=$2
    local full_url="${PRODUCTION_URL}${endpoint}"
    
    echo ""
    echo "[$name] Testing $endpoint..."
    
    start_time=$(date +%s.%N)
    response=$(curl -s -o /dev/null -w "%{http_code}|%{time_total}|%{size_download}" \
        --max-time 30 \
        --location \
        "$full_url" 2>&1)
    end_time=$(date +%s.%N)
    
    duration_ms=$(echo "($end_time - $start_time) * 1000" | bc)
    
    if [[ $? -eq 0 ]]; then
        status_code=$(echo "$response" | cut -d'|' -f1)
        time_total=$(echo "$response" | cut -d'|' -f2)
        size=$(echo "$response" | cut -d'|' -f3)
        
        echo "   Status: $status_code, Duration: ${duration_ms}ms, Size: $size bytes"
        
        # Log to debug file
        echo "{\"sessionId\":\"debug-session\",\"runId\":\"prod-perf\",\"hypothesisId\":\"P1\",\"location\":\"test_prod_perf.sh:$name\",\"message\":\"$name completed\",\"data\":{\"endpoint\":\"$endpoint\",\"duration_ms\":$duration_ms,\"status\":$status_code,\"size\":$size},\"timestamp\":$(date +%s%3N)}" >> "$LOG_FILE"
        
        echo "$duration_ms"
    else
        echo "   Error: Request failed"
        echo "{\"sessionId\":\"debug-session\",\"runId\":\"prod-perf\",\"hypothesisId\":\"P1\",\"location\":\"test_prod_perf.sh:$name\",\"message\":\"$name failed\",\"data\":{\"endpoint\":\"$endpoint\",\"error\":\"Request failed\"},\"timestamp\":$(date +%s%3N)}" >> "$LOG_FILE"
        echo "0"
    fi
}

# Test endpoints
home_duration=$(test_endpoint "/" "HOME_PAGE")
sleep 1

login_duration=$(test_endpoint "/login" "LOGIN_PAGE")
sleep 1

register_duration=$(test_endpoint "/register" "REGISTER_PAGE")
sleep 1

# Test API endpoints
health_duration=$(test_endpoint "/api/v1/health/" "HEALTH_API")
sleep 1

# Summary
echo ""
echo "=================================================================================="
echo "PERFORMANCE SUMMARY"
echo "=================================================================================="
echo "Home Page: ${home_duration}ms"
echo "Login Page: ${login_duration}ms"
echo "Register Page: ${register_duration}ms"
echo "Health API: ${health_duration}ms"

# Check for slow responses
if (( $(echo "$home_duration > 2000" | bc -l) )); then
    echo "⚠️  Home page is SLOW (>2s)"
fi
if (( $(echo "$login_duration > 2000" | bc -l) )); then
    echo "⚠️  Login page is SLOW (>2s)"
fi
if (( $(echo "$register_duration > 2000" | bc -l) )); then
    echo "⚠️  Register page is SLOW (>2s)"
fi

echo ""
echo "Debug log written to: $LOG_FILE"

