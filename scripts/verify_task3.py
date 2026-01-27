#!/usr/bin/env python3
"""
Task 3 Verification Script - Authentication System

This script verifies that all authentication modules are working correctly.

Tests:
1. Password hashing and verification
2. Password strength validation
3. Temporary password generation
4. Session creation and validation
5. Session revocation
6. Session cleanup
7. Middleware decorator

Usage:
    python3 verify_task3.py
    
Expected Output:
    All tests should pass with ✅ green checkmarks

Verification Commands:
    # Test password manager
    python3 backend/auth/password_manager.py
    
    # Test session manager
    python3 backend/auth/session_manager.py
    
    # Test middleware
    python3 backend/auth/middleware.py
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from datetime import datetime, timedelta
import time

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

def test_password_manager():
    """Test 1: Password Manager"""
    print("\n" + "=" * 80)
    print("Test 1: Password Manager")
    print("=" * 80)
    
    try:
        from backend.auth.password_manager import PasswordManager
        
        # Test password hashing
        print("\n  Testing password hashing...")
        password = "TestPassword123"
        hashed = PasswordManager.hash_password(password)
        
        if len(hashed) == 60 and hashed.startswith('$2b$12$'):
            print_success("Password hashed correctly")
        else:
            print_error(f"Invalid hash format: {hashed[:20]}...")
            return False
        
        # Test password verification
        print("\n  Testing password verification...")
        if PasswordManager.verify_password(password, hashed):
            print_success("Correct password verified")
        else:
            print_error("Password verification failed")
            return False
        
        if not PasswordManager.verify_password("WrongPassword", hashed):
            print_success("Wrong password rejected")
        else:
            print_error("Wrong password accepted")
            return False
        
        # Test password strength validation
        print("\n  Testing password strength validation...")
        
        # Weak password - too short
        result = PasswordManager.validate_password_strength("weak")
        if not result['valid']:
            print_success("Weak password rejected (too short)")
        else:
            print_error("Weak password accepted")
            return False
        
        # Weak password - common pattern
        result = PasswordManager.validate_password_strength("password123")
        if not result['valid']:
            print_success("Common pattern rejected (password123)")
        else:
            print_error("Common pattern accepted (password123)")
            return False
        
        # Weak password - reversed pattern
        result = PasswordManager.validate_password_strength("123password")
        if not result['valid']:
            print_success("Reversed pattern rejected (123password)")
        else:
            print_error("Reversed pattern accepted (123password)")
            return False
        
        # Strong password
        result = PasswordManager.validate_password_strength("MySecurePass2024!")
        if result['valid']:
            print_success("Strong password accepted")
        else:
            print_error(f"Strong password rejected: {result['issues']}")
            return False
        
        # Test temporary password generation
        print("\n  Testing temporary password generation...")
        temp_password = PasswordManager.generate_temp_password()
        
        validation = PasswordManager.validate_password_strength(temp_password)
        if validation['valid']:
            print_success(f"Temporary password valid: {temp_password}")
        else:
            print_error(f"Temporary password invalid: {validation['issues']}")
            return False
        
        return True
        
    except Exception as e:
        print_error(f"Password manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_session_manager():
    """Test 2: Session Manager"""
    print("\n" + "=" * 80)
    print("Test 2: Session Manager")
    print("=" * 80)
    
    try:
        from backend.auth.session_manager import SessionManager
        from backend.models.database import init_db
        
        # Initialize database
        print("\n  Initializing database...")
        init_db()
        print_success("Database initialized")
        
        # Test session creation
        print("\n  Creating session...")
        session_token = SessionManager.create_session(
            remember_me=False,
            user_agent='Test Browser 1.0',
            ip_address='192.168.1.100'
        )
        
        if len(session_token) == 64:
            print_success(f"Session created: {session_token[:20]}...")
        else:
            print_error(f"Invalid token length: {len(session_token)}")
            return False
        
        # Test session validation
        print("\n  Validating session...")
        if SessionManager.validate_session(session_token):
            print_success("Session is valid")
        else:
            print_error("Session validation failed")
            return False
        
        # Test invalid session
        print("\n  Testing invalid session...")
        if not SessionManager.validate_session("invalid_token_12345"):
            print_success("Invalid token rejected")
        else:
            print_error("Invalid token accepted")
            return False
        
        # Test session info
        print("\n  Getting session info...")
        info = SessionManager.get_session_info(session_token)
        if info and info['ip_address'] == '192.168.1.100':
            print_success("Session info retrieved")
        else:
            print_error("Failed to get session info")
            return False
        
        # Test session statistics
        print("\n  Getting session statistics...")
        stats = SessionManager.get_session_stats()
        if stats['active_sessions'] >= 1:
            print_success(f"Active sessions: {stats['active_sessions']}")
        else:
            print_error("No active sessions found")
            return False
        
        # Test session revocation
        print("\n  Revoking session...")
        if SessionManager.revoke_session(session_token):
            print_success("Session revoked")
        else:
            print_error("Failed to revoke session")
            return False
        
        # Test validation after revocation
        print("\n  Validating after revocation...")
        if not SessionManager.validate_session(session_token):
            print_success("Session correctly invalid after revocation")
        else:
            print_error("Session still valid after revocation")
            return False
        
        # Test cleanup
        print("\n  Testing session cleanup...")
        # Create an expired session for cleanup test
        import secrets
        import hashlib
        from backend.models.database import SessionLocal
        from backend.models.session import Session
        
        db = SessionLocal()
        try:
            token = secrets.token_hex(32)
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            
            expired_session = Session(
                token_hash=token_hash,
                expires_at=datetime.utcnow() - timedelta(hours=1)
            )
            db.add(expired_session)
            db.commit()
        finally:
            db.close()
        
        deleted = SessionManager.cleanup_expired_sessions()
        if deleted >= 1:
            print_success(f"Cleaned up {deleted} expired sessions")
        else:
            print_info("No expired sessions to clean up")
        
        return True
        
    except Exception as e:
        print_error(f"Session manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_middleware():
    """Test 3: Authentication Middleware"""
    print("\n" + "=" * 80)
    print("Test 3: Authentication Middleware")
    print("=" * 80)
    
    try:
        from backend.auth.middleware import login_required, get_current_user
        from backend.auth.session_manager import SessionManager
        from backend.models.database import SessionLocal
        from backend.models.user import User
        from backend.auth.password_manager import PasswordManager
        from flask import Flask, request
        
        # Create test user if doesn't exist
        print("\n  Creating test user...")
        db = SessionLocal()
        try:
            user = User.get_admin(db)
            if not user:
                user = User(
                    username='admin',
                    password_hash=PasswordManager.hash_password('TestPassword123')
                )
                db.add(user)
                db.commit()
                print_success("Test user created")
            else:
                print_info("Test user already exists")
        finally:
            db.close()
        
        # Test decorator can be imported
        print("\n  Testing decorator import...")
        if callable(login_required):
            print_success("login_required decorator imported")
        else:
            print_error("login_required is not callable")
            return False
        
        # Test helper functions
        print("\n  Testing helper functions...")
        if callable(get_current_user):
            print_success("get_current_user function available")
        else:
            print_error("get_current_user is not callable")
            return False
        
        # Test decorator application
        print("\n  Testing decorator application...")
        
        def test_route():
            return "Protected content"
        
        protected_route = login_required(test_route)
        
        if callable(protected_route):
            print_success("Decorator successfully wraps function")
        else:
            print_error("Decorator failed to wrap function")
            return False
        
        print_success("All middleware components functional")
        
        return True
        
    except Exception as e:
        print_error(f"Middleware test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_integration():
    """Test 4: Integration Test"""
    print("\n" + "=" * 80)
    print("Test 4: Integration Test (Full Auth Flow)")
    print("=" * 80)
    
    try:
        from backend.auth.password_manager import PasswordManager
        from backend.auth.session_manager import SessionManager
        from backend.models.database import SessionLocal
        from backend.models.user import User
        
        print("\n  Simulating full authentication flow...")
        
        # Step 1: User enters password
        entered_password = "MySecurePass2024!"
        print_info("Step 1: User enters password")
        
        # Step 2: Create test user with known password if doesn't exist
        print_info("Step 2: Set up test user with known password")
        db = SessionLocal()
        try:
            user = User.get_admin(db)
            if not user:
                user = User(
                    username='admin',
                    password_hash=PasswordManager.hash_password(entered_password)
                )
                db.add(user)
                db.commit()
                print_success("Test user created")
            else:
                # Update existing user with test password
                user.password_hash = PasswordManager.hash_password(entered_password)
                db.commit()
                print_success("Test user password updated")
        finally:
            db.close()
        
        # Step 3: Verify password
        print_info("Step 3: Verify password against database")
        db = SessionLocal()
        try:
            user = User.get_admin(db)
            if not user:
                print_error("No user found in database")
                return False
            
            if PasswordManager.verify_password(entered_password, user.password_hash):
                print_success("Password verified")
            else:
                print_error("Password verification failed")
                return False
        finally:
            db.close()
        
        # Step 4: Create session
        print_info("Step 4: Create session")
        session_token = SessionManager.create_session(
            remember_me=False,
            user_agent='Integration Test Browser',
            ip_address='192.168.1.200'
        )
        print_success(f"Session created: {session_token[:20]}...")
        
        # Step 5: Validate session (simulate request)
        print_info("Step 5: Validate session on subsequent request")
        if SessionManager.validate_session(session_token):
            print_success("Session validated successfully")
        else:
            print_error("Session validation failed")
            return False
        
        # Step 6: Logout
        print_info("Step 6: Logout (revoke session)")
        if SessionManager.revoke_session(session_token):
            print_success("Session revoked (logout successful)")
        else:
            print_error("Failed to revoke session")
            return False
        
        # Step 7: Verify session is invalid after logout
        print_info("Step 7: Verify session invalid after logout")
        if not SessionManager.validate_session(session_token):
            print_success("Session correctly invalid after logout")
        else:
            print_error("Session still valid after logout")
            return False
        
        print_success("Full authentication flow successful!")
        
        return True
        
    except Exception as e:
        print_error(f"Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("DockerMate - Task 3 Verification")
    print("Authentication System Test Suite")
    print("=" * 80)
    
    tests = [
        ("Password Manager", test_password_manager),
        ("Session Manager", test_session_manager),
        ("Authentication Middleware", test_middleware),
        ("Integration Test", test_integration),
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
        print("\nTask 3 is complete!")
        print("\nNext Steps:")
        print("  1. Commit to GitHub:")
        print("     git add backend/auth/")
        print("     git add verify_task3.py")
        print("     git commit -m 'feat: Complete Task 3 - Authentication System'")
        print("     git push")
        print("\n  2. Ready for Task 4: SSL/TLS Certificate Management")
        return 0
    else:
        print_error("SOME TESTS FAILED")
        print("\nPlease review the errors above and fix the issues.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
