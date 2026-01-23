"""
Authentication Package

This package contains all authentication-related modules for DockerMate.

Modules:
    password_manager: Bcrypt password hashing and validation
    session_manager: Session token creation and validation
    middleware: Flask route protection and authentication checks

Usage:
    # Import password functions
    from backend.auth.password_manager import PasswordManager
    
    # Import session functions
    from backend.auth.session_manager import SessionManager
    
    # Import middleware
    from backend.auth.middleware import require_auth, is_authenticated
    
    # Or import everything
    from backend.auth import PasswordManager, SessionManager, require_auth

Example - Complete Login Flow:
    from backend.auth import PasswordManager, SessionManager, require_auth
    from flask import Flask, request, make_response, redirect
    
    app = Flask(__name__)
    
    @app.route('/login', methods=['POST'])
    def login():
        password = request.form.get('password')
        user = User.get_admin(db)
        
        # Verify password
        if PasswordManager.verify_password(password, user.password_hash):
            # Create session
            session_token = SessionManager.create_session(
                remember_me=request.form.get('remember_me') == 'on',
                user_agent=request.headers.get('User-Agent'),
                ip_address=request.remote_addr
            )
            
            # Set cookie
            response = make_response(redirect('/dashboard'))
            response.set_cookie('session', session_token, httponly=True, secure=True)
            return response
        else:
            return "Invalid password", 401
    
    @app.route('/dashboard')
    @require_auth()
    def dashboard():
        return "Welcome to dashboard!"
"""

# Import main classes
from backend.auth.password_manager import PasswordManager
from backend.auth.session_manager import SessionManager
from backend.auth.middleware import (
    require_auth,
    is_authenticated,
    get_current_session_info
)

# Public API
__all__ = [
    # Password management
    'PasswordManager',
    
    # Session management
    'SessionManager',
    
    # Middleware
    'require_auth',
    'is_authenticated',
    'get_current_session_info',
]
