#!/bin/bash
set -euo pipefail

# E2E Test Runner for CI/CD
# Runs all MCP scenarios in a Docker environment
#
# Usage:
#   ./scripts/run-e2e-tests.sh [scenario1.json] [scenario2.json] ...
#   ./scripts/run-e2e-tests.sh  # Runs all scenarios
#
# Environment Variables:
#   COMPOSE_FILE_PATH     - Docker compose file (default: docker-compose.server.yml)
#   MCP_RUNNER_SERVICE    - MCP runner service name (default: mcp-runner)
#   TARGET_BACKEND        - Backend URL (default: http://backend:8000)
#   TARGET_FRONTEND       - Frontend URL (default: http://frontend:3000)
#   E2E_TIMEOUT           - Timeout per scenario in seconds (default: 300)

COMPOSE_FILE_PATH="${COMPOSE_FILE_PATH:-docker-compose.server.yml}"
SERVICE="${MCP_RUNNER_SERVICE:-mcp-runner}"
TARGET_BACKEND="${TARGET_BACKEND:-http://backend:8000}"
TARGET_FRONTEND="${TARGET_FRONTEND:-http://frontend:3000}"
E2E_TIMEOUT="${E2E_TIMEOUT:-300}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "E2E Test Runner"
echo "=========================================="
echo "Compose file: ${COMPOSE_FILE_PATH}"
echo "Service: ${SERVICE}"
echo "Backend: ${TARGET_BACKEND}"
echo "Frontend: ${TARGET_FRONTEND}"
echo "Timeout: ${E2E_TIMEOUT}s per scenario"
echo ""

# Determine which scenarios to run
if [[ $# -gt 0 ]]; then
  SCENARIOS=("$@")
  echo "Running ${#SCENARIOS[@]} specified scenario(s)..."
else
  # Default: run all e2e scenarios
  SCENARIOS=(
    "/work/scenarios/smoke.json"
    "/work/scenarios/no_dev_next_endpoints.json"
    "/work/scenarios/home_status_e2e.json"
    "/work/scenarios/login_e2e.json"
    "/work/scenarios/full_registration_e2e.json"
    "/work/scenarios/profile_build_schema.json"
    "/work/scenarios/lexical_graph_e2e.json"
    "/work/scenarios/grammar_study_e2e.json"
    "/work/scenarios/cando_lesson_e2e.json"
    "/work/scenarios/prelesson_kit_flow.json"
  )
  echo "Running all ${#SCENARIOS[@]} E2E scenarios..."
fi

echo ""

# Check if Docker services are running
if ! docker compose -f "${COMPOSE_FILE_PATH}" ps "${SERVICE}" | grep -q "Up"; then
  echo -e "${YELLOW}⚠️  MCP runner service not running. Starting services...${NC}"
  docker compose -f "${COMPOSE_FILE_PATH}" up -d "${SERVICE}"
  echo "Waiting for service to be ready..."
  sleep 5
fi

# Wait for backend and frontend to be healthy
echo "Waiting for backend and frontend to be healthy..."
MAX_WAIT=120
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
  if docker compose -f "${COMPOSE_FILE_PATH}" ps backend | grep -q "healthy" && \
     docker compose -f "${COMPOSE_FILE_PATH}" ps frontend | grep -q "healthy"; then
    echo -e "${GREEN}✅ Services are healthy${NC}"
    break
  fi
  sleep 2
  WAITED=$((WAITED + 2))
  echo -n "."
done

if [ $WAITED -ge $MAX_WAIT ]; then
  echo -e "\n${RED}❌ Services did not become healthy within ${MAX_WAIT}s${NC}"
  docker compose -f "${COMPOSE_FILE_PATH}" ps
  exit 1
fi

echo ""

# Run scenarios
FAILED_SCENARIOS=()
PASSED_SCENARIOS=()

for scenario in "${SCENARIOS[@]}"; do
  scenario_name=$(basename "$scenario" .json)
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "Running: ${scenario_name}"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  
  # Run scenario with timeout
  if timeout "${E2E_TIMEOUT}" docker compose -f "${COMPOSE_FILE_PATH}" exec -T -e TARGET_BACKEND="${TARGET_BACKEND}" -e TARGET_FRONTEND="${TARGET_FRONTEND}" "${SERVICE}" \
    node /work/scripts/mcp_runner.mjs "$scenario"; then
    echo -e "${GREEN}✅ PASS: ${scenario_name}${NC}"
    PASSED_SCENARIOS+=("$scenario_name")
  else
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 124 ]; then
      echo -e "${RED}❌ TIMEOUT: ${scenario_name} (exceeded ${E2E_TIMEOUT}s)${NC}"
    else
      echo -e "${RED}❌ FAIL: ${scenario_name}${NC}"
    fi
    FAILED_SCENARIOS+=("$scenario_name")
  fi
  echo ""
done

# Summary
echo "=========================================="
echo "E2E Test Summary"
echo "=========================================="
echo -e "${GREEN}Passed: ${#PASSED_SCENARIOS[@]}${NC}"
echo -e "${RED}Failed: ${#FAILED_SCENARIOS[@]}${NC}"
echo ""

if [ ${#FAILED_SCENARIOS[@]} -gt 0 ]; then
  echo -e "${RED}Failed scenarios:${NC}"
  for failed in "${FAILED_SCENARIOS[@]}"; do
    echo "  - ${failed}"
  done
  echo ""
  exit 1
else
  echo -e "${GREEN}✅ All scenarios passed!${NC}"
  exit 0
fi
