"""
DockerMate - Development Flask Application (HTTP Mode)

TEMPORARY FILE FOR PHASE 2 TESTING ONLY

This version runs on HTTP (not HTTPS) to avoid SSL certificate issues
during local development and testing.

For production, use the main app.py with proper SSL certificates.

Usage:
    python app_dev.py

Access at: http://localhost:5000
"""

from flask import Flask, redirect, request, jsonify, render_template
from backend.models.database import init_db
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
app.config['DATABASE_PATH'] = os.getenv('DATABASE_PATH', 'data/dockermate.db')
app.config['TESTING'] = True          # Disable HTTPS redirect
app.config['RATELIMIT_ENABLED'] = True  # Flask-Limiter disables itself when TESTING; re-enable

# Initialise rate-limiter (extensions.py creates the Limiter instance)
from backend.extensions import limiter
limiter.init_app(app)

# Import and register authentication blueprint
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

# Import middleware for route protection
from backend.auth.middleware import require_auth, get_current_session_info, is_authenticated

# Start background scheduler once.
# In debug mode Flask spawns a reloader child (WERKZEUG_RUN_MAIN=true) — only
# start there to avoid a duplicate.  Outside debug mode the guard is skipped.
if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    from backend.services.scheduler import start_scheduler
    start_scheduler()

# ========================================
# Health Check Endpoint
# ========================================

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "version": "1.0.0-dev",
        "service": "DockerMate (Development Mode - HTTP)",
        "warning": "This is development mode. Use app.py for production."
    })


# ========================================
# Authentication Routes
# ========================================

@app.route('/')
def index():
    """Root route - redirect to dashboard if authenticated, otherwise login"""
    if is_authenticated():
        return redirect('/dashboard')
    else:
        return redirect('/login')


@app.route('/login')
def login_page():
    """Login page"""
    return render_template('login.html')


@app.route('/login', methods=['POST'])
def login_post():
    """Login POST - forwards to auth blueprint"""
    from backend.api.auth import login as auth_login
    return auth_login()


@app.route('/dashboard')
@require_auth()
def dashboard():
    """Main dashboard - requires authentication"""
    session_info = get_current_session_info()
    return render_template('dashboard.html', session=session_info)


@app.route('/containers')
@require_auth()
def containers():
    """Containers page"""
    session_info = get_current_session_info()
    return render_template('containers.html', session=session_info)


@app.route('/images')
@require_auth()
def images():
    """Images page"""
    session_info = get_current_session_info()
    return render_template('images.html', session=session_info)


@app.route('/networks')
@require_auth()
def networks():
    """Networks page"""
    session_info = get_current_session_info()
    return render_template('networks.html', session=session_info)


@app.route('/health')
@require_auth()
def health():
    """Health & Alerts detail page"""
    session_info = get_current_session_info()
    return render_template('health.html', session=session_info)


@app.route('/settings')
@require_auth()
def settings():
    """Settings page"""
    session_info = get_current_session_info()
    return render_template('settings.html', session=session_info)


@app.route('/logout', methods=['POST'])
def logout():
    """Logout route - calls the auth API"""
    from backend.api.auth import logout as auth_logout
    return auth_logout()


# ========================================
# Error Handlers
# ========================================

@app.errorhandler(429)
def rate_limit_exceeded(error):
    """Handle rate-limit (429) errors from Flask-Limiter"""
    return jsonify({
        "error": "Rate limit exceeded",
        "message": "Too many requests. Please try again later.",
        "retry_after": error.retry_after if hasattr(error, 'retry_after') else None
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
    # Initialize database
    logger.info("Initializing database...")
    try:
        init_db()
        logger.info("✓ Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    
    logger.info("=" * 50)
    logger.info("DockerMate (Development Mode - HTTP)")
    logger.info("=" * 50)
    logger.warning("⚠️  Running in HTTP mode (no SSL)")
    logger.warning("⚠️  For testing Phase 2 template updates only")
    logger.warning("⚠️  Use app.py for production with HTTPS")
    logger.info("=" * 50)
    logger.info("Access at: http://localhost:5000")
    logger.info("Access from network: http://192.168.13.142:5000")
    logger.info("=" * 50)
    
    # Run on HTTP for development testing
    app.run(host='0.0.0.0', port=5000, debug=True)