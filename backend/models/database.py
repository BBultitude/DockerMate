"""
Database Configuration and Setup Module

This module handles all SQLAlchemy configuration for DockerMate.
It uses SQLite as the database (perfect for single-user home labs).

Key Design Decisions:
- SQLite instead of PostgreSQL/MySQL: Simpler, no external server needed
- Single file database: Easy backup and restore
- Thread-safe configuration: check_same_thread=False for Flask
- Session factory pattern: Clean database connection management

Usage:
    from backend.models.database import engine, SessionLocal, Base, init_db
    
    # Initialize database (creates all tables)
    init_db()
    
    # Get a database session
    db = SessionLocal()
    try:
        # Do database operations
        user = db.query(User).first()
    finally:
        db.close()

Verification:
    python3 -c "from backend.models.database import init_db; init_db()"
    ls -la /tmp/dockermate.db  # Should exist
"""

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import Generator
import os
import logging

# Set up logging for database operations
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# Database Configuration
# =============================================================================

# Import Config for centralized configuration
try:
    from config import Config
    DATABASE_PATH = Config.DATABASE_PATH
except ImportError:
    # Fallback for standalone testing
    DATABASE_PATH = os.getenv('DATABASE_PATH', '/tmp/dockermate.db')

# Construct SQLite connection string
# Format: sqlite:///path/to/database.db
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Create SQLAlchemy engine
# check_same_thread=False: Required for SQLite with Flask (multi-threading)
# echo=False: Set to True to see all SQL queries (useful for debugging)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False  # Set to True for SQL query debugging
)

# Enable foreign key constraints for SQLite
# SQLite doesn't enforce foreign keys by default - we need to enable them
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """
    Enable foreign key constraints in SQLite
    
    This is called automatically when a new database connection is created.
    Foreign keys are essential for maintaining referential integrity.
    
    Example:
        If a session references a user, and that user is deleted,
        the session should also be deleted (CASCADE).
    """
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# Session factory - creates new database sessions
# autocommit=False: Manual transaction control (safer)
# autoflush=False: Manual flushing (more control)
# bind=engine: Connect to our SQLite database
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for all ORM models
# All database models will inherit from this
Base = declarative_base()

# =============================================================================
# Database Session Management
# =============================================================================

def get_db() -> Generator:
    """
    Dependency injection for database sessions (used in Flask routes)
    
    This is a generator function that provides a database session
    and ensures it's properly closed after use.
    
    Usage in Flask:
        @app.route('/api/users')
        def get_users():
            db = next(get_db())
            try:
                users = db.query(User).all()
                return jsonify([user.to_dict() for user in users])
            finally:
                db.close()
    
    Yields:
        Database session object
        
    Example:
        db = next(get_db())
        try:
            user = db.query(User).first()
        finally:
            db.close()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =============================================================================
# Database Initialization
# =============================================================================

def init_db():
    """
    Initialize the database by creating all tables

    IMPORTANT: This function is maintained for backward compatibility only.
    For schema changes, use Alembic migrations instead:
        - alembic revision --autogenerate -m "Description"
        - alembic upgrade head

    Migrations are automatically run on container startup via docker-entrypoint.sh

    This function should be called once when the application first starts.
    It reads all models that inherit from Base and creates their tables.

    Tables created:
        - users: User authentication
        - sessions: Session tracking
        - containers: Container metadata
        - host_config: Hardware configuration
        - environments: Environment tags
        - ssl_certificates: SSL cert management

    Safe to call multiple times - won't recreate existing tables.

    Verification:
        python3 -c "from backend.models.database import init_db; init_db()"

    Example:
        from backend.models.database import init_db
        init_db()  # Creates all tables
    """
    # Ensure data directory exists
    db_dir = os.path.dirname(DATABASE_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        logger.info(f"Created database directory: {db_dir}")
    
    # Import all models so they're registered with Base
    # This must happen before create_all() is called
    try:
        from backend.models.user import User
        from backend.models.session import Session
        from backend.models.environment import Environment
        from backend.models.host_config import HostConfig
        from backend.models.ssl_certificate import SSLCertificate
        from backend.models.image import Image
        from backend.models.update_history import UpdateHistory
        from backend.models.network import Network
        from backend.models.ip_reservation import IPReservation
        logger.info("All models imported successfully")
    except ImportError as e:
        logger.warning(f"Some models not yet created: {e}")
        # This is okay during development
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    logger.info(f"Database initialized at: {DATABASE_PATH}")

# =============================================================================
# Database Utility Functions
# =============================================================================

def get_db_info() -> dict:
    """
    Get information about the database
    
    Returns:
        Dictionary with database metadata:
        - path: Database file path
        - exists: Whether file exists
        - size_bytes: File size in bytes
        - tables: List of table names
        
    Example:
        info = get_db_info()
        print(f"Database at {info['path']}")
        print(f"Tables: {', '.join(info['tables'])}")
    """
    info = {
        'path': DATABASE_PATH,
        'exists': os.path.exists(DATABASE_PATH),
        'size_bytes': 0,
        'tables': []
    }
    
    if info['exists']:
        info['size_bytes'] = os.path.getsize(DATABASE_PATH)
        
        # Get table names
        from sqlalchemy import inspect
        inspector = inspect(engine)
        info['tables'] = inspector.get_table_names()
    
    return info

def reset_database():
    """
    DANGER: Drop all tables and recreate them
    
    This will DELETE ALL DATA in the database!
    Only use during development or testing.
    
    Usage:
        from backend.models.database import reset_database
        reset_database()  # All data will be lost!
        
    Verification:
        # Database will be empty after reset
        sqlite3 /tmp/dockermate.db "SELECT COUNT(*) FROM users;"
        # Should return 0
    """
    logger.warning("RESETTING DATABASE - ALL DATA WILL BE LOST!")
    
    # Drop all tables
    Base.metadata.drop_all(bind=engine)
    logger.info("All tables dropped")
    
    # Recreate all tables
    init_db()
    logger.info("Database reset complete")

# =============================================================================
# Testing and Verification
# =============================================================================

if __name__ == "__main__":
    """
    Test the database setup when run directly
    
    Usage:
        python3 backend/models/database.py
    """
    print("=" * 80)
    print("DockerMate Database Setup Test")
    print("=" * 80)
    
    # Initialize database
    print("\n1. Initializing database...")
    init_db()
    
    # Show database info
    print("\n2. Database information:")
    info = get_db_info()
    print(f"   Path: {info['path']}")
    print(f"   Exists: {info['exists']}")
    print(f"   Size: {info['size_bytes']} bytes")
    print(f"   Tables: {', '.join(info['tables']) if info['tables'] else 'None yet'}")
    
    # Test session creation
    print("\n3. Testing session creation...")
    db = SessionLocal()
    try:
        print("   ✅ Session created successfully")
    finally:
        db.close()
        print("   ✅ Session closed successfully")
    
    print("\n" + "=" * 80)
    print("Database setup test complete!")
    print("=" * 80)
