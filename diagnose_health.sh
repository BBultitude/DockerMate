#!/bin/bash
# DockerMate Health Diagnostics for Raspberry Pi

echo "=== DockerMate Health Diagnostics ==="
echo "Timestamp: $(date)"
echo ""

echo "1. Testing health endpoint response time..."
time docker exec dockermate curl -fk https://localhost:5000/api/health -o /tmp/health_response.json 2>&1
echo ""

echo "2. Health endpoint response:"
docker exec dockermate cat /tmp/health_response.json 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "Failed to parse JSON"
echo ""

echo "3. Container health status:"
docker inspect dockermate --format='{{json .State.Health}}' | python3 -m json.tool
echo ""

echo "4. Recent health check logs (last 10 checks):"
docker inspect dockermate --format='{{range .State.Health.Log}}{{.Start}} - Exit: {{.ExitCode}} - Output: {{.Output}}{{"\n"}}{{end}}' | tail -20
echo ""

echo "5. Container resource usage:"
docker stats dockermate --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}"
echo ""

echo "6. Recent application logs (last 30 lines):"
docker logs --tail 30 dockermate
echo ""

echo "7. Storage I/O check (database location):"
docker exec dockermate ls -lh /app/data/ 2>/dev/null || echo "Cannot access /app/data"
echo ""

echo "8. Testing database connectivity:"
docker exec dockermate python3 -c "
from backend.database import SessionLocal
import time
start = time.time()
try:
    db = SessionLocal()
    db.execute('SELECT 1')
    db.close()
    elapsed = time.time() - start
    print(f'Database ping: {elapsed:.3f}s')
except Exception as e:
    print(f'Database error: {e}')
" 2>&1
echo ""

echo "9. Testing Docker daemon connectivity:"
docker exec dockermate python3 -c "
from backend.utils.docker_client import get_docker_client
import time
start = time.time()
try:
    client = get_docker_client()
    client.ping()
    elapsed = time.time() - start
    print(f'Docker ping: {elapsed:.3f}s')
except Exception as e:
    print(f'Docker error: {e}')
" 2>&1
echo ""

echo "=== Diagnostics Complete ==="
