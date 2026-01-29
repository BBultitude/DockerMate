#!/bin/bash
# Docker entrypoint script for DockerMate development
# Handles database initialization and setup

set -e

echo "======================================================================"
echo "DockerMate Development Container Starting"
echo "======================================================================"

# Initialize database
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
        print("No user found. Creating default admin user...")
        print("  Username: admin")
        print("  Password: admin123")
        print("")
        print("⚠️  IMPORTANT: Change this password after first login!")
        print("")
        
        # Create default user with hashed password
        user = User(
            username='admin',
            password_hash=PasswordManager.hash_password("admin123")
        )
        db.add(user)
        db.commit()
        print("✓ Default user created")
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
EOF

echo ""
echo "======================================================================"
echo "Starting Flask Application"
echo "======================================================================"
echo "Access DockerMate at: http://localhost:5000"
echo ""
echo "Default Credentials:"
echo "  Username: admin"
echo "  Password: admin123"
echo ""
echo "⚠️  Remember to change the password after first login!"
echo "======================================================================"
echo ""

# Start Flask application
exec python3 app_dev.py