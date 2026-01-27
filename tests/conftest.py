"""
Pytest Configuration and Shared Fixtures

This module provides centralized test configuration and fixtures for all tests.
It ensures proper database isolation using in-memory SQLite for testing.

Fixtures:
    test_db_engine: In-memory SQLite engine for testing
    test_db_session: Database session for tests
    db_setup: Setup and teardown for database tests
    test_app: Flask application configured for testing
    client: Flask test client

Usage:
    # Tests automatically use these fixtures via pytest
    def test_something(db_setup):
        # Database is ready to use
        pass
"""

import pytest
import os
import tempfile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from flask import Flask

# Import database components
from backend.models.database import Base, SessionLocal
from backend.models.user import User
from backend.models.session import Session as SessionModel
from backend.models.environment import Environment
from backend.models.host_config import HostConfig
from backend.models.container import Container

# Import managers for test setup
from backend.auth.password_manager import PasswordManager


# =============================================================================
# Database Fixtures
# =============================================================================

@pytest.fixture(scope='session')
def test_db_engine():
    """
    Create in-memory SQLite engine for testing
    
    Scope: session (created once per test session)
    
    This fixture creates a fresh in-memory database that is:
    - Fast (no disk I/O)
    - Isolated (no conflicts with production database)
    - Clean (automatically destroyed after tests)
    """
    # Create in-memory SQLite engine
    engine = create_engine(
        'sqlite:///:memory:',
        echo=False,  # Set to True for SQL debugging
        connect_args={'check_same_thread': False}  # Allow multiple threads
    )
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    yield engine
    
    # Cleanup
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope='function')
def test_db_session(test_db_engine):
    """
    Create database session for testing
    
    Scope: function (new session for each test)
    
    This provides a fresh database session for each test function,
    ensuring complete isolation between tests.
    """
    # Create session factory
    TestSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_db_engine
    )
    
    # Create session
    session = TestSessionLocal()
    
    yield session
    
    # Cleanup
    session.rollback()
    session.close()


@pytest.fixture(scope='function')
def db_setup(test_db_engine):
    """
    Setup and teardown for database tests
    
    Scope: function (runs before/after each test)
    
    This fixture:
    1. Creates all tables in test database
    2. Yields control to test
    3. Cleans up all data after test
    
    Usage:
        def test_something(db_setup):
            # Database is ready
            db = SessionLocal()
            # ... test code ...
            db.close()
    """
    # Monkey-patch the SessionLocal to use test engine
    original_bind = SessionLocal.kw.get('bind')
    SessionLocal.configure(bind=test_db_engine)
    
    # Create all tables (idempotent)
    Base.metadata.create_all(test_db_engine)
    
    yield
    
    # Cleanup: delete all data from all tables
    session = SessionLocal()
    try:
        # Delete in reverse order to respect foreign keys
        session.query(SessionModel).delete()
        session.query(Container).delete()
        session.query(Environment).delete()
        session.query(HostConfig).delete()
        session.query(User).delete()
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Cleanup error: {e}")
    finally:
        session.close()
    
    # Restore original bind
    if original_bind:
        SessionLocal.configure(bind=original_bind)


@pytest.fixture(scope='function')
def test_user(db_setup):
    """
    Create test user for authentication tests
    
    Creates a user with known credentials:
    - Username: admin
    - Password: TestPassword123!
    
    Usage:
        def test_login(test_user):
            # User already exists in database
            # Can login with 'admin' / 'TestPassword123!'
            pass
    """
    db = SessionLocal()
    try:
        # Check if user already exists
        user = db.query(User).filter_by(username='admin').first()
        if not user:
            user = User(
                username='admin',
                password_hash=PasswordManager.hash_password('TestPassword123!')
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        yield user
        
    finally:
        db.close()


# =============================================================================
# Flask Application Fixtures
# =============================================================================

@pytest.fixture(scope='function')
def test_app(db_setup):
    """
    Create Flask application configured for testing
    
    This fixture provides a Flask app instance with:
    - Testing mode enabled
    - Test database configuration
    - All routes registered
    
    Usage:
        def test_route(test_app):
            with test_app.app_context():
                # Test code here
                pass
    """
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test_secret_key_for_testing_only'
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
    
    # Import and register routes
    from backend.auth.middleware import require_auth, is_authenticated, get_current_session_info
    
    # Add test routes
    @app.route('/login')
    def login_page():
        return "Login page"
    
    @app.route('/protected-page')
    @require_auth()
    def protected_page():
        return "Protected content"
    
    @app.route('/protected-api')
    @require_auth(api=True)
    def protected_api():
        return {"message": "Protected API response"}
    
    @app.route('/check-status')
    def check_status():
        if is_authenticated():
            return "Logged in"
        return "Not logged in"
    
    @app.route('/session-info')
    @require_auth()
    def session_info():
        info = get_current_session_info()
        if info:
            # info is already a dict from middleware
            return info
        return {"error": "No session"}, 401
    
    yield app


@pytest.fixture(scope='function')
def client(test_app):
    """
    Create Flask test client
    
    This provides a test client for making HTTP requests to the Flask app.
    
    Usage:
        def test_endpoint(client):
            response = client.get('/some-route')
            assert response.status_code == 200
    """
    return test_app.test_client()


# =============================================================================
# Environment Configuration
# =============================================================================

@pytest.fixture(scope='session', autouse=True)
def setup_test_environment():
    """
    Configure environment for testing (runs automatically)
    
    This fixture:
    - Sets test environment variables
    - Configures paths for testing
    - Runs once per test session
    """
    # Set test environment variable
    os.environ['TESTING'] = '1'
    
    # Use temporary directory for any file operations
    test_data_dir = tempfile.mkdtemp()
    os.environ['TEST_DATA_DIR'] = test_data_dir
    
    yield
    
    # Cleanup
    import shutil
    if os.path.exists(test_data_dir):
        shutil.rmtree(test_data_dir)
    
    # Remove test environment variable
    os.environ.pop('TESTING', None)
    os.environ.pop('TEST_DATA_DIR', None)


# =============================================================================
# Pytest Configuration
# =============================================================================

def pytest_configure(config):
    """
    Pytest configuration hook
    
    This runs before any tests and configures pytest behavior.
    """
    # Add custom markers
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )


def pytest_collection_modifyitems(config, items):
    """
    Modify test collection
    
    This hook allows us to modify test items after collection.
    Currently unused but available for future enhancements.
    """
    pass