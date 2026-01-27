"""
Unit Tests for Authentication Middleware

Tests the @require_auth decorator and helper functions.

Test Coverage:
- @require_auth() decorator for HTML routes
- @require_auth(api=True) decorator for API routes  
- is_authenticated() helper
- get_current_session_info() helper

Design Philosophy:
- Uses centralized fixtures from conftest.py
- Test both protected and unprotected routes
- Verify redirect behavior for HTML routes
- Verify JSON error for API routes
- Test with valid and invalid sessions

Run tests:
    pytest tests/unit/test_middleware.py -v
    pytest tests/unit/test_middleware.py -v --cov=backend/auth/middleware
"""

import pytest
import json
import time
from datetime import datetime, timedelta
from flask import Flask
from backend.auth.middleware import require_auth, is_authenticated, get_current_session_info
from backend.auth.session_manager import SessionManager
from backend.models.database import SessionLocal
from backend.models.session import Session as SessionModel
from backend.models.user import User


class TestRequireAuthDecorator:
    """Test @require_auth() decorator"""
    
    def test_protected_page_without_auth(self, client, db_setup):
        """Test accessing protected HTML page without authentication"""
        response = client.get('/protected-page')
        
        # Should redirect to login
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_protected_page_with_valid_auth(self, client, db_setup):
        """Test accessing protected HTML page with valid session"""
        # Create a session
        token = SessionManager.create_session()
        
        # Set cookie
        client.set_cookie('session', token)
        
        # Access protected page
        response = client.get('/protected-page')
        
        assert response.status_code == 200
        assert b'Protected content' in response.data
    
    def test_protected_page_with_invalid_token(self, client, db_setup):
        """Test accessing protected page with invalid token"""
        # Set invalid cookie
        client.set_cookie('session', 'invalid_token_12345')
        
        response = client.get('/protected-page')
        
        # Should redirect to login
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_protected_page_with_expired_session(self, client, db_setup):
        """Test accessing protected page with expired session"""
        # Create session and manually expire it
        token = SessionManager.create_session()
        
        db = SessionLocal()
        session = db.query(SessionModel).first()
        session.expires_at = datetime.utcnow() - timedelta(hours=1)
        db.commit()
        db.close()
        
        # Set expired session cookie
        client.set_cookie('session', token)
        
        response = client.get('/protected-page')
        
        # Should redirect to login
        assert response.status_code == 302
        assert '/login' in response.location


class TestRequireAuthAPIDecorator:
    """Test @require_auth(api=True) decorator"""
    
    def test_protected_api_without_auth(self, client, db_setup):
        """Test accessing protected API without authentication"""
        response = client.get('/protected-api')
        
        # Should return 401 JSON response (not redirect)
        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_protected_api_with_valid_auth(self, client, db_setup):
        """Test accessing protected API with valid session"""
        # Create session
        token = SessionManager.create_session()
        
        # Set cookie
        client.set_cookie('session', token)
        
        response = client.get('/protected-api')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data
    
    def test_protected_api_with_invalid_token(self, client, db_setup):
        """Test accessing protected API with invalid token"""
        client.set_cookie('session', 'invalid_token')
        
        response = client.get('/protected-api')
        
        # Should return 401 JSON (not redirect)
        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data


class TestIsAuthenticated:
    """Test is_authenticated() helper function"""
    
    def test_is_authenticated_with_valid_session(self, client, db_setup):
        """Test is_authenticated returns True with valid session"""
        token = SessionManager.create_session()
        client.set_cookie('session', token)
        
        response = client.get('/check-status')
        
        assert response.status_code == 200
        assert b'Logged in' in response.data
    
    def test_is_authenticated_with_invalid_token(self, client, db_setup):
        """Test is_authenticated returns False with invalid token"""
        client.set_cookie('session', 'invalid_token')
        
        response = client.get('/check-status')
        
        assert response.status_code == 200
        assert b'Not logged in' in response.data


class TestGetCurrentSessionInfo:
    """Test get_current_session_info() helper"""
    
    def test_get_session_info_valid(self, client, db_setup):
        """Test getting session info with valid session"""
        user_agent = "Test Browser"
        ip_address = "192.168.1.100"
        
        token = SessionManager.create_session(
            user_agent=user_agent,
            ip_address=ip_address
        )
        
        client.set_cookie('session', token)
        
        response = client.get('/session-info')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'id' in data
        assert 'expires_at' in data
        assert data['ip_address'] == ip_address
        assert data['user_agent'] == user_agent
    
    def test_get_session_info_invalid(self, client, db_setup):
        """Test getting session info without valid session"""
        # The route itself is protected, so it will redirect
        response = client.get('/session-info')
        
        assert response.status_code == 302  # Redirect to login


class TestMiddlewareEdgeCases:
    """Test edge cases in middleware"""
    
    def test_multiple_decorators_on_route(self, db_setup):
        """Test route with multiple decorators"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        
        # Add login route that middleware expects
        @app.route('/login')
        def login_page():
            return "Login page"
        
        @app.route('/multi-protected')
        @require_auth()
        def multi_protected():
            return "Multi protected"
        
        client = app.test_client()
        
        # Without auth - should redirect to login
        response = client.get('/multi-protected')
        assert response.status_code == 302
        
        # With auth - should work
        token = SessionManager.create_session()
        client.set_cookie('session', token)
        response = client.get('/multi-protected')
        assert response.status_code == 200
    
    def test_decorator_preserves_function_metadata(self, db_setup):
        """Test that @require_auth preserves function name and docstring"""
        app = Flask(__name__)
        
        @app.route('/test')
        @require_auth()
        def test_function():
            """Test docstring"""
            return "test"
        
        # Function metadata should be preserved
        assert test_function.__name__ == 'test_function'
        assert test_function.__doc__ == 'Test docstring'
    
    def test_session_validation_updates_last_accessed(self, client, db_setup):
        """Test that accessing protected route updates last_accessed"""
        token = SessionManager.create_session()
        
        # Get initial last_accessed
        db = SessionLocal()
        session = db.query(SessionModel).first()
        initial_last_accessed = session.last_accessed
        db.close()
        
        # Wait a moment
        time.sleep(0.1)
        
        # Access protected route
        client.set_cookie('session', token)
        client.get('/protected-page')
        
        # Check last_accessed was updated
        db = SessionLocal()
        session = db.query(SessionModel).first()
        final_last_accessed = session.last_accessed
        db.close()
        
        if initial_last_accessed:
            assert final_last_accessed > initial_last_accessed
        else:
            assert final_last_accessed is not None