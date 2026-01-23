"""
Flask Application Entry Point

This is the main entry point for the DockerMate application.

Why Flask?
- Lightweight and simple (KISS principle)
- No complex build process needed
- Perfect for single-user home lab applications
- Easy to understand for beginners

Design decisions:
- HTTPS by default (self-signed certificates)
- Single-user authentication (no multi-user complexity)
- Session-based auth (simpler than JWT)
- SQLite database (no external dependencies)

Security features:
- HTTPS enforcement (HTTP redirects to HTTPS)
- Auto-generated self-signed certificates
- httpOnly, secure cookies
- TLS 1.2+ only

Usage:
    python3 app.py
"""

from flask import Flask, redirect, request, jsonify, url_for, render_template, session, flash
from backend.models.database import init_db, SessionLocal
from backend.models.user import User
from backend.models.environment import Environment
from backend.ssl.cert_manager import CertificateManager
from backend.auth.password_manager import PasswordManager
from backend.auth.session_manager import SessionManager as AuthSessionManager
from backend.auth.middleware import login_required
from config import Config
import ssl
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)

# Load configuration
app.config.from_object(Config)


def create_ssl_context():
    """
    Create SSL context for HTTPS
    
    Generates self-signed certificate if one doesn't exist.
    This is acceptable for home labs - users add a one-time
    browser security exception.
    
    Returns:
        ssl.SSLContext configured for TLS 1.2+
    
    Security:
        - TLS 1.2 minimum (no TLS 1.0/1.1)
        - Strong cipher suites
        - Self-signed certificate auto-generation
    """
    cert_path = os.path.join(Config.SSL_DIR, 'cert.pem')
    key_path = os.path.join(Config.SSL_DIR, 'key.pem')
    
    # Generate certificate if doesn't exist
    if not os.path.exists(cert_path) or not os.path.exists(key_path):
        logger.info("Generating self-signed SSL certificate...")
        result = CertificateManager.generate_self_signed_cert(
            output_dir=Config.SSL_DIR
        )
        logger.info(f"Certificate generated, expires: {result['expires_at']}")
    
    # Create SSL context
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_path, key_path)
    
    # Security: Disable old TLS versions
    context.options |= ssl.OP_NO_TLSv1
    context.options |= ssl.OP_NO_TLSv1_1
    
    logger.info("SSL context created (TLS 1.2+)")
    return context


def init_default_environments():
    """
    Initialize default environment types in database
    
    Creates the four standard environments:
    - PRD (Production) - Red
    - UAT (User Acceptance Testing) - Yellow
    - DEV (Development) - Green
    - SANDBOX (Experimental) - Blue
    
    This is called on first run to populate the environments table.
    """
    db = SessionLocal()
    try:
        # Check if environments already exist
        existing = db.query(Environment).count()
        if existing > 0:
            logger.info(f"Environments already initialized ({existing} found)")
            return
        
        # Define default environments
        environments = [
            {
                'code': 'PRD',
                'name': 'Production',
                'description': 'Critical production services',
                'color': 'red',
                'icon_emoji': '🔴',
                'display_order': 1,
                'require_confirmation': True,
                'prevent_auto_update': True
            },
            {
                'code': 'UAT',
                'name': 'User Acceptance Testing',
                'description': 'Pre-production testing environment',
                'color': 'yellow',
                'icon_emoji': '🟡',
                'display_order': 2,
                'require_confirmation': True,
                'prevent_auto_update': False
            },
            {
                'code': 'DEV',
                'name': 'Development',
                'description': 'Development and testing',
                'color': 'green',
                'icon_emoji': '🟢',
                'display_order': 3,
                'require_confirmation': False,
                'prevent_auto_update': False
            },
            {
                'code': 'SANDBOX',
                'name': 'Sandbox',
                'description': 'Experimental and testing',
                'color': 'blue',
                'icon_emoji': '🔵',
                'display_order': 4,
                'require_confirmation': False,
                'prevent_auto_update': False
            }
        ]
        
        # Create environments
        for env_data in environments:
            env = Environment(**env_data)
            db.add(env)
        
        db.commit()
        logger.info("Default environments initialized")
        
    except Exception as e:
        logger.error(f"Failed to initialize environments: {e}")
        db.rollback()
    finally:
        db.close()


@app.before_request
def force_https():
    """
    Force HTTPS for all requests
    
    Redirects HTTP requests to HTTPS (except Let's Encrypt validation).
    This ensures all traffic is encrypted.
    
    Why:
        Even on home networks, HTTPS prevents:
        - Password sniffing
        - Session hijacking
        - Man-in-the-middle attacks
    """
    # Already HTTPS, continue
    if request.is_secure:
        return
    
    # Allow Let's Encrypt ACME challenge (uses HTTP)
    if request.path.startswith('/.well-known/acme-challenge/'):
        return
    
    # Redirect HTTP to HTTPS
    url = request.url.replace('http://', 'https://', 1)
    return redirect(url, code=301)


# ============================================
# PUBLIC ROUTES (No Authentication Required)
# ============================================

@app.route('/api/health')
def health_check():
    """
    Health check endpoint
    
    Used by Docker, monitoring tools, and load balancers
    to verify the application is running.
    
    Returns:
        JSON: {"status": "healthy", "version": "1.0.0"}
    """
    return jsonify({
        "status": "healthy",
        "version": "1.0.0",
        "ssl_enabled": True
    })


@app.route('/setup', methods=['GET', 'POST'])
def setup():
    """
    Initial setup wizard
    
    First-run configuration:
    - Create admin password
    - Configure SSL (self-signed/Let's Encrypt/custom)
    - Detect hardware profile
    - Initialize environments
    
    This route is only accessible before setup is complete.
    After setup, it redirects to login.
    """
    setup_complete_file = os.path.join(Config.DATA_DIR, 'setup_complete')
    
    # If already set up, redirect to login
    if os.path.exists(setup_complete_file):
        return redirect(url_for('login'))
    
    if request.method == 'GET':
        return render_template('setup.html')
    
    # POST: Process setup
    try:
        password = request.form.get('password')
        
        if not password:
            flash('Password is required', 'error')
            return render_template('setup.html')
        
        # Validate password strength
        validation = PasswordManager.validate_password_strength(password)
        if not validation['valid']:
            for issue in validation['issues']:
                flash(issue, 'error')
            return render_template('setup.html')
        
        # Create admin user
        db = SessionLocal()
        try:
            # Hash password
            password_hash = PasswordManager.hash_password(password)
            
            # Create user
            user = User(
                username='admin',
                password_hash=password_hash
            )
            db.add(user)
            db.commit()
            logger.info("Admin user created")
            
        finally:
            db.close()
        
        # Initialize default environments
        init_default_environments()
        
        # Mark setup as complete
        with open(setup_complete_file, 'w') as f:
            f.write(f"Setup completed at {datetime.now().isoformat()}\n")
        
        logger.info("Setup complete!")
        flash('Setup complete! Please log in.', 'success')
        return redirect(url_for('login'))
        
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        flash('Setup failed. Please try again.', 'error')
        return render_template('setup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login page
    
    GET: Show login form
    POST: Process login attempt
    
    On successful login:
    - Creates session
    - Sets httpOnly, secure cookie
    - Redirects to dashboard
    """
    # If already logged in, redirect to dashboard
    session_token = request.cookies.get('session')
    if session_token and AuthSessionManager.validate_session(session_token):
        return redirect(url_for('dashboard'))
    
    if request.method == 'GET':
        return render_template('login.html')
    
    # POST: Process login
    try:
        password = request.form.get('password')
        remember_me = request.form.get('remember_me') == 'on'
        
        if not password:
            flash('Password is required', 'error')
            return render_template('login.html')
        
        # Get user
        db = SessionLocal()
        try:
            user = db.query(User).first()
            
            if not user:
                flash('Setup not complete', 'error')
                return redirect(url_for('setup'))
            
            # Verify password
            if not PasswordManager.verify_password(password, user.password_hash):
                flash('Invalid password', 'error')
                logger.warning(f"Failed login attempt from {request.remote_addr}")
                return render_template('login.html')
            
            # Create session
            session_token = AuthSessionManager.create_session(
                remember_me=remember_me,
                user_agent=request.headers.get('User-Agent'),
                ip_address=request.remote_addr
            )
            
            logger.info(f"Successful login from {request.remote_addr}")
            
            # Set cookie and redirect
            response = redirect(url_for('dashboard'))
            response.set_cookie(
                'session',
                session_token,
                httponly=True,
                secure=True,
                samesite='Strict',
                max_age=604800 if remember_me else 28800  # 7 days or 8 hours
            )
            
            return response
            
        finally:
            db.close()
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        flash('Login failed. Please try again.', 'error')
        return render_template('login.html')


@app.route('/logout', methods=['POST'])
def logout():
    """
    Logout endpoint
    
    Revokes session and clears cookie.
    Redirects to login page.
    """
    session_token = request.cookies.get('session')
    
    if session_token:
        AuthSessionManager.revoke_session(session_token)
        logger.info("User logged out")
    
    response = redirect(url_for('login'))
    response.set_cookie('session', '', expires=0)
    
    return response


# ============================================
# PROTECTED ROUTES (Authentication Required)
# ============================================

@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    """
    Main dashboard
    
    Shows:
    - Container summary
    - Recent activity
    - Health status
    - Quick actions
    """
    return render_template('dashboard.html')

@app.route('/settings')
@login_required
def settings():
    """
    Settings page
    
    Configure:
    - Password
    - SSL certificate
    - Environment tags
    - Hardware profile
    - Auto-update preferences
    """
    return render_template('settings.html')

@app.route('/containers')
@login_required
def containers():
    """Containers page (Sprint 2)"""
    return render_template('containers.html')

@app.route('/images')
@login_required
def images():
    """Images page (Sprint 3)"""
    return render_template('images.html')

@app.route('/networks')
@login_required
def networks():
    """Networks page (Sprint 4)"""
    return render_template('networks.html')

# ============================================
# ERROR HANDLERS
# ============================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Not found'}), 404
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal error: {error}")
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Internal server error'}), 500
    return render_template('errors/500.html'), 500


@app.errorhandler(403)
def forbidden(error):
    """Handle 403 errors"""
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Forbidden'}), 403
    return render_template('errors/403.html'), 403


# ============================================
# MAIN ENTRY POINT
# ============================================

if __name__ == '__main__':
    # Ensure directories exist
    Config.ensure_directories()
    
    # Initialize database
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized")
    
    # Check if first run
    setup_complete = os.path.exists(os.path.join(Config.DATA_DIR, 'setup_complete'))
    
    if not setup_complete:
        logger.info("=" * 60)
        logger.info("FIRST RUN DETECTED")
        logger.info("Starting setup wizard on HTTP (port 5000)")
        logger.info("Visit: http://localhost:5000/setup")
        logger.info("After setup, application will restart with HTTPS")
        logger.info("=" * 60)
        
        # Run HTTP for initial setup
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True
        )
    else:
        logger.info("=" * 60)
        logger.info("Starting DockerMate with HTTPS")
        logger.info("Access at: https://localhost:5000")
        logger.info("(Accept browser security exception for self-signed cert)")
        logger.info("=" * 60)
        
        # Run HTTPS for normal operation
        context = create_ssl_context()
        app.run(
            host='0.0.0.0',
            port=5000,
            ssl_context=context,
            debug=False  # Disable debug in HTTPS mode for security
        )
