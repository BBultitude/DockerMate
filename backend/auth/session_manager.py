"""
Session Management

This module handles user session creation, validation, and revocation.
Sessions are used to keep users logged in after successful authentication.

Design Philosophy:
- Single-user home lab (only one user account)
- Session tokens are cryptographically secure (256-bit)
- Tokens are hashed before storage (SHA-256)
- Configurable expiry times
- IP and User-Agent tracking for security

Security Notes:
- Never store plain session tokens in database
- Always hash tokens before storage
- Clean up expired sessions automatically
- Track IP and User-Agent for audit trail
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from backend.models.database import SessionLocal
from backend.models.session import Session as SessionModel


class SessionManager:
    """Session management for single-user home lab"""
    
    SESSION_EXPIRY_DEFAULT = timedelta(hours=8)
    SESSION_EXPIRY_REMEMBER = timedelta(days=7)
    
    @staticmethod
    def create_session(remember_me: bool = False, 
                      user_agent: Optional[str] = None,
                      ip_address: Optional[str] = None) -> str:
        """
        Create new session after successful login
        
        Returns: session token (64 char hex)
        """
        # Generate secure token
        session_token = secrets.token_hex(32)  # 256 bits
        
        # Set expiry
        if remember_me:
            expires_at = datetime.utcnow() + SessionManager.SESSION_EXPIRY_REMEMBER
        else:
            expires_at = datetime.utcnow() + SessionManager.SESSION_EXPIRY_DEFAULT
        
        # Hash token before storing
        token_hash = SessionManager._hash_token(session_token)
        
        # Store in database
        db = SessionLocal()
        try:
            session = SessionModel(
                token_hash=token_hash,
                expires_at=expires_at,
                user_agent=user_agent,
                ip_address=ip_address
            )
            db.add(session)
            db.commit()
        finally:
            db.close()
        
        return session_token
    
    @staticmethod
    def validate_session(session_token: str) -> bool:
        """Validate session token"""
        if not session_token:
            return False
        
        token_hash = SessionManager._hash_token(session_token)
        
        db = SessionLocal()
        try:
            session = db.query(SessionModel).filter_by(token_hash=token_hash).first()
            
            if not session:
                return False
            
            # Check expiry
            if session.expires_at < datetime.utcnow():
                db.delete(session)
                db.commit()
                return False
            
            # Update last accessed
            session.last_accessed = datetime.utcnow()
            db.commit()
            
            return True
        finally:
            db.close()
    
    @staticmethod
    def revoke_session(session_token: str):
        """Revoke a session token"""
        if not session_token:
            return
        
        token_hash = SessionManager._hash_token(session_token)
        
        db = SessionLocal()
        try:
            session = db.query(SessionModel).filter_by(token_hash=token_hash).first()
            if session:
                db.delete(session)
                db.commit()
        finally:
            db.close()
    
    @staticmethod
    def _hash_token(token: str) -> str:
        """Hash token using SHA-256"""
        return hashlib.sha256(token.encode()).hexdigest()
    
    # ========================================
    # NEW METHODS ADDED FOR TASK 7
    # ========================================
    
    @staticmethod
    def get_session_info(session_token: str) -> Optional[dict]:
        """
        Get session information without modifying it
        
        Args:
            session_token: Session token from cookie
            
        Returns:
            dict with session info or None if not found/expired
            {
                'id': 1,
                'expires_at': datetime,
                'last_accessed': datetime,
                'ip_address': '192.168.1.100',
                'user_agent': 'Mozilla/5.0...'
            }
        
        Use Cases:
        - Display session info to user
        - Check expiry time
        - Security audit
        
        Verification:
        token = SessionManager.create_session()
        info = SessionManager.get_session_info(token)
        print(info)
        """
        if not session_token:
            return None
        
        token_hash = SessionManager._hash_token(session_token)
        
        db = SessionLocal()
        try:
            session = db.query(SessionModel).filter_by(token_hash=token_hash).first()
            
            if not session:
                return None
            
            # Check if expired
            if session.expires_at < datetime.utcnow():
                return None
            
            return {
                'id': session.id,
                'expires_at': session.expires_at,
                'last_accessed': session.last_accessed,
                'ip_address': session.ip_address,
                'user_agent': session.user_agent
            }
        finally:
            db.close()
    
    @staticmethod
    def get_session_id(session_token: str) -> Optional[int]:
        """
        Get session database ID from token
        
        Args:
            session_token: Session token from cookie
            
        Returns:
            int: Session ID or None if not found
        
        Use Cases:
        - Check if session is current session
        - Prevent revoking current session
        
        Verification:
        token = SessionManager.create_session()
        session_id = SessionManager.get_session_id(token)
        print(f"Session ID: {session_id}")
        """
        info = SessionManager.get_session_info(session_token)
        return info['id'] if info else None
    
    @staticmethod
    def get_all_sessions(current_token: str) -> list:
        """
        Get all active sessions
        
        Args:
            current_token: Current session token (to mark as current)
            
        Returns:
            List of session dictionaries:
            [
                {
                    'id': 1,
                    'created_at': '2026-01-23T10:00:00',
                    'expires_at': '2026-01-23T18:00:00',
                    'last_accessed': '2026-01-23T10:30:00',
                    'ip_address': '192.168.1.100',
                    'user_agent': 'Mozilla/5.0...',
                    'current': True
                }
            ]
        
        Use Cases:
        - Show user all logged-in devices
        - Security audit
        - Revoke old/suspicious sessions
        
        Verification:
        token = SessionManager.create_session()
        sessions = SessionManager.get_all_sessions(token)
        for s in sessions:
            print(f"Session {s['id']}: {s['ip_address']} (current: {s['current']})")
        """
        current_hash = SessionManager._hash_token(current_token)
        
        db = SessionLocal()
        try:
            # Get only non-expired sessions
            sessions = db.query(SessionModel).filter(
                SessionModel.expires_at > datetime.utcnow()
            ).order_by(SessionModel.created_at.desc()).all()
            
            result = []
            for session in sessions:
                result.append({
                    'id': session.id,
                    'created_at': session.created_at.isoformat(),
                    'expires_at': session.expires_at.isoformat(),
                    'last_accessed': session.last_accessed.isoformat() if session.last_accessed else None,
                    'ip_address': session.ip_address,
                    'user_agent': session.user_agent,
                    'current': session.token_hash == current_hash
                })
            
            return result
        finally:
            db.close()
    
    @staticmethod
    def revoke_session_by_id(session_id: int) -> bool:
        """
        Revoke session by database ID
        
        Args:
            session_id: Database ID of session to revoke
            
        Returns:
            bool: True if revoked, False if not found
        
        Use Cases:
        - Revoke session from lost/stolen device
        - Security cleanup
        - Manual session management
        
        Security:
        - Should check this isn't current session before calling
        - Prevents accidental logout
        
        Verification:
        token = SessionManager.create_session()
        session_id = SessionManager.get_session_id(token)
        # Don't revoke current session in real code!
        # success = SessionManager.revoke_session_by_id(session_id)
        """
        db = SessionLocal()
        try:
            session = db.query(SessionModel).filter_by(id=session_id).first()
            
            if not session:
                return False
            
            db.delete(session)
            db.commit()
            return True
        finally:
            db.close()
    
    @staticmethod
    def revoke_all_sessions_except(keep_token: str):
        """
        Revoke all sessions except the specified one
        
        Args:
            keep_token: Session token to keep active
            
        Use Cases:
        - After password change (security best practice)
        - Force re-login on all other devices
        - Security incident response
        
        Security:
        - Keeps current session active
        - User doesn't get logged out unexpectedly
        - All other devices must re-authenticate
        
        Verification:
        # Create multiple sessions
        token1 = SessionManager.create_session()
        token2 = SessionManager.create_session()
        token3 = SessionManager.create_session()
        
        # Revoke all except token1
        SessionManager.revoke_all_sessions_except(token1)
        
        # Verify: token1 valid, token2 and token3 invalid
        print(SessionManager.validate_session(token1))  # True
        print(SessionManager.validate_session(token2))  # False
        print(SessionManager.validate_session(token3))  # False
        """
        keep_hash = SessionManager._hash_token(keep_token)
        
        db = SessionLocal()
        try:
            # Delete all sessions except the one we want to keep
            db.query(SessionModel).filter(
                SessionModel.token_hash != keep_hash
            ).delete()
            db.commit()
        finally:
            db.close()
