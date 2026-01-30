#!/bin/bash
# ==============================================================================
# Sprint 2 Task 6 Verification Script
# Container UI List & Actions
# ==============================================================================
#
# This script verifies the implementation of Sprint 2 Task 6:
# - Container UI loads without errors
# - Hardware limits display correctly
# - Filtering works (status, environment, search)
# - Auto-refresh functionality
# - Container actions (start/stop/restart/delete)
# - Toast notifications
# - Confirmation modals
# - Container details modal
#
# Prerequisites:
# - Docker Compose environment running
# - Default admin user created (admin/admin123)
#
# Usage:
#     chmod +x scripts/verify_sprint2_task6.sh
#     ./scripts/verify_sprint2_task6.sh
#
# ==============================================================================

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
PASS=0
FAIL=0

# Base URL
BASE_URL="http://localhost:5000"

echo ""
echo "======================================================================"
echo "  Sprint 2 - Task 6: Container UI List & Actions"
echo "  Verification Script"
echo "======================================================================"
echo ""
echo "Note: API endpoints are unprotected per v2.0.0 perimeter security design"
echo ""

# ==============================================================================
# 0. Cleanup Existing Test Containers
# ==============================================================================
echo "0. Cleanup Existing Test Containers"
echo "=============================="

# Check for existing test container
EXISTING=$(curl -s "$BASE_URL/api/containers" | grep -o "task6-test-nginx" || true)

if [ -n "$EXISTING" ]; then
    echo "Found existing test container, cleaning up..."
    
    # Try to delete by name (force delete)
    DELETE_RESULT=$(curl -s -X DELETE "$BASE_URL/api/containers/task6-test-nginx?force=true")
    
    if echo "$DELETE_RESULT" | grep -q '"success": true'; then
        echo -e "${GREEN}✓${NC} Existing test container removed"
        ((PASS++))
        sleep 2
    else
        echo -e "${YELLOW}⚠${NC} Could not remove existing container (may not exist)"
        echo "  This is OK, continuing..."
    fi
else
    echo -e "${GREEN}✓${NC} No existing test containers to clean up"
    ((PASS++))
fi

echo ""

# ==============================================================================
# 1. Prerequisites Check
# ==============================================================================
echo "1. Prerequisites Check"
echo "=============================="

# Check Docker Compose running
if docker compose -f docker-compose.dev.yml ps 2>/dev/null | grep -q "Up"; then
    echo -e "${GREEN}✓${NC} Docker Compose environment is running"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Docker Compose environment not running"
    echo "  Start with: docker compose -f docker-compose.dev.yml up -d"
    ((FAIL++))
    exit 1
fi

# Check jq installed (for JSON parsing)
if command -v jq &> /dev/null; then
    echo -e "${GREEN}✓${NC} jq is installed"
    ((PASS++))
else
    echo -e "${YELLOW}⚠${NC} jq not installed (JSON parsing will be limited)"
    echo "  Install: sudo apt-get install jq"
fi

echo ""

# ==============================================================================
# 2. API Endpoint Verification
# ==============================================================================
echo "2. API Endpoint Verification"
echo "=============================="

# Health check
HEALTH=$(curl -s "$BASE_URL/api/health")
if echo "$HEALTH" | grep -q '"status"'; then
    echo -e "${GREEN}✓${NC} Health endpoint responding"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Health endpoint not responding"
    ((FAIL++))
fi

# Hardware profile
HARDWARE=$(curl -s "$BASE_URL/api/system/hardware")
if echo "$HARDWARE" | grep -q '"success": true'; then
    PROFILE=$(echo "$HARDWARE" | jq -r '.data.profile_name' 2>/dev/null || echo "unknown")
    MAX_CONTAINERS=$(echo "$HARDWARE" | jq -r '.data.max_containers' 2>/dev/null || echo "unknown")
    echo -e "${GREEN}✓${NC} Hardware endpoint responding"
    echo "  Profile: $PROFILE (Max containers: $MAX_CONTAINERS)"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Hardware endpoint not responding"
    ((FAIL++))
fi

# Container list
CONTAINERS=$(curl -s "$BASE_URL/api/containers")
if echo "$CONTAINERS" | grep -q '"success": true'; then
    COUNT=$(echo "$CONTAINERS" | jq '.data | length' 2>/dev/null || echo "unknown")
    echo -e "${GREEN}✓${NC} Containers endpoint responding"
    echo "  Current containers: $COUNT"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Containers endpoint not responding"
    ((FAIL++))
fi

echo ""

# ==============================================================================
# 3. UI Template Verification
# ==============================================================================
echo "3. UI Template Verification"
echo "=============================="

required_templates=(
    "frontend/templates/containers.html"
    "frontend/templates/components/navbar.html"
    "frontend/templates/base.html"
)

for template in "${required_templates[@]}"; do
    if [ -f "$template" ]; then
        echo -e "${GREEN}✓${NC} $template exists"
        ((PASS++))
    else
        echo -e "${RED}✗${NC} $template missing"
        ((FAIL++))
    fi
done

echo ""

# ==============================================================================
# 4. Container UI Page Load Test
# ==============================================================================
echo "4. Container UI Page Load Test"
echo "=============================="

# Note: UI routes ARE protected, so we need to login first
echo "Logging in for UI access (UI routes are protected)..."
LOGIN_RESPONSE=$(curl -s -c /tmp/ui_session.txt -X POST "$BASE_URL/api/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"password": "admin123"}')

if echo "$LOGIN_RESPONSE" | grep -q '"success": true'; then
    echo -e "${GREEN}✓${NC} UI session established"
    ((PASS++))
    
    UI_RESPONSE=$(curl -s -b /tmp/ui_session.txt -w "\n%{http_code}" "$BASE_URL/containers")
else
    echo -e "${RED}✗${NC} Could not establish UI session"
    echo "  Note: UI routes require authentication per v2.0.0 design"
    ((FAIL++))
    UI_RESPONSE="401"
fi
HTTP_CODE=$(echo "$UI_RESPONSE" | tail -n1)
BODY=$(echo "$UI_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓${NC} Container UI page loads (HTTP 200)"
    ((PASS++))
    
    # Check for essential UI elements
    if echo "$BODY" | grep -q "x-data"; then
        echo -e "${GREEN}✓${NC} Alpine.js state management detected"
        ((PASS++))
    else
        echo -e "${RED}✗${NC} Alpine.js state management missing"
        ((FAIL++))
    fi
    
    if echo "$BODY" | grep -q "Hardware Profile"; then
        echo -e "${GREEN}✓${NC} Hardware profile display detected"
        ((PASS++))
    else
        echo -e "${RED}✗${NC} Hardware profile display missing"
        ((FAIL++))
    fi
    
    if echo "$BODY" | grep -q "modal"; then
        echo -e "${GREEN}✓${NC} Modal system detected"
        ((PASS++))
    else
        echo -e "${YELLOW}⚠${NC} Modal system not detected (may be dynamically loaded)"
    fi
    
else
    echo -e "${RED}✗${NC} Container UI page failed to load (HTTP $HTTP_CODE)"
    ((FAIL++))
fi

echo ""

# ==============================================================================
# 5. UI Feature Verification
# ==============================================================================
echo "5. UI Feature Verification"
echo "=============================="

# Check for filtering controls
if echo "$BODY" | grep -q "x-model=\"filters.status\""; then
    echo -e "${GREEN}✓${NC} Status filter detected"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Status filter missing"
    ((FAIL++))
fi

if echo "$BODY" | grep -q "x-model=\"filters.environment\""; then
    echo -e "${GREEN}✓${NC} Environment filter detected"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Environment filter missing"
    ((FAIL++))
fi

if echo "$BODY" | grep -q "x-model=\"filters.search\""; then
    echo -e "${GREEN}✓${NC} Search filter detected"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Search filter missing"
    ((FAIL++))
fi

# Check for action buttons
ACTION_BUTTONS=(
    "start"
    "stop"
    "restart"
    "delete"
)

for action in "${ACTION_BUTTONS[@]}"; do
    if echo "$BODY" | grep -qi "$action"; then
        echo -e "${GREEN}✓${NC} $action button/action detected"
        ((PASS++))
    else
        echo -e "${YELLOW}⚠${NC} $action button/action not clearly detected"
    fi
done

# Check for auto-refresh
if echo "$BODY" | grep -q "setInterval"; then
    echo -e "${GREEN}✓${NC} Auto-refresh mechanism detected"
    ((PASS++))
else
    echo -e "${YELLOW}⚠${NC} Auto-refresh not detected (may be in external JS)"
fi

echo ""

# ==============================================================================
# 6. Functional Testing (Create Test Container)
# ==============================================================================
echo "6. Functional Testing"
echo "=============================="

# Create test container via API
echo "Creating test container..."
CREATE_RESPONSE=$(curl -s -X POST "$BASE_URL/api/containers" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "task6-test-nginx",
        "image": "nginx:alpine",
        "environment": "DEV",
        "ports": {"80/tcp": "8082"},
        "auto_start": true,
        "pull_if_missing": true
    }')

if echo "$CREATE_RESPONSE" | grep -q '"success": true'; then
    CONTAINER_NAME=$(echo "$CREATE_RESPONSE" | jq -r '.data.name' 2>/dev/null)
    CONTAINER_DOCKER_ID=$(echo "$CREATE_RESPONSE" | jq -r '.data.container_id' 2>/dev/null)
    echo -e "${GREEN}✓${NC} Test container created (name: $CONTAINER_NAME)"
    echo "  Docker ID: ${CONTAINER_DOCKER_ID:0:12}..."
    ((PASS++))
    
    # Wait for container to start
    sleep 5
    
    # Verify container appears in list
    UPDATED_LIST=$(curl -s "$BASE_URL/api/containers")
    if echo "$UPDATED_LIST" | grep -q "task6-test-nginx"; then
        echo -e "${GREEN}✓${NC} Container appears in API list"
        ((PASS++))
    else
        echo -e "${RED}✗${NC} Container not found in API list"
        ((FAIL++))
    fi
    
    # Test container actions (using container name)
    echo ""
    echo "Testing container actions (using container name: $CONTAINER_NAME)..."
    
    # Stop container
    STOP_RESPONSE=$(curl -s -X POST "$BASE_URL/api/containers/$CONTAINER_NAME/stop")
    if echo "$STOP_RESPONSE" | grep -q '"success": true'; then
        echo -e "${GREEN}✓${NC} Stop action works"
        ((PASS++))
    else
        echo -e "${RED}✗${NC} Stop action failed"
        echo "  Response: $STOP_RESPONSE"
        ((FAIL++))
    fi
    
    sleep 2
    
    # Start container
    START_RESPONSE=$(curl -s -X POST "$BASE_URL/api/containers/$CONTAINER_NAME/start")
    if echo "$START_RESPONSE" | grep -q '"success": true'; then
        echo -e "${GREEN}✓${NC} Start action works"
        ((PASS++))
    else
        echo -e "${RED}✗${NC} Start action failed"
        echo "  Response: $START_RESPONSE"
        ((FAIL++))
    fi
    
    sleep 2
    
    # Restart container
    RESTART_RESPONSE=$(curl -s -X POST "$BASE_URL/api/containers/$CONTAINER_NAME/restart")
    if echo "$RESTART_RESPONSE" | grep -q '"success": true'; then
        echo -e "${GREEN}✓${NC} Restart action works"
        ((PASS++))
    else
        echo -e "${RED}✗${NC} Restart action failed"
        echo "  Response: $RESTART_RESPONSE"
        ((FAIL++))
    fi
    
    sleep 2
    
    # Delete container
    DELETE_RESPONSE=$(curl -s -X DELETE "$BASE_URL/api/containers/$CONTAINER_NAME?force=true")
    if echo "$DELETE_RESPONSE" | grep -q '"success": true'; then
        echo -e "${GREEN}✓${NC} Delete action works"
        ((PASS++))
    else
        echo -e "${RED}✗${NC} Delete action failed"
        echo "  Response: $DELETE_RESPONSE"
        ((FAIL++))
    fi
    
else
    echo -e "${RED}✗${NC} Failed to create test container"
    echo "  Response: $CREATE_RESPONSE"
    ((FAIL++))
fi

echo ""

# ==============================================================================
# 7. Browser Console Error Check (Manual)
# ==============================================================================
echo "7. Manual Verification Required"
echo "=============================="

echo -e "${YELLOW}⚠${NC} The following checks require manual verification:"
echo ""
echo "  1. Open http://localhost:5000/containers in browser"
echo "  2. Open Developer Tools (F12)"
echo "  3. Check Console tab for JavaScript errors"
echo "  4. Verify container list displays correctly"
echo "  5. Test filtering by status/environment/search"
echo "  6. Verify auto-refresh updates list every 10 seconds"
echo "  7. Test action buttons (start/stop/restart/delete)"
echo "  8. Verify toast notifications appear on actions"
echo "  9. Verify confirmation modal on delete"
echo "  10. Test container details modal"
echo ""
echo "Expected Results:"
echo "  ✓ No console errors"
echo "  ✓ Container list loads and displays correctly"
echo "  ✓ Hardware limits show profile name and max containers"
echo "  ✓ Filters work correctly"
echo "  ✓ Auto-refresh updates list"
echo "  ✓ Action buttons trigger expected API calls"
echo "  ✓ Toast notifications appear and auto-dismiss"
echo "  ✓ Confirmation modal prevents accidental deletes"
echo "  ✓ Details modal shows complete container information"
echo ""

# ==============================================================================
# 8. Flask Logs Check
# ==============================================================================
echo "8. Flask Application Logs"
echo "=============================="

echo "Recent Flask logs (last 50 lines):"
docker compose -f docker-compose.dev.yml logs --tail=50 dockermate

echo ""

# ==============================================================================
# Summary
# ==============================================================================
echo "======================================================================"
echo "Verification Summary"
echo "======================================================================"
echo -e "Automated Tests Passed: ${GREEN}${PASS}${NC}"
echo -e "Automated Tests Failed: ${RED}${FAIL}${NC}"
echo ""

# Cleanup
rm -f /tmp/ui_session.txt

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✓ All automated checks passed!${NC}"
    echo ""
    echo "Task 6 Status: ${YELLOW}90% Complete${NC}"
    echo ""
    echo "Remaining Steps:"
    echo "  1. Complete manual browser testing (see section 7)"
    echo "  2. Verify no console errors"
    echo "  3. Test all UI interactions"
    echo "  4. Document any issues found"
    echo ""
    echo "When manual testing is complete:"
    echo "  - Update PROJECT_STATUS.md"
    echo "  - Mark Task 6 as 100% complete"
    echo "  - Proceed to Task 7 (Container Create Form)"
    exit 0
else
    echo -e "${RED}✗ Some automated checks failed.${NC}"
    echo ""
    echo "Common Issues:"
    echo "  - Docker Compose not running: docker compose -f docker-compose.dev.yml up -d"
    echo "  - Missing templates: Check file paths"
    echo "  - API failures: Check Flask logs above"
    echo "  - Database issues: Restart Docker Compose with --build"
    echo ""
    echo "Debug Commands:"
    echo "  docker compose -f docker-compose.dev.yml logs -f"
    echo "  curl http://localhost:5000/api/health"
    echo "  curl http://localhost:5000/api/containers"
    exit 1
fi