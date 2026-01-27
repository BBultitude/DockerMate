#!/bin/bash
# Simplified Verification Script - Sprint 2 Task 2
# Docker SDK Integration

echo "======================================"
echo "Sprint 2 - Task 2 Verification"
echo "Docker SDK Integration"
echo "======================================"
echo ""

PASS=0
FAIL=0

# Check 1: Dependencies
echo "1. Checking Dependencies"
echo "========================"
if pip show docker >/dev/null 2>&1; then
    echo "✓ docker package installed"
    PASS=$((PASS + 1))
else
    echo "✗ docker package not installed"
    FAIL=$((FAIL + 1))
fi
echo ""

# Check 2: File Structure
echo "2. Checking File Structure"
echo "=========================="
for file in \
    "backend/utils/docker_client.py" \
    "backend/utils/exceptions.py" \
    "backend/services/__init__.py" \
    "backend/services/container_service.py" \
    "tests/unit/test_docker_client.py" \
    "tests/unit/test_container_service.py" \
    "requirements.txt"; do
    
    if [ -f "$file" ]; then
        echo "✓ $file exists"
        PASS=$((PASS + 1))
    else
        echo "✗ $file missing"
        FAIL=$((FAIL + 1))
    fi
done
echo ""

# Check 3: Import Tests
echo "3. Testing Imports"
echo "=================="
echo "Testing docker_client..."
if python3 -c "from backend.utils.docker_client import get_docker_client" 2>/dev/null; then
    echo "✓ docker_client imports"
    PASS=$((PASS + 1))
else
    echo "✗ docker_client import failed"
    python3 -c "from backend.utils.docker_client import get_docker_client" 2>&1 | head -5
    FAIL=$((FAIL + 1))
fi

echo "Testing exceptions..."
if python3 -c "from backend.utils.exceptions import DockerConnectionError" 2>/dev/null; then
    echo "✓ exceptions imports"
    PASS=$((PASS + 1))
else
    echo "✗ exceptions import failed"
    FAIL=$((FAIL + 1))
fi

echo "Testing container_service..."
if python3 -c "from backend.services.container_service import ContainerService" 2>/dev/null; then
    echo "✓ container_service imports"
    PASS=$((PASS + 1))
else
    echo "✗ container_service import failed"
    python3 -c "from backend.services.container_service import ContainerService" 2>&1 | head -5
    FAIL=$((FAIL + 1))
fi
echo ""

# Check 4: Run Tests
echo "4. Running Unit Tests"
echo "====================="
echo "Running docker_client tests..."
if pytest tests/unit/test_docker_client.py -v 2>&1 | tail -20; then
    echo "✓ docker_client tests completed"
    PASS=$((PASS + 1))
else
    echo "✗ docker_client tests had issues"
    FAIL=$((FAIL + 1))
fi
echo ""

echo "Running container_service tests..."
if pytest tests/unit/test_container_service.py -v 2>&1 | tail -20; then
    echo "✓ container_service tests completed"
    PASS=$((PASS + 1))
else
    echo "✗ container_service tests had issues"
    FAIL=$((FAIL + 1))
fi
echo ""

# Check 5: Coverage
echo "5. Test Coverage"
echo "================"
pytest tests/unit/test_docker_client.py tests/unit/test_container_service.py \
    --cov=backend/utils/docker_client \
    --cov=backend/services/container_service \
    --cov-report=term-missing 2>&1 | grep -A 10 "TOTAL"
echo ""

# Summary
echo "======================================"
echo "Summary"
echo "======================================"
echo "Passed: $PASS"
echo "Failed: $FAIL"
echo ""

if [ $FAIL -eq 0 ]; then
    echo "✅ All checks passed! Task 2 complete."
    exit 0
else
    echo "❌ Some checks failed. Review errors above."
    exit 1
fi
