#!/bin/bash
# Script to open browser and show learning plan

set -e

echo "Creating test user and completing profile..."
cd /home/benedikt/aiLanguageTutor

# Run the test script to create user and complete profile
docker exec ai-tutor-backend python /tmp/test_profile_plan_display.py 2>&1 | grep -E "(TEST_USERNAME|Authenticated|Profile completed)" || true

echo ""
echo "=========================================="
echo "Learning Plan Browser Access"
echo "=========================================="
echo ""
echo "The frontend is available at: http://localhost:3000"
echo ""
echo "To see the learning plan:"
echo "1. Open your browser and go to: http://localhost:3000"
echo "2. Login with a test account (or use the one just created)"
echo "3. The learning plan should appear automatically"
echo ""
echo "If you want to see it in an automated browser, I can take a screenshot."
echo "Would you like me to take a screenshot? (This will be saved to /tmp/learning_plan.png)"

