"""
Task 5 Verification - Flask Application Setup

Tests:
1. Import all required modules
2. Flask app configuration
3. Database initialization
4. SSL certificate generation
5. Template files exist
6. Routes are defined
7. Error handlers exist

Usage:
    python verify_task5.py
"""

import sys
import os

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def test_header(test_name):
    print(f"\n{Colors.BLUE}{test_name}{Colors.END}")

def test_pass(message):
    print(f"{Colors.GREEN}✅ PASS{Colors.END} - {message}")

def test_fail(message):
    print(f"{Colors.RED}❌ FAIL{Colors.END} - {message}")

def run_tests():
    """Run all verification tests"""
    passed = 0
    failed = 0
    
    print("=" * 60)
    print("Task 5 Verification - Flask Application Setup")
    print("=" * 60)
    
    # Test 1: Import Flask modules
    test_header("Test 1: Import Flask and dependencies")
    try:
        from flask import Flask, render_template, redirect, url_for
        import ssl
        test_pass("Flask modules imported successfully")
        passed += 1
    except Exception as e:
        test_fail(f"Flask import failed: {e}")
        failed += 1
    
    # Test 2: Import app.py
    test_header("Test 2: Import app.py")
    try:
        sys.path.insert(0, '.')
        import app
        test_pass("app.py imported successfully")
        passed += 1
    except Exception as e:
        test_fail(f"app.py import failed: {e}")
        failed += 1
        return  # Can't continue without app
    
    # Test 3: Check Flask app exists
    test_header("Test 3: Flask application object")
    try:
        assert hasattr(app, 'app'), "No Flask app object found"
        assert isinstance(app.app, Flask), "app is not a Flask instance"
        test_pass("Flask application object exists")
        passed += 1
    except Exception as e:
        test_fail(f"{e}")
        failed += 1
    
    # Test 4: Check routes are defined
    test_header("Test 4: Application routes")
    try:
        routes = [rule.rule for rule in app.app.url_map.iter_rules()]
        
        required_routes = [
            '/setup',
            '/login',
            '/logout',
            '/dashboard',
            '/api/health'
        ]
        
        missing_routes = [r for r in required_routes if r not in routes]
        
        if missing_routes:
            test_fail(f"Missing routes: {missing_routes}")
            failed += 1
        else:
            test_pass(f"All required routes defined ({len(required_routes)} routes)")
            passed += 1
    except Exception as e:
        test_fail(f"Route check failed: {e}")
        failed += 1
    
    # Test 5: Check template files exist
    test_header("Test 5: Template files")
    try:
        # Get the directory where the script is running from
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        required_templates = [
            'frontend/templates/base.html',
            'frontend/templates/setup.html',
            'frontend/templates/login.html',
            'frontend/templates/dashboard.html',
            'frontend/templates/errors/404.html',
            'frontend/templates/errors/500.html',
            'frontend/templates/errors/403.html'
        ]
        
        missing_templates = []
        for template in required_templates:
            template_path = os.path.join(script_dir, template)
            if not os.path.exists(template_path):
                missing_templates.append(template)
        
        if missing_templates:
            test_fail(f"Missing templates: {missing_templates}")
            failed += 1
        else:
            test_pass(f"All template files exist ({len(required_templates)} templates)")
            passed += 1
    except Exception as e:
        test_fail(f"Template check failed: {e}")
        failed += 1
    
    # Test 6: Check error handlers
    test_header("Test 6: Error handlers")
    try:
        error_handlers = app.app.error_handler_spec.get(None, {})
        
        required_errors = [404, 500, 403]
        has_all_handlers = all(code in error_handlers for code in required_errors)
        
        if not has_all_handlers:
            test_fail("Missing error handlers")
            failed += 1
        else:
            test_pass("All error handlers defined (404, 500, 403)")
            passed += 1
    except Exception as e:
        test_fail(f"Error handler check failed: {e}")
        failed += 1
    
    # Test 7: Check SSL certificate generation function
    test_header("Test 7: SSL certificate generation")
    try:
        assert hasattr(app, 'create_ssl_context'), "create_ssl_context function not found"
        test_pass("SSL certificate generation function exists")
        passed += 1
    except Exception as e:
        test_fail(f"{e}")
        failed += 1
    
    # Test 8: Check authentication integration
    test_header("Test 8: Authentication integration")
    try:
        from backend.auth.middleware import login_required
        from backend.auth.session_manager import SessionManager
        from backend.auth.password_manager import PasswordManager
        test_pass("Authentication modules integrated")
        passed += 1
    except Exception as e:
        test_fail(f"Authentication integration failed: {e}")
        failed += 1
    
    # Test 9: Check database models import
    test_header("Test 9: Database models integration")
    try:
        from backend.models.database import init_db, SessionLocal
        from backend.models.user import User
        test_pass("Database models integrated")
        passed += 1
    except Exception as e:
        test_fail(f"Database integration failed: {e}")
        failed += 1
    
    # Test 10: Check config integration
    test_header("Test 10: Configuration integration")
    try:
        from config import Config
        assert hasattr(Config, 'SSL_DIR'), "Config missing SSL_DIR"
        assert hasattr(Config, 'DATA_DIR'), "Config missing DATA_DIR"
        test_pass("Configuration properly integrated")
        passed += 1
    except Exception as e:
        test_fail(f"Config integration failed: {e}")
        failed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print(f"Results: {passed}/{passed + failed} tests passed")
    print("=" * 60)
    
    if failed == 0:
        print(f"{Colors.GREEN}✅ All tests passed! Task 5 complete.{Colors.END}")
        return 0
    else:
        print(f"{Colors.RED}❌ Some tests failed. Review errors above.{Colors.END}")
        return 1

if __name__ == '__main__':
    sys.exit(run_tests())
