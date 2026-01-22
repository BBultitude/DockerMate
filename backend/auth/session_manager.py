"""
Session Manager - Session Token Management

This module handles all session-related operations for DockerMate authentication.

Security Design:
- Session tokens: 256-bit cryptographically secure random
- Token hashing: SHA-256 before database storage
- Configurable expiry: 8 hours default, 7 days with "remember me"
- IP and user agent tracking for security auditing
- Automatic cleanup of expired sessions

Why Hash Session Tokens:
- If database is compromised, attacker can't use session tokens
- Similar to password hashing, but SHA-256 is sufficient (not bcrypt)
- Bcrypt is intentionally slow - not needed for sessions
- Fast validation is important for every request

Session Flow:
    1. User logs in → create_session()
    2. Generate random 256-bit token
    3. Hash with SHA-256
    4. Store hash in database
    5. Send plain token to browser (httpOnly cookie)
    6. On each request → validate_session()
    7. Hash incoming token, lookup in database
    8. If found and not expired → valid session

Usage:
    from backend.auth.session_manager import SessionManager
    from flask import request, make_response
    
    # After successful login
    session_token = SessionManager.create_session(
        remember_me=False,
        user_agent=request.headers.get('User-Agent'),
        ip_address=request.remote_addr
    )
    
    # Set cookie (httpOnly, secure, SameSite)
    response = make_response(redirect('/dashboard'))
    response.set_cookie('session', session_token, httponly=True, secure=True)
    
    # On each request
    token = request.cookies.get('session')
    if SessionManager.validate_session(token):
        # Valid session
        pass
    else:
        # Invalid or expired
        redirect('/login')

Verification:
    python3 -c "from backend.auth.session_manager import SessionManager; \
                token = SessionManager.create_session(); \
                print('Valid:', SessionManager.validate_session(token))"
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from backend.models.database import SessionLocal
from backend.models.session import Session as SessionModel

class SessionManager:
    """
    Session management for authentication
    
    Handles creation, validation, and cleanup of user sessions.
    All session tokens are hashed with SHA-256 before storage.
    
    Security Features:
    - 256-bit cryptographically secure tokens
    - SHA-256 hashing before storage
    - Configurable expiry times
    - IP and user agent tracking
    - Automatic cleanup
    
    Example:
        # Login flow
        @app.route('/login', methods=['POST'])
        def login():
            password = request.form.get('password')
            user = User.get_admin(db)
            
            if PasswordManager.verify_password(password, user.password_hash):
                # Create session
                session_token = SessionManager.create_session(
                    remember_me=request.form.get('remember_me') == 'on',
                    user_agent=request.headers.get('User-Agent'),
                    ip_address=request.remote_addr
                )
                
                # Set cookie
                response = make_response(redirect('/dashboard'))
                response.set_cookie(
                    'session',
                    session_token,
                    httponly=True,
                    secure=True,
                    samesite='Strict'
                )
                return response
        
        # Validation on each request
        @app.route('/api/containers')
        def containers():
            token = request.cookies.get('session')
            if not SessionManager.validate_session(token):
                return redirect('/login')
            
            # Valid session - continue
            return jsonify(containers)
    """
    
    # Session expiry times
    SESSION_EXPIRY_DEFAULT = timedelta(hours=8)
    SESSION_EXPIRY_REMEMBER = timedelta(days=7)
    
    # ==========================================================================
    # Session Creation
    # ==========================================================================
    
    @staticmethod
    def create_session(
        remember_me: bool = False,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> str:
        """
        Create new session after successful login
        
        Generates secure 256-bit random token, hashes it with SHA-256,
        stores hash in database, and returns plain token for cookie.
        
        Args:
            remember_me: If True, session lasts 7 days instead of 8 hours
            user_agent: Browser user agent string (for security auditing)
            ip_address: Client IP address (for security auditing)
            
        Returns:
            Plain session token (64 hex characters)
            Send this to browser as httpOnly cookie
            
        Example:
            # After password verification
            session_token = SessionManager.create_session(
                remember_me=True,
                user_agent='Mozilla/5.0 ...',
                ip_address='192.168.1.100'
            )
            
            # Set cookie
            response.set_cookie(
                'session',
                session_token,
                httponly=True,      # Not accessible via JavaScript
                secure=True,        # HTTPS only
                samesite='Strict',  # CSRF protection
                max_age=604800      # 7 days if remember_me
            )
            
        Security Note:
            The plain token is ONLY sent to the browser once.
            It's never stored in the database in plain form.
            Database only stores SHA-256 hash of the token.
        """
        # Generate secure random token (256 bits = 32 bytes = 64 hex chars)
        session_token = secrets.token_hex(32)
        
        # Set expiry based on remember_me
        if remember_me:
            expires_at = datetime.utcnow() + SessionManager.SESSION_EXPIRY_REMEMBER
        else:
            expires_at = datetime.utcnow() + SessionManager.SESSION_EXPIRY_DEFAULT
        
        # Hash token before storing (SHA-256)
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
        
        # Return plain token (send to browser)
        return session_token
    
    # ==========================================================================
    # Session Validation
    # ==========================================================================
    
    @staticmethod
    def validate_session(session_token: str) -> bool:
        """
        Validate session token
        
        Checks if token exists in database and is not expired.
        Updates last_accessed timestamp if valid.
        
        This should be called on EVERY authenticated request.
        
        Args:
            session_token: Plain session token from cookie
            
        Returns:
            True if valid and not expired, False otherwise
            
        Example:
            # Flask middleware or decorator
            @app.before_request
            def check_session():
                if request.path.startswith('/api/'):
                    token = request.cookies.get('session')
                    if not SessionManager.validate_session(token):
                        return redirect('/login')
            
            # Or manual check
            token = request.cookies.get('session')
            if SessionManager.validate_session(token):
                # Valid session - proceed
                return render_template('dashboard.html')
            else:
                # Invalid or expired
                return redirect('/login')
                
        Performance Note:
            This function is called on every request, so it needs to be fast.
            That's why we use SHA-256 (fast) instead of bcrypt (slow).
        """
        if not session_token:
            return False
        
        # Hash incoming token
        token_hash = SessionManager._hash_token(session_token)
        
        db = SessionLocal()
        try:
            # Find session by hash
            session = db.query(SessionModel).filter_by(token_hash=token_hash).first()
            
            if not session:
                return False
            
            # Check if expired
            if session.expires_at < datetime.utcnow():
                # Expired - delete it
                db.delete(session)
                db.commit()
                return False
            
            # Valid session - update last accessed
            session.last_accessed = datetime.utcnow()
            db.commit()
            
            return True
            
        except Exception:
            # Any error = invalid session
            return False
        finally:
            db.close()
    
    # ==========================================================================
    # Session Revocation
    # ==========================================================================
    
    @staticmethod
    def revoke_session(session_token: str) -> bool:
        """
        Revoke (delete) a specific session
        
        Used for logout. Removes session from database so token
        becomes invalid immediately.
        
        Args:
            session_token: Plain session token from cookie
            
        Returns:
            True if session was found and deleted, False otherwise
            
        Example:
            # Logout endpoint
            @app.route('/logout', methods=['POST'])
            def logout():
                token = request.cookies.get('session')
                SessionManager.revoke_session(token)
                
                # Clear cookie
                response = make_response(redirect('/login'))
                response.set_cookie('session', '', expires=0)
                return response
        """
        if not session_token:
            return False
        
        # Hash token
        token_hash = SessionManager._hash_token(session_token)
        
        db = SessionLocal()
        try:
            # Find and delete session
            session = db.query(SessionModel).filter_by(token_hash=token_hash).first()
            
            if session:
                db.delete(session)
                db.commit()
                return True
            
            return False
            
        finally:
            db.close()
    
    @staticmethod
    def revoke_all_sessions() -> int:
        """
        Revoke ALL sessions (force logout everywhere)
        
        Used when:
        - User changes password (security best practice)
        - Security incident detected
        - Admin wants to force re-login
        
        Returns:
            Number of sessions revoked
            
        Example:
            # After password change
            @app.route('/change-password', methods=['POST'])
            def change_password():
                # ... verify old password, set new password ...
                
                # Revoke all sessions (force re-login)
                revoked = SessionManager.revoke_all_sessions()
                
                flash(f"Password changed. {revoked} sessions revoked. Please login.")
                return redirect('/login')
        """
        db = SessionLocal()
        try:
            count = SessionModel.revoke_all_sessions(db)
            return count
        finally:
            db.close()
    
    # ==========================================================================
    # Session Information
    # ==========================================================================
    
    @staticmethod
    def get_session_info(session_token: str) -> Optional[Dict]:
        """
        Get information about a session
        
        Returns session details without validating expiry.
        Useful for displaying active sessions to user.
        
        Args:
            session_token: Plain session token from cookie
            
        Returns:
            Dictionary with session info, or None if not found
            
        Example:
            # Show current session info
            token = request.cookies.get('session')
            info = SessionManager.get_session_info(token)
            
            if info:
                print(f"Logged in from: {info['ip_address']}")
                print(f"Browser: {info['user_agent']}")
                print(f"Expires: {info['expires_at']}")
        """
        if not session_token:
            return None
        
        token_hash = SessionManager._hash_token(session_token)
        
        db = SessionLocal()
        try:
            session = db.query(SessionModel).filter_by(token_hash=token_hash).first()
            
            if session:
                return session.to_dict()
            
            return None
            
        finally:
            db.close()
    
    @staticmethod
    def get_active_sessions() -> List[Dict]:
        """
        Get all active (non-expired) sessions
        
        Useful for showing user all their active sessions
        so they can revoke suspicious ones.
        
        Returns:
            List of session dictionaries
            
        Example:
            # Show active sessions page
            @app.route('/sessions')
            @login_required
            def sessions_page():
                active = SessionManager.get_active_sessions()
                return render_template('sessions.html', sessions=active)
        """
        db = SessionLocal()
        try:
            sessions = SessionModel.get_active_sessions(db)
            return [s.to_dict() for s in sessions]
        finally:
            db.close()
    
    # ==========================================================================
    # Session Cleanup
    # ==========================================================================
    
    @staticmethod
    def cleanup_expired_sessions() -> int:
        """
        Delete all expired sessions from database
        
        Should be run periodically (e.g., daily via cron or scheduler)
        to keep database clean and small.
        
        Returns:
            Number of expired sessions deleted
            
        Example:
            # Run daily cleanup (in scheduler or cron)
            from apscheduler.schedulers.background import BackgroundScheduler
            
            scheduler = BackgroundScheduler()
            scheduler.add_job(
                SessionManager.cleanup_expired_sessions,
                'cron',
                hour=3  # Run at 3 AM daily
            )
            scheduler.start()
            
            # Or manual cleanup
            deleted = SessionManager.cleanup_expired_sessions()
            print(f"Cleaned up {deleted} expired sessions")
        """
        db = SessionLocal()
        try:
            count = SessionModel.cleanup_expired(db)
            return count
        finally:
            db.close()
    
    # ==========================================================================
    # Private Helper Functions
    # ==========================================================================
    
    @staticmethod
    def _hash_token(token: str) -> str:
        """
        Hash session token using SHA-256
        
        This is a private function - only used internally.
        Session tokens are hashed before storage for security.
        
        Args:
            token: Plain session token (64 hex chars)
            
        Returns:
            SHA-256 hash (64 hex chars)
            
        Why SHA-256 (not bcrypt):
        - Fast validation (called on every request)
        - Tokens are already high-entropy (256 bits random)
        - Bcrypt's slowness is unnecessary for random tokens
        - SHA-256 is still secure for this use case
        """
        return hashlib.sha256(token.encode()).hexdigest()
    
    # ==========================================================================
    # Statistics and Monitoring
    # ==========================================================================
    
    @staticmethod
    def get_session_stats() -> Dict:
        """
        Get session statistics
        
        Useful for monitoring and debugging.
        
        Returns:
            Dictionary with:
            - total_sessions: Total sessions in database
            - active_sessions: Non-expired sessions
            - expired_sessions: Expired sessions (should be cleaned)
            
        Example:
            stats = SessionManager.get_session_stats()
            print(f"Active sessions: {stats['active_sessions']}")
            
            if stats['expired_sessions'] > 100:
                print("Running cleanup...")
                SessionManager.cleanup_expired_sessions()
        """
        db = SessionLocal()
        try:
            total = db.query(SessionModel).count()
            active = SessionModel.count_active_sessions(db)
            expired = total - active
            
            return {
                'total_sessions': total,
                'active_sessions': active,
                'expired_sessions': expired
            }
        finally:
            db.close()

# =============================================================================
# Testing and Verification
# =============================================================================

if __name__ == "__main__":
    """
    Test the SessionManager when run directly
    
    Usage:
        python3 backend/auth/session_manager.py
    """
    from backend.models.database import init_db
    
    print("=" * 80)
    print("DockerMate Session Manager Test")
    print("=" * 80)
    
    # Initialize database
    print("\n1. Initializing database...")
    init_db()
    print("   ✅ Database initialized")
    
    # Test 2: Create session
    print("\n2. Creating session...")
    session_token = SessionManager.create_session(
        remember_me=False,
        user_agent='Test Browser 1.0',
        ip_address='192.168.1.100'
    )
    print(f"   Token: {session_token[:20]}... ({len(session_token)} chars)")
    print("   ✅ Session created")
    
    # Test 3: Validate session
    print("\n3. Validating session...")
    if SessionManager.validate_session(session_token):
        print("   ✅ Session is valid")
    else:
        print("   ❌ Session validation failed")
    
    # Test 4: Get session info
    print("\n4. Getting session info...")
    info = SessionManager.get_session_info(session_token)
    if info:
        print(f"   IP: {info['ip_address']}")
        print(f"   User Agent: {info['user_agent']}")
        print(f"   Expires: {info['expires_at']}")
        print("   ✅ Session info retrieved")
    else:
        print("   ❌ Failed to get session info")
    
    # Test 5: Session statistics
    print("\n5. Getting session statistics...")
    stats = SessionManager.get_session_stats()
    print(f"   Total sessions: {stats['total_sessions']}")
    print(f"   Active sessions: {stats['active_sessions']}")
    print(f"   Expired sessions: {stats['expired_sessions']}")
    print("   ✅ Statistics retrieved")
    
    # Test 6: Revoke session
    print("\n6. Revoking session (logout)...")
    if SessionManager.revoke_session(session_token):
        print("   ✅ Session revoked")
    else:
        print("   ❌ Failed to revoke session")
    
    # Test 7: Validate after revocation
    print("\n7. Validating after revocation...")
    if not SessionManager.validate_session(session_token):
        print("   ✅ Session correctly invalid after revocation")
    else:
        print("   ❌ Session still valid (BAD!)")
    
    print("\n" + "=" * 80)
    print("Session Manager test complete!")
    print("=" * 80)
