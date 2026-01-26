"""
Host Configuration Model

Stores hardware profile detection results and system configuration.
This is a singleton model - only one row should exist in the database.

Hardware Profiles:
    RASPBERRY_PI: <= 4 cores, <= 8GB RAM, max 15 containers
    LOW_END: <= 4 cores, <= 16GB RAM, max 20 containers
    MEDIUM_SERVER: <= 16 cores, <= 64GB RAM, max 50 containers
    HIGH_END: <= 32 cores, <= 128GB RAM, max 100 containers
    ENTERPRISE: > 32 cores, > 128GB RAM, max 200 containers

Container Limits:
    - 0-75% of max: No warnings
    - 75-90% of max: Approaching limit warning
    - 90-100% of max: At limit warning
    - >100%: Blocked unless user overrides

Usage:
    from backend.models.host_config import HostConfig
    
    # Get or create config
    config = HostConfig.get_or_create(db)
    
    # Check if at container limit
    if config.is_at_container_limit(current_count=45):
        print("Warning: approaching container limit")
"""

from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime
from sqlalchemy.sql import func
from backend.models.database import Base


class HostConfig(Base):
    """
    Host configuration and hardware profile
    
    Singleton model - only one row should exist.
    Stores detected hardware profile and enforces container limits.
    """
    
    __tablename__ = 'host_config'
    
    # Primary key
    id = Column(Integer, primary_key=True, default=1)
    
    # Hardware Detection
    profile_name = Column(String(50), nullable=False)  # RASPBERRY_PI, LOW_END, etc.
    cpu_cores = Column(Integer, nullable=False)
    ram_gb = Column(Float, nullable=False)
    is_raspberry_pi = Column(Boolean, default=False)
    
    # Container Limits
    max_containers = Column(Integer, nullable=False, default=50)
    container_limit_warning_threshold = Column(Integer, default=75)  # Percentage
    container_limit_critical_threshold = Column(Integer, default=90)  # Percentage
    
    # Feature Flags (based on hardware)
    enable_continuous_monitoring = Column(Boolean, default=True)
    enable_log_analysis = Column(Boolean, default=True)
    enable_auto_update = Column(Boolean, default=True)
    
    # Update Intervals (seconds)
    update_check_interval = Column(Integer, default=21600)  # 6 hours default
    health_check_interval = Column(Integer, default=300)     # 5 minutes default
    
    # Network Limits
    network_size_limit = Column(String(10), default='/24')  # Max subnet size
    
    # Timestamps
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return (
            f"<HostConfig(profile={self.profile_name}, "
            f"cpu={self.cpu_cores}, ram={self.ram_gb}GB, "
            f"max_containers={self.max_containers})>"
        )
    
    @classmethod
    def get_or_create(cls, db):
        """
        Get existing config or create new one
        
        Args:
            db: Database session
            
        Returns:
            HostConfig instance
        """
        config = db.query(cls).filter(cls.id == 1).first()
        if not config:
            # Will be populated by hardware detector
            config = cls(
                id=1,
                profile_name='UNKNOWN',
                cpu_cores=0,
                ram_gb=0.0,
                max_containers=50
            )
            db.add(config)
            db.commit()
            db.refresh(config)
        return config
    
    def is_at_container_limit(self, current_count, strict=False):
        """
        Check if current container count is at or near limit
        
        Args:
            current_count: Current number of containers
            strict: If True, only return True if exactly at or over limit
            
        Returns:
            tuple: (bool: at_limit, str: warning_level)
                warning_level: 'none', 'warning', 'critical', 'exceeded'
        """
        percentage = (current_count / self.max_containers) * 100
        
        if current_count > self.max_containers:
            return (True, 'exceeded')
        elif percentage >= self.container_limit_critical_threshold:
            return (not strict, 'critical')
        elif percentage >= self.container_limit_warning_threshold:
            return (not strict, 'warning')
        else:
            return (False, 'none')
    
    def get_container_limit_message(self, current_count):
        """
        Get human-readable message about container limits
        
        Args:
            current_count: Current number of containers
            
        Returns:
            str: Message describing limit status
        """
        at_limit, level = self.is_at_container_limit(current_count)
        remaining = self.max_containers - current_count
        percentage = (current_count / self.max_containers) * 100
        
        if level == 'exceeded':
            return (
                f"⛔ Container limit exceeded! "
                f"You have {current_count} containers but your {self.profile_name} "
                f"profile supports a maximum of {self.max_containers}. "
                f"Consider removing unused containers or upgrading hardware."
            )
        elif level == 'critical':
            return (
                f"⚠️ Critical: {remaining} containers remaining "
                f"({current_count}/{self.max_containers}, {percentage:.0f}%). "
                f"You are near the limit for your {self.profile_name} profile."
            )
        elif level == 'warning':
            return (
                f"⚠️ Warning: {remaining} containers remaining "
                f"({current_count}/{self.max_containers}, {percentage:.0f}%). "
                f"Approaching limit for your {self.profile_name} profile."
            )
        else:
            return (
                f"✅ {remaining} containers remaining "
                f"({current_count}/{self.max_containers}, {percentage:.0f}%)"
            )
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'profile_name': self.profile_name,
            'cpu_cores': self.cpu_cores,
            'ram_gb': self.ram_gb,
            'is_raspberry_pi': self.is_raspberry_pi,
            'max_containers': self.max_containers,
            'container_limit_warning_threshold': self.container_limit_warning_threshold,
            'container_limit_critical_threshold': self.container_limit_critical_threshold,
            'enable_continuous_monitoring': self.enable_continuous_monitoring,
            'enable_log_analysis': self.enable_log_analysis,
            'enable_auto_update': self.enable_auto_update,
            'update_check_interval': self.update_check_interval,
            'health_check_interval': self.health_check_interval,
            'network_size_limit': self.network_size_limit,
            'detected_at': self.detected_at.isoformat() if self.detected_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
