"""
Unit tests for Session Manager

Tests session creation and validation.
Note: Cleanup functions not implemented in Sprint 1

Run with: pytest tests/unit/test_session_manager.py -v
"""

import pytest
from datetime import datetime, timedelta
from backend.auth.session_manager import SessionManager
from backend.models.database import SessionLocal
from backend.models.session import Session as SessionModel


class TestSessionCreation:
    """Test session creation"""
    
    def test_create_session_returns_token(self):
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
    
    def test_create_session_stores_in_database(self):
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
    
    def test_create_session_default_expiry(self):
        """Test that default session expiry is 8 hours"""
        token = SessionManager.create_session()
        token_hash = SessionManager._hash_token(token)
        
        db = SessionLocal()
        try:
            session = db.query(SessionModel).filter_by(token_hash=token_hash).first()
            
            # Expiry should be ~8 hours from now
            expected_expiry = datetime.utcnow() + timedelta(hours=8)
            time_diff = abs((session.expires_at - expected_expiry).total_seconds())
            
            # Allow 10 second tolerance
            assert time_diff < 10
        finally:
            if session:
                db.delete(session)
                db.commit()
            db.close()
    
    def test_create_session_remember_me_expiry(self):
        """Test that remember_me sets 7 day expiry"""
        token = SessionManager.create_session(remember_me=True)
        token_hash = SessionManager._hash_token(token)
        
        db = SessionLocal()
        try:
            session = db.query(SessionModel).filter_by(token_hash=token_hash).first()
            
            # Expiry should be ~7 days from now
            expected_expiry = datetime.utcnow() + timedelta(days=7)
            time_diff = abs((session.expires_at - expected_expiry).total_seconds())
            
            # Allow 10 second tolerance
            assert time_diff < 10
        finally:
            if session:
                db.delete(session)
                db.commit()
            db.close()
    
    def test_create_session_stores_metadata(self):
        """Test that user agent and IP are stored"""
        token = SessionManager.create_session(
            user_agent="TestBrowser/1.0",
            ip_address="192.168.1.100"
        )
        token_hash = SessionManager._hash_token(token)
        
        db = SessionLocal()
        try:
            session = db.query(SessionModel).filter_by(token_hash=token_hash).first()
            
            assert session.user_agent == "TestBrowser/1.0"
            assert session.ip_address == "192.168.1.100"
        finally:
            if session:
                db.delete(session)
                db.commit()
            db.close()


class TestSessionValidation:
    """Test session validation"""
    
    def test_validate_valid_session(self):
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
    
    def test_validate_invalid_token_format(self):
        """Test that invalid token format fails"""
        assert SessionManager.validate_session("invalid") is False
        assert SessionManager.validate_session("") is False
        assert SessionManager.validate_session(None) is False
    
    def test_validate_nonexistent_session(self):
        """Test that nonexistent session fails validation"""
        fake_token = "0" * 64  # Valid format but doesn't exist
        
        assert SessionManager.validate_session(fake_token) is False
    
    def test_validate_expired_session(self):
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
        
        # Should be deleted from database
        db = SessionLocal()
        try:
            session = db.query(SessionModel).filter_by(token_hash=token_hash).first()
            assert session is None
        finally:
            db.close()
    
    def test_validate_updates_last_accessed(self):
        """Test that validation updates last_accessed timestamp"""
        token = SessionManager.create_session()
        token_hash = SessionManager._hash_token(token)
        
        # Wait a moment
        import time
        time.sleep(0.1)
        
        # Validate
        SessionManager.validate_session(token)
        
        # Check last_accessed was updated
        db = SessionLocal()
        try:
            session = db.query(SessionModel).filter_by(token_hash=token_hash).first()
            assert session.last_accessed is not None
            
            # Should be very recent (within last second)
            time_diff = (datetime.utcnow() - session.last_accessed).total_seconds()
            assert time_diff < 1
        finally:
            if session:
                db.delete(session)
                db.commit()
            db.close()


class TestTokenHashing:
    """Test token hashing functionality"""
    
    def test_hash_token_consistent(self):
        """Test that hashing same token produces same hash"""
        token = "test_token_123"
        hash1 = SessionManager._hash_token(token)
        hash2 = SessionManager._hash_token(token)
        
        assert hash1 == hash2
    
    def test_hash_token_format(self):
        """Test that token hash is SHA-256 hex (64 chars)"""
        token = "test_token_123"
        token_hash = SessionManager._hash_token(token)
        
        # SHA-256 hash is 64 hex characters
        assert len(token_hash) == 64
        assert all(c in '0123456789abcdef' for c in token_hash)
    
    def test_hash_different_tokens_different_hashes(self):
        """Test that different tokens produce different hashes"""
        hash1 = SessionManager._hash_token("token1")
        hash2 = SessionManager._hash_token("token2")
        
        assert hash1 != hash2


# Pytest fixtures
@pytest.fixture
def valid_session():
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
def expired_session():
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
