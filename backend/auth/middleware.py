"""
Authentication Middleware

This module provides Flask decorators and middleware for protecting routes
that require authentication. It makes it easy to add authentication to any
route with a simple @require_auth decorator.

Design Philosophy:
- Simple decorator-based approach (Pythonic)
- Clear error messages for debugging
- Automatic redirect to login for HTML routes
- JSON error responses for API routes
- Educational comments for learning

Usage Examples:

    # Protect a route (redirect to login if not authenticated)
    @app.route('/dashboard')
    @require_auth()
    def dashboard():
        return render_template('dashboard.html')
    
    # Protect an API route (return JSON error if not authenticated)
    @app.route('/api/containers')
    @require_auth(api=True)
    def list_containers():
        return jsonify({"containers": [...]})
    
    # Optional: Check auth without enforcing
    @app.route('/home')
    def home():
        if is_authenticated():
            return render_template('dashboard.html')
        else:
            return render_template('landing.html')

Security Notes:
- Session validation happens on every request
- Expired sessions are automatically cleaned up
- Invalid sessions result in redirect/error
- Session token never exposed to client JavaScript (httpOnly cookie)
"""

from functools import wraps
from flask import request, redirect, jsonify, url_for
from backend.auth.session_manager import SessionManager
import logging

logger = logging.getLogger(__name__)


def require_auth(api=False):
    """
    Decorator to require authentication for a route
    
    Args:
        api: If True, returns JSON error (for API routes)
             If False, redirects to login page (for HTML routes)
    
    Usage:
        @app.route('/dashboard')
        @require_auth()
        def dashboard():
            return render_template('dashboard.html')
        
        @app.route('/api/data')
        @require_auth(api=True)
        def get_data():
            return jsonify({"data": "..."})
    
    How it works:
    1. Extract session token from cookie
    2. Validate session using SessionManager
    3. If valid: allow request to proceed
    4. If invalid: redirect to login (HTML) or return 401 (API)
    
    Security:
    - Session validation includes expiry check
    - Expired sessions are automatically deleted
    - Last accessed timestamp is updated on valid sessions
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get session token from cookie (use 'auth_session' to avoid Flask session conflict)
            session_token = request.cookies.get('auth_session')

            # Validate session
            if not session_token or not SessionManager.validate_session(session_token):
                logger.warning(f"Unauthorized access attempt to {request.path} from {request.remote_addr}")

                # API routes return JSON error
                if api:
                    return jsonify({
                        "success": False,
                        "error": "Authentication required",
                        "redirect": "/login"
                    }), 401

                # HTML routes redirect to login
                else:
                    # Store original URL to redirect back after login
                    return redirect(url_for('login_page', next=request.url))

            # Session valid, proceed with request
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def is_authenticated():
    """
    Check if current request is authenticated (without enforcing)

    Returns:
        bool: True if valid session exists, False otherwise

    Usage:
        @app.route('/home')
        def home():
            if is_authenticated():
                return render_template('dashboard.html')
            else:
                return render_template('landing.html')

    Use Cases:
    - Conditional content based on auth status
    - Optional authentication
    - Custom handling of unauthenticated users

    Note: This does NOT protect the route. Use @require_auth for that.
    """
    session_token = request.cookies.get('auth_session')
    
    if not session_token:
        return False
    
    return SessionManager.validate_session(session_token)


def get_current_session_info():
    """
    Get information about the current session

    Returns:
        dict or None: Session info if authenticated, None otherwise
        {
            'id': 1,
            'expires_at': datetime,
            'last_accessed': datetime,
            'ip_address': '192.168.1.100',
            'user_agent': 'Mozilla/5.0...'
        }

    Usage:
        @app.route('/profile')
        @require_auth()
        def profile():
            session = get_current_session_info()
            return render_template('profile.html', session=session)

    Use Cases:
    - Display session info to user
    - Show "Last login" timestamp
    - Show "Session expires in X hours"
    - Security audit (show IP/user agent)
    """
    session_token = request.cookies.get('auth_session')
    
    if not session_token:
        return None
    
    return SessionManager.get_session_info(session_token)


def before_request_check():
    """
    Flask before_request handler for automatic session validation

    This can be registered globally to validate sessions on every request.
    Not required if using @require_auth decorator, but can be useful for
    automatic cleanup of expired sessions.

    Usage in app.py:
        from backend.auth.middleware import before_request_check

        @app.before_request
        def check_auth():
            return before_request_check()

    What it does:
    - Checks session validity on every request
    - Cleans up expired sessions automatically
    - Updates last_accessed timestamp
    - Does NOT enforce authentication (use @require_auth for that)

    Note: For home labs, this might be overkill. Use @require_auth on
    specific routes instead for simpler architecture.
    """
    session_token = request.cookies.get('auth_session')
    
    if session_token:
        # Validate and update session
        # This also cleans up expired sessions
        SessionManager.validate_session(session_token)
    
    # Always allow request to proceed
    # Individual routes use @require_auth to enforce
    return None
