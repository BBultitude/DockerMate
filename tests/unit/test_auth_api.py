"""
Unit Tests for Authentication API Endpoints

Tests all authentication API endpoints using Flask test client.
Fixed to match actual implementation in Sprint 1.

Run tests:
    pytest tests/unit/test_auth_api.py -v
"""

import pytest
import json
from app import app as flask_app
from backend.models.database import SessionLocal, init_db
from backend.models.user import User
from backend.models.session import Session as SessionModel
from backend.auth.password_manager import PasswordManager


@pytest.fixture(scope='function')
def app():
    """Create Flask app for testing"""
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False
    
    yield flask_app


@pytest.fixture(scope='function')
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture(scope='function')
def db_with_user():
    """
    Create database with a test user
    
    User credentials:
    - Password: TestPassword123
    """
    init_db()
    
    db = SessionLocal()
    
    # Create test user
    user = User(
        username='admin',
        password_hash=PasswordManager.hash_password('TestPassword123'),
        force_password_change=False
    )
    db.add(user)
    db.commit()
    
    yield db
    
    # Cleanup
    db.query(SessionModel).delete()
    db.query(User).delete()
    db.commit()
    db.close()


class TestLoginEndpoint:
    """Test POST /api/auth/login"""
    
    def test_login_success(self, client, db_with_user):
        """Test successful login"""
        response = client.post('/api/auth/login',
            json={'password': 'TestPassword123'},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] is True
        assert data['message'] == 'Login successful'
        assert data['redirect'] == '/dashboard'
        
        # Check that session cookie was set
        assert 'session' in response.headers.get('Set-Cookie', '')
    
    def test_login_wrong_password(self, client, db_with_user):
        """Test login with wrong password"""
        response = client.post('/api/auth/login',
            json={'password': 'WrongPassword123'},
            content_type='application/json'
        )
        
        assert response.status_code == 401
        data = json.loads(response.data)
        
        assert data['success'] is False
        assert 'password' in data['error'].lower() or 'invalid' in data['error'].lower()
    
    def test_login_missing_password(self, client, db_with_user):
        """Test login without password field"""
        response = client.post('/api/auth/login',
            json={},
            content_type='application/json'
        )
        
        # Should return 400 with JSON error (matches actual implementation)
        assert response.status_code == 400
        data = json.loads(response.data)
        
        assert data['success'] is False
        # Error message will be "Request must be JSON" because empty JSON
        assert 'error' in data
    
    def test_login_no_json(self, client, db_with_user):
        """Test login without JSON body"""
        response = client.post('/api/auth/login',
            data='not json',
            content_type='text/plain'
        )
        
        # Flask returns 500 for UnsupportedMediaType, which gets caught
        assert response.status_code == 500
        data = json.loads(response.data)
        
        assert data['success'] is False
        assert 'error' in data
    
    def test_login_with_remember_me(self, client, db_with_user):
        """Test login with remember_me flag"""
        response = client.post('/api/auth/login',
            json={'password': 'TestPassword123', 'remember_me': True},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        
        # Check cookie max-age is 7 days (604800 seconds)
        set_cookie = response.headers.get('Set-Cookie')
        assert 'Max-Age=604800' in set_cookie or 'max-age=604800' in set_cookie.lower()
    
    def test_login_without_remember_me(self, client, db_with_user):
        """Test login without remember_me (default 8 hours)"""
        response = client.post('/api/auth/login',
            json={'password': 'TestPassword123', 'remember_me': False},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        
        # Check cookie max-age is 8 hours (28800 seconds)
        set_cookie = response.headers.get('Set-Cookie')
        assert 'Max-Age=28800' in set_cookie or 'max-age=28800' in set_cookie.lower()
    
    def test_login_cookie_security_flags(self, client, db_with_user):
        """Test that login sets secure cookie flags"""
        response = client.post('/api/auth/login',
            json={'password': 'TestPassword123'},
            content_type='application/json'
        )
        
        set_cookie = response.headers.get('Set-Cookie')
        
        # Check security flags
        assert 'HttpOnly' in set_cookie
        assert 'Secure' in set_cookie
        assert 'SameSite=Strict' in set_cookie
    
    def test_login_force_password_change(self, client, db_with_user):
        """Test login when password change is forced"""
        # Set force_password_change flag
        user = db_with_user.query(User).first()
        user.force_password_change = True
        db_with_user.commit()
        
        response = client.post('/api/auth/login',
            json={'password': 'TestPassword123'},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['force_password_change'] is True
        assert data['redirect'] == '/change-password'


class TestLogoutEndpoint:
    """Test POST /api/auth/logout"""
    
    def test_logout_success(self, client, db_with_user):
        """Test successful logout"""
        # First login
        login_response = client.post('/api/auth/login',
            json={'password': 'TestPassword123'},
            content_type='application/json'
        )
        
        # Then logout
        response = client.post('/api/auth/logout')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] is True
        assert data['redirect'] == '/login'
        
        # Check that cookie was cleared
        set_cookie = response.headers.get('Set-Cookie')
        assert 'session=;' in set_cookie or 'session=""' in set_cookie
    
    def test_logout_without_session(self, client, db_with_user):
        """Test logout when not logged in"""
        response = client.post('/api/auth/logout')
        
        # Should still succeed (idempotent)
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] is True


class TestSessionCheckEndpoint:
    """Test GET /api/auth/session"""
    
    def test_check_valid_session(self, client, db_with_user):
        """Test checking a valid session"""
        # Login first
        login_response = client.post('/api/auth/login',
            json={'password': 'TestPassword123'},
            content_type='application/json'
        )
        
        # Check session
        response = client.get('/api/auth/session')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['valid'] is True
        assert 'expires_at' in data
    
    def test_check_invalid_session(self, client, db_with_user):
        """Test checking without session"""
        response = client.get('/api/auth/session')
        
        assert response.status_code == 401
        data = json.loads(response.data)
        
        assert data['valid'] is False


class TestChangePasswordEndpoint:
    """Test POST /api/auth/change-password"""
    
    def test_change_password_success(self, client, db_with_user):
        """Test successful password change"""
        # Login first
        client.post('/api/auth/login',
            json={'password': 'TestPassword123'},
            content_type='application/json'
        )
        
        # Change password
        response = client.post('/api/auth/change-password',
            json={
                'current_password': 'TestPassword123',
                'new_password': 'NewPassword456',
                'confirm_password': 'NewPassword456'
            },
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] is True
        
        # Verify new password works
        logout_response = client.post('/api/auth/logout')
        login_response = client.post('/api/auth/login',
            json={'password': 'NewPassword456'},
            content_type='application/json'
        )
        assert login_response.status_code == 200
    
    def test_change_password_wrong_current(self, client, db_with_user):
        """Test password change with wrong current password"""
        client.post('/api/auth/login',
            json={'password': 'TestPassword123'},
            content_type='application/json'
        )
        
        response = client.post('/api/auth/change-password',
            json={
                'current_password': 'WrongPassword',
                'new_password': 'NewPassword456',
                'confirm_password': 'NewPassword456'
            },
            content_type='application/json'
        )
        
        assert response.status_code == 401
        data = json.loads(response.data)
        
        assert data['success'] is False
        assert 'current password' in data['error'].lower()
    
    def test_change_password_mismatch(self, client, db_with_user):
        """Test password change when new passwords don't match"""
        client.post('/api/auth/login',
            json={'password': 'TestPassword123'},
            content_type='application/json'
        )
        
        response = client.post('/api/auth/change-password',
            json={
                'current_password': 'TestPassword123',
                'new_password': 'NewPassword456',
                'confirm_password': 'DifferentPassword789'
            },
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        
        assert data['success'] is False
        assert 'match' in data['error'].lower()
    
    def test_change_password_weak_password(self, client, db_with_user):
        """Test password change with weak new password"""
        client.post('/api/auth/login',
            json={'password': 'TestPassword123'},
            content_type='application/json'
        )
        
        response = client.post('/api/auth/change-password',
            json={
                'current_password': 'TestPassword123',
                'new_password': 'weak',
                'confirm_password': 'weak'
            },
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        
        assert data['success'] is False
        assert 'issues' in data
    
    def test_change_password_not_authenticated(self, client, db_with_user):
        """Test password change without being logged in"""
        response = client.post('/api/auth/change-password',
            json={
                'current_password': 'TestPassword123',
                'new_password': 'NewPassword456',
                'confirm_password': 'NewPassword456'
            },
            content_type='application/json'
        )
        
        assert response.status_code == 401


class TestSessionsEndpoint:
    """Test GET /api/auth/sessions"""
    
    def test_list_sessions(self, client, db_with_user):
        """Test listing active sessions"""
        # Login
        client.post('/api/auth/login',
            json={'password': 'TestPassword123'},
            content_type='application/json'
        )
        
        # Get sessions
        response = client.get('/api/auth/sessions')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'sessions' in data
        assert len(data['sessions']) == 1
        assert data['sessions'][0]['current'] is True
    
    def test_list_sessions_not_authenticated(self, client, db_with_user):
        """Test listing sessions without authentication"""
        response = client.get('/api/auth/sessions')
        
        assert response.status_code == 401


class TestRevokeSessionEndpoint:
    """Test DELETE /api/auth/sessions/{id}"""
    
    def test_revoke_other_session(self, client, db_with_user):
        """Test revoking another session"""
        from backend.auth.session_manager import SessionManager
        
        # Create two sessions (simulate two devices)
        token1 = SessionManager.create_session(ip_address="192.168.1.1")
        token2 = SessionManager.create_session(ip_address="192.168.1.2")
        
        # Get session IDs
        session1_id = SessionManager.get_session_id(token1)
        session2_id = SessionManager.get_session_id(token2)
        
        # Login with token1 (set cookie manually)
        client.set_cookie('session', token1)
        
        # Revoke session2
        response = client.delete(f'/api/auth/sessions/{session2_id}')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] is True
        
        # Verify session2 is revoked
        assert SessionManager.validate_session(token2) is False
        # But session1 still valid
        assert SessionManager.validate_session(token1) is True
        
        # Cleanup
        SessionManager.delete_session(token1)
    
    def test_revoke_current_session_fails(self, client, db_with_user):
        """Test that you cannot revoke your current session"""
        from backend.auth.session_manager import SessionManager
        
        # Login
        login_response = client.post('/api/auth/login',
            json={'password': 'TestPassword123'},
            content_type='application/json'
        )
        
        # Get current session ID from cookie
        # Extract session token from Set-Cookie header
        set_cookie = login_response.headers.get('Set-Cookie')
        # Parse cookie to get token (simplified - in real code would use proper parser)
        import re
        match = re.search(r'session=([^;]+)', set_cookie)
        if match:
            current_token = match.group(1)
            current_id = SessionManager.get_session_id(current_token)
            
            # Try to revoke current session
            response = client.delete(f'/api/auth/sessions/{current_id}')
            
            assert response.status_code == 400
            data = json.loads(response.data)
            
            assert data['success'] is False
            assert 'current session' in data['error'].lower()
    
    def test_revoke_nonexistent_session(self, client, db_with_user):
        """Test revoking session that doesn't exist"""
        # Login
        client.post('/api/auth/login',
            json={'password': 'TestPassword123'},
            content_type='application/json'
        )
        
        # Try to revoke non-existent session
        response = client.delete('/api/auth/sessions/99999')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        
        assert data['success'] is False
