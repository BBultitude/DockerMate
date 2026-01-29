#!/bin/bash
# Docker Compose Integration Test Script
# Tests DockerMate development environment

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0

echo "======================================================================"
echo "DockerMate Docker Compose Integration Test"
echo "======================================================================"
echo ""

# Test 1: Docker Compose available
echo "Test 1: Checking Docker Compose..."
if docker compose version &>/dev/null; then
    echo -e "${GREEN}✓${NC} Docker Compose is available"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Docker Compose not found"
    echo "  Install: sudo apt-get install docker-compose-plugin"
    ((FAIL++))
fi
echo ""

# Test 2: Docker daemon running
echo "Test 2: Checking Docker daemon..."
if docker ps &>/dev/null; then
    echo -e "${GREEN}✓${NC} Docker daemon is running"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Docker daemon not accessible"
    echo "  Start: sudo systemctl start docker"
    echo "  Access: sudo usermod -aG docker \$USER && newgrp docker"
    ((FAIL++))
fi
echo ""

# Test 3: Configuration files exist
echo "Test 3: Checking configuration files..."
if [ -f "docker-compose.dev.yml" ] && [ -f "Dockerfile.dev" ]; then
    echo -e "${GREEN}✓${NC} Configuration files present"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Missing configuration files"
    [ ! -f "docker-compose.dev.yml" ] && echo "  Missing: docker-compose.dev.yml"
    [ ! -f "Dockerfile.dev" ] && echo "  Missing: Dockerfile.dev"
    ((FAIL++))
fi
echo ""

# Stop here if prerequisites failed
if [ $FAIL -gt 0 ]; then
    echo -e "${RED}Prerequisites not met. Fix issues above before continuing.${NC}"
    exit 1
fi

# Test 4: Start containers
echo "Test 4: Starting DockerMate container..."
if docker compose -f docker-compose.dev.yml up -d --build &>/dev/null; then
    echo -e "${GREEN}✓${NC} Container started successfully"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Failed to start container"
    docker compose -f docker-compose.dev.yml logs
    ((FAIL++))
    exit 1
fi
echo ""

# Wait for startup
echo "Waiting for application to start..."
sleep 10

# Test 5: Container running
echo "Test 5: Verifying container status..."
if docker compose -f docker-compose.dev.yml ps | grep -q "Up"; then
    echo -e "${GREEN}✓${NC} Container is running"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Container not running"
    docker compose -f docker-compose.dev.yml ps
    ((FAIL++))
fi
echo ""

# Test 6: Health endpoint
echo "Test 6: Testing health endpoint..."
HEALTH_RESPONSE=$(curl -s http://localhost:5000/api/health)
if echo "$HEALTH_RESPONSE" | grep -q '"status"'; then
    echo -e "${GREEN}✓${NC} Health endpoint responding"
    echo "  Response: $(echo $HEALTH_RESPONSE | jq -r '.status' 2>/dev/null || echo 'JSON parse failed')"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Health endpoint not responding"
    echo "  Response: $HEALTH_RESPONSE"
    ((FAIL++))
fi
echo ""

# Test 7: Hardware profile endpoint
echo "Test 7: Testing hardware profile endpoint..."
HARDWARE_RESPONSE=$(curl -s http://localhost:5000/api/system/hardware)
if echo "$HARDWARE_RESPONSE" | grep -q '"success": true'; then
    PROFILE=$(echo "$HARDWARE_RESPONSE" | jq -r '.data.profile_name' 2>/dev/null)
    MAX_CONTAINERS=$(echo "$HARDWARE_RESPONSE" | jq -r '.data.max_containers' 2>/dev/null)
    echo -e "${GREEN}✓${NC} Hardware profile endpoint working"
    echo "  Profile: $PROFILE"
    echo "  Max Containers: $MAX_CONTAINERS"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Hardware profile endpoint failed"
    echo "  Response: $HARDWARE_RESPONSE"
    ((FAIL++))
fi
echo ""

# Test 8: Containers list endpoint
echo "Test 8: Testing containers list endpoint..."
CONTAINERS_RESPONSE=$(curl -s http://localhost:5000/api/containers)
if echo "$CONTAINERS_RESPONSE" | grep -q '"success": true'; then
    COUNT=$(echo "$CONTAINERS_RESPONSE" | jq -r '.count' 2>/dev/null)
    echo -e "${GREEN}✓${NC} Containers endpoint working"
    echo "  Container count: $COUNT"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Containers endpoint failed"
    echo "  Response: $CONTAINERS_RESPONSE"
    ((FAIL++))
fi
echo ""

# Test 9: Create container via API
echo "Test 9: Testing container creation..."
CREATE_RESPONSE=$(curl -s -X POST http://localhost:5000/api/containers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-nginx-integration",
    "image": "nginx:alpine",
    "environment": "DEV",
    "ports": {"80/tcp": "8082"},
    "auto_start": true,
    "pull_if_missing": true
  }')

if echo "$CREATE_RESPONSE" | grep -q '"success": true'; then
    echo -e "${GREEN}✓${NC} Container created successfully"
    CONTAINER_NAME=$(echo "$CREATE_RESPONSE" | jq -r '.data.name' 2>/dev/null)
    echo "  Container: $CONTAINER_NAME"
    ((PASS++))
    
    # Wait for container to start
    sleep 3
    
    # Verify container exists in Docker
    if docker ps | grep -q "test-nginx-integration"; then
        echo -e "${GREEN}✓${NC} Container visible in Docker"
    else
        echo -e "${YELLOW}⚠${NC} Container not visible in docker ps (may still be starting)"
    fi
else
    echo -e "${RED}✗${NC} Container creation failed"
    echo "  Response: $CREATE_RESPONSE"
    ((FAIL++))
fi
echo ""

# Test 10: UI accessibility
echo "Test 10: Testing UI accessibility..."
UI_RESPONSE=$(curl -s -I http://localhost:5000/containers | grep "HTTP")
if echo "$UI_RESPONSE" | grep -q "200"; then
    echo -e "${GREEN}✓${NC} UI is accessible"
    ((PASS++))
else
    echo -e "${RED}✗${NC} UI not accessible"
    echo "  Response: $UI_RESPONSE"
    ((FAIL++))
fi
echo ""

# Test 11: Docker socket access from container
echo "Test 11: Testing Docker socket access from container..."
SOCKET_TEST=$(docker compose -f docker-compose.dev.yml exec -T dockermate \
  ls -la /var/run/docker.sock 2>&1)
if echo "$SOCKET_TEST" | grep -q "docker.sock"; then
    echo -e "${GREEN}✓${NC} Docker socket mounted correctly"
    ((PASS++))
else
    echo -e "${RED}✗${NC} Docker socket not accessible"
    echo "  Error: $SOCKET_TEST"
    ((FAIL++))
fi
echo ""

# Cleanup
echo "Cleaning up test container..."
curl -s -X DELETE http://localhost:5000/api/containers/1 &>/dev/null || true
sleep 2

# Stop containers
echo "Stopping DockerMate container..."
docker compose -f docker-compose.dev.yml down &>/dev/null

# Summary
echo "======================================================================"
echo "Test Summary"
echo "======================================================================"
echo -e "Passed: ${GREEN}${PASS}${NC}"
echo -e "Failed: ${RED}${FAIL}${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed! Docker Compose setup is working correctly.${NC}"
    echo ""
    echo "You can now use:"
    echo "  docker compose -f docker-compose.dev.yml up"
    echo ""
    echo "Access DockerMate at: http://localhost:5000"
    exit 0
else
    echo -e "${RED}✗ Some tests failed. Review errors above.${NC}"
    echo ""
    echo "Common fixes:"
    echo "  - Add user to docker group: sudo usermod -aG docker \$USER"
    echo "  - Start Docker daemon: sudo systemctl start docker"
    echo "  - Rebuild containers: docker compose -f docker-compose.dev.yml up --build"
    exit 1
fi
