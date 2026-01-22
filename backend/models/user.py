"""
User Model - Authentication and User Management

This module defines the User database model for DockerMate.

Key Design Decision: SINGLE USER ONLY
DockerMate is designed for home labs (single-user environments).
There will only ever be ONE user in this table with username='admin'.
No multi-user support - that's enterprise complexity we don't need.

Why Single User:
- Home labs are typically managed by one person
- No need for user management overhead
- No need for roles/permissions
- Simpler authentication flow
- Easier password reset

Database Table: users

Columns:
    id: Primary key (always 1)
    username: Always 'admin' (never changes)
    password_hash: Bcrypt hashed password (work factor 12)
    force_password_change: Flag for password resets
    password_reset_at: Timestamp of last reset
    created_at: Account creation timestamp
    updated_at: Last modification timestamp

Security Features:
- Password stored as bcrypt hash (never plain text)
- Work factor 12 (good balance for home hardware)
- Force password change after reset
- Timestamp tracking for security audits

Usage:
    from backend.models.user import User
    from backend.auth.password_manager import PasswordManager
    
    # Create user
    user = User(
        password_hash=PasswordManager.hash_password("MyPassword123")
    )
    db.add(user)
    db.commit()
    
    # Verify password
    if PasswordManager.verify_password(entered_password, user.password_hash):
        print("Login successful")

Verification:
    python3 -c "from backend.models.user import User; print(User.__tablename__)"
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from backend.models.database import Base
from typing import Dict, Optional
import json

class User(Base):
    """
    User model for single-user authentication
    
    DockerMate is designed for home labs with single-user access.
    This table will only ever contain ONE row with username='admin'.
    
    Attributes:
        id (int): Primary key (always 1 for the single admin user)
        username (str): Always 'admin' - never changes
        password_hash (str): Bcrypt hashed password (work factor 12)
        force_password_change (bool): True after password reset
        password_reset_at (datetime): When password was last reset
        created_at (datetime): When user was created (first setup)
        updated_at (datetime): Last password change or update
    
    Example:
        # Create the admin user during initial setup
        from backend.auth.password_manager import PasswordManager
        
        user = User(
            username='admin',
            password_hash=PasswordManager.hash_password('InitialPassword123')
        )
        db.add(user)
        db.commit()
        
        # Later: verify login
        user = db.query(User).first()
        if PasswordManager.verify_password(password, user.password_hash):
            # Login successful
            pass
    """
    
    # Table name in database
    __tablename__ = "users"
    
    # ==========================================================================
    # Columns
    # ==========================================================================
    
    # Primary key - always 1 for single user
    id = Column(
        Integer,
        primary_key=True,
        index=True,
        comment="Primary key - always 1 for single admin user"
    )
    
    # Username - always 'admin'
    username = Column(
        String(255),
        default='admin',
        nullable=False,
        comment="Username - always 'admin' for single-user design"
    )
    
    # Password hash - bcrypt with work factor 12
    # Never store plain text passwords!
    password_hash = Column(
        String(255),
        nullable=False,
        comment="Bcrypt password hash (work factor 12)"
    )
    
    # Force password change - set to True after password reset
    # User must change password on next login
    force_password_change = Column(
        Boolean,
        default=False,
        comment="Force password change on next login (after reset)"
    )
    
    # Password reset timestamp - when reset_password.py was run
    password_reset_at = Column(
        DateTime,
        nullable=True,
        comment="Timestamp of last password reset"
    )
    
    # Created timestamp - when initial setup was completed
    created_at = Column(
        DateTime,
        server_default=func.now(),
        comment="Account creation timestamp (first setup)"
    )
    
    # Updated timestamp - automatically updated on any change
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last update timestamp (password changes, etc.)"
    )
    
    # ==========================================================================
    # Methods
    # ==========================================================================
    
    def to_dict(self, include_password_hash: bool = False) -> Dict:
        """
        Convert user to dictionary (for JSON responses)
        
        Args:
            include_password_hash: If True, include password hash (dangerous!)
                                   Default False for security
        
        Returns:
            Dictionary representation of user
            
        Example:
            user = db.query(User).first()
            user_dict = user.to_dict()
            # Returns: {'id': 1, 'username': 'admin', 'created_at': '...'}
            
        Security Note:
            NEVER send password hash to frontend!
            Only include for debugging/testing purposes.
        """
        data = {
            'id': self.id,
            'username': self.username,
            'force_password_change': self.force_password_change,
            'password_reset_at': self.password_reset_at.isoformat() if self.password_reset_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        # Only include password hash if explicitly requested (dangerous!)
        if include_password_hash:
            data['password_hash'] = self.password_hash
        
        return data
    
    def __repr__(self) -> str:
        """
        String representation for debugging
        
        Returns:
            Human-readable string showing user info
            
        Example:
            user = db.query(User).first()
            print(user)
            # Output: <User(id=1, username='admin', created_at='2026-01-21 10:30:00')>
        """
        return (
            f"<User("
            f"id={self.id}, "
            f"username='{self.username}', "
            f"force_password_change={self.force_password_change}, "
            f"created_at='{self.created_at}'"
            f")>"
        )
    
    # ==========================================================================
    # Static Methods - Helper Functions
    # ==========================================================================
    
    @staticmethod
    def get_admin(db) -> Optional['User']:
        """
        Get the admin user (should only be one)
        
        Args:
            db: Database session
            
        Returns:
            User object or None if not found
            
        Example:
            from backend.models.database import SessionLocal
            db = SessionLocal()
            try:
                admin = User.get_admin(db)
                if admin:
                    print(f"Admin created at: {admin.created_at}")
            finally:
                db.close()
        """
        return db.query(User).first()
    
    @staticmethod
    def exists(db) -> bool:
        """
        Check if admin user exists (setup complete)
        
        Args:
            db: Database session
            
        Returns:
            True if user exists, False otherwise
            
        Example:
            from backend.models.database import SessionLocal
            db = SessionLocal()
            try:
                if User.exists(db):
                    print("Setup complete")
                else:
                    print("Need to run initial setup")
            finally:
                db.close()
        """
        return db.query(User).count() > 0

# =============================================================================
# Testing and Verification
# =============================================================================

if __name__ == "__main__":
    """
    Test the User model when run directly
    
    Usage:
        python3 backend/models/user.py
    """
    from backend.models.database import init_db, SessionLocal
    
    print("=" * 80)
    print("DockerMate User Model Test")
    print("=" * 80)
    
    # Initialize database
    print("\n1. Initializing database...")
    init_db()
    
    # Create test user
    print("\n2. Creating test user...")
    db = SessionLocal()
    try:
        # Check if user already exists
        existing_user = User.get_admin(db)
        if existing_user:
            print(f"   ⚠️  User already exists: {existing_user}")
            print("   Deleting for fresh test...")
            db.delete(existing_user)
            db.commit()
        
        # Create new user
        user = User(
            username='admin',
            password_hash='$2b$12$test_hash_not_real'  # Fake hash for testing
        )
        db.add(user)
        db.commit()
        print(f"   ✅ User created: {user}")
        
        # Test to_dict()
        print("\n3. Testing to_dict()...")
        user_dict = user.to_dict()
        print(f"   User dict (safe): {json.dumps(user_dict, indent=2)}")
        
        # Test static methods
        print("\n4. Testing static methods...")
        admin = User.get_admin(db)
        print(f"   get_admin(): {admin}")
        
        exists = User.exists(db)
        print(f"   exists(): {exists}")
        
        print("\n   ✅ All tests passed!")
        
    except Exception as e:
        print(f"\n   ❌ Error: {e}")
        db.rollback()
    finally:
        db.close()
    
    print("\n" + "=" * 80)
    print("User model test complete!")
    print("=" * 80)
