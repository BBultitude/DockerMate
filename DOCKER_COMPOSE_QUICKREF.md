# Docker Compose Quick Reference

## Essential Commands

```bash
# Start development
docker compose -f docker-compose.dev.yml up

# Start in background
docker compose -f docker-compose.dev.yml up -d

# Stop everything
docker compose -f docker-compose.dev.yml down

# Rebuild and start
docker compose -f docker-compose.dev.yml up --build

# View logs
docker compose -f docker-compose.dev.yml logs -f

# Restart service
docker compose -f docker-compose.dev.yml restart

# Execute command in container
docker compose -f docker-compose.dev.yml exec dockermate bash
```

## Common Tasks

### First Time Setup
```bash
sudo usermod -aG docker $USER
newgrp docker
docker compose -f docker-compose.dev.yml up --build
```

### Daily Workflow
```bash
docker compose -f docker-compose.dev.yml up
# Edit code → Save → Auto-reload
# Ctrl+C to stop
docker compose -f docker-compose.dev.yml down
```

### Testing API
```bash
# Create container
curl -X POST http://localhost:5000/api/containers \
  -H "Content-Type: application/json" \
  -d '{"name":"test","image":"nginx:latest","ports":{"80/tcp":"8081"}}'

# List containers
curl http://localhost:5000/api/containers

# View UI
http://localhost:5000/containers
```

### Troubleshooting
```bash
# View logs
docker compose -f docker-compose.dev.yml logs

# Restart
docker compose -f docker-compose.dev.yml restart

# Clean restart
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.dev.yml up --build

# Complete cleanup
docker compose -f docker-compose.dev.yml down -v
```

## Port Format Reference

```json
{
  "ports": {
    "80/tcp": "8080",     # Container port 80 → Host port 8080
    "443/tcp": "8443",    # Container port 443 → Host port 8443
    "3000/tcp": "3000"    # Container port 3000 → Host port 3000
  }
}
```

## When to Rebuild

| Change | Rebuild? | Command |
|--------|----------|---------|
| Python/HTML code | ❌ No | Auto-reload |
| requirements.txt | ✅ Yes | `up --build` |
| Dockerfile.dev | ✅ Yes | `up --build` |
| docker-compose.dev.yml | ⚠️ Recreate | `up --force-recreate` |
