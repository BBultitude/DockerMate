# Docker Compose Development Guide

## Overview

DockerMate uses Docker Compose for development to match production architecture and avoid permission issues with the Docker socket. This guide covers setup, daily workflow, and troubleshooting.

## Quick Start

```bash
# Start development environment
docker compose -f docker-compose.dev.yml up --build

# Access application
# http://localhost:5000

# Default credentials (development only)
# Username: admin
# Password: admin123
```

**⚠️ IMPORTANT:** Change the default password after first login!

## Prerequisites

- Docker Engine 20.10+ with Compose plugin
- Docker daemon running
- User in `docker` group (or use `sudo`)

### Setup Docker Access (First Time Only)

```bash
# Add your user to docker group
sudo usermod -aG docker $USER

# Apply group membership (choose one):
newgrp docker              # Quick refresh
# OR
logout && login            # Full reset

# Verify Docker access
docker ps                  # Should work without sudo

# Start Docker daemon if needed
sudo systemctl start docker
sudo systemctl enable docker  # Auto-start on boot
```

## Development Environment

### File Structure

```
dockermate/
├── docker-compose.dev.yml     # Development orchestration
├── Dockerfile.dev             # Development container image
├── app_dev.py                 # Flask app (HTTP, debug mode)
├── backend/                   # Live-mounted for auto-reload
├── frontend/                  # Live-mounted for auto-reload
├── data/                      # Database persistence
└── certs/                     # SSL certificates
```

### Architecture

```
┌─────────────────────────────────────┐
│  DockerMate Container               │
│  ┌───────────────────────────────┐  │
│  │  Flask App (app_dev.py)       │  │
│  │  Port: 5000                   │  │
│  │  Mode: HTTP + Debug           │  │
│  └───────────────────────────────┘  │
│         │                            │
│         │ Bind Mounts                │
│         ├─ ./backend  (live reload) │
│         ├─ ./frontend (live reload) │
│         └─ /var/run/docker.sock     │
│                 │                    │
└─────────────────┼────────────────────┘
                  │
                  ▼
         Host Docker Daemon
```

## Daily Workflow

### Starting Development

```bash
# Start containers (builds on first run)
docker compose -f docker-compose.dev.yml up

# Or start in background (detached)
docker compose -f docker-compose.dev.yml up -d

# View logs (if detached)
docker compose -f docker-compose.dev.yml logs -f
```

### Making Code Changes

**No rebuild required for code changes!**

1. Edit Python files in `backend/` or templates in `frontend/`
2. Save file
3. Flask detects change and auto-reloads (1-2 seconds)
4. Refresh browser to see changes

Example:
```bash
# Edit a file
vim backend/api/containers.py

# Save and Flask automatically reloads
# Check logs: "Detected change, reloading..."

# Test immediately in browser
curl http://localhost:5000/api/containers
```

### Stopping Development

```bash
# Stop containers (preserves database)
docker compose -f docker-compose.dev.yml down

# Stop and remove volumes (clean slate)
docker compose -f docker-compose.dev.yml down -v
```

## When to Rebuild

| Change Type | Action Required | Command |
|-------------|----------------|---------|
| Edit `.py` or `.html` files | ✅ None (auto-reload) | Just save file |
| Change `requirements.txt` | 🔄 Rebuild image | `docker compose up --build` |
| Change `Dockerfile.dev` | 🔄 Rebuild image | `docker compose up --build` |
| Change `docker-compose.dev.yml` | 🔄 Recreate containers | `docker compose up --force-recreate` |
| Flask crashed | 🔄 Restart service | `docker compose restart` |

### Rebuild Commands

```bash
# Rebuild and start
docker compose -f docker-compose.dev.yml up --build

# Force recreate without rebuild
docker compose -f docker-compose.dev.yml up --force-recreate

# Restart single service
docker compose -f docker-compose.dev.yml restart dockermate
```

## Testing Container Management

### Create Container via API

```bash
curl -X POST http://localhost:5000/api/containers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-nginx",
    "image": "nginx:latest",
    "environment": "DEV",
    "ports": {"80/tcp": "8081"},
    "auto_start": true,
    "pull_if_missing": true
  }'
```

Expected response:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "test-nginx",
    "state": "running",
    "environment": "DEV",
    ...
  }
}
```

### Verify Container

```bash
# View in DockerMate UI
http://localhost:5000/containers

# Verify on host Docker
docker ps

# Check container logs
docker logs test-nginx
```

### Container Actions

```bash
# List containers
curl http://localhost:5000/api/containers

# Get hardware profile
curl http://localhost:5000/api/system/hardware

# Stop container
curl -X POST http://localhost:5000/api/containers/1/stop

# Start container
curl -X POST http://localhost:5000/api/containers/1/start

# Delete container
curl -X DELETE http://localhost:5000/api/containers/1
```

## Troubleshooting

### Setup Not Complete Error

If you see "Setup not complete. Please complete initial setup":

```bash
# The entrypoint script should auto-create admin user
# Check logs for initialization messages
docker compose -f docker-compose.dev.yml logs

# If database is corrupted, reset it
docker compose -f docker-compose.dev.yml down -v
docker compose -f docker-compose.dev.yml up --build

# Default credentials will be created:
# Username: admin
# Password: admin123
```

### Container Won't Start

```bash
# View logs
docker compose -f docker-compose.dev.yml logs

# Check Docker daemon
sudo systemctl status docker

# Verify socket permissions
ls -l /var/run/docker.sock
# Should show: srw-rw---- 1 root docker

# Restart everything
docker compose -f docker-compose.dev.yml restart
```

### Port Already in Use

```bash
# Check what's using port 5000
sudo lsof -i :5000

# Stop conflicting process
pkill -f app_dev.py

# Or change port in docker-compose.dev.yml:
ports:
  - "5001:5000"  # Use 5001 on host instead
```

### Permission Denied Errors

```bash
# Database files owned by root
sudo chown -R $USER:$USER data/

# Docker socket not accessible
sudo usermod -aG docker $USER
newgrp docker

# Using sudo for docker-compose
# Fix: Add user to docker group (see Setup section)
```

### Changes Not Reflecting

```bash
# Force rebuild
docker compose -f docker-compose.dev.yml up --build

# Clear Python cache
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# Check if volumes mounted correctly
docker compose -f docker-compose.dev.yml exec dockermate ls -la /app/backend
```

### Cannot Connect to Docker Daemon

```bash
# From inside container
docker compose -f docker-compose.dev.yml exec dockermate \
  ls -la /var/run/docker.sock

# Should show socket is mounted
# If not, check docker-compose.dev.yml volumes section

# Verify socket on host
ls -la /var/run/docker.sock
```

### Flask Not Auto-Reloading

```bash
# Check Flask environment variables
docker compose -f docker-compose.dev.yml exec dockermate env | grep FLASK

# Should show:
# FLASK_ENV=development
# FLASK_DEBUG=1

# Restart with fresh build
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.dev.yml up --build
```

## Useful Commands

### Container Management

```bash
# List running containers
docker compose -f docker-compose.dev.yml ps

# Execute command in container
docker compose -f docker-compose.dev.yml exec dockermate bash

# View real-time logs
docker compose -f docker-compose.dev.yml logs -f

# View last 100 log lines
docker compose -f docker-compose.dev.yml logs --tail=100

# Restart specific service
docker compose -f docker-compose.dev.yml restart dockermate
```

### Database Management

```bash
# Access SQLite database
docker compose -f docker-compose.dev.yml exec dockermate \
  sqlite3 /app/data/dockermate.db

# Backup database
docker compose -f docker-compose.dev.yml exec dockermate \
  cp /app/data/dockermate.db /app/data/backup.db

# View database on host
sqlite3 data/dockermate.db "SELECT * FROM containers;"
```

### Cleanup

```bash
# Stop and remove containers
docker compose -f docker-compose.dev.yml down

# Remove volumes (deletes database!)
docker compose -f docker-compose.dev.yml down -v

# Remove images
docker compose -f docker-compose.dev.yml down --rmi all

# Complete cleanup
docker compose -f docker-compose.dev.yml down -v --rmi all --remove-orphans
```

## Environment Variables

Configure in `docker-compose.dev.yml`:

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_ENV` | `development` | Flask environment mode |
| `FLASK_DEBUG` | `1` | Enable debug mode |
| `DATABASE_PATH` | `/app/data/dockermate.db` | SQLite database location |
| `DOCKERMATE_SSL_MODE` | `disabled` | Disable HTTPS for development |
| `PYTHONUNBUFFERED` | `1` | Show logs immediately |

## Production vs Development

### Development (docker-compose.dev.yml)

- ✅ HTTP only (no SSL complexity)
- ✅ Debug mode enabled
- ✅ Live code reload
- ✅ Mounted source code
- ✅ Verbose logging
- ✅ Port 5000 exposed

### Production (docker-compose.yml - Coming in Sprint 6)

- ✅ HTTPS with certificates
- ✅ Production optimizations
- ✅ No debug mode
- ✅ Baked code (no mounts)
- ✅ Structured logging
- ✅ Health checks
- ✅ Restart policies
- ✅ Resource limits

## Testing Checklist

Before committing changes, verify:

- [ ] Container starts successfully
- [ ] API endpoints respond correctly
- [ ] UI loads without errors
- [ ] Container creation works
- [ ] Container actions (start/stop/delete) work
- [ ] Hardware profile displays correctly
- [ ] Database persists after restart
- [ ] Logs show no errors
- [ ] Browser console shows no errors

## Integration Tests

```bash
# Run full integration test
./scripts/test_docker_compose.sh

# Manual verification
docker compose -f docker-compose.dev.yml up -d

# Wait for startup
sleep 5

# Test health endpoint
curl http://localhost:5000/api/health

# Test hardware endpoint
curl http://localhost:5000/api/system/hardware

# Test containers endpoint
curl http://localhost:5000/api/containers

# Test UI loads
curl -I http://localhost:5000/containers

# Cleanup
docker compose -f docker-compose.dev.yml down
```

## Performance Tips

### Optimize Build Times

```bash
# Use BuildKit for faster builds
DOCKER_BUILDKIT=1 docker compose -f docker-compose.dev.yml build

# Skip unnecessary rebuilds
docker compose -f docker-compose.dev.yml up --no-build
```

### Reduce Log Noise

```bash
# Only show errors
docker compose -f docker-compose.dev.yml up --quiet-pull

# Limit log lines
docker compose -f docker-compose.dev.yml logs --tail=50
```

### Speed Up Iteration

```bash
# Start detached and tail logs
docker compose -f docker-compose.dev.yml up -d && \
  docker compose -f docker-compose.dev.yml logs -f
```

## Getting Help

- Check logs: `docker compose -f docker-compose.dev.yml logs`
- Inspect container: `docker compose -f docker-compose.dev.yml exec dockermate bash`
- View configuration: `docker compose -f docker-compose.dev.yml config`
- GitHub Issues: [DockerMate Issues](https://github.com/BBultitude/DockerMate/issues)

## Contributing

When submitting pull requests:

1. Test changes with `docker compose -f docker-compose.dev.yml up --build`
2. Verify all API endpoints work
3. Check UI functionality
4. Include any new environment variables in documentation
5. Update this guide if workflow changes

## License

See [LICENSE](LICENSE) for details.