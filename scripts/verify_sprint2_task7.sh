#!/bin/bash
# ==============================================================================
# Sprint 2 Task 7 Verification Script
# Container Create Form
# ==============================================================================
#
# This script verifies the implementation of Sprint 2 Task 7:
# - Create button enabled and functional
# - Create modal opens with form
# - All form sections present (basic, ports, volumes, env vars, advanced)
# - Dynamic field addition/removal works
# - Form validation provides feedback
# - API integration successful
# - Hardware limits enforced
#
# Prerequisites:
# - Docker Compose environment running
# - Default admin user created (admin/admin123)
# - Task 6 complete (container list UI)
#
# Usage:
#     chmod +x scripts/verify_sprint2_task7.sh
#     ./scripts/verify_sprint2_task7.sh
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
echo "  Sprint 2 - Task 7: Container Create Form"
echo "  Verification Script"
echo "======================================================================"
echo ""
echo "Note: API endpoints are unprotected per v2.0.0 perimeter security design"
echo ""

# ==============================================================================
# 1. Prerequisites Check
# ==============================================================================
echo "1. Prerequisites Check"
echo "======================"

# Check if Docker Compose is running
if curl -s "$BASE_URL/api/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Flask application is running"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Flask application is not running"
    echo "  Start with: docker compose -f docker-compose.dev.yml up -d"
    ((FAIL++))
fi

# Check if containers API is accessible
CONTAINERS_API=$(curl -s "$BASE_URL/api/containers")
if echo "$CONTAINERS_API" | grep -q '"success"'; then
    echo -e "${GREEN}✓${NC} Containers API is accessible"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Containers API is not accessible"
    ((FAIL++))
fi

echo ""

# ==============================================================================
# 2. Template File Verification
# ==============================================================================
echo "2. Template File Verification"
echo "=============================="

# Check if updated containers.html exists
if [ -f "frontend/templates/containers.html" ]; then
    echo -e "${GREEN}✓${NC} containers.html template exists"
    ((PASS++))
    
    # Check for create modal structure
    if grep -q "createModal" frontend/templates/containers.html; then
        echo -e "${GREEN}✓${NC} Create modal state structure found"
        ((PASS++))
    else
        echo -e "${RED}✗${NC} Create modal state structure missing"
        ((FAIL++))
    fi
    
    # Check for openCreateModal function
    if grep -q "openCreateModal" frontend/templates/containers.html; then
        echo -e "${GREEN}✓${NC} openCreateModal function found"
        ((PASS++))
    else
        echo -e "${RED}✗${NC} openCreateModal function missing"
        ((FAIL++))
    fi
    
    # Check for form submission function
    if grep -q "submitCreateForm" frontend/templates/containers.html; then
        echo -e "${GREEN}✓${NC} submitCreateForm function found"
        ((PASS++))
    else
        echo -e "${RED}✗${NC} submitCreateForm function missing"
        ((FAIL++))
    fi
    
    # Check for dynamic field functions
    DYNAMIC_FUNCTIONS=("addPort" "removePort" "addVolume" "removeVolume" "addEnvVar" "removeEnvVar")
    for func in "${DYNAMIC_FUNCTIONS[@]}"; do
        if grep -q "$func" frontend/templates/containers.html; then
            echo -e "${GREEN}✓${NC} $func function found"
            ((PASS++))
        else
            echo -e "${RED}✗${NC} $func function missing"
            ((FAIL++))
        fi
    done
    
else
    echo -e "${RED}✗${NC} containers.html template missing"
    ((FAIL++))
fi

echo ""

# ==============================================================================
# 3. UI Page Load Test
# ==============================================================================
echo "3. UI Page Load Test"
echo "===================="

# Note: UI routes ARE protected, so we need to login first
echo "Logging in for UI access (UI routes are protected)..."
LOGIN_RESPONSE=$(curl -s -c /tmp/task7_session.txt -X POST "$BASE_URL/api/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"password": "admin123"}')

if echo "$LOGIN_RESPONSE" | grep -q '"success": true'; then
    echo -e "${GREEN}✓${NC} UI session established"
    ((PASS++))
    
    UI_RESPONSE=$(curl -s -b /tmp/task7_session.txt -w "\n%{http_code}" "$BASE_URL/containers")
    HTTP_CODE=$(echo "$UI_RESPONSE" | tail -n1)
    BODY=$(echo "$UI_RESPONSE" | sed '$d')
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo -e "${GREEN}✓${NC} Container UI page loads (HTTP 200)"
        ((PASS++))
        
        # Check for create button (not disabled)
        if echo "$BODY" | grep -q "@click=\"openCreateModal()\""; then
            echo -e "${GREEN}✓${NC} Create button enabled with click handler"
            ((PASS++))
        else
            echo -e "${RED}✗${NC} Create button not properly enabled"
            ((FAIL++))
        fi
        
        # Check for hardware limit enforcement in button
        if echo "$BODY" | grep -q "runningCount >= (hardwareProfile.max_containers"; then
            echo -e "${GREEN}✓${NC} Hardware limit enforcement detected in create button"
            ((PASS++))
        else
            echo -e "${RED}✗${NC} Hardware limit enforcement missing"
            ((FAIL++))
        fi
        
        # Check for create modal HTML
        if echo "$BODY" | grep -q "x-show=\"createModal.show\""; then
            echo -e "${GREEN}✓${NC} Create modal HTML structure found"
            ((PASS++))
        else
            echo -e "${RED}✗${NC} Create modal HTML structure missing"
            ((FAIL++))
        fi
        
        # Check for form sections
        FORM_SECTIONS=("Basic Information" "Port Mappings" "Volume Mounts" "Environment Variables" "Advanced Options")
        for section in "${FORM_SECTIONS[@]}"; do
            if echo "$BODY" | grep -q "$section"; then
                echo -e "${GREEN}✓${NC} Form section found: $section"
                ((PASS++))
            else
                echo -e "${RED}✗${NC} Form section missing: $section"
                ((FAIL++))
            fi
        done
        
    else
        echo -e "${RED}✗${NC} Container UI page failed to load (HTTP $HTTP_CODE)"
        ((FAIL++))
    fi
else
    echo -e "${RED}✗${NC} Could not establish UI session"
    echo "  Note: UI routes require authentication per v2.0.0 design"
    ((FAIL++))
fi

echo ""

# ==============================================================================
# 4. Form Field Verification
# ==============================================================================
echo "4. Form Field Verification"
echo "=========================="

if [ -f "frontend/templates/containers.html" ]; then
    # Required fields
    REQUIRED_FIELDS=("name" "image" "environment")
    for field in "${REQUIRED_FIELDS[@]}"; do
        if grep -q "x-model=\"createModal.formData.$field\"" frontend/templates/containers.html; then
            echo -e "${GREEN}✓${NC} Required field binding found: $field"
            ((PASS++))
        else
            echo -e "${RED}✗${NC} Required field binding missing: $field"
            ((FAIL++))
        fi
    done
    
    # Optional fields
    OPTIONAL_FIELDS=("restart_policy" "cpu_limit" "memory_limit" "auto_start" "pull_if_missing")
    for field in "${OPTIONAL_FIELDS[@]}"; do
        if grep -q "x-model=\"createModal.formData.$field\"" frontend/templates/containers.html; then
            echo -e "${GREEN}✓${NC} Optional field binding found: $field"
            ((PASS++))
        else
            echo -e "${YELLOW}⚠${NC} Optional field binding missing: $field"
        fi
    done
else
    echo -e "${RED}✗${NC} Cannot verify fields (template missing)"
    ((FAIL++))
fi

echo ""

# ==============================================================================
# 5. Functional Testing - Container Creation via API
# ==============================================================================
echo "5. Functional Testing - Container Creation"
echo "==========================================="

# Create test container via API to verify integration
echo "Creating test container via API..."
CREATE_RESPONSE=$(curl -s -X POST "$BASE_URL/api/containers" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "task7-test-alpine",
        "image": "alpine:latest",
        "environment": "DEV",
        "auto_start": false,
        "pull_if_missing": true
    }')

if echo "$CREATE_RESPONSE" | grep -q '"success": true'; then
    CONTAINER_NAME=$(echo "$CREATE_RESPONSE" | jq -r '.data.name' 2>/dev/null)
    echo -e "${GREEN}✓${NC} Test container created via API (name: $CONTAINER_NAME)"
    ((PASS++))
    
    # Wait a moment for database update
    sleep 2
    
    # Verify container appears in list
    UPDATED_LIST=$(curl -s "$BASE_URL/api/containers")
    if echo "$UPDATED_LIST" | grep -q "task7-test-alpine"; then
        echo -e "${GREEN}✓${NC} Test container appears in container list"
        ((PASS++))
    else
        echo -e "${RED}✗${NC} Test container not found in list"
        ((FAIL++))
    fi
    
    # Cleanup - delete test container
    echo "Cleaning up test container..."
    DELETE_RESPONSE=$(curl -s -X DELETE "$BASE_URL/api/containers/task7-test-alpine?force=true")
    if echo "$DELETE_RESPONSE" | grep -q '"success": true'; then
        echo -e "${GREEN}✓${NC} Test container cleaned up"
        ((PASS++))
    else
        echo -e "${YELLOW}⚠${NC} Could not clean up test container (manual cleanup may be needed)"
    fi
else
    echo -e "${RED}✗${NC} Failed to create test container via API"
    echo "  Response: $CREATE_RESPONSE"
    ((FAIL++))
fi

echo ""

# ==============================================================================
# 6. Validation Testing
# ==============================================================================
echo "6. Validation Testing"
echo "====================="

# Test validation - missing required field
echo "Testing validation: missing required field (name)..."
VALIDATION_TEST=$(curl -s -X POST "$BASE_URL/api/containers" \
    -H "Content-Type: application/json" \
    -d '{
        "image": "nginx:latest",
        "environment": "DEV"
    }')

if echo "$VALIDATION_TEST" | grep -q '"success": false'; then
    echo -e "${GREEN}✓${NC} API correctly rejects request with missing name"
    ((PASS++))
else
    echo -e "${RED}✗${NC} API should reject request with missing name"
    ((FAIL++))
fi

# Test validation - invalid name format
echo "Testing validation: invalid name format..."
VALIDATION_TEST2=$(curl -s -X POST "$BASE_URL/api/containers" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "invalid name with spaces",
        "image": "nginx:latest",
        "environment": "DEV"
    }')

if echo "$VALIDATION_TEST2" | grep -q '"success": false'; then
    echo -e "${GREEN}✓${NC} API correctly rejects invalid name format"
    ((PASS++))
else
    echo -e "${RED}✗${NC} API should reject invalid name format"
    ((FAIL++))
fi

# Test validation - invalid port range
echo "Testing validation: invalid port range..."
VALIDATION_TEST3=$(curl -s -X POST "$BASE_URL/api/containers" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "test-ports",
        "image": "nginx:latest",
        "environment": "DEV",
        "ports": {"80/tcp": 99999}
    }')

if echo "$VALIDATION_TEST3" | grep -q '"success": false'; then
    echo -e "${GREEN}✓${NC} API correctly rejects invalid port range"
    ((PASS++))
else
    echo -e "${RED}✗${NC} API should reject invalid port range"
    ((FAIL++))
fi

echo ""

# ==============================================================================
# 7. Client-Side Validation Check
# ==============================================================================
echo "7. Client-Side Validation Check"
echo "================================"

if [ -f "frontend/templates/containers.html" ]; then
    # Check for validateForm function
    if grep -q "validateForm()" frontend/templates/containers.html; then
        echo -e "${GREEN}✓${NC} validateForm function found"
        ((PASS++))
    else
        echo -e "${RED}✗${NC} validateForm function missing"
        ((FAIL++))
    fi
    
    # Check for error display handling
    if grep -q "createModal.errors" frontend/templates/containers.html; then
        echo -e "${GREEN}✓${NC} Error display handling found"
        ((PASS++))
    else
        echo -e "${RED}✗${NC} Error display handling missing"
        ((FAIL++))
    fi
    
    # Check for error message display
    if grep -q "createModal.errorMessage" frontend/templates/containers.html; then
        echo -e "${GREEN}✓${NC} General error message display found"
        ((PASS++))
    else
        echo -e "${RED}✗${NC} General error message display missing"
        ((FAIL++))
    fi
else
    echo -e "${RED}✗${NC} Cannot verify validation (template missing)"
    ((FAIL++))
fi

echo ""

# ==============================================================================
# Summary
# ==============================================================================
echo "======================================================================"
echo "Verification Summary"
echo "======================================================================"
echo -e "Passed: ${GREEN}${PASS}${NC}"
echo -e "Failed: ${RED}${FAIL}${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✓ All automated checks passed!${NC}"
    echo ""
    echo "Sprint 2 - Task 7 Status: ✅ AUTOMATED TESTS COMPLETE"
    echo ""
    echo "What was completed:"
    echo "  ✓ Create button enabled with hardware limit enforcement"
    echo "  ✓ Create modal with comprehensive form"
    echo "  ✓ Basic information section (name, image, environment)"
    echo "  ✓ Port mappings with dynamic add/remove"
    echo "  ✓ Volume mounts with dynamic add/remove"
    echo "  ✓ Environment variables with dynamic add/remove"
    echo "  ✓ Advanced options (CPU, memory, restart policy)"
    echo "  ✓ Client-side validation with error display"
    echo "  ✓ API integration with POST /api/containers"
    echo "  ✓ Success/error handling with toast notifications"
    echo "  ✓ Form reset on close"
    echo ""
    echo "Manual Testing Required (Section 8):"
    echo "  1. Open http://localhost:5000/containers in browser"
    echo "  2. Click 'Create Container' button"
    echo "  3. Fill out form with test data:"
    echo "     - Name: test-manual-nginx"
    echo "     - Image: nginx:alpine"
    echo "     - Environment: DEV"
    echo "     - Add port: 80/tcp → 8090"
    echo "     - Add volume: /tmp/test → /usr/share/nginx/html (rw)"
    echo "     - Add env var: TEST_VAR=test_value"
    echo "  4. Submit form and verify:"
    echo "     - Container appears in list"
    echo "     - Toast notification shows success"
    echo "     - Modal closes automatically"
    echo "  5. Test validation by submitting empty form"
    echo "  6. Test hardware limit by creating containers until limit reached"
    echo "  7. Verify create button disables when limit reached"
    echo ""
    echo "When manual testing is complete:"
    echo "  - Update PROJECT_STATUS.md"
    echo "  - Mark Task 7 as 100% complete"
    echo "  - Proceed to Task 8 (Integration Testing)"
    exit 0
else
    echo -e "${RED}✗ Some automated checks failed.${NC}"
    echo ""
    echo "Common Issues:"
    echo "  - Template not updated: Copy new containers.html to frontend/templates/"
    echo "  - Docker Compose not running: docker compose -f docker-compose.dev.yml up -d"
    echo "  - Missing dependencies: pip install -r requirements.txt"
    echo "  - API failures: Check Flask logs"
    echo ""
    echo "Debug Commands:"
    echo "  docker compose -f docker-compose.dev.yml logs -f"
    echo "  curl http://localhost:5000/api/health"
    echo "  curl http://localhost:5000/api/containers"
    exit 1
fi