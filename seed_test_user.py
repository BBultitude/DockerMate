"""
Database Seeding Script for Development Testing

This script creates a test admin user so you can log in during development
without needing to complete the initial setup wizard.

Usage:
    python seed_test_user.py

Default credentials:
    Username: admin
    Password: testpassword123

WARNING: This is for DEVELOPMENT ONLY. Do not use in production.
"""

import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.models.database import SessionLocal, init_db
from backend.models.user import User
from backend.auth.password_manager import PasswordManager

def seed_test_user():
    """Create test admin user for development"""
    
    print("=" * 60)
    print("DockerMate - Development User Seeding")
    print("=" * 60)
    
    # Initialize database (create tables if needed)
    print("Initializing database...")
    init_db()
    
    # Get database session
    db = SessionLocal()
    
    try:
        # Check if user already exists
        existing_user = db.query(User).filter_by(username='admin').first()
        
        if existing_user:
            print("✓ Test user 'admin' already exists")
            print(f"  Created: {existing_user.created_at}")
            print(f"  User ID: {existing_user.id}")
            print("\nTo reset password, delete the user first:")
            print("  rm data/dockermate.db")
            print("  python seed_test_user.py")
            return
        
        # Create test user
        print("Creating test user...")
        
        # Hash password
        password_hash = PasswordManager.hash_password('testpassword123')
        
        # Create user object
        user = User(
            username='admin',
            password_hash=password_hash,
            force_password_change=False,  # Don't force change for testing
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Add to database
        db.add(user)
        db.commit()
        
        print("✓ Test user created successfully!")
        print("")
        print("=" * 60)
        print("LOGIN CREDENTIALS (Development Only)")
        print("=" * 60)
        print("Username: admin")
        print("Password: testpassword123")
        print("=" * 60)
        print("")
        print("You can now log in at:")
        print("  http://localhost:5000/login")
        print("  http://192.168.13.142:5000/login")
        print("")
        print("⚠️  WARNING: These credentials are for DEVELOPMENT ONLY")
        print("⚠️  Change password in production environments")
        print("")
        
    except Exception as e:
        print(f"✗ Error creating test user: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == '__main__':
    seed_test_user()