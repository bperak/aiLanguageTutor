#!/bin/bash
# Test script for pre-lesson kit integration
# This script tests the pre-lesson kit integration flow

set -e

BASE_URL="${BASE_URL:-https://ailanguagetutor.syntagent.com}"
CAN_DO_ID="${CAN_DO_ID:-JFまるごと:336}"
USERNAME="${USERNAME:-admin_bperak}"
PASSWORD="${PASSWORD:-Teachable1A}"

echo "🧪 Testing Pre-Lesson Kit Integration"
echo "======================================"
echo "Base URL: $BASE_URL"
echo "CanDo ID: $CAN_DO_ID"
echo "Username: $USERNAME"
echo ""

# Step 1: Login and get token
echo "📝 Step 1: Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}")

TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
  echo "❌ Login failed!"
  echo "Response: $LOGIN_RESPONSE"
  exit 1
fi

echo "✅ Login successful"
echo ""

# Step 2: Get user info
echo "📝 Step 2: Getting user info..."
USER_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/auth/me" \
  -H "Authorization: Bearer $TOKEN")

USER_ID=$(echo "$USER_RESPONSE" | grep -o '"id":"[^"]*' | cut -d'"' -f4)

if [ -z "$USER_ID" ]; then
  echo "❌ Failed to get user ID!"
  echo "Response: $USER_RESPONSE"
  exit 1
fi

echo "✅ User ID: $USER_ID"
echo ""

# Step 3: Check if lesson exists
echo "📝 Step 3: Checking existing lessons..."
LESSON_LIST=$(curl -s -X GET "$BASE_URL/api/v1/cando/lessons/list?can_do_id=$(echo "$CAN_DO_ID" | jq -rR @uri)" \
  -H "Authorization: Bearer $TOKEN")

echo "Lessons found: $(echo "$LESSON_LIST" | grep -o '"id":[0-9]*' | wc -l)"
echo ""

# Step 4: Check backend logs for pre-lesson kit
echo "📝 Step 4: Checking backend logs for pre-lesson kit activity..."
echo "Run this command to see logs:"
echo "  docker logs ai-tutor-backend --tail 100 | grep -i 'prelesson\|kit'"
echo ""

# Step 5: Instructions for manual testing
echo "📝 Step 5: Manual Testing Instructions"
echo "======================================"
echo "1. Navigate to: $BASE_URL/cando/$(echo "$CAN_DO_ID" | jq -rR @uri)"
echo "2. Open browser console (F12)"
echo "3. Look for these console messages:"
echo "   - '👤 User ID for kit integration: $USER_ID'"
echo "   - '🟦 Compile status: {prelesson_kit_available: true/false}'"
echo "   - '📊 Pre-lesson kit usage: {...}' (after compilation)"
echo "4. Verify UI shows 'Pre-Lesson Kit Integration' card"
echo "5. Check backend logs:"
echo "   docker logs ai-tutor-backend --tail 100 | grep -i 'prelesson\|kit'"
echo ""
echo "Expected backend log messages:"
echo "  - prelesson_kit_fetched_from_path"
echo "  - prelesson_kit_integrated_into_compilation"
echo "  - prelesson_kit_usage_tracked"
echo ""

echo "✅ Test script complete!"
echo ""
echo "To trigger a compilation with pre-lesson kit:"
echo "1. Go to the lesson page"
echo "2. Click 'Regenerate' or compile a new lesson"
echo "3. The pre-lesson kit will be automatically fetched and integrated"
echo ""

