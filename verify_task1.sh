#!/bin/bash
#
# Task 1 Verification Script
#
# This script verifies that the project structure is set up correctly.
# It checks:
# 1. All required directories exist
# 2. All __init__.py files are present
# 3. Main application files exist
# 4. Python can import the modules
#
# Usage:
#   bash verify_task1.sh
#
# Expected output: All checks should show ✅

echo "🔍 DockerMate Task 1 Verification"
echo "=================================="
echo ""

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Track failures
FAILURES=0

# Function to check if directory exists
check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✅${NC} Directory exists: $1"
    else
        echo -e "${RED}❌${NC} Directory missing: $1"
        FAILURES=$((FAILURES + 1))
    fi
}

# Function to check if file exists
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✅${NC} File exists: $1"
    else
        echo -e "${RED}❌${NC} File missing: $1"
        FAILURES=$((FAILURES + 1))
    fi
}

echo "1. Checking Backend Directories..."
echo "-----------------------------------"
check_dir "backend"
check_dir "backend/api"
check_dir "backend/auth"
check_dir "backend/ssl"
check_dir "backend/managers"
check_dir "backend/models"
check_dir "backend/utils"
check_dir "backend/scheduler"
echo ""

echo "2. Checking Frontend Directories..."
echo "------------------------------------"
check_dir "frontend"
check_dir "frontend/static"
check_dir "frontend/static/css"
check_dir "frontend/static/js"
check_dir "frontend/static/img"
check_dir "frontend/templates"
check_dir "frontend/templates/components"
echo ""

echo "3. Checking Other Directories..."
echo "---------------------------------"
check_dir "tests"
check_dir "tests/unit"
check_dir "tests/integration"
check_dir "data"
check_dir "data/ssl"
check_dir "data/backups"
check_dir "stacks"
check_dir "exports"
check_dir "docs"
echo ""

echo "4. Checking Python Package Files..."
echo "------------------------------------"
check_file "backend/__init__.py"
check_file "backend/api/__init__.py"
check_file "backend/auth/__init__.py"
check_file "backend/ssl/__init__.py"
check_file "backend/managers/__init__.py"
check_file "backend/models/__init__.py"
check_file "backend/utils/__init__.py"
check_file "backend/scheduler/__init__.py"
check_file "tests/__init__.py"
check_file "tests/unit/__init__.py"
check_file "tests/integration/__init__.py"
echo ""

echo "5. Checking Main Application Files..."
echo "--------------------------------------"
check_file "app.py"
check_file "config.py"
echo ""

echo "6. Testing Python Imports..."
echo "----------------------------"
# Try to import the configuration module
if python3 -c "import sys; sys.path.insert(0, '.'); from config import Config; print('Config imported successfully')" 2>/dev/null; then
    echo -e "${GREEN}✅${NC} Can import config module"
else
    echo -e "${RED}❌${NC} Cannot import config module"
    FAILURES=$((FAILURES + 1))
fi

# Try to parse duration
if python3 -c "import sys; sys.path.insert(0, '.'); from config import Config; assert Config.parse_duration('8h') == 28800; print('Duration parsing works')" 2>/dev/null; then
    echo -e "${GREEN}✅${NC} Config.parse_duration() works"
else
    echo -e "${RED}❌${NC} Config.parse_duration() failed"
    FAILURES=$((FAILURES + 1))
fi
echo ""

echo "7. Summary"
echo "----------"
if [ $FAILURES -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed! Task 1 complete.${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Review the created files"
    echo "  2. Proceed to Task 2: Database Models & Schema"
    exit 0
else
    echo -e "${RED}❌ $FAILURES check(s) failed${NC}"
    echo ""
    echo "Please review the failures above and fix them."
    exit 1
fi
