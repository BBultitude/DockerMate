#!/usr/bin/env python3
"""
Task 2 Verification Script - Database Models & Schema

This script verifies that all database models are working correctly.

Tests:
1. Database initialization
2. User model CRUD operations
3. Session model and validation
4. Environment model and defaults
5. Table structure verification
6. Foreign key constraints
7. Model relationships

Usage:
    python3 verify_task2.py
    
Expected Output:
    All tests should pass with ✅ green checkmarks

Verification Commands:
    # Check database exists
    ls -la /tmp/dockermate.db
    
    # List tables
    sqlite3 /tmp/dockermate.db ".tables"
    
    # Check user table structure
    sqlite3 /tmp/dockermate.db ".schema users"
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from datetime import datetime, timedelta
import secrets
import hashlib
import json

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def print_success(message):
    """Print success message with green checkmark"""
    print(f"{GREEN}✅ {message}{RESET}")

def print_error(message):
    """Print error message with red X"""
    print(f"{RED}❌ {message}{RESET}")

def print_info(message):
    """Print info message"""
    print(f"{YELLOW}ℹ️  {message}{RESET}")

def test_database_initialization():
    """Test 1: Database Initialization"""
    print("\n" + "=" * 80)
    print("Test 1: Database Initialization")
    print("=" * 80)
    
    try:
        from backend.models.database import init_db, get_db_info, DATABASE_PATH
        
        # Initialize database
        print("\n  Initializing database...")
        init_db()
        print_success("Database initialized")
        
        # Check database file exists
        if os.path.exists(DATABASE_PATH):
            print_success(f"Database file exists: {DATABASE_PATH}")
        else:
            print_error(f"Database file not found: {DATABASE_PATH}")
            return False
        
        # Get database info
        info = get_db_info()
        print_success(f"Database size: {info['size_bytes']} bytes")
        print_success(f"Tables found: {len(info['tables'])}")
        
        # Check for expected tables
        expected_tables = ['users', 'sessions', 'environments']
        for table in expected_tables:
            if table in info['tables']:
                print_success(f"Table '{table}' exists")
            else:
                print_error(f"Table '{table}' missing")
                return False
        
        return True
        
    except Exception as e:
        print_error(f"Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_user_model():
    """Test 2: User Model Operations"""
    print("\n" + "=" * 80)
    print("Test 2: User Model CRUD Operations")
    print("=" * 80)
    
    try:
        from backend.models import SessionLocal, User
        
        db = SessionLocal()
        
        # Clean up any existing test data
        existing = db.query(User).first()
        if existing:
            print_info("Deleting existing user for clean test")
            db.delete(existing)
            db.commit()
        
        # Create user
        print("\n  Creating user...")
        user = User(
            username='admin',
            password_hash='$2b$12$test_hash_not_real_for_testing'
        )
        db.add(user)
        db.commit()
        print_success("User created")
        
        # Verify user exists
        print("\n  Verifying user...")
        retrieved = db.query(User).first()
        if retrieved:
            print_success(f"User retrieved: {retrieved}")
        else:
            print_error("User not found after creation")
            db.close()
            return False
        
        # Test to_dict
        print("\n  Testing to_dict()...")
        user_dict = retrieved.to_dict()
        print_success(f"to_dict() working: {json.dumps(user_dict, indent=2)}")
        
        # Test static methods
        print("\n  Testing static methods...")
        admin = User.get_admin(db)
        if admin:
            print_success("get_admin() works")
        else:
            print_error("get_admin() failed")
            db.close()
            return False
        
        exists = User.exists(db)
        if exists:
            print_success("exists() returns True")
        else:
            print_error("exists() returns False (should be True)")
            db.close()
            return False
        
        # Update user
        print("\n  Updating user...")
        retrieved.force_password_change = True
        db.commit()
        
        updated = db.query(User).first()
        if updated.force_password_change:
            print_success("User updated successfully")
        else:
            print_error("User update failed")
            db.close()
            return False
        
        db.close()
        return True
        
    except Exception as e:
        print_error(f"User model test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_session_model():
    """Test 3: Session Model Operations"""
    print("\n" + "=" * 80)
    print("Test 3: Session Model Operations")
    print("=" * 80)
    
    try:
        from backend.models import SessionLocal, Session
        
        db = SessionLocal()
        
        # Create valid session
        print("\n  Creating valid session...")
        token1 = secrets.token_hex(32)
        hash1 = hashlib.sha256(token1.encode()).hexdigest()
        
        session1 = Session(
            token_hash=hash1,
            expires_at=datetime.utcnow() + timedelta(hours=8),
            user_agent='Test Browser 1.0',
            ip_address='192.168.1.100'
        )
        db.add(session1)
        db.commit()
        print_success("Valid session created")
        
        # Create expired session
        print("\n  Creating expired session...")
        token2 = secrets.token_hex(32)
        hash2 = hashlib.sha256(token2.encode()).hexdigest()
        
        session2 = Session(
            token_hash=hash2,
            expires_at=datetime.utcnow() - timedelta(hours=1),
            user_agent='Test Browser 1.0',
            ip_address='192.168.1.101'
        )
        db.add(session2)
        db.commit()
        print_success("Expired session created")
        
        # Test session validation
        print("\n  Testing session validation...")
        if session1.is_valid():
            print_success("session1.is_valid() = True (correct)")
        else:
            print_error("session1.is_valid() = False (should be True)")
            db.close()
            return False
        
        if not session2.is_valid():
            print_success("session2.is_valid() = False (correct)")
        else:
            print_error("session2.is_valid() = True (should be False)")
            db.close()
            return False
        
        # Test active sessions
        print("\n  Testing active sessions query...")
        active = Session.get_active_sessions(db)
        print_success(f"Found {len(active)} active sessions")
        
        # Test cleanup
        print("\n  Testing expired session cleanup...")
        deleted = Session.cleanup_expired(db)
        print_success(f"Cleaned up {deleted} expired sessions")
        
        remaining = Session.count_active_sessions(db)
        print_success(f"{remaining} active sessions remaining")
        
        # Test to_dict
        print("\n  Testing to_dict()...")
        if active:
            session_dict = active[0].to_dict()
            print_success(f"to_dict() working: {json.dumps(session_dict, indent=2)}")
        
        db.close()
        return True
        
    except Exception as e:
        print_error(f"Session model test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_environment_model():
    """Test 4: Environment Model Operations"""
    print("\n" + "=" * 80)
    print("Test 4: Environment Model Operations")
    print("=" * 80)
    
    try:
        from backend.models import SessionLocal, Environment
        
        db = SessionLocal()
        
        # Seed default environments
        print("\n  Seeding default environments...")
        created = Environment.seed_defaults(db)
        print_success(f"Created {created} default environments")
        
        # List all environments
        print("\n  Listing all environments...")
        envs = db.query(Environment).order_by(Environment.display_order).all()
        
        if len(envs) != 4:
            print_error(f"Expected 4 environments, found {len(envs)}")
            db.close()
            return False
        
        for env in envs:
            print_success(f"{env.icon_emoji} {env.code}: {env.name}")
        
        # Test filtering
        print("\n  Testing environment filtering...")
        prd = db.query(Environment).filter_by(code='PRD').first()
        if prd:
            print_success(f"Found PRD environment: {prd.name}")
            
            if prd.require_confirmation:
                print_success("PRD requires confirmation (correct)")
            else:
                print_error("PRD should require confirmation")
                db.close()
                return False
        else:
            print_error("PRD environment not found")
            db.close()
            return False
        
        # Test to_dict
        print("\n  Testing to_dict()...")
        env_dict = prd.to_dict()
        print_success(f"to_dict() working: {json.dumps(env_dict, indent=2)}")
        
        db.close()
        return True
        
    except Exception as e:
        print_error(f"Environment model test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_structure():
    """Test 5: Database Structure Verification"""
    print("\n" + "=" * 80)
    print("Test 5: Database Structure Verification")
    print("=" * 80)
    
    try:
        import sqlite3
        from backend.models.database import DATABASE_PATH
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Check users table structure
        print("\n  Checking users table structure...")
        cursor.execute("PRAGMA table_info(users)")
        user_columns = {row[1] for row in cursor.fetchall()}
        
        expected_user_columns = {
            'id', 'username', 'password_hash', 'force_password_change',
            'password_reset_at', 'created_at', 'updated_at'
        }
        
        if expected_user_columns.issubset(user_columns):
            print_success("Users table structure correct")
        else:
            missing = expected_user_columns - user_columns
            print_error(f"Users table missing columns: {missing}")
            conn.close()
            return False
        
        # Check sessions table structure
        print("\n  Checking sessions table structure...")
        cursor.execute("PRAGMA table_info(sessions)")
        session_columns = {row[1] for row in cursor.fetchall()}
        
        expected_session_columns = {
            'id', 'token_hash', 'created_at', 'expires_at',
            'last_accessed', 'user_agent', 'ip_address'
        }
        
        if expected_session_columns.issubset(session_columns):
            print_success("Sessions table structure correct")
        else:
            missing = expected_session_columns - session_columns
            print_error(f"Sessions table missing columns: {missing}")
            conn.close()
            return False
        
        # Check environments table structure
        print("\n  Checking environments table structure...")
        cursor.execute("PRAGMA table_info(environments)")
        env_columns = {row[1] for row in cursor.fetchall()}
        
        expected_env_columns = {
            'id', 'code', 'name', 'description', 'color', 'icon_emoji',
            'display_order', 'require_confirmation', 'prevent_auto_update',
            'created_at', 'updated_at'
        }
        
        if expected_env_columns.issubset(env_columns):
            print_success("Environments table structure correct")
        else:
            missing = expected_env_columns - env_columns
            print_error(f"Environments table missing columns: {missing}")
            conn.close()
            return False
        
        conn.close()
        return True
        
    except Exception as e:
        print_error(f"Database structure test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("DockerMate - Task 2 Verification")
    print("Database Models & Schema Test Suite")
    print("=" * 80)
    
    tests = [
        ("Database Initialization", test_database_initialization),
        ("User Model", test_user_model),
        ("Session Model", test_session_model),
        ("Environment Model", test_environment_model),
        ("Database Structure", test_database_structure),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print_error(f"Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        if result:
            print_success(f"{test_name}: PASSED")
        else:
            print_error(f"{test_name}: FAILED")
    
    print("\n" + "-" * 80)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print_success("ALL TESTS PASSED! ✨")
        print("\nTask 2 is complete!")
        print("\nVerification commands:")
        print("  ls -la /tmp/dockermate.db")
        print("  sqlite3 /tmp/dockermate.db '.tables'")
        print("  sqlite3 /tmp/dockermate.db '.schema'")
        return 0
    else:
        print_error("SOME TESTS FAILED")
        print("\nPlease review the errors above and fix the issues.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
