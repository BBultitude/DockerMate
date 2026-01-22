"""
Authentication Middleware - Flask Route Protection

This module provides Flask middleware for protecting routes and
requiring authentication.

Key Components:
- @login_required decorator: Protect routes requiring authentication
- check_authentication(): Middleware to run before each request
- get_current_user(): Get authenticated user from session

Usage in Flask:
    from flask import Flask
    from backend.auth.middleware import login_required, init_auth_middleware
    
    app = Flask(__name__)
    
    # Initialize middleware
    init_auth_middleware(app)
    
    # Public route (no decorator)
    @app.route('/login')
    def login():
        return render_template('login.html')
    
    # Protected route (requires login)
    @app.route('/dashboard')
    @login_required
    def dashboard():
        return render_template('dashboard.html')
    
    # API endpoint (requires login)
    @app.route('/api/containers')
    @login_required
    def containers():
        return jsonify(containers)

How It Works:
    1. User visits protected route
    2. @login_required decorator runs first
    3. Checks for session cookie
    4. Validates session with SessionManager
    5. If valid: continue to route
    6. If invalid: redirect to /login

Verification:
    # Test without login
    curl http://localhost:5000/dashboard
    # Should redirect to /login
    
    # Test with valid session
    curl -b "session=abc123..." http://localhost:5000/dashboard
    # Should show dashboard
"""

from functools import wraps
from flask import request, redirect, url_for, g, current_app
from typing import Optional, Callable
from backend.auth.session_manager import SessionManager
from backend.models.database import SessionLocal
from backend.models.user import User

# =============================================================================
# Login Required Decorator
# =============================================================================

def login_required(f: Callable) -> Callable:
    """
    Decorator to protect routes requiring authentication
    
    Add this decorator to any route that requires the user to be logged in.
    If user is not authenticated, redirects to login page.
    
    Args:
        f: Function to decorate (Flask route handler)
        
    Returns:
        Wrapped function that checks authentication first
        
    Example:
        # Protect a page
        @app.route('/dashboard')
        @login_required
        def dashboard():
            # Only accessible if logged in
            return render_template('dashboard.html')
        
        # Protect an API endpoint
        @app.route('/api/containers')
        @login_required
        def list_containers():
            # Only accessible if logged in
            containers = get_all_containers()
            return jsonify(containers)
        
        # Multiple decorators (login_required should be closest to function)
        @app.route('/admin')
        @other_decorator
        @login_required
        def admin_page():
            return "Admin only"
    
    How It Works:
        1. User requests /dashboard
        2. @login_required decorator runs first
        3. Extracts session cookie from request
        4. Calls SessionManager.validate_session(token)
        5. If valid: calls original function (dashboard)
        6. If invalid: returns redirect to /login
        
    Security Note:
        Session validation happens on EVERY request to protected routes.
        This ensures expired or revoked sessions can't access protected resources.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get session token from cookie
        session_token = request.cookies.get('session')
        
        # Validate session
        if not SessionManager.validate_session(session_token):
            # Invalid or expired session - redirect to login
            
            # Store the URL they were trying to access
            # so we can redirect back after login
            next_url = request.url
            
            # Redirect to login with next parameter
            return redirect(url_for('login', next=next_url))
        
        # Valid session - continue to route
        return f(*args, **kwargs)
    
    return decorated_function

# =============================================================================
# Current User Helper
# =============================================================================

def get_current_user() -> Optional[User]:
    """
    Get the currently authenticated user
    
    Returns the User object for the logged-in user.
    Returns None if not authenticated.
    
    This function checks the Flask 'g' object first (cached),
    then validates session and queries database if needed.
    
    Returns:
        User object if authenticated, None otherwise
        
    Example:
        # In a route
        @app.route('/profile')
        @login_required
        def profile():
            user = get_current_user()
            return render_template('profile.html', user=user)
        
        # In a template (if user is passed)
        <h1>Welcome, {{ user.username }}!</h1>
        
    Caching:
        User is cached in Flask's 'g' object for the duration
        of the request to avoid multiple database queries.
    """
    # Check if already cached in request context
    if hasattr(g, 'current_user'):
        return g.current_user
    
    # Get session token from cookie
    session_token = request.cookies.get('session')
    
    # Validate session
    if not SessionManager.validate_session(session_token):
        return None
    
    # Get user from database
    db = SessionLocal()
    try:
        user = User.get_admin(db)
        
        # Cache in request context
        g.current_user = user
        
        return user
    finally:
        db.close()

# =============================================================================
# Authentication Check (Before Request)
# =============================================================================

def check_authentication():
    """
    Check authentication before each request
    
    This function runs BEFORE every request (via @app.before_request).
    It checks if the route requires authentication and validates session.
    
    Public routes (no authentication required):
    - /login
    - /static/*
    - /.well-known/* (for Let's Encrypt)
    
    All other routes are protected by default.
    
    How It Works:
        1. Request comes in (e.g., GET /dashboard)
        2. Flask calls this function first
        3. Check if route is public (login, static files)
        4. If public: allow through
        5. If protected: validate session
        6. If valid session: allow through
        7. If invalid: redirect to /login
        
    Example:
        # In app.py
        from backend.auth.middleware import check_authentication
        
        app = Flask(__name__)
        app.before_request(check_authentication)
        
        # Now all routes are protected by default
        # except login and static files
        
    Note:
        This is an alternative to using @login_required on every route.
        Choose ONE approach:
        - Option A: Use @login_required decorator on protected routes
        - Option B: Use check_authentication() to protect everything by default
    """
    # Public endpoints that don't require authentication
    public_endpoints = [
        'login',           # Login page
        'static',          # Static files (CSS, JS, images)
        'health_check',    # Health check for Docker
    ]
    
    # Public paths that don't require authentication
    public_paths = [
        '/login',
        '/static/',
        '/.well-known/',  # Let's Encrypt verification
        '/api/health',    # Health check endpoint
    ]
    
    # Check if this is a public endpoint
    if request.endpoint in public_endpoints:
        return None
    
    # Check if this is a public path
    for path in public_paths:
        if request.path.startswith(path):
            return None
    
    # Protected route - validate session
    session_token = request.cookies.get('session')
    
    if not SessionManager.validate_session(session_token):
        # Invalid session - redirect to login
        
        # Store URL they were trying to access
        if request.method == 'GET':
            next_url = request.url
            return redirect(url_for('login', next=next_url))
        else:
            # For POST/PUT/DELETE, just redirect to login
            return redirect(url_for('login'))
    
    # Valid session - continue
    return None

# =============================================================================
# Middleware Initialization
# =============================================================================

def init_auth_middleware(app):
    """
    Initialize authentication middleware for Flask app
    
    Call this once during app initialization to set up authentication.
    
    Args:
        app: Flask application instance
        
    Example:
        # In app.py
        from flask import Flask
        from backend.auth.middleware import init_auth_middleware
        
        app = Flask(__name__)
        
        # Initialize authentication
        init_auth_middleware(app)
        
        # Now authentication is enabled
        
    What This Does:
        1. Registers before_request handler (check_authentication)
        2. Makes get_current_user available in templates
        3. Sets up session configuration
        
    Alternative:
        If you prefer to use @login_required decorators instead
        of automatic protection, you can skip this and just
        import the decorator directly.
    """
    # Register before_request handler
    # This runs before EVERY request
    app.before_request(check_authentication)
    
    # Make get_current_user available in templates
    @app.context_processor
    def inject_user():
        """
        Inject current user into all templates
        
        This allows templates to access {{ current_user }}
        without explicitly passing it in every route.
        
        Example template usage:
            {% if current_user %}
                <p>Logged in as: {{ current_user.username }}</p>
            {% else %}
                <a href="/login">Login</a>
            {% endif %}
        """
        return {
            'current_user': get_current_user()
        }
    
    # Configure session
    # These settings are important for security
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,   # Prevent JavaScript access
        SESSION_COOKIE_SECURE=True,     # HTTPS only
        SESSION_COOKIE_SAMESITE='Strict', # CSRF protection
    )

# =============================================================================
# Helper Functions
# =============================================================================

def is_authenticated() -> bool:
    """
    Check if current request is authenticated
    
    Simple boolean check for authentication.
    Useful in templates or route logic.
    
    Returns:
        True if authenticated, False otherwise
        
    Example:
        # In a route
        if is_authenticated():
            return render_template('dashboard.html')
        else:
            return redirect('/login')
        
        # In a template
        {% if is_authenticated() %}
            <a href="/logout">Logout</a>
        {% else %}
            <a href="/login">Login</a>
        {% endif %}
    """
    session_token = request.cookies.get('session')
    return SessionManager.validate_session(session_token)

def logout_user():
    """
    Logout current user by revoking session
    
    Call this in your logout route to invalidate the session.
    
    Example:
        @app.route('/logout', methods=['POST'])
        def logout():
            from backend.auth.middleware import logout_user
            
            logout_user()
            
            response = make_response(redirect('/login'))
            response.set_cookie('session', '', expires=0)
            return response
    """
    session_token = request.cookies.get('session')
    if session_token:
        SessionManager.revoke_session(session_token)

# =============================================================================
# Testing and Verification
# =============================================================================

if __name__ == "__main__":
    """
    Test the middleware when run directly
    
    This creates a minimal Flask app to test the authentication.
    
    Usage:
        python3 backend/auth/middleware.py
        
    Then visit:
        http://localhost:5001/public   (should work)
        http://localhost:5001/protected (should redirect to /login)
    """
    from flask import Flask, make_response
    from backend.models.database import init_db
    from backend.auth.password_manager import PasswordManager
    
    print("=" * 80)
    print("DockerMate Authentication Middleware Test")
    print("=" * 80)
    
    # Initialize database
    print("\n1. Initializing database...")
    init_db()
    
    # Create test user
    print("\n2. Creating test user...")
    from backend.models.database import SessionLocal
    from backend.models.user import User
    
    db = SessionLocal()
    try:
        existing = User.get_admin(db)
        if existing:
            print("   (User already exists)")
        else:
            user = User(
                username='admin',
                password_hash=PasswordManager.hash_password('TestPassword123')
            )
            db.add(user)
            db.commit()
            print("   ✅ Test user created (password: TestPassword123)")
    finally:
        db.close()
    
    # Create minimal Flask app
    print("\n3. Creating test Flask app...")
    app = Flask(__name__)
    app.secret_key = 'test_secret_key'
    
    # Public route
    @app.route('/public')
    def public_page():
        return "This is a public page (no authentication required)"
    
    # Protected route
    @app.route('/protected')
    @login_required
    def protected_page():
        return "This is a protected page (authentication required)"
    
    # Login route (simplified for testing)
    @app.route('/login')
    def login():
        return "Login page (in real app, this would be a form)"
    
    print("   ✅ Flask app created")
    
    print("\n4. Test server starting...")
    print("   Visit: http://localhost:5001/public (should work)")
    print("   Visit: http://localhost:5001/protected (should redirect)")
    print("\n   Press Ctrl+C to stop")
    print("=" * 80)
    
    # Run test server
    app.run(debug=True, port=5001)
