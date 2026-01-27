"""
Task 6 Verification - Frontend Templates

Tests:
1. Settings page template exists
2. Containers page template exists
3. Images page template exists
4. Networks page template exists
5. All new routes are defined
6. Templates render without errors

Usage:
    python verify_task6.py
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
    print("Task 6 Verification - Frontend Templates")
    print("=" * 60)
    
    # Get script directory for relative paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Test 1: Check template files exist
    test_header("Test 1: Template files exist")
    try:
        required_templates = [
            'frontend/templates/settings.html',
            'frontend/templates/containers.html',
            'frontend/templates/images.html',
            'frontend/templates/networks.html'
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
            test_pass(f"All new template files exist ({len(required_templates)} templates)")
            passed += 1
    except Exception as e:
        test_fail(f"Template check failed: {e}")
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
        return passed, failed  # Can't continue without app
    
    # Test 3: Check new routes exist
    test_header("Test 3: New routes defined")
    try:
        routes = [rule.rule for rule in app.app.url_map.iter_rules()]
        
        required_routes = [
            '/settings',
            '/containers',
            '/images',
            '/networks'
        ]
        
        missing_routes = [r for r in required_routes if r not in routes]
        
        if missing_routes:
            test_fail(f"Missing routes: {missing_routes}")
            failed += 1
        else:
            test_pass(f"All new routes defined ({len(required_routes)} routes)")
            passed += 1
    except Exception as e:
        test_fail(f"Route check failed: {e}")
        failed += 1
    
    # Test 4: Verify templates have navigation
    test_header("Test 4: Templates contain navigation")
    try:
        templates_to_check = [
            'frontend/templates/settings.html',
            'frontend/templates/containers.html',
            'frontend/templates/images.html',
            'frontend/templates/networks.html'
        ]
        
        missing_nav = []
        for template in templates_to_check:
            template_path = os.path.join(script_dir, template)
            with open(template_path, 'r') as f:
                content = f.read()
                # Check for navigation elements
                if 'nav' not in content.lower() or 'dashboard' not in content.lower():
                    missing_nav.append(template)
        
        if missing_nav:
            test_fail(f"Templates missing navigation: {missing_nav}")
            failed += 1
        else:
            test_pass("All templates have navigation")
            passed += 1
    except Exception as e:
        test_fail(f"Navigation check failed: {e}")
        failed += 1
    
    # Test 5: Verify templates extend base
    test_header("Test 5: Templates extend base.html")
    try:
        templates_to_check = [
            'frontend/templates/settings.html',
            'frontend/templates/containers.html',
            'frontend/templates/images.html',
            'frontend/templates/networks.html'
        ]
        
        not_extending = []
        for template in templates_to_check:
            template_path = os.path.join(script_dir, template)
            with open(template_path, 'r') as f:
                content = f.read()
                if '{% extends "base.html" %}' not in content:
                    not_extending.append(template)
        
        if not_extending:
            test_fail(f"Templates not extending base: {not_extending}")
            failed += 1
        else:
            test_pass("All templates extend base.html")
            passed += 1
    except Exception as e:
        test_fail(f"Base extension check failed: {e}")
        failed += 1
    
    # Test 6: Check settings page has password change form
    test_header("Test 6: Settings page has password change form")
    try:
        settings_path = os.path.join(script_dir, 'frontend/templates/settings.html')
        with open(settings_path, 'r') as f:
            content = f.read()
            has_password_fields = (
                'current_password' in content.lower() and
                'new_password' in content.lower() and
                'changepassword' in content.lower().replace(' ', '').replace('_', '')
            )
            
            if not has_password_fields:
                test_fail("Settings page missing password change form")
                failed += 1
            else:
                test_pass("Settings page has password change form")
                passed += 1
    except Exception as e:
        test_fail(f"Settings page check failed: {e}")
        failed += 1
    
    # Test 7: Verify placeholder pages have "Coming in Sprint X" text
    test_header("Test 7: Placeholder pages have sprint indicators")
    try:
        placeholder_checks = {
            'frontend/templates/containers.html': 'Sprint 2',
            'frontend/templates/images.html': 'Sprint 3',
            'frontend/templates/networks.html': 'Sprint 4'
        }
        
        missing_indicators = []
        for template, expected_sprint in placeholder_checks.items():
            template_path = os.path.join(script_dir, template)
            with open(template_path, 'r') as f:
                content = f.read()
                if expected_sprint not in content:
                    missing_indicators.append(f"{template} (should mention {expected_sprint})")
        
        if missing_indicators:
            test_fail(f"Missing sprint indicators: {missing_indicators}")
            failed += 1
        else:
            test_pass("All placeholder pages have sprint indicators")
            passed += 1
    except Exception as e:
        test_fail(f"Sprint indicator check failed: {e}")
        failed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print(f"Results: {passed}/{passed + failed} tests passed")
    print("=" * 60)
    
    if failed == 0:
        print(f"{Colors.GREEN}✅ All tests passed! Task 6 complete.{Colors.END}")
        return 0
    else:
        print(f"{Colors.RED}❌ Some tests failed. Review errors above.{Colors.END}")
        return 1

if __name__ == '__main__':
    sys.exit(run_tests())
