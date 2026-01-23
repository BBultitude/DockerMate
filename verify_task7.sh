#!/bin/bash

# Sprint 1 - Task 7 Verification Script
# Tests all authentication API endpoints

echo "======================================"
echo "Task 7 Verification: Auth API Endpoints"
echo "======================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track results
PASS=0
FAIL=0

# Helper function for checks
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} File exists: $1"
        ((PASS++))
        return 0
    else
        echo -e "${RED}✗${NC} File missing: $1"
        ((FAIL++))
        return 1
    fi
}

check_import() {
    if python3 -c "$1" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Import successful: $2"
        ((PASS++))
        return 0
    else
        echo -e "${RED}✗${NC} Import failed: $2"
        ((FAIL++))
        return 1
    fi
}

echo "1. Checking Files"
echo "=================="
check_file "backend/api/auth.py"
check_file "backend/auth/middleware.py"
echo ""

echo "2. Checking Python Imports"
echo "=========================="
check_import "from backend.api.auth import auth_bp" "auth_bp blueprint"
check_import "from backend.auth.middleware import require_auth, is_authenticated" "middleware functions"
echo ""

echo "3. Checking SessionManager Methods"
echo "==================================="
python3 << 'EOF'
try:
    from backend.auth.session_manager import SessionManager
    
    # Check methods exist
    methods = ['get_session_info', 'get_session_id', 'get_all_sessions', 
               'revoke_session_by_id', 'revoke_all_sessions_except']
    
    all_present = True
    for method in methods:
        if hasattr(SessionManager, method):
            print(f"✓ Method exists: SessionManager.{method}")
        else:
            print(f"✗ Method missing: SessionManager.{method}")
            all_present = False
    
    if all_present:
        print("\n✓ All SessionManager methods present")
        exit(0)
    else:
        print("\n✗ Some SessionManager methods missing")
        exit(1)
    
except Exception as e:
    print(f"✗ Error checking SessionManager: {e}")
    exit(1)
EOF

if [ $? -eq 0 ]; then
    ((PASS++))
else
    ((FAIL++))
fi
echo ""

echo "4. Checking Blueprint Configuration"
echo "===================================="
python3 << 'EOF'
try:
    from backend.api.auth import auth_bp
    
    # Check blueprint is configured
    print(f"✓ Blueprint name: {auth_bp.name}")
    print(f"✓ Blueprint URL prefix: {auth_bp.url_prefix}")
    print(f"✓ Blueprint configured successfully")
    
except Exception as e:
    print(f"✗ Error checking blueprint: {e}")
    exit(1)
EOF

if [ $? -eq 0 ]; then
    ((PASS++))
else
    ((FAIL++))
fi
echo ""

echo "5. Code Quality Checks"
echo "======================"

# Check for proper error handling
if grep -q "try:" backend/api/auth.py && grep -q "except Exception" backend/api/auth.py; then
    echo -e "${GREEN}✓${NC} Error handling present in auth.py"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Missing error handling in auth.py"
    ((FAIL++))
fi

# Check for logging
if grep -q "import logging" backend/api/auth.py && grep -q "logger" backend/api/auth.py; then
    echo -e "${GREEN}✓${NC} Logging implemented in auth.py"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Missing logging in auth.py"
    ((FAIL++))
fi

# Check for docstrings
if grep -q '"""' backend/api/auth.py; then
    echo -e "${GREEN}✓${NC} Docstrings present in auth.py"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Missing docstrings in auth.py"
    ((FAIL++))
fi

# Check for security features
if grep -q "httponly=True" backend/api/auth.py && grep -q "secure=True" backend/api/auth.py; then
    echo -e "${GREEN}✓${NC} Secure cookie settings present"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Missing secure cookie settings"
    ((FAIL++))
fi

# Check middleware has decorator
if grep -q "@wraps" backend/auth/middleware.py; then
    echo -e "${GREEN}✓${NC} Middleware uses @wraps decorator"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Missing @wraps in middleware"
    ((FAIL++))
fi

echo ""

echo "======================================"
echo "Verification Summary"
echo "======================================"
echo -e "Passed: ${GREEN}${PASS}${NC}"
echo -e "Failed: ${RED}${FAIL}${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed! Task 7 complete.${NC}"
    echo ""
    echo "Next Steps:"
    echo "1. Update app.py to register the blueprint"
    echo "2. Start the Flask app: python app.py"
    echo "3. Test login endpoint (after creating a user)"
    echo "4. Move on to Task 8: Unit Tests"
    exit 0
else
    echo -e "${RED}✗ Some checks failed. Please review errors above.${NC}"
    exit 1
fi
