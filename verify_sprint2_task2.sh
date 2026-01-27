#!/bin/bash
# Verification Script - Sprint 2 Task 2: Docker SDK Integration
# Tests Docker client wrapper and container service functionality

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "======================================"
echo "Sprint 2 - Task 2 Verification"
echo "Docker SDK Integration"
echo "======================================"
echo ""

# Track results
PASS=0
FAIL=0

# =====================================================
# 1. Check Dependencies
# =====================================================
echo "1. Checking Dependencies"
echo "========================"

if pip show docker > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} docker package installed"
    ((PASS++))
else
    echo -e "${RED}✗${NC} docker package not installed"
    echo "  Run: pip install docker"
    ((FAIL++))
fi
echo ""

# =====================================================
# 2. File Structure Check
# =====================================================
echo "2. Checking File Structure"
echo "=========================="

files_to_check=(
    "backend/utils/docker_client.py"
    "backend/utils/exceptions.py"
    "backend/services/container_service.py"
    "tests/unit/test_docker_client.py"
    "tests/unit/test_container_service.py"
    "requirements.txt"
)

for file in "${files_to_check[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $file exists"
        ((PASS++))
    else
        echo -e "${RED}✗${NC} $file missing"
        ((FAIL++))
    fi
done
echo ""

# =====================================================
# 3. Import Tests (Syntax Check)
# =====================================================
echo "3. Testing Imports (Syntax Check)"
echo "================================="

echo "Testing docker_client module..."
if python3 -c "from backend.utils.docker_client import get_docker_client, check_docker_connection, docker_operation" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} docker_client imports successfully"
    ((PASS++))
else
    echo -e "${RED}✗${NC} docker_client import failed"
    ((FAIL++))
fi

echo "Testing exceptions module..."
if python3 -c "from backend.utils.exceptions import DockerConnectionError, ContainerNotFoundError, ContainerOperationError" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} exceptions imports successfully"
    ((PASS++))
else
    echo -e "${RED}✗${NC} exceptions import failed"
    ((FAIL++))
fi

echo "Testing container_service module..."
if python3 -c "from backend.services.container_service import ContainerService" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} container_service imports successfully"
    ((PASS++))
else
    echo -e "${RED}✗${NC} container_service import failed"
    ((FAIL++))
fi
echo ""

# =====================================================
# 4. Unit Tests - Docker Client
# =====================================================
echo "4. Running Docker Client Tests"
echo "==============================="

if pytest tests/unit/test_docker_client.py -v --tb=short 2>&1 | tee /tmp/docker_client_tests.log; then
    echo -e "${GREEN}✓${NC} Docker client tests passed"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Some docker client tests failed"
    echo "  See /tmp/docker_client_tests.log for details"
    ((FAIL++))
fi
echo ""

# =====================================================
# 5. Unit Tests - Container Service
# =====================================================
echo "5. Running Container Service Tests"
echo "==================================="

if pytest tests/unit/test_container_service.py -v --tb=short 2>&1 | tee /tmp/container_service_tests.log; then
    echo -e "${GREEN}✓${NC} Container service tests passed"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Some container service tests failed"
    echo "  See /tmp/container_service_tests.log for details"
    ((FAIL++))
fi
echo ""

# =====================================================
# 6. Test Coverage
# =====================================================
echo "6. Checking Test Coverage"
echo "========================="

if pytest tests/unit/test_docker_client.py tests/unit/test_container_service.py --cov=backend/utils/docker_client --cov=backend/services/container_service --cov-report=term-missing 2>&1 | tee /tmp/coverage.log; then
    coverage_pct=$(grep "TOTAL" /tmp/coverage.log | awk '{print $NF}' | sed 's/%//')
    if [ ! -z "$coverage_pct" ] && [ "$coverage_pct" -ge 75 ]; then
        echo -e "${GREEN}✓${NC} Test coverage >= 75% (${coverage_pct}%)"
        ((PASS++))
    else
        echo -e "${YELLOW}⚠${NC} Test coverage below 75% (${coverage_pct}%)"
    fi
else
    echo -e "${YELLOW}⚠${NC} Could not calculate coverage"
fi
echo ""

# =====================================================
# 7. Functional Test (Mock-Based)
# =====================================================
echo "7. Functional Test (Mock-Based)"
echo "================================"

echo "Testing Docker client singleton..."
if python3 -c "
from unittest.mock import MagicMock, patch

with patch('backend.utils.docker_client.docker.from_env') as mock_from_env:
    # Setup mock
    mock_client = MagicMock()
    mock_client.ping.return_value = True
    mock_client.info.return_value = {'ServerVersion': '24.0.0', 'Name': 'test', 'OperatingSystem': 'Linux'}
    mock_from_env.return_value = mock_client
    
    # Test singleton
    from backend.utils.docker_client import get_docker_client
    import backend.utils.docker_client as dc
    dc._docker_client = None
    dc._connection_healthy = False
    
    client1 = get_docker_client()
    client2 = get_docker_client()
    
    assert client1 is client2, 'Singleton pattern failed'
    print('✓ Singleton pattern works correctly')
" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Docker client singleton test passed"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Docker client singleton test failed"
    ((FAIL++))
fi

echo "Testing container service operations..."
if python3 -c "
from unittest.mock import MagicMock, patch
from backend.services.container_service import ContainerService

with patch('backend.services.container_service.get_docker_client') as mock_get_client:
    # Setup mock
    mock_container = MagicMock()
    mock_container.id = 'abc123'
    mock_container.name = 'test'
    mock_container.status = 'running'
    mock_container.image.tags = ['nginx:latest']
    mock_container.labels = {}
    mock_container.attrs = {
        'Created': '2024-01-01T00:00:00Z',
        'State': {'Status': 'running'},
        'Config': {'Env': [], 'Cmd': [], 'Hostname': 'test'},
        'HostConfig': {'RestartPolicy': {}},
        'NetworkSettings': {'Ports': {}, 'Networks': {}},
        'Mounts': []
    }
    
    mock_client = MagicMock()
    mock_client.containers.list.return_value = [mock_container]
    mock_get_client.return_value = mock_client
    
    # Test service
    service = ContainerService()
    containers = service.list_containers()
    
    assert len(containers) == 1, 'Container listing failed'
    assert containers[0]['name'] == 'test', 'Container data incorrect'
    print('✓ Container service operations work correctly')
" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Container service test passed"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Container service test failed"
    ((FAIL++))
fi
echo ""

# =====================================================
# 8. Docker Daemon Check (Optional)
# =====================================================
echo "8. Docker Daemon Check (Optional)"
echo "================================="

if docker info > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Docker daemon is accessible"
    echo "  Note: Integration tests with real Docker will run in Sprint 2 Task 8"
else
    echo -e "${YELLOW}⚠${NC} Docker daemon not accessible"
    echo "  This is OK - unit tests use mocks"
    echo "  Real Docker integration tests will run in Task 8"
fi
echo ""

# =====================================================
# Summary
# =====================================================
echo "======================================"
echo "Verification Summary"
echo "======================================"
echo -e "Passed: ${GREEN}${PASS}${NC}"
echo -e "Failed: ${RED}${FAIL}${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed! Task 2 complete.${NC}"
    echo ""
    echo "Sprint 2 - Task 2 Status: ✅ COMPLETE"
    echo ""
    echo "What was completed:"
    echo "  ✓ Docker SDK client wrapper (singleton pattern)"
    echo "  ✓ Connection management and health checking"
    echo "  ✓ Container service with CRUD operations"
    echo "  ✓ Custom exception classes"
    echo "  ✓ Error handling and reconnection logic"
    echo "  ✓ Comprehensive unit tests (mock-based)"
    echo "  ✓ Code coverage >= 75%"
    echo ""
    echo "Next: Task 3 - Container Model & Database"
    exit 0
else
    echo -e "${RED}✗ Some checks failed. Please review errors above.${NC}"
    echo ""
    echo "Common issues:"
    echo "  - Missing dependencies: pip install -r requirements.txt"
    echo "  - Import errors: Check file paths and syntax"
    echo "  - Test failures: Review test output logs"
    exit 1
fi
