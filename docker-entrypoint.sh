#!/bin/bash
# Docker entrypoint script for DockerMate development
# Handles database initialization and setup

set -e

echo "======================================================================"
echo "DockerMate Development Container Starting"
echo "======================================================================"

# Fix migration state (one-time fix for images table)
if [ -f "backend/fix_migrations.py" ]; then
    echo "Fixing migration state..."
    python3 backend/fix_migrations.py
    rm backend/fix_migrations.py
    echo "✓ Migration state fixed"
fi

# Run database migrations
echo "Running database migrations..."
alembic upgrade head
echo "✓ Database migrations applied"

# Initialize database (backward compatibility)
echo ""
echo "Initializing database..."
python3 << 'EOF'
from backend.models.database import init_db, SessionLocal
from backend.models.user import User
from backend.models.host_config import HostConfig
from backend.utils.hardware_detector import update_host_config
from backend.auth.password_manager import PasswordManager
import os

# Initialize database (creates tables)
print("Creating database tables...")
init_db()

# Create session
db = SessionLocal()

try:
    # Check if user exists
    user = db.query(User).first()

    if not user:
        print("No user found. Please visit /setup to create your admin account.")
        print("")
    else:
        print("✓ User already exists, skipping creation")
    
    # Check if hardware config exists
    config = HostConfig.get_or_create(db)
    
    if config.profile_name == 'UNKNOWN' or config.cpu_cores == 0:
        print("Detecting hardware profile...")
        config = update_host_config(db, config)
        db.commit()
        print(f"✓ Hardware detected: {config.profile_name}")
        print(f"  CPUs: {config.cpu_cores}")
        print(f"  RAM: {config.ram_gb}GB")
        print(f"  Max Containers: {config.max_containers}")
    else:
        print(f"✓ Hardware profile: {config.profile_name}")
    
finally:
    db.close()

print("✓ Database initialization complete")

# Recover any managed containers missing from the database
# (e.g. after a database reset or migration)
print("")
print("Syncing managed containers with database...")
try:
    from backend.services.container_manager import ContainerManager
    with ContainerManager() as manager:
        sync_result = manager.sync_managed_containers_to_database()
    if sync_result['recovered'] > 0:
        print(f"✓ Recovered {sync_result['recovered']} managed container(s): {sync_result['recovered_containers']}")
    else:
        print("✓ All managed containers are in sync")
except Exception as e:
    print(f"⚠️  Container sync failed (non-fatal): {e}")
EOF

echo ""
echo "======================================================================"
echo "Starting Flask Application"
echo "======================================================================"
echo "Access DockerMate at: https://localhost:5000"
echo ""
echo "Default Credentials:"
echo "  Username: admin"
echo "  Password: admin123"
echo ""
echo "⚠️  Remember to change the password after first login!"
echo "======================================================================"
echo ""

# Start Flask application
exec python3 app.py