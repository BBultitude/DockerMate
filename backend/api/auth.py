"""
Authentication API Endpoints

This module provides REST API endpoints for user authentication in DockerMate.
Since DockerMate is designed for single-user home labs, there's only one user
account, but we still implement secure session-based authentication.

Endpoints:
- POST   /api/auth/login           - Login with password
- POST   /api/auth/logout          - Logout and revoke session
- GET    /api/auth/session         - Check if session is valid
- POST   /api/auth/change-password - Change password
- GET    /api/auth/sessions        - List all active sessions
- DELETE /api/auth/sessions/{id}   - Revoke specific session

Security Features:
- bcrypt password hashing (never store plain passwords)
- SHA-256 session token hashing (never store plain tokens)
- httpOnly cookies (prevent JavaScript access)
- Secure flag (HTTPS only)
- SameSite=Strict (CSRF protection)
- Rate limiting on login attempts

Design Philosophy:
- Single-user home lab focus (no multi-user complexity)
- Simple password auth (no LDAP/SAML enterprise bloat)
- Clear error messages for troubleshooting
- Educational comments for learning
"""

from flask import Blueprint, request, jsonify, make_response, redirect
from backend.models.database import SessionLocal
from backend.models.user import User
from backend.models.session import Session as SessionModel
from backend.auth.password_manager import PasswordManager
from backend.auth.session_manager import SessionManager
from backend.extensions import limiter
from datetime import datetime
import logging

# Create blueprint for authentication routes
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# Set up logging
logger = logging.getLogger(__name__)


@auth_bp.route('/login', methods=['POST'])
@limiter.limit("5 per 15 minutes")
def login():
    """
    Login endpoint - authenticate user and create session
    
    POST /api/auth/login
    Content-Type: application/json
    
    Request Body:
    {
        "password": "user's password",
        "remember_me": false  # optional, default false
    }
    
    Success Response (200):
    {
        "success": true,
        "message": "Login successful",
        "redirect": "/dashboard",
        "force_password_change": false
    }
    Sets cookie: session=<token>; HttpOnly; Secure; SameSite=Strict
    
    Error Responses:
    - 400: Missing password
    - 401: Invalid password
    - 500: Server error
    
    Security Notes:
    - Password is verified using bcrypt (slow on purpose to prevent brute force)
    - Session token is 256-bit cryptographically secure random
    - Token is hashed (SHA-256) before storing in database
    - Cookie is httpOnly (JavaScript cannot access)
    - Cookie is Secure (HTTPS only)
    - Cookie is SameSite=Strict (CSRF protection)
    
    Rate Limiting:
    - Should implement rate limiting in production
    - For home labs, not critical (trusted network)
    
    Verification:
    curl -k -X POST https://localhost:5000/api/auth/login \
         -H "Content-Type: application/json" \
         -d '{"password":"YourPassword123"}'
    """
    try:
        # Get JSON data from request
        data = request.get_json()
        
        if not data:
            logger.warning("Login attempt with no JSON body")
            return jsonify({
                "success": False,
                "error": "Request must be JSON"
            }), 400
        
        password = data.get('password')
        remember_me = data.get('remember_me', False)
        
        # Validate password field exists
        if not password:
            logger.warning("Login attempt with missing password field")
            return jsonify({
                "success": False,
                "error": "Password is required"
            }), 400
        
        # Get the single user from database
        db = SessionLocal()
        try:
            user = db.query(User).first()
            
            # Check if setup is complete
            if not user:
                logger.error("Login attempt but no user exists - setup not complete")
                return jsonify({
                    "success": False,
                    "error": "Setup not complete. Please complete initial setup.",
                    "redirect": "/setup"
                }), 400
            
            # Verify password using bcrypt
            # This is intentionally slow (bcrypt work factor 12) to prevent brute force
            if not PasswordManager.verify_password(password, user.password_hash):
                logger.warning(f"Failed login attempt from {request.remote_addr}")
                return jsonify({
                    "success": False,
                    "error": "Invalid password"
                }), 401
            
            # Password verified! Create session
            logger.info(f"Successful login from {request.remote_addr}")
            
            session_token = SessionManager.create_session(
                remember_me=remember_me,
                user_agent=request.headers.get('User-Agent'),
                ip_address=request.remote_addr
            )
            
            # Prepare response
            response_data = {
                "success": True,
                "message": "Login successful",
                "redirect": "/dashboard",
                "force_password_change": user.force_password_change
            }
            
            # If password change is forced, redirect to password change
            if user.force_password_change:
                response_data["redirect"] = "/change-password"
                response_data["message"] = "Please change your password"
            
            response = make_response(jsonify(response_data))
            
            # Set secure session cookie
            # httpOnly: JavaScript cannot access (XSS protection)
            # secure: HTTPS only (no plain HTTP)
            # samesite: Strict CSRF protection
            max_age = 604800 if remember_me else 28800  # 7 days or 8 hours
            
            response.set_cookie(
                'session',
                session_token,
                httponly=True,
                secure=True,  # HTTPS only
                samesite='Strict',
                max_age=max_age
            )
            
            return response
            
        finally:
            db.close()
    
    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Internal server error"
        }), 500


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """
    Logout endpoint - revoke session and clear cookie
    
    POST /api/auth/logout
    
    Success Response (200):
    {
        "success": true,
        "message": "Logged out successfully",
        "redirect": "/login"
    }
    Clears cookie: session
    
    Notes:
    - Revokes session in database (token becomes invalid)
    - Clears session cookie
    - Safe to call even if not logged in
    
    Verification:
    curl -k -X POST https://localhost:5000/api/auth/logout \
         --cookie "session=<your-token>"
    """
    try:
        # Get session token from cookie
        session_token = request.cookies.get('session')
        
        # Revoke session if exists
        if session_token:
            SessionManager.revoke_session(session_token)
            logger.info(f"User logged out from {request.remote_addr}")
        
        # Prepare response
        response = make_response(jsonify({
            "success": True,
            "message": "Logged out successfully",
            "redirect": "/login"
        }))
        
        # Clear session cookie by setting it to expire immediately
        response.set_cookie('session', '', expires=0)
        
        return response
    
    except Exception as e:
        logger.error(f"Logout error: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Internal server error"
        }), 500


@auth_bp.route('/session', methods=['GET'])
def check_session():
    """
    Check if current session is valid
    
    GET /api/auth/session
    
    Success Response (200):
    {
        "valid": true,
        "expires_at": "2026-01-23T12:00:00Z",
        "last_accessed": "2026-01-23T10:30:00Z"
    }
    
    Invalid Session Response (401):
    {
        "valid": false,
        "error": "Session expired or invalid"
    }
    
    Use Cases:
    - Frontend checks if user is still logged in
    - Periodic session validation
    - Determining if redirect to login is needed
    
    Verification:
    curl -k https://localhost:5000/api/auth/session \
         --cookie "session=<your-token>"
    """
    try:
        session_token = request.cookies.get('session')
        
        if not session_token:
            return jsonify({
                "valid": False,
                "error": "No session token"
            }), 401
        
        # Validate session and get details
        session_info = SessionManager.get_session_info(session_token)
        
        if session_info:
            return jsonify({
                "valid": True,
                "expires_at": session_info['expires_at'].isoformat(),
                "last_accessed": session_info['last_accessed'].isoformat() if session_info['last_accessed'] else None
            })
        else:
            return jsonify({
                "valid": False,
                "error": "Session expired or invalid"
            }), 401
    
    except Exception as e:
        logger.error(f"Session check error: {str(e)}", exc_info=True)
        return jsonify({
            "valid": False,
            "error": "Internal server error"
        }), 500


@auth_bp.route('/change-password', methods=['POST'])
def change_password():
    """
    Change password endpoint
    
    POST /api/auth/change-password
    Content-Type: application/json
    
    Request Body:
    {
        "current_password": "old password",
        "new_password": "new password",
        "confirm_password": "new password again"
    }
    
    Success Response (200):
    {
        "success": true,
        "message": "Password changed successfully"
    }
    
    Error Responses:
    - 400: Validation errors (passwords don't match, weak password)
    - 401: Current password incorrect or not logged in
    - 500: Server error
    
    Password Requirements:
    - Minimum 12 characters
    - Must contain uppercase letter
    - Must contain lowercase letter
    - Must contain digit
    - Special characters recommended
    
    Security Notes:
    - Requires valid session (must be logged in)
    - Verifies current password before changing
    - Validates new password strength
    - Revokes all other sessions after password change (security best practice)
    
    Verification:
    curl -k -X POST https://localhost:5000/api/auth/change-password \
         -H "Content-Type: application/json" \
         --cookie "session=<your-token>" \
         -d '{"current_password":"Old123","new_password":"New123456789","confirm_password":"New123456789"}'
    """
    try:
        # Require authentication
        session_token = request.cookies.get('session')
        if not SessionManager.validate_session(session_token):
            return jsonify({
                "success": False,
                "error": "Not authenticated"
            }), 401
        
        # Get request data
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "Request must be JSON"
            }), 400
        
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')
        
        # Validate all fields present
        if not all([current_password, new_password, confirm_password]):
            return jsonify({
                "success": False,
                "error": "All fields required: current_password, new_password, confirm_password"
            }), 400
        
        # Validate passwords match
        if new_password != confirm_password:
            return jsonify({
                "success": False,
                "error": "New passwords do not match"
            }), 400
        
        # Validate new password strength
        strength_check = PasswordManager.validate_password_strength(new_password)
        if not strength_check['valid']:
            return jsonify({
                "success": False,
                "error": "Password does not meet requirements",
                "issues": strength_check['issues'],
                "suggestions": strength_check['suggestions']
            }), 400
        
        # Get user and verify current password
        db = SessionLocal()
        try:
            user = db.query(User).first()
            
            if not user:
                return jsonify({
                    "success": False,
                    "error": "User not found"
                }), 500
            
            # Verify current password
            if not PasswordManager.verify_password(current_password, user.password_hash):
                logger.warning(f"Failed password change attempt - wrong current password from {request.remote_addr}")
                return jsonify({
                    "success": False,
                    "error": "Current password is incorrect"
                }), 401
            
            # Hash new password
            new_password_hash = PasswordManager.hash_password(new_password)
            
            # Update password in database
            user.password_hash = new_password_hash
            user.force_password_change = False
            user.password_reset_at = datetime.utcnow()
            
            db.commit()
            
            logger.info(f"Password changed successfully from {request.remote_addr}")
            
            # Revoke all sessions except current (security best practice)
            # User must re-login on all other devices
            SessionManager.revoke_all_sessions_except(session_token)
            
            return jsonify({
                "success": True,
                "message": "Password changed successfully",
                "info": "All other sessions have been logged out"
            })
            
        finally:
            db.close()
    
    except Exception as e:
        logger.error(f"Password change error: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Internal server error"
        }), 500


@auth_bp.route('/sessions', methods=['GET'])
def list_sessions():
    """
    List all active sessions
    
    GET /api/auth/sessions
    
    Success Response (200):
    {
        "sessions": [
            {
                "id": 1,
                "created_at": "2026-01-23T10:00:00Z",
                "expires_at": "2026-01-23T18:00:00Z",
                "last_accessed": "2026-01-23T10:30:00Z",
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0...",
                "current": true
            }
        ]
    }
    
    Use Cases:
    - See all devices logged in
    - Identify unauthorized access
    - Revoke sessions from lost/stolen devices
    
    Security:
    - Requires valid session
    - Shows limited info (no tokens)
    - Current session marked for easy identification
    
    Verification:
    curl -k https://localhost:5000/api/auth/sessions \
         --cookie "session=<your-token>"
    """
    try:
        # Require authentication
        session_token = request.cookies.get('session')
        if not SessionManager.validate_session(session_token):
            return jsonify({
                "success": False,
                "error": "Not authenticated"
            }), 401
        
        # Get all sessions
        sessions_data = SessionManager.get_all_sessions(session_token)
        
        return jsonify({
            "sessions": sessions_data
        })
    
    except Exception as e:
        logger.error(f"List sessions error: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Internal server error"
        }), 500


@auth_bp.route('/sessions/<int:session_id>', methods=['DELETE'])
def revoke_session(session_id):
    """
    Revoke a specific session
    
    DELETE /api/auth/sessions/{id}
    
    Success Response (200):
    {
        "success": true,
        "message": "Session revoked successfully"
    }
    
    Error Responses:
    - 400: Cannot revoke current session (use logout instead)
    - 401: Not authenticated
    - 404: Session not found
    - 500: Server error
    
    Use Cases:
    - Log out from a lost/stolen device
    - Revoke old sessions
    - Security cleanup
    
    Security:
    - Cannot revoke current session (prevents accidental logout)
    - Requires valid session
    
    Verification:
    curl -k -X DELETE https://localhost:5000/api/auth/sessions/2 \
         --cookie "session=<your-token>"
    """
    try:
        # Require authentication
        session_token = request.cookies.get('session')
        if not SessionManager.validate_session(session_token):
            return jsonify({
                "success": False,
                "error": "Not authenticated"
            }), 401
        
        # Prevent revoking current session (use logout instead)
        current_session_id = SessionManager.get_session_id(session_token)
        if current_session_id == session_id:
            return jsonify({
                "success": False,
                "error": "Cannot revoke current session. Use logout endpoint instead."
            }), 400
        
        # Revoke the session
        success = SessionManager.revoke_session_by_id(session_id)
        
        if success:
            logger.info(f"Session {session_id} revoked from {request.remote_addr}")
            return jsonify({
                "success": True,
                "message": "Session revoked successfully"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Session not found"
            }), 404
    
    except Exception as e:
        logger.error(f"Revoke session error: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Internal server error"
        }), 500


# Error handlers for the auth blueprint
@auth_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors in auth routes"""
    return jsonify({
        "success": False,
        "error": "Endpoint not found"
    }), 404


@auth_bp.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors (wrong HTTP method)"""
    return jsonify({
        "success": False,
        "error": "Method not allowed"
    }), 405


@auth_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal error: {str(error)}", exc_info=True)
    return jsonify({
        "success": False,
        "error": "Internal server error"
    }), 500
