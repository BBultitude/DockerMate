"""
Unit tests for Session Manager

Tests session creation and validation using centralized test fixtures.

Run with: pytest tests/unit/test_session_manager.py -v
"""

import pytest
from datetime import datetime, timedelta
from backend.auth.session_manager import SessionManager
from backend.models.database import SessionLocal
from backend.models.session import Session as SessionModel


class TestSessionCreation:
    """Test session creation"""
    
    def test_create_session_returns_token(self, db_setup):
        """Test that create_session returns a valid token"""
        token = SessionManager.create_session()
        
        # Should be 64 character hex string (32 bytes)
        assert len(token) == 64
        assert all(c in '0123456789abcdef' for c in token)
        
        # Cleanup
        token_hash = SessionManager._hash_token(token)
        db = SessionLocal()
        try:
            session = db.query(SessionModel).filter_by(token_hash=token_hash).first()
            if session:
                db.delete(session)
                db.commit()
        finally:
            db.close()
    
    def test_create_session_stores_in_database(self, db_setup):
        """Test that session is stored in database"""
        token = SessionManager.create_session()
        
        # Hash token to find in database
        token_hash = SessionManager._hash_token(token)
        
        db = SessionLocal()
        try:
            session = db.query(SessionModel).filter_by(token_hash=token_hash).first()
            assert session is not None
            assert session.token_hash == token_hash
        finally:
            # Cleanup
            if session:
                db.delete(session)
                db.commit()
            db.close()
    
    def test_create_session_default_expiry(self, db_setup):
        """Test that default session expiry is 8 hours"""
        token = SessionManager.create_session()
        token_hash = SessionManager._hash_token(token)
        
        db = SessionLocal()
        try:
            session = db.query(SessionModel).filter_by(token_hash=token_hash).first()
            
            # Check expiry is approximately 8 hours from now
            expected_expiry = datetime.utcnow() + timedelta(hours=8)
            time_diff = abs((session.expires_at - expected_expiry).total_seconds())
            
            # Should be within 5 seconds (account for test execution time)
            assert time_diff < 5
        finally:
            if session:
                db.delete(session)
                db.commit()
            db.close()
    
    def test_create_session_with_remember_me(self, db_setup):
        """Test that remember_me extends expiry to 7 days"""
        token = SessionManager.create_session(remember_me=True)
        token_hash = SessionManager._hash_token(token)
        
        db = SessionLocal()
        try:
            session = db.query(SessionModel).filter_by(token_hash=token_hash).first()
            
            # Check expiry is approximately 7 days from now
            expected_expiry = datetime.utcnow() + timedelta(days=7)
            time_diff = abs((session.expires_at - expected_expiry).total_seconds())
            
            # Should be within 5 seconds
            assert time_diff < 5
        finally:
            if session:
                db.delete(session)
                db.commit()
            db.close()
    
    def test_create_session_with_metadata(self, db_setup):
        """Test that session stores user agent and IP address"""
        user_agent = "Mozilla/5.0 Test Browser"
        ip_address = "192.168.1.100"
        
        token = SessionManager.create_session(
            user_agent=user_agent,
            ip_address=ip_address
        )
        token_hash = SessionManager._hash_token(token)
        
        db = SessionLocal()
        try:
            session = db.query(SessionModel).filter_by(token_hash=token_hash).first()
            
            assert session.user_agent == user_agent
            assert session.ip_address == ip_address
        finally:
            if session:
                db.delete(session)
                db.commit()
            db.close()


class TestSessionValidation:
    """Test session validation"""
    
    def test_validate_valid_session(self, db_setup):
        """Test that valid session passes validation"""
        token = SessionManager.create_session()
        
        try:
            # Should validate successfully
            assert SessionManager.validate_session(token) is True
        finally:
            # Cleanup
            token_hash = SessionManager._hash_token(token)
            db = SessionLocal()
            try:
                session = db.query(SessionModel).filter_by(token_hash=token_hash).first()
                if session:
                    db.delete(session)
                    db.commit()
            finally:
                db.close()
    
    def test_validate_invalid_token_format(self, db_setup):
        """Test that invalid token format fails"""
        assert SessionManager.validate_session("invalid") is False
        assert SessionManager.validate_session("") is False
        assert SessionManager.validate_session(None) is False
    
    def test_validate_nonexistent_session(self, db_setup):
        """Test that nonexistent session fails validation"""
        fake_token = "0" * 64  # Valid format but doesn't exist
        
        assert SessionManager.validate_session(fake_token) is False
    
    def test_validate_expired_session(self, db_setup):
        """Test that expired session fails validation and is deleted"""
        # Create session
        token = SessionManager.create_session()
        token_hash = SessionManager._hash_token(token)
        
        # Manually expire it
        db = SessionLocal()
        try:
            session = db.query(SessionModel).filter_by(token_hash=token_hash).first()
            session.expires_at = datetime.utcnow() - timedelta(hours=1)
            db.commit()
        finally:
            db.close()
        
        # Should fail validation
        assert SessionManager.validate_session(token) is False
        
        # Session should be deleted
        db = SessionLocal()
        try:
            session = db.query(SessionModel).filter_by(token_hash=token_hash).first()
            assert session is None
        finally:
            db.close()


class TestSessionRevocation:
    """Test session revocation"""
    
    def test_revoke_session(self, db_setup):
        """Test that session can be revoked"""
        token = SessionManager.create_session()
        
        # Should exist
        assert SessionManager.validate_session(token) is True
        
        # Revoke it
        SessionManager.revoke_session(token)
        
        # Should no longer exist
        assert SessionManager.validate_session(token) is False
    
    def test_revoke_nonexistent_session(self, db_setup):
        """Test revoking nonexistent session"""
        fake_token = "0" * 64
        
        # Should not raise error
        SessionManager.revoke_session(fake_token)


# Note: cleanup_expired_sessions() not implemented in Sprint 1
# class TestSessionCleanup:
#     """Test session cleanup"""
#     
#     def test_cleanup_expired_sessions(self, db_setup):
#         """Test that expired sessions are cleaned up"""
#         # Will be implemented in future sprint


class TestTokenHashing:
    """Test internal token hashing"""
    
    def test_hash_token(self, db_setup):
        """Test that _hash_token produces consistent hashes"""
        token = "test_token_123"
        
        hash1 = SessionManager._hash_token(token)
        hash2 = SessionManager._hash_token(token)
        
        # Same token should produce same hash
        assert hash1 == hash2
    
    def test_hash_token_format(self, db_setup):
        """Test that hash is in correct format"""
        token = "test_token"
        token_hash = SessionManager._hash_token(token)
        
        # SHA-256 hash is 64 hex characters
        assert len(token_hash) == 64
        assert all(c in '0123456789abcdef' for c in token_hash)
    
    def test_hash_different_tokens_different_hashes(self, db_setup):
        """Test that different tokens produce different hashes"""
        hash1 = SessionManager._hash_token("token1")
        hash2 = SessionManager._hash_token("token2")
        
        assert hash1 != hash2


# Additional fixtures for session tests
@pytest.fixture
def valid_session(db_setup):
    """Fixture providing a valid session token"""
    token = SessionManager.create_session()
    yield token
    # Cleanup
    token_hash = SessionManager._hash_token(token)
    db = SessionLocal()
    try:
        session = db.query(SessionModel).filter_by(token_hash=token_hash).first()
        if session:
            db.delete(session)
            db.commit()
    finally:
        db.close()


@pytest.fixture
def expired_session(db_setup):
    """Fixture providing an expired session token"""
    token = SessionManager.create_session()
    token_hash = SessionManager._hash_token(token)
    
    # Expire it
    db = SessionLocal()
    try:
        session = db.query(SessionModel).filter_by(token_hash=token_hash).first()
        session.expires_at = datetime.utcnow() - timedelta(hours=1)
        db.commit()
    finally:
        db.close()
    
    yield token
    # No cleanup needed (expired sessions auto-delete)


class TestSessionManagerWithFixtures:
    """Additional tests using fixtures"""
    
    def test_valid_session_fixture(self, valid_session):
        """Test that valid_session fixture provides valid token"""
        assert SessionManager.validate_session(valid_session) is True
    
    def test_expired_session_fixture(self, expired_session):
        """Test that expired_session fixture provides expired token"""
        assert SessionManager.validate_session(expired_session) is False