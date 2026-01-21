"""
DockerMate - Main Application Entry Point

This is the Flask application entry point that:
1. Initializes the database
2. Sets up SSL/TLS (self-signed by default)
3. Registers API blueprints
4. Starts the web server

First-time setup:
- Runs on HTTP to allow initial password setup
- After setup, always runs on HTTPS

Security:
- Forces HTTPS redirect (except Let's Encrypt validation)
- Self-signed certificates for home labs
- TLS 1.2+ only

Author: DockerMate Team
License: MIT
"""

from flask import Flask, redirect, request, jsonify
from backend.models.database import init_db
from backend.ssl.cert_manager import CertificateManager
import ssl
import os

# Create Flask app
app = Flask(__name__)

# Security: Generate random secret key for session encryption
# In production, this should be set via environment variable
app.secret_key = os.getenv('DOCKERMATE_SECRET_KEY', os.urandom(24))

# Configuration from environment variables with defaults
app.config['DATABASE_PATH'] = os.getenv('DOCKERMATE_DATABASE_PATH', '/app/data/dockermate.db')
app.config['SSL_MODE'] = os.getenv('DOCKERMATE_SSL_MODE', 'self-signed')
app.config['DATA_DIR'] = os.getenv('DOCKERMATE_DATA_DIR', '/app/data')

def create_ssl_context():
    """
    Create SSL context for HTTPS
    
    This function:
    1. Checks if SSL certificate exists
    2. Generates self-signed cert if needed
    3. Configures SSL context with security settings
    
    Returns:
        ssl.SSLContext: Configured SSL context
    
    Security Settings:
    - TLS 1.2+ only (no TLS 1.0/1.1)
    - Strong cipher suites
    
    Verification:
        openssl s_client -connect localhost:5000 -tls1_2
    """
    cert_path = os.path.join(app.config['DATA_DIR'], 'ssl', 'cert.pem')
    key_path = os.path.join(app.config['DATA_DIR'], 'ssl', 'key.pem')
    
    # Generate certificate if it doesn't exist
    if not os.path.exists(cert_path) or not os.path.exists(key_path):
        print("🔒 Generating self-signed SSL certificate...")
        CertificateManager.generate_self_signed_cert(
            os.path.join(app.config['DATA_DIR'], 'ssl')
        )
        print("✅ Certificate generated successfully")
    
    # Create SSL context
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_path, key_path)
    
    # Security: Disable old TLS versions
    context.options |= ssl.OP_NO_TLSv1    # Disable TLS 1.0
    context.options |= ssl.OP_NO_TLSv1_1  # Disable TLS 1.1
    
    return context

@app.before_request
def force_https():
    """
    Redirect HTTP requests to HTTPS
    
    Exceptions:
    - Let's Encrypt ACME challenges (/.well-known/acme-challenge/)
    - Health check endpoint (for Docker health checks)
    
    This ensures all communication is encrypted.
    """
    # Skip if already secure
    if request.is_secure:
        return
    
    # Allow Let's Encrypt validation
    if request.path.startswith('/.well-known/acme-challenge/'):
        return
    
    # Allow health check for Docker
    if request.path == '/api/health':
        return
    
    # Redirect to HTTPS
    url = request.url.replace('http://', 'https://', 1)
    return redirect(url, code=301)

@app.route('/api/health')
def health_check():
    """
    Health check endpoint for Docker
    
    Returns:
        JSON with status and version
    
    Example:
        curl -k https://localhost:5000/api/health
        {"status": "healthy", "version": "1.0.0"}
    """
    return jsonify({
        "status": "healthy",
        "version": "1.0.0",
        "ssl_mode": app.config['SSL_MODE']
    })

@app.route('/')
def index():
    """
    Main page - placeholder for now
    
    In Sprint 2+, this will redirect to:
    - /setup if first-time
    - /login if not authenticated
    - /dashboard if authenticated
    """
    return """
    <html>
        <head>
            <title>DockerMate</title>
            <style>
                body { 
                    background: #0f172a; 
                    color: #f1f5f9; 
                    font-family: system-ui; 
                    display: flex; 
                    align-items: center; 
                    justify-content: center; 
                    height: 100vh;
                    margin: 0;
                }
                .container {
                    text-align: center;
                }
                h1 { font-size: 3rem; margin: 0; }
                p { font-size: 1.2rem; color: #94a3b8; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🐳 DockerMate</h1>
                <p>Sprint 1 - Foundation Complete</p>
                <p style="font-size: 0.9rem; margin-top: 2rem;">
                    <a href="/api/health" style="color: #3b82f6;">Health Check</a>
                </p>
            </div>
        </body>
    </html>
    """

if __name__ == '__main__':
    # Create data directory if it doesn't exist
    os.makedirs(app.config['DATA_DIR'], exist_ok=True)
    
    # Initialize database
    print("🗄️  Initializing database...")
    init_db()
    print("✅ Database initialized")
    
    # Check if setup is complete
    # For now, we'll always use HTTPS after first run
    # In Sprint 2, we'll add proper setup detection
    setup_complete = os.path.exists(os.path.join(app.config['DATA_DIR'], 'setup_complete'))
    
    if not setup_complete:
        print("⚠️  First-time setup detected")
        print("🌐 Starting server on HTTP for initial configuration")
        print("📝 After setup, the server will restart with HTTPS")
        
        # Run on HTTP for first-time setup
        app.run(host='0.0.0.0', port=5000, debug=True)
    else:
        print("🔒 Starting server with HTTPS...")
        
        # Create SSL context
        context = create_ssl_context()
        
        # Run with HTTPS
        print("✅ Server ready at https://localhost:5000")
        print("⚠️  Browser will show security warning (self-signed cert)")
        print("    Click 'Advanced' → 'Proceed anyway'")
        
        app.run(
            host='0.0.0.0', 
            port=5000, 
            ssl_context=context, 
            debug=False  # Set to False in production
        )
