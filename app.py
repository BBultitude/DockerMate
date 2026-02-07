"""
DockerMate - Flask Application Entry Point

This is the main Flask application that serves the DockerMate web interface.
It handles HTTPS setup, database initialization, and route registration.

Features:
- Automatic HTTPS with self-signed certificates
- Database initialization on startup
- Authentication system
- Health check endpoint
- Route protection with session management

Design Philosophy:
- Simple single-file entry point
- Auto-generate SSL certificates on first run
- Educational comments for learning
- Clear error handling
"""

from flask import Flask, redirect, request, jsonify, render_template
from backend.models.database import init_db
from backend.ssl.cert_manager import CertificateManager
from config import Config
import ssl
import os
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask application
app = Flask(__name__, 
            template_folder='frontend/templates',
            static_folder='frontend/static')
app.secret_key = os.urandom(24)

# Configuration
app.config['DATABASE_PATH'] = Config.DATABASE_PATH
app.config['SSL_MODE'] = Config.SSL_MODE

## Import and register authentication blueprint
from backend.api.auth import auth_bp
app.register_blueprint(auth_bp)

# Import and register system blueprint (Sprint 2 Task 6)
from backend.api.system import system_bp
app.register_blueprint(system_bp)

# Import and register containers blueprint (Sprint 2 Task 5)
from backend.api.containers import containers_bp
app.register_blueprint(containers_bp)

# Import and register images blueprint (Sprint 3)
from backend.api.images import images_bp
app.register_blueprint(images_bp)

# Import and register networks blueprint (Sprint 4)
from backend.api.networks import networks_bp
app.register_blueprint(networks_bp)

# Import and register volumes blueprint (Sprint 5 Task 1)
from backend.api.volumes import volumes_bp
app.register_blueprint(volumes_bp)

# Import and register stacks blueprint (Sprint 5 Task 3)
from backend.api.stacks import stacks_bp
app.register_blueprint(stacks_bp)

# Import and register converter blueprint (Sprint 5 Task 4)
from backend.api.converter import converter_bp
app.register_blueprint(converter_bp)

# Import and initialise rate limiter (Sprint 5 — SEC-001)
from backend.extensions import limiter
limiter.init_app(app)

# Import and initialise CSRF protection (Sprint 5 — SECURITY-003)
from backend.extensions import csrf
# Configure CSRF to avoid cookie name conflict with session cookie
app.config['WTF_CSRF_TIME_LIMIT'] = None  # Tokens don't expire (tied to session)
app.config['WTF_CSRF_SSL_STRICT'] = False  # Allow self-signed certs
csrf.init_app(app)

# Import middleware for route protection
from backend.auth.middleware import require_auth, get_current_session_info, is_authenticated


def create_ssl_context():
    """
    Create SSL context for HTTPS
    
    This function generates a self-signed certificate if one doesn't exist,
    then creates an SSL context with secure settings.
    
    Returns:
        ssl.SSLContext: Configured SSL context for HTTPS
    
    Security Settings:
    - TLS 1.2+ only (no TLS 1.0/1.1)
    - Disables weak ciphers
    - Uses 2048-bit RSA keys
    
    Home Lab Notes:
    - Self-signed certificates are acceptable for home labs
    - Browser will show warning (one-time security exception needed)
    - For public-facing deployments, use Let's Encrypt instead
    """
    cert_path = os.path.join(Config.SSL_DIR, 'cert.pem')
    key_path = os.path.join(Config.SSL_DIR, 'key.pem')
    
    # Generate cert if doesn't exist
    if not os.path.exists(cert_path):
        logger.info("Generating self-signed certificate...")
        try:
            CertificateManager.generate_self_signed_cert()
            logger.info("✓ Self-signed certificate generated successfully")
        except Exception as e:
            logger.error(f"Failed to generate certificate: {e}")
            raise
    
    # Create SSL context
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_path, key_path)
    
    # Security settings - disable old TLS versions
    context.options |= ssl.OP_NO_TLSv1
    context.options |= ssl.OP_NO_TLSv1_1
    
    return context


@app.before_request
def force_https():
    """
    Redirect HTTP to HTTPS

    This ensures all traffic is encrypted. For home labs, even self-signed
    HTTPS is better than plain HTTP.

    Exceptions:
    - Testing mode (app.config['TESTING'])
    - First-time setup (before setup_complete file exists)
    - Let's Encrypt validation paths (/.well-known/acme-challenge/)
    - Requests already using HTTPS
    """
    # Skip HTTPS redirect in testing mode
    if app.config.get('TESTING'):
        return

    if request.is_secure:
        return

    # Allow HTTP during first-time setup
    setup_complete = os.path.exists(os.path.join(Config.DATA_DIR, 'setup_complete'))
    if not setup_complete:
        return

    # Allow Let's Encrypt validation
    if request.path.startswith('/.well-known/acme-challenge/'):
        return

    # Redirect to HTTPS
    url = request.url.replace('http://', 'https://', 1)
    return redirect(url, code=301)


@app.after_request
def set_security_headers(response):
    """
    Add security headers to all responses (Sprint 5 - SEC-002)

    Security Headers:
    - Content-Security-Policy: Prevents XSS attacks by controlling resource sources
    - X-Content-Type-Options: Prevents MIME-sniffing attacks
    - X-Frame-Options: Prevents clickjacking attacks
    - X-XSS-Protection: Legacy XSS protection (for older browsers)
    - Referrer-Policy: Controls referrer information in requests

    CSP Policy Breakdown:
    - default-src 'self': Only load resources from same origin by default
    - script-src: Allow scripts from self, CDNs (Alpine.js), and inline scripts
    - style-src: Allow styles from self, CDNs (Tailwind), and inline styles
    - img-src: Allow images from self and data URIs
    - connect-src: Allow API calls to self
    - font-src: Allow fonts from self and data URIs
    - frame-ancestors 'none': Prevent embedding in iframes (clickjacking protection)

    Educational Notes:
    - 'unsafe-inline' needed for Alpine.js and Tailwind's inline styles
    - 'unsafe-eval' needed for Alpine.js reactive expressions (x-text, x-show, etc.)
    - CDN domains whitelisted for Tailwind CSS and Alpine.js
    - In production, consider moving to PostCSS build to remove CDN dependency
    - CSP violations logged to browser console for debugging
    """
    # Content Security Policy
    csp_policy = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' cdn.tailwindcss.com cdn.jsdelivr.net unpkg.com; "
        "style-src 'self' 'unsafe-inline' cdn.tailwindcss.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self' cdn.jsdelivr.net; "
        "font-src 'self' data:; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )
    response.headers['Content-Security-Policy'] = csp_policy

    # Additional security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

    # HTTPS Strict Transport Security (only if using HTTPS)
    if request.is_secure:
        # max-age=31536000 = 1 year
        # includeSubDomains applies to all subdomains
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

    return response


# ========================================
# Health Check Endpoint
# ========================================

@app.route('/api/health')
def health_check():
    """
    Health check endpoint for monitoring
    
    GET /api/health
    
    Returns:
        JSON with status and version
    
    Use Cases:
    - Docker health checks
    - Monitoring systems
    - Uptime checks
    
    Verification:
    curl -k https://localhost:5000/api/health
    """
    return jsonify({
        "status": "healthy",
        "version": "1.0.0",
        "service": "DockerMate"
    })


# ========================================
# TASK 7: Authentication Routes
# ========================================

@app.route('/')
def index():
    """
    Root route - redirect to dashboard if authenticated, otherwise login
    
    This provides a friendly default landing page.
    """
    from backend.auth.middleware import is_authenticated
    
    if is_authenticated():
        return redirect('/dashboard')
    else:
        return redirect('/login')


@app.route('/login')
def login_page():
    """
    Login page
    
    GET /login
    
    Displays the login form for user authentication.
    
    Note: The actual login processing happens at POST /api/auth/login
    """
    return render_template('login.html')


@app.route('/dashboard')
@require_auth()
def dashboard():
    """
    Main dashboard - requires authentication

    GET /dashboard

    This is the main application interface. Users must be logged in to access.

    Authentication:
    - Protected by @require_auth() decorator
    - Redirects to /login if not authenticated
    - Validates session on every request

    Session Info:
    - Passed to template for display
    - Shows IP address, user agent, expiry time
    """
    session_info = get_current_session_info()
    return render_template('dashboard.html', session=session_info)


@app.route('/containers')
@require_auth()
def containers_page():
    """Containers management page"""
    session_info = get_current_session_info()
    return render_template('containers.html', session=session_info)


@app.route('/images')
@require_auth()
def images_page():
    """Images management page"""
    session_info = get_current_session_info()
    return render_template('images.html', session=session_info)


@app.route('/networks')
@require_auth()
def networks_page():
    """Networks management page"""
    session_info = get_current_session_info()
    return render_template('networks.html', session=session_info)


@app.route('/volumes')
@require_auth()
def volumes_page():
    """Volumes management page"""
    session_info = get_current_session_info()
    return render_template('volumes.html', session=session_info)


@app.route('/stacks')
@require_auth()
def stacks_page():
    """Stacks management page"""
    session_info = get_current_session_info()
    return render_template('stacks.html', session=session_info)


@app.route('/converter')
@require_auth()
def converter_page():
    """Docker Run to Compose converter page"""
    session_info = get_current_session_info()
    return render_template('converter.html', session=session_info)


@app.route('/settings')
@require_auth()
def settings_page():
    """Settings page"""
    session_info = get_current_session_info()
    return render_template('settings.html', session=session_info)


@app.route('/health')
@require_auth()
def health_page():
    """Health monitoring page"""
    session_info = get_current_session_info()
    return render_template('health.html', session=session_info)


# ========================================
# Error Handlers
# ========================================

@app.errorhandler(429)
def rate_limit_exceeded(error):
    """Handle 429 Too Many Requests from Flask-Limiter"""
    return jsonify({
        "error": "Rate limit exceeded",
        "message": "Too many requests. Please try again later."
    }), 429


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        "error": "Not found",
        "message": "The requested resource was not found"
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal error: {str(error)}", exc_info=True)
    return jsonify({
        "error": "Internal server error",
        "message": "An unexpected error occurred"
    }), 500


# ========================================
# Application Startup
# ========================================

if __name__ == '__main__':
    # Ensure all required directories exist
    logger.info("Ensuring required directories exist...")
    try:
        Config.ensure_directories()
        logger.info("✓ Directories created successfully")
    except Exception as e:
        logger.error(f"Failed to create directories: {e}")
        raise

    # Initialize database
    logger.info("Initializing database...")
    try:
        init_db()
        logger.info("✓ Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

    # Start health metrics collection worker (Sprint 5 Tasks 5-7)
    if not app.config.get('TESTING'):
        logger.info("Starting health metrics collection worker...")
        try:
            from backend.services.metrics_worker import start_metrics_worker
            start_metrics_worker(interval_seconds=60)  # Collect every 60 seconds
            logger.info("✓ Metrics worker started")
        except Exception as e:
            logger.warning(f"Failed to start metrics worker: {e}")
            logger.warning("Health monitoring will work but historical metrics won't be collected")

    # Check if setup is complete
    setup_complete = os.path.exists(os.path.join(Config.DATA_DIR, 'setup_complete'))

    if not setup_complete:
        logger.warning("First time setup - running HTTP for initial config")
        logger.info("Visit http://localhost:5000/setup to complete setup")
        # Run HTTP only for initial setup
        app.run(host='0.0.0.0', port=5000, debug=True)
    else:
        logger.info("Starting DockerMate with HTTPS...")
        try:
            context = create_ssl_context()
            logger.info("✓ SSL context created")
            logger.info("=" * 50)
            logger.info("DockerMate is running!")
            logger.info("Access at: https://localhost:5000")
            logger.info("=" * 50)
            app.run(host='0.0.0.0', port=5000, ssl_context=context, debug=False)
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            raise
