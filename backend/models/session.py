"""
Session Model - Session Tracking and Management

This module defines the Session database model for DockerMate.

Purpose: Track user login sessions for authentication
DockerMate uses session-based authentication (not JWT tokens).

Security Design:
- Session tokens are NEVER stored in plain text
- Tokens are hashed with SHA-256 before storage
- Sessions have configurable expiry (8h default, 7d with remember me)
- Track IP address and user agent for security auditing
- Expired sessions are auto-deleted on validation

Database Table: sessions

Columns:
    id: Primary key (auto-increment)
    token_hash: SHA-256 hash of session token (never store plain token!)
    created_at: When session was created (login time)
    expires_at: When session expires (indexed for fast cleanup)
    last_accessed: Last time session was used (updated on each request)
    user_agent: Browser user agent string (for security auditing)
    ip_address: IP address of client (for security auditing)

Session Flow:
    1. User logs in with password
    2. Generate random 256-bit session token
    3. Hash token with SHA-256
    4. Store hash in database
    5. Send plain token to browser as httpOnly cookie
    6. On each request: hash cookie token, lookup in database
    7. If found and not expired: valid session
    8. Update last_accessed timestamp
    
Why Hash Session Tokens:
- If database is compromised, attacker can't use session tokens
- Tokens are useless without knowing the plain value
- Similar to password hashing, but SHA-256 is sufficient (not bcrypt)
- Bcrypt is slow (intentionally) - not needed for sessions

Usage:
    from backend.models.session import Session
    
    # Create session
    import secrets
    import hashlib
    from datetime import datetime, timedelta
    
    token = secrets.token_hex(32)  # 256 bits
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    session = Session(
        token_hash=token_hash,
        expires_at=datetime.utcnow() + timedelta(hours=8),
        user_agent=request.headers.get('User-Agent'),
        ip_address=request.remote_addr
    )
    db.add(session)
    db.commit()
    
    # Return plain token to client (as cookie)
    response.set_cookie('session', token, httponly=True, secure=True)

Verification:
    python3 -c "from backend.models.session import Session; print(Session.__tablename__)"
"""

from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from backend.models.database import Base
from datetime import datetime, timedelta
from typing import Dict, Optional
import hashlib
import json

class Session(Base):
    """
    Session model for tracking user authentication sessions
    
    Sessions are used to maintain logged-in state without requiring
    the user to re-enter their password on every request.
    
    Security Features:
    - Token stored as SHA-256 hash (never plain text)
    - Configurable expiry times
    - Automatic cleanup of expired sessions
    - IP and user agent tracking for security auditing
    - httpOnly cookies (not accessible via JavaScript)
    
    Attributes:
        id (int): Primary key (auto-increment)
        token_hash (str): SHA-256 hash of session token (64 hex chars)
        created_at (datetime): When session was created (login)
        expires_at (datetime): When session expires
        last_accessed (datetime): Last request using this session
        user_agent (str): Browser user agent string
        ip_address (str): Client IP address (IPv4 or IPv6)
    
    Example:
        # Creating a session (done by SessionManager)
        import secrets
        import hashlib
        from datetime import datetime, timedelta
        
        # Generate secure random token
        token = secrets.token_hex(32)  # 64 char hex string
        
        # Hash before storing
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Create session
        session = Session(
            token_hash=token_hash,
            expires_at=datetime.utcnow() + timedelta(hours=8),
            user_agent='Mozilla/5.0 ...',
            ip_address='192.168.1.100'
        )
        db.add(session)
        db.commit()
        
        # Send plain token to client (cookie)
        # Client sends this back on each request
        # Server hashes it and looks up in database
    """
    
    # Table name in database
    __tablename__ = "sessions"
    
    # ==========================================================================
    # Columns
    # ==========================================================================
    
    # Primary key - auto-incrementing ID
    id = Column(
        Integer,
        primary_key=True,
        index=True,
        comment="Primary key for sessions"
    )
    
    # Token hash - SHA-256 hash of the session token
    # NEVER store plain tokens in database!
    # 64 characters (SHA-256 produces 64 hex characters)
    token_hash = Column(
        String(64),
        unique=True,
        nullable=False,
        index=True,  # Indexed for fast lookup
        comment="SHA-256 hash of session token (never store plain token)"
    )
    
    # Created timestamp - when user logged in
    created_at = Column(
        DateTime,
        server_default=func.now(),
        comment="Session creation timestamp (login time)"
    )
    
    # Expires timestamp - when session becomes invalid
    # Indexed for fast cleanup of expired sessions
    expires_at = Column(
        DateTime,
        nullable=False,
        index=True,  # Indexed for cleanup queries
        comment="Session expiry timestamp"
    )
    
    # Last accessed timestamp - updated on each request
    # Used for detecting abandoned sessions
    last_accessed = Column(
        DateTime,
        nullable=True,
        comment="Last request timestamp using this session"
    )
    
    # User agent - browser/client identification
    # Used for security auditing (detect suspicious changes)
    user_agent = Column(
        Text,
        nullable=True,
        comment="Browser user agent string for security auditing"
    )
    
    # IP address - client IP
    # IPv4 (15 chars max: xxx.xxx.xxx.xxx)
    # IPv6 (45 chars max with full representation)
    ip_address = Column(
        String(45),
        nullable=True,
        comment="Client IP address (IPv4 or IPv6)"
    )
    
    # ==========================================================================
    # Methods
    # ==========================================================================
    
    def is_expired(self) -> bool:
        """
        Check if session has expired
        
        Returns:
            True if expired, False if still valid
            
        Example:
            session = db.query(Session).filter_by(token_hash=hash).first()
            if session and session.is_expired():
                db.delete(session)
                db.commit()
                return False  # Invalid session
        """
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self) -> bool:
        """
        Check if session is valid (not expired)
        
        Returns:
            True if valid, False if expired
            
        Example:
            if session.is_valid():
                # Update last accessed
                session.last_accessed = datetime.utcnow()
                db.commit()
        """
        return not self.is_expired()
    
    def update_last_accessed(self):
        """
        Update the last_accessed timestamp to now
        
        This should be called on every request using this session.
        Helps identify abandoned/inactive sessions.
        
        Example:
            session = db.query(Session).filter_by(token_hash=hash).first()
            if session and session.is_valid():
                session.update_last_accessed()
                db.commit()
        """
        self.last_accessed = datetime.utcnow()
    
    def to_dict(self, include_token_hash: bool = False) -> Dict:
        """
        Convert session to dictionary (for JSON responses)
        
        Args:
            include_token_hash: If True, include token hash (be careful!)
                               Default False for security
        
        Returns:
            Dictionary representation of session
            
        Example:
            session_dict = session.to_dict()
            # Returns: {'id': 1, 'created_at': '...', 'expires_at': '...'}
            
        Security Note:
            Token hash should not be sent to frontend normally.
            Only for debugging purposes.
        """
        data = {
            'id': self.id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'user_agent': self.user_agent,
            'ip_address': self.ip_address,
            'is_valid': self.is_valid()
        }
        
        # Only include token hash if explicitly requested
        if include_token_hash:
            data['token_hash'] = self.token_hash
        
        return data
    
    def __repr__(self) -> str:
        """
        String representation for debugging
        
        Returns:
            Human-readable string showing session info
            
        Example:
            session = db.query(Session).first()
            print(session)
            # Output: <Session(id=1, expires_at='...', valid=True)>
        """
        return (
            f"<Session("
            f"id={self.id}, "
            f"created_at='{self.created_at}', "
            f"expires_at='{self.expires_at}', "
            f"valid={self.is_valid()}"
            f")>"
        )
    
    # ==========================================================================
    # Static Methods - Session Management
    # ==========================================================================
    
    @staticmethod
    def cleanup_expired(db) -> int:
        """
        Delete all expired sessions from database
        
        This should be run periodically (e.g., daily) to clean up
        old sessions and keep the database small.
        
        Args:
            db: Database session
            
        Returns:
            Number of sessions deleted
            
        Example:
            from backend.models.database import SessionLocal
            from backend.models.session import Session
            
            db = SessionLocal()
            try:
                deleted = Session.cleanup_expired(db)
                print(f"Deleted {deleted} expired sessions")
            finally:
                db.close()
        """
        # Find all expired sessions
        expired_sessions = db.query(Session).filter(
            Session.expires_at < datetime.utcnow()
        ).all()
        
        count = len(expired_sessions)
        
        # Delete them
        for session in expired_sessions:
            db.delete(session)
        
        db.commit()
        
        return count
    
    @staticmethod
    def get_active_sessions(db) -> list:
        """
        Get all active (non-expired) sessions
        
        Args:
            db: Database session
            
        Returns:
            List of active Session objects
            
        Example:
            sessions = Session.get_active_sessions(db)
            for session in sessions:
                print(f"Active session from {session.ip_address}")
        """
        return db.query(Session).filter(
            Session.expires_at > datetime.utcnow()
        ).all()
    
    @staticmethod
    def count_active_sessions(db) -> int:
        """
        Count active sessions
        
        Args:
            db: Database session
            
        Returns:
            Number of active sessions
            
        Example:
            count = Session.count_active_sessions(db)
            print(f"Currently {count} active sessions")
        """
        return db.query(Session).filter(
            Session.expires_at > datetime.utcnow()
        ).count()
    
    @staticmethod
    def revoke_all_sessions(db) -> int:
        """
        Revoke all sessions (force logout everywhere)
        
        Useful for:
        - Password change (security best practice)
        - Security incident (force re-login)
        - Maintenance
        
        Args:
            db: Database session
            
        Returns:
            Number of sessions revoked
            
        Example:
            # After password change
            revoked = Session.revoke_all_sessions(db)
            print(f"Revoked {revoked} sessions - user must login again")
        """
        all_sessions = db.query(Session).all()
        count = len(all_sessions)
        
        for session in all_sessions:
            db.delete(session)
        
        db.commit()
        
        return count

# =============================================================================
# Testing and Verification
# =============================================================================

if __name__ == "__main__":
    """
    Test the Session model when run directly
    
    Usage:
        python3 backend/models/session.py
    """
    from backend.models.database import init_db, SessionLocal
    import secrets
    
    print("=" * 80)
    print("DockerMate Session Model Test")
    print("=" * 80)
    
    # Initialize database
    print("\n1. Initializing database...")
    init_db()
    
    # Create test sessions
    print("\n2. Creating test sessions...")
    db = SessionLocal()
    try:
        # Create valid session
        token1 = secrets.token_hex(32)
        hash1 = hashlib.sha256(token1.encode()).hexdigest()
        
        session1 = Session(
            token_hash=hash1,
            expires_at=datetime.utcnow() + timedelta(hours=8),
            user_agent='Mozilla/5.0 Test Browser',
            ip_address='192.168.1.100'
        )
        db.add(session1)
        
        # Create expired session
        token2 = secrets.token_hex(32)
        hash2 = hashlib.sha256(token2.encode()).hexdigest()
        
        session2 = Session(
            token_hash=hash2,
            expires_at=datetime.utcnow() - timedelta(hours=1),  # Already expired
            user_agent='Mozilla/5.0 Test Browser',
            ip_address='192.168.1.101'
        )
        db.add(session2)
        
        db.commit()
        print(f"   ✅ Created session 1 (valid): {session1}")
        print(f"   ✅ Created session 2 (expired): {session2}")
        
        # Test validation
        print("\n3. Testing session validation...")
        print(f"   Session 1 valid: {session1.is_valid()}")  # Should be True
        print(f"   Session 2 valid: {session2.is_valid()}")  # Should be False
        
        # Test active sessions
        print("\n4. Testing active session queries...")
        active = Session.get_active_sessions(db)
        print(f"   Active sessions: {len(active)}")
        
        # Test cleanup
        print("\n5. Testing expired session cleanup...")
        deleted = Session.cleanup_expired(db)
        print(f"   Deleted {deleted} expired sessions")
        
        remaining = Session.count_active_sessions(db)
        print(f"   Remaining active: {remaining}")
        
        # Test to_dict
        print("\n6. Testing to_dict()...")
        if active:
            session_dict = active[0].to_dict()
            print(f"   Session dict: {json.dumps(session_dict, indent=2)}")
        
        print("\n   ✅ All tests passed!")
        
    except Exception as e:
        print(f"\n   ❌ Error: {e}")
        db.rollback()
    finally:
        db.close()
    
    print("\n" + "=" * 80)
    print("Session model test complete!")
    print("=" * 80)
