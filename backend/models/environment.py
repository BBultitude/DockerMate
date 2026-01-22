"""
Environment Model - Environment Tag Management

This module defines the Environment database model for DockerMate.

Purpose: Define environment types for containers and hosts
Environments help organize containers and apply appropriate safety levels.

Environment Types (Default):
    PRD (Production): Critical services, maximum safety
    UAT (User Acceptance Testing): Pre-production testing
    DEV (Development): Development work, relaxed safety
    SANDBOX (Experimental): Testing and experiments, no safety

Design Philosophy:
- Safety levels based on environment
- Visual indicators (colors, icons)
- Prevent accidents in production
- Allow fast iteration in development

Database Table: environments

Columns:
    id: Primary key
    code: Unique code (PRD, UAT, DEV, SANDBOX)
    name: Display name
    description: What this environment is for
    color: Color for UI (red, yellow, green, blue)
    icon_emoji: Emoji icon for visual identification
    display_order: Sort order in UI
    require_confirmation: Force confirmation for destructive actions
    prevent_auto_update: Prevent automatic updates

Environment-Based Features:
    PRD:
        - Confirmation required for updates/deletions
        - No auto-updates by default
        - Backup before changes
        - High visibility warnings
    
    UAT:
        - Some confirmations
        - Optional auto-updates
        - Medium visibility warnings
    
    DEV:
        - No confirmations (fast iteration)
        - Auto-updates enabled by default
        - Low visibility warnings
    
    SANDBOX:
        - No confirmations
        - Auto-updates enabled
        - Experimental features available

Usage:
    from backend.models.environment import Environment
    
    # Get all environments
    envs = db.query(Environment).order_by(Environment.display_order).all()
    
    # Get production environment
    prd = db.query(Environment).filter_by(code='PRD').first()
    
    # Check if confirmation required
    if prd.require_confirmation:
        # Show confirmation dialog
        pass

Verification:
    python3 -c "from backend.models.environment import Environment; print(Environment.__tablename__)"
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.sql import func
from backend.models.database import Base
from typing import Dict, List
from datetime import datetime

class Environment(Base):
    """
    Environment model for organizing containers
    
    Environments help apply appropriate safety levels and policies
    to containers based on their purpose (production vs development).
    
    Attributes:
        id (int): Primary key
        code (str): Unique environment code (PRD, UAT, DEV, SANDBOX)
        name (str): Display name ("Production", "Development", etc.)
        description (str): What this environment is for
        color (str): Color for UI badges (red, yellow, green, blue, gray)
        icon_emoji (str): Emoji icon for visual identification
        display_order (int): Sort order in UI (lower = first)
        require_confirmation (bool): Force confirmation for destructive actions
        prevent_auto_update (bool): Prevent automatic updates
        created_at (datetime): When environment was created
        updated_at (datetime): Last modification
    
    Example:
        # Create production environment
        prd = Environment(
            code='PRD',
            name='Production',
            description='Critical production services',
            color='red',
            icon_emoji='🔴',
            display_order=1,
            require_confirmation=True,
            prevent_auto_update=True
        )
        db.add(prd)
        db.commit()
    """
    
    # Table name in database
    __tablename__ = "environments"
    
    # ==========================================================================
    # Columns
    # ==========================================================================
    
    # Primary key
    id = Column(
        Integer,
        primary_key=True,
        index=True,
        comment="Primary key for environments"
    )
    
    # Environment code - PRD, UAT, DEV, SANDBOX
    # Must be unique, used for filtering/querying
    code = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique environment code (PRD, UAT, DEV, SANDBOX)"
    )
    
    # Display name - shown in UI
    name = Column(
        String(255),
        nullable=False,
        comment="Display name (Production, Development, etc.)"
    )
    
    # Description - explains purpose
    description = Column(
        Text,
        nullable=True,
        comment="What this environment is for"
    )
    
    # Color for UI badges/indicators
    # Tailwind CSS colors: red, yellow, green, blue, gray
    color = Column(
        String(20),
        default='gray',
        comment="Color for UI (red, yellow, green, blue, gray)"
    )
    
    # Icon emoji for visual identification
    icon_emoji = Column(
        String(10),
        default='🔵',
        comment="Emoji icon for visual identification"
    )
    
    # Display order - controls sorting in UI
    # Lower number = displayed first
    display_order = Column(
        Integer,
        default=999,
        comment="Sort order in UI (lower = first)"
    )
    
    # Require confirmation for destructive actions
    # If True: Show confirmation dialogs for updates/deletions
    require_confirmation = Column(
        Boolean,
        default=False,
        comment="Force confirmation for destructive actions"
    )
    
    # Prevent auto-updates
    # If True: Don't auto-update containers in this environment
    prevent_auto_update = Column(
        Boolean,
        default=False,
        comment="Prevent automatic updates"
    )
    
    # Timestamps
    created_at = Column(
        DateTime,
        server_default=func.now(),
        comment="Environment creation timestamp"
    )
    
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last update timestamp"
    )
    
    # ==========================================================================
    # Methods
    # ==========================================================================
    
    def to_dict(self) -> Dict:
        """
        Convert environment to dictionary (for JSON responses)
        
        Returns:
            Dictionary representation of environment
            
        Example:
            env = db.query(Environment).filter_by(code='PRD').first()
            env_dict = env.to_dict()
            # Returns: {'code': 'PRD', 'name': 'Production', ...}
        """
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'color': self.color,
            'icon_emoji': self.icon_emoji,
            'display_order': self.display_order,
            'require_confirmation': self.require_confirmation,
            'prevent_auto_update': self.prevent_auto_update,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self) -> str:
        """
        String representation for debugging
        
        Returns:
            Human-readable string showing environment info
            
        Example:
            env = db.query(Environment).first()
            print(env)
            # Output: <Environment(PRD, Production, requires_confirmation=True)>
        """
        return (
            f"<Environment("
            f"{self.code}, "
            f"{self.name}, "
            f"requires_confirmation={self.require_confirmation}"
            f")>"
        )
    
    # ==========================================================================
    # Static Methods - Default Environments
    # ==========================================================================
    
    @staticmethod
    def get_default_environments() -> List[Dict]:
        """
        Get default environment configurations
        
        Returns:
            List of environment dictionaries ready for insertion
            
        Example:
            from backend.models.environment import Environment
            defaults = Environment.get_default_environments()
            for env_data in defaults:
                env = Environment(**env_data)
                db.add(env)
            db.commit()
        """
        return [
            {
                'code': 'PRD',
                'name': 'Production',
                'description': 'Critical production services - maximum safety',
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
                'description': 'Development environment - fast iteration',
                'color': 'green',
                'icon_emoji': '🟢',
                'display_order': 3,
                'require_confirmation': False,
                'prevent_auto_update': False
            },
            {
                'code': 'SANDBOX',
                'name': 'Sandbox',
                'description': 'Experimental environment - no restrictions',
                'color': 'blue',
                'icon_emoji': '🔵',
                'display_order': 4,
                'require_confirmation': False,
                'prevent_auto_update': False
            }
        ]
    
    @staticmethod
    def seed_defaults(db) -> int:
        """
        Seed database with default environments
        
        Safe to call multiple times - won't create duplicates.
        
        Args:
            db: Database session
            
        Returns:
            Number of environments created
            
        Example:
            from backend.models.database import SessionLocal
            from backend.models.environment import Environment
            
            db = SessionLocal()
            try:
                created = Environment.seed_defaults(db)
                print(f"Created {created} default environments")
            finally:
                db.close()
        """
        created = 0
        
        for env_data in Environment.get_default_environments():
            # Check if already exists
            existing = db.query(Environment).filter_by(code=env_data['code']).first()
            if not existing:
                env = Environment(**env_data)
                db.add(env)
                created += 1
        
        db.commit()
        return created

# =============================================================================
# Testing and Verification
# =============================================================================

if __name__ == "__main__":
    """
    Test the Environment model when run directly
    
    Usage:
        python3 backend/models/environment.py
    """
    from backend.models.database import init_db, SessionLocal
    import json
    
    print("=" * 80)
    print("DockerMate Environment Model Test")
    print("=" * 80)
    
    # Initialize database
    print("\n1. Initializing database...")
    init_db()
    
    # Seed default environments
    print("\n2. Seeding default environments...")
    db = SessionLocal()
    try:
        created = Environment.seed_defaults(db)
        print(f"   ✅ Created {created} default environments")
        
        # List all environments
        print("\n3. Listing all environments...")
        envs = db.query(Environment).order_by(Environment.display_order).all()
        for env in envs:
            print(f"   {env.icon_emoji} {env.code}: {env.name}")
            print(f"      Confirmation required: {env.require_confirmation}")
            print(f"      Prevent auto-update: {env.prevent_auto_update}")
        
        # Test to_dict
        print("\n4. Testing to_dict()...")
        if envs:
            env_dict = envs[0].to_dict()
            print(f"   {json.dumps(env_dict, indent=2)}")
        
        # Test filtering
        print("\n5. Testing filtering...")
        prd = db.query(Environment).filter_by(code='PRD').first()
        print(f"   Production environment: {prd}")
        
        print("\n   ✅ All tests passed!")
        
    except Exception as e:
        print(f"\n   ❌ Error: {e}")
        db.rollback()
    finally:
        db.close()
    
    print("\n" + "=" * 80)
    print("Environment model test complete!")
    print("=" * 80)
