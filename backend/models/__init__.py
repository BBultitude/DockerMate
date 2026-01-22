"""
Database Models Package

This package contains all SQLAlchemy database models for DockerMate.

Models:
    User: Single admin user for authentication
    Session: User session tracking
    Environment: Environment tags (PRD/UAT/DEV/SANDBOX)
    HostConfig: Host configuration and hardware profile
    SSLCertificate: SSL certificate tracking
    
Future Models (Sprint 2+):
    Container: Container metadata
    Network: Network configuration
    IPReservation: IP address reservations
    UpdateCheck: Update detection results
    UpdateHistory: Update tracking
    HealthCheck: Health monitoring results
    LogAnalysis: Log analysis results
    SecurityEvent: Security audit logging

Usage:
    # Import database setup
    from backend.models.database import init_db, SessionLocal, Base
    
    # Import models
    from backend.models.user import User
    from backend.models.session import Session
    from backend.models.environment import Environment
    
    # Or import everything
    from backend.models import User, Session, Environment, init_db

Example:
    from backend.models import init_db, SessionLocal, User
    
    # Initialize database
    init_db()
    
    # Use models
    db = SessionLocal()
    try:
        user = db.query(User).first()
    finally:
        db.close()
"""

# Import database setup
from backend.models.database import (
    engine,
    SessionLocal,
    Base,
    get_db,
    init_db,
    get_db_info,
    reset_database
)

# Import models
from backend.models.user import User
from backend.models.session import Session
from backend.models.environment import Environment

# Try to import optional models (may not exist yet)
try:
    from backend.models.host_config import HostConfig
except ImportError:
    HostConfig = None

try:
    from backend.models.ssl_certificate import SSLCertificate
except ImportError:
    SSLCertificate = None

# Public API
__all__ = [
    # Database functions
    'engine',
    'SessionLocal',
    'Base',
    'get_db',
    'init_db',
    'get_db_info',
    'reset_database',
    
    # Models
    'User',
    'Session',
    'Environment',
    'HostConfig',
    'SSLCertificate',
]
