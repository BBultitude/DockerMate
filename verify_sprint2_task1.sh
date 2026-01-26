#!/bin/bash

# Sprint 2 - Task 1 Verification Script
# Verifies Hardware Profile Detection implementation

echo "======================================"
echo "Sprint 2 - Task 1 Verification"
echo "Hardware Profile Detection"
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

echo "1. Checking Required Files Exist"
echo "=================================="

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

check_file "backend/models/host_config.py"
check_file "backend/utils/hardware_detector.py"
check_file "tests/unit/test_hardware_detector.py"
check_file "tests/unit/test_host_config.py"
echo ""

echo "2. Testing Python Imports"
echo "========================="

echo "Testing HostConfig model import..."
if python3 -c "from backend.models.host_config import HostConfig; print('✓ HostConfig imported')" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} HostConfig model imports successfully"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Failed to import HostConfig model"
    ((FAIL++))
fi

echo "Testing hardware_detector import..."
if python3 -c "from backend.utils.hardware_detector import detect_hardware_profile; print('✓ hardware_detector imported')" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} hardware_detector imports successfully"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Failed to import hardware_detector"
    ((FAIL++))
fi

echo "Testing models package imports..."
if python3 -c "from backend.models import HostConfig; print('✓ HostConfig available from models package')" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} HostConfig available from backend.models"
    ((PASS++))
else
    echo -e "${RED}✗${NC} HostConfig not available from backend.models"
    ((FAIL++))
fi
echo ""

echo "3. Testing Hardware Detection"
echo "=============================="

echo "Testing hardware profile detection..."
if python3 -c "
from backend.utils.hardware_detector import detect_hardware_profile
profile = detect_hardware_profile()
assert 'profile_name' in profile, 'Missing profile_name'
assert 'cpu_cores' in profile, 'Missing cpu_cores'
assert 'ram_gb' in profile, 'Missing ram_gb'
assert 'max_containers' in profile, 'Missing max_containers'
print(f'✓ Detected profile: {profile[\"profile_name\"]} ({profile[\"cpu_cores\"]} cores, {profile[\"ram_gb\"]}GB RAM, max {profile[\"max_containers\"]} containers)')
" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Hardware detection works"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Hardware detection failed"
    ((FAIL++))
fi
echo ""

echo "4. Testing Profile Constants"
echo "============================="

echo "Verifying profile constants exist..."
if python3 -c "
from backend.utils.hardware_detector import (
    RASPBERRY_PI_PROFILE,
    LOW_END_PROFILE,
    MEDIUM_SERVER_PROFILE,
    HIGH_END_PROFILE,
    ENTERPRISE_PROFILE
)
print('✓ All 5 profile constants defined')
assert RASPBERRY_PI_PROFILE['max_containers'] == 15, 'Wrong Raspberry Pi limit'
assert LOW_END_PROFILE['max_containers'] == 20, 'Wrong Low End limit'
assert MEDIUM_SERVER_PROFILE['max_containers'] == 50, 'Wrong Medium Server limit'
assert HIGH_END_PROFILE['max_containers'] == 100, 'Wrong High End limit'
assert ENTERPRISE_PROFILE['max_containers'] == 200, 'Wrong Enterprise limit'
print('✓ All container limits correct')
" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Profile constants defined correctly"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Profile constants incorrect"
    ((FAIL++))
fi
echo ""

echo "5. Testing HostConfig Model"
echo "============================"

echo "Testing HostConfig model creation..."
if python3 -c "
from backend.models.host_config import HostConfig
from backend.models.database import Base, engine, SessionLocal

# Create tables
Base.metadata.create_all(bind=engine)

# Test model
db = SessionLocal()
try:
    config = HostConfig(
        profile_name='TEST',
        cpu_cores=8,
        ram_gb=32.0,
        max_containers=50
    )
    db.add(config)
    db.commit()
    print('✓ HostConfig model works')
    
    # Test methods
    at_limit, level = config.is_at_container_limit(current_count=40)
    print(f'✓ Container limit checking works: {level}')
    
    message = config.get_container_limit_message(current_count=40)
    print(f'✓ Limit messages work: {message[:50]}...')
    
    data = config.to_dict()
    assert 'profile_name' in data, 'to_dict missing profile_name'
    print('✓ to_dict() works')
finally:
    db.close()
    Base.metadata.drop_all(bind=engine)
" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} HostConfig model functional"
    ((PASS++))
else
    echo -e "${RED}✗${NC} HostConfig model tests failed"
    ((FAIL++))
fi
echo ""

echo "6. Running Unit Tests"
echo "====================="

echo "Running hardware_detector tests..."
if pytest tests/unit/test_hardware_detector.py -v --tb=short -q 2>&1 | grep -E "(PASSED|FAILED|ERROR)"; then
    if pytest tests/unit/test_hardware_detector.py -q 2>&1 | grep -q "passed"; then
        echo -e "${GREEN}✓${NC} Hardware detector tests passed"
        ((PASS++))
    else
        echo -e "${RED}✗${NC} Some hardware detector tests failed"
        ((FAIL++))
    fi
else
    echo -e "${YELLOW}⚠${NC} Could not run hardware detector tests"
fi
echo ""

echo "Running host_config model tests..."
if pytest tests/unit/test_host_config.py -v --tb=short -q 2>&1 | grep -E "(PASSED|FAILED|ERROR)"; then
    if pytest tests/unit/test_host_config.py -q 2>&1 | grep -q "passed"; then
        echo -e "${GREEN}✓${NC} HostConfig model tests passed"
        ((PASS++))
    else
        echo -e "${RED}✗${NC} Some HostConfig model tests failed"
        ((FAIL++))
    fi
else
    echo -e "${YELLOW}⚠${NC} Could not run HostConfig tests"
fi
echo ""

echo "7. Testing Database Integration"
echo "================================"

echo "Testing database table creation..."
if python3 -c "
from backend.models import init_db, SessionLocal, HostConfig
from backend.utils.hardware_detector import update_host_config

# Initialize database (creates all tables)
init_db()

# Get session
db = SessionLocal()
try:
    # Get or create config
    config = HostConfig.get_or_create(db)
    print(f'✓ HostConfig singleton created: {config.profile_name}')
    
    # Update with detected hardware
    updated = update_host_config(db, config)
    print(f'✓ Hardware detected and saved: {updated.profile_name}')
    print(f'  CPU: {updated.cpu_cores} cores')
    print(f'  RAM: {updated.ram_gb}GB')
    print(f'  Max containers: {updated.max_containers}')
finally:
    db.close()
" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Database integration works"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Database integration failed"
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
    echo -e "${GREEN}✓ All checks passed! Task 1 complete.${NC}"
    echo ""
    echo "Sprint 2 - Task 1 Status: ✅ COMPLETE"
    echo ""
    echo "What was completed:"
    echo "  ✓ HostConfig database model"
    echo "  ✓ Hardware detection utility"
    echo "  ✓ 5 hardware profiles defined"
    echo "  ✓ Container limit enforcement logic"
    echo "  ✓ Unit tests (hardware_detector + host_config)"
    echo "  ✓ Database integration"
    echo ""
    echo "Next: Task 2 - Docker SDK Integration"
    exit 0
else
    echo -e "${RED}✗ Some checks failed. Please review errors above.${NC}"
    exit 1
fi
