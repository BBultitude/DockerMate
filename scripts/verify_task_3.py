#!/usr/bin/env python3
"""
Verification Script for Sprint 2 Task 3 - Container Database Model
==================================================================

This script verifies that the Container model and migration are correctly
implemented and all tests pass.

Verification Steps:
1. Check Container model exists and has required fields
2. Verify migration file exists with correct version
3. Run unit tests and check for 100% pass rate
4. Verify database schema after migration
5. Test basic CRUD operations
6. Verify indexes are created correctly

Exit Codes:
    0: All verifications passed
    1: One or more verifications failed
"""

import sys
import os
import subprocess
from pathlib import Path


def print_header(message):
    """Print a formatted header."""
    print(f"\n{'=' * 70}")
    print(f"  {message}")
    print(f"{'=' * 70}\n")


def print_success(message):
    """Print a success message."""
    print(f"✓ {message}")


def print_error(message):
    """Print an error message."""
    print(f"✗ {message}")


def print_info(message):
    """Print an info message."""
    print(f"ℹ {message}")


def verify_model_exists():
    """Verify Container model file exists."""
    print_header("Step 1: Verify Container Model Exists")
    
    model_path = Path('app/models/container.py')
    
    if not model_path.exists():
        print_error(f"Container model not found at {model_path}")
        return False
    
    print_success(f"Container model found at {model_path}")
    
    # Check for required fields in model
    required_fields = [
        'container_id', 'name', 'state', 'environment', 'image_name',
        'ports_json', 'cpu_limit', 'memory_limit', 'cpu_usage', 'memory_usage',
        'restart_policy', 'auto_start', 'created_at', 'started_at',
        'stopped_at', 'updated_at'
    ]
    
    with open(model_path, 'r') as f:
        content = f.read()
    
    missing_fields = []
    for field in required_fields:
        if field not in content:
            missing_fields.append(field)
    
    if missing_fields:
        print_error(f"Missing required fields: {', '.join(missing_fields)}")
        return False
    
    print_success("All required fields present in model")
    
    # Check for required methods
    required_methods = [
        'to_dict', 'update_state', 'update_resources',
        'validate_state', 'validate_restart_policy'
    ]
    
    missing_methods = []
    for method in required_methods:
        if f"def {method}" not in content:
            missing_methods.append(method)
    
    if missing_methods:
        print_error(f"Missing required methods: {', '.join(missing_methods)}")
        return False
    
    print_success("All required methods present in model")
    
    return True


def verify_migration_exists():
    """Verify migration file exists with correct version."""
    print_header("Step 2: Verify Migration Exists")
    
    migration_path = Path('migrations/versions/002_create_containers.py')
    
    if not migration_path.exists():
        print_error(f"Migration not found at {migration_path}")
        return False
    
    print_success(f"Migration found at {migration_path}")
    
    # Check migration content
    with open(migration_path, 'r') as f:
        content = f.read()
    
    # Verify revision numbers
    if "revision = '002'" not in content:
        print_error("Migration revision should be '002'")
        return False
    
    if "down_revision = '001'" not in content:
        print_error("Migration down_revision should be '001'")
        return False
    
    print_success("Migration version numbers correct")
    
    # Verify key migration operations
    required_operations = [
        'op.create_table',
        'op.create_index',
        'containers'
    ]
    
    missing_operations = []
    for operation in required_operations:
        if operation not in content:
            missing_operations.append(operation)
    
    if missing_operations:
        print_error(f"Missing operations: {', '.join(missing_operations)}")
        return False
    
    print_success("All required migration operations present")
    
    return True


def run_unit_tests():
    """Run unit tests for Container model."""
    print_header("Step 3: Run Unit Tests")
    
    test_path = 'tests/unit/test_container_model.py'
    
    if not Path(test_path).exists():
        print_error(f"Test file not found at {test_path}")
        return False
    
    print_info("Running pytest for Container model tests...")
    
    try:
        result = subprocess.run(
            ['pytest', test_path, '-v', '--tb=short'],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        print(result.stdout)
        
        if result.returncode != 0:
            print_error("Unit tests failed")
            print(result.stderr)
            return False
        
        # Parse output for test count
        if 'passed' in result.stdout:
            print_success("All unit tests passed")
            return True
        else:
            print_error("Could not verify test results")
            return False
            
    except subprocess.TimeoutExpired:
        print_error("Tests timed out after 60 seconds")
        return False
    except FileNotFoundError:
        print_error("pytest not found - ensure it's installed in virtual environment")
        return False


def verify_database_schema():
    """Verify database schema after migration."""
    print_header("Step 4: Verify Database Schema")
    
    try:
        # Import after model is available
        from app import create_app, db
        from app.models.container import Container
        
        app = create_app('testing')
        
        with app.app_context():
            # Get table info
            inspector = db.inspect(db.engine)
            
            if 'containers' not in inspector.get_table_names():
                print_error("Containers table not found in database")
                return False
            
            print_success("Containers table exists in database")
            
            # Verify columns
            columns = inspector.get_columns('containers')
            column_names = [col['name'] for col in columns]
            
            required_columns = [
                'id', 'container_id', 'name', 'state', 'environment',
                'image_name', 'ports_json', 'cpu_limit', 'memory_limit',
                'cpu_usage', 'memory_usage', 'restart_policy', 'auto_start',
                'created_at', 'started_at', 'stopped_at', 'updated_at'
            ]
            
            missing_columns = [col for col in required_columns if col not in column_names]
            
            if missing_columns:
                print_error(f"Missing columns: {', '.join(missing_columns)}")
                return False
            
            print_success(f"All {len(required_columns)} required columns present")
            
            # Verify indexes
            indexes = inspector.get_indexes('containers')
            index_names = [idx['name'] for idx in indexes]
            
            required_indexes = [
                'ix_containers_container_id',
                'ix_containers_name',
                'ix_containers_state',
                'ix_containers_environment'
            ]
            
            missing_indexes = [idx for idx in required_indexes if idx not in index_names]
            
            if missing_indexes:
                print_error(f"Missing indexes: {', '.join(missing_indexes)}")
                return False
            
            print_success(f"All {len(required_indexes)} required indexes present")
            
            return True
            
    except Exception as e:
        print_error(f"Failed to verify database schema: {str(e)}")
        return False


def test_crud_operations():
    """Test basic CRUD operations on Container model."""
    print_header("Step 5: Test Basic CRUD Operations")
    
    try:
        from app import create_app, db
        from app.models.container import Container
        from datetime import datetime
        
        app = create_app('testing')
        
        with app.app_context():
            # Create
            print_info("Testing CREATE operation...")
            container = Container(
                container_id='verify123abc45' * 5 + 'abcd',
                name='verify-test',
                state='running',
                image_name='nginx:latest',
                environment='test'
            )
            db.session.add(container)
            db.session.commit()
            container_id = container.id
            print_success(f"Container created with ID {container_id}")
            
            # Read
            print_info("Testing READ operation...")
            found = Container.query.get(container_id)
            if not found or found.name != 'verify-test':
                print_error("Failed to read container")
                return False
            print_success("Container read successfully")
            
            # Update
            print_info("Testing UPDATE operation...")
            found.state = 'exited'
            found.update_state('exited')
            db.session.commit()
            
            updated = Container.query.get(container_id)
            if updated.state != 'exited':
                print_error("Failed to update container")
                return False
            print_success("Container updated successfully")
            
            # Delete
            print_info("Testing DELETE operation...")
            db.session.delete(updated)
            db.session.commit()
            
            deleted = Container.query.get(container_id)
            if deleted is not None:
                print_error("Failed to delete container")
                return False
            print_success("Container deleted successfully")
            
            return True
            
    except Exception as e:
        print_error(f"CRUD operations failed: {str(e)}")
        return False


def verify_model_methods():
    """Verify model property methods work correctly."""
    print_header("Step 6: Verify Model Methods")
    
    try:
        from app import create_app, db
        from app.models.container import Container
        from datetime import datetime, timedelta
        
        app = create_app('testing')
        
        with app.app_context():
            # Test is_running property
            print_info("Testing is_running property...")
            container = Container(
                container_id='method123abc45' * 5 + 'abcd',
                name='method-test',
                state='running',
                image_name='nginx:latest'
            )
            
            if not container.is_running:
                print_error("is_running should be True for running container")
                return False
            print_success("is_running property works correctly")
            
            # Test uptime calculation
            print_info("Testing uptime_seconds property...")
            container.started_at = datetime.utcnow() - timedelta(seconds=300)
            uptime = container.uptime_seconds
            if not (299 <= uptime <= 301):
                print_error(f"uptime_seconds should be ~300, got {uptime}")
                return False
            print_success("uptime_seconds property works correctly")
            
            # Test memory conversions
            print_info("Testing memory conversion properties...")
            container.memory_usage = 268435456  # 256 MB
            container.memory_limit = 536870912  # 512 MB
            
            if container.memory_usage_mb != 256.0:
                print_error(f"memory_usage_mb should be 256.0, got {container.memory_usage_mb}")
                return False
            
            if container.memory_limit_mb != 512.0:
                print_error(f"memory_limit_mb should be 512.0, got {container.memory_limit_mb}")
                return False
            
            print_success("Memory conversion properties work correctly")
            
            # Test to_dict method
            print_info("Testing to_dict() method...")
            data = container.to_dict()
            
            required_keys = [
                'id', 'container_id', 'name', 'state', 'environment',
                'image_name', 'created_at', 'updated_at'
            ]
            
            missing_keys = [key for key in required_keys if key not in data]
            if missing_keys:
                print_error(f"to_dict() missing keys: {', '.join(missing_keys)}")
                return False
            
            print_success("to_dict() method works correctly")
            
            # Test validation methods
            print_info("Testing validation methods...")
            
            if not Container.validate_state('running'):
                print_error("validate_state should accept 'running'")
                return False
            
            if Container.validate_state('invalid'):
                print_error("validate_state should reject 'invalid'")
                return False
            
            if not Container.validate_restart_policy('always'):
                print_error("validate_restart_policy should accept 'always'")
                return False
            
            if Container.validate_restart_policy('invalid'):
                print_error("validate_restart_policy should reject 'invalid'")
                return False
            
            print_success("Validation methods work correctly")
            
            return True
            
    except Exception as e:
        print_error(f"Method verification failed: {str(e)}")
        return False


def main():
    """Run all verification steps."""
    print("\n" + "=" * 70)
    print("  Sprint 2 Task 3: Container Database Model Verification")
    print("=" * 70)
    
    steps = [
        ("Model Exists", verify_model_exists),
        ("Migration Exists", verify_migration_exists),
        ("Unit Tests Pass", run_unit_tests),
        ("Database Schema", verify_database_schema),
        ("CRUD Operations", test_crud_operations),
        ("Model Methods", verify_model_methods),
    ]
    
    results = []
    
    for step_name, step_func in steps:
        try:
            result = step_func()
            results.append((step_name, result))
        except Exception as e:
            print_error(f"Step '{step_name}' raised exception: {str(e)}")
            results.append((step_name, False))
    
    # Print summary
    print_header("Verification Summary")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for step_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {step_name}")
    
    print(f"\n  Results: {passed}/{total} steps passed")
    
    if passed == total:
        print_success("\n  All verifications passed! ✓")
        return 0
    else:
        print_error(f"\n  {total - passed} verification(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
