# Storage Path Configuration

DockerMate allows you to customize where persistent data is stored using environment variables.

## Default Paths

By default, DockerMate stores all data in `/app/data`:

```
/app/data/
├── dockermate.db      # SQLite database
├── ssl/               # SSL certificates
│   ├── cert.pem
│   └── key.pem
├── backups/           # Database backups
└── setup_complete     # Setup marker file
```

## Customizing Storage Paths

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DOCKERMATE_DATA_DIR` | `/app/data` | Base data directory for all persistent storage |
| `DOCKERMATE_DATABASE_PATH` | `${DATA_DIR}/dockermate.db` | SQLite database file path |

### Docker Compose Example

```yaml
version: '3.8'

services:
  dockermate:
    image: dockermate:latest
    volumes:
      # Custom data directory
      - /mnt/nas/dockermate:/app/data
      # Or use a named volume
      # - dockermate-data:/app/data
    environment:
      # Optional: explicitly set data directory (defaults to /app/data)
      - DOCKERMATE_DATA_DIR=/app/data

volumes:
  dockermate-data:
    driver: local
```

### Docker Run Example

```bash
docker run -d \
  --name dockermate \
  -p 5000:5000 \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v /mnt/nas/dockermate:/app/data \
  -e DOCKERMATE_DATA_DIR=/app/data \
  dockermate:latest
```

## Advanced: Custom Paths for Each Component

If you need fine-grained control over where each component stores data, you can customize individual paths:

```yaml
environment:
  # Base directory
  - DOCKERMATE_DATA_DIR=/mnt/storage/dockermate

  # Database on SSD for performance
  - DOCKERMATE_DATABASE_PATH=/mnt/ssd/dockermate.db
```

**Note:** When using custom paths, ensure the directories exist and have proper permissions (readable/writable by the container user).

## Verification

Check current configuration from inside the container:

```bash
docker exec dockermate python3 -c "from config import Config; import json; print(json.dumps(Config.get_config_dict(), indent=2))"
```

Output example:
```json
{
  "BASE_DIR": "/app",
  "DATA_DIR": "/app/data",
  "SSL_DIR": "/app/data/ssl",
  "DATABASE_PATH": "/app/data/dockermate.db",
  "SSL_MODE": "self-signed"
}
```

## Migration from Hardcoded Paths

If you're upgrading from a version with hardcoded `/app/data` paths:

1. **No action needed** - The default paths remain the same
2. Your existing data in `/app/data` will continue to work
3. To move data to a new location:

```bash
# Stop DockerMate
docker stop dockermate

# Copy data to new location
cp -r ./data /mnt/nas/dockermate

# Update docker-compose.yml volume mount
# - ./data:/app/data  →  - /mnt/nas/dockermate:/app/data

# Start DockerMate
docker start dockermate
```

## Directory Structure

All subdirectories are created automatically on startup if they don't exist:

- `${DATA_DIR}/ssl/` - SSL certificates
- `${DATA_DIR}/backups/` - Database backups
- `${DATA_DIR}/setup_complete` - Setup marker

## Security Considerations

1. **Permissions**: Ensure the mounted volume has appropriate permissions for the container user
2. **Backups**: Store backups on a separate volume from the main database
3. **NAS/Network Storage**: Acceptable for home labs, but local storage is faster
4. **Encryption**: Consider encrypted volumes for sensitive data

## Troubleshooting

### Permission Denied Errors

```bash
# Fix permissions on host
chown -R 1000:1000 /path/to/data
chmod -R 755 /path/to/data
```

### Database Locked Errors

SQLite databases on network storage (NFS, CIFS) may experience locking issues. Use local storage for the database:

```yaml
environment:
  - DOCKERMATE_DATABASE_PATH=/app/local/dockermate.db
volumes:
  - dockermate-local:/app/local  # Local volume
  - /mnt/nas/backups:/app/data/backups  # Network storage for backups only
```

### Checking Directory Creation

```bash
# View logs during startup
docker logs dockermate 2>&1 | grep -i "director"

# Should see:
# INFO:__main__:Ensuring required directories exist...
# INFO:__main__:✓ Directories created successfully
```

## Examples

### Scenario 1: NAS Storage for All Data

```yaml
volumes:
  - /mnt/nas/dockermate:/app/data
```

### Scenario 2: SSD for Database, HDD for Backups

```yaml
volumes:
  - /mnt/ssd/dockermate:/app/data
  - /mnt/hdd/backups:/app/data/backups
```

### Scenario 3: Named Docker Volumes

```yaml
volumes:
  - dockermate-data:/app/data
  - dockermate-ssl:/app/data/ssl

volumes:
  dockermate-data:
    driver: local
  dockermate-ssl:
    driver: local
```

## Related Configuration

- See `docker-compose.yml` for complete configuration examples
- See `config.py` for all available environment variables
- See `SECURITY.md` for SSL certificate configuration
