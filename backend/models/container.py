"""
Container Model - DockerMate Sprint 2 Task 3
============================================
SQLAlchemy model for container metadata and state management.

This model stores container information from Docker and provides:
- Container identification and naming
- State tracking (running, stopped, etc.)
- Environment tagging for organization
- Image association
- Port mapping storage
- Resource limits and usage tracking
- Timestamps for lifecycle management

Design Principles:
- Store Docker container metadata in SQLite
- Support environment-based organization (dev, prod, test, etc.)
- Track container state for UI display
- Enable filtering and searching
- Support hardware profile limits from Task 1
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, BigInteger, Boolean, DateTime, Text, Index
from backend.models.database import Base


class Container(Base):
    """
    Container model representing Docker container metadata.
    
    Stores container information retrieved from Docker daemon and provides
    organizational features like environment tags. Links to images and tracks
    container state for management operations.
    
    Relationships:
    - Belongs to one Image (many-to-one)
    - Has many Ports (one-to-many) - Sprint 2 Task 4
    - Has many Volumes (one-to-many) - Future sprint
    - Belongs to one or more Networks (many-to-many) - Sprint 4
    
    Hardware Awareness:
    - Container limits enforced by HardwareProfile (Task 1)
    - State tracking enables resource monitoring
    - CPU/memory metrics support profile-based warnings
    """
    
    __tablename__ = 'containers'
    
    # Primary key
    id = Column(Integer, primary_key=True)
    
    # Docker identification - container_id is Docker's unique 64-char hex ID
    container_id = Column(
        String(64), 
        unique=True, 
        nullable=False,
        index=True,
        comment='Docker container ID (64-character hex string)'
    )
    
    # Container naming and identification
    name = Column(
        String(255), 
        nullable=False,
        index=True,
        comment='Container name (user-friendly identifier)'
    )
    
    # State management - matches Docker container states
    # Valid states: created, running, paused, restarting, removing, exited, dead
    state = Column(
        String(20), 
        nullable=False, 
        default='created',
        index=True,
        comment='Current container state (running, stopped, etc.)'
    )
    
    # Environment tagging for organization
    # Examples: 'dev', 'prod', 'test', 'staging'
    # Can be null for untagged containers
    environment = Column(
        String(50),
        nullable=True,
        index=True,
        comment='Environment tag (dev, prod, test, etc.)'
    )
    
    # Image association - links to Image model (Sprint 3)
    # Foreign key will be added in Sprint 3 when Image model is created
    # For now, store image name as string
    image_name = Column(
        String(255),
        nullable=False,
        comment='Docker image name (e.g., nginx:latest)'
    )
    
    # Port mappings stored as JSON string
    # Format: [{"host": "8080", "container": "80", "protocol": "tcp"}, ...]
    # Parsed into Port objects in Sprint 2 Task 4
    ports_json = Column(
        Text,
        nullable=True,
        comment='JSON array of port mappings'
    )
    
    # Resource limits (optional) - CPU and memory constraints
    cpu_limit = Column(
        Float,
        nullable=True,
        comment='CPU limit in cores (e.g., 1.5 for 1.5 cores)'
    )
    
    memory_limit = Column(
        BigInteger,
        nullable=True,
        comment='Memory limit in bytes'
    )
    
    # Resource usage (updated periodically from Docker stats)
    cpu_usage = Column(
        Float,
        nullable=True,
        default=0.0,
        comment='Current CPU usage percentage'
    )
    
    memory_usage = Column(
        BigInteger,
        nullable=True,
        default=0,
        comment='Current memory usage in bytes'
    )
    
    # Restart policy - how container should restart on failure
    # Values: 'no', 'on-failure', 'always', 'unless-stopped'
    restart_policy = Column(
        String(20),
        nullable=True,
        default='no',
        comment='Container restart policy'
    )
    
    # Auto-start flag - whether container should start with DockerMate
    auto_start = Column(
        Boolean,
        nullable=False,
        default=False,
        comment='Whether container should auto-start with system'
    )
    
    # Timestamps for lifecycle tracking
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment='When container was created in Docker'
    )
    
    started_at = Column(
        DateTime,
        nullable=True,
        comment='When container was last started'
    )
    
    stopped_at = Column(
        DateTime,
        nullable=True,
        comment='When container was last stopped'
    )
    
    # DockerMate metadata
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment='When record was last updated in DockerMate'
    )
    
    # Composite index for common query: state + environment
    __table_args__ = (
        Index('ix_containers_state_environment', 'state', 'environment'),
    )
    
    def __init__(self, **kwargs):
        """Initialize container with defaults."""
        # Set defaults for fields not provided
        if 'state' not in kwargs:
            kwargs['state'] = 'created'
        if 'cpu_usage' not in kwargs:
            kwargs['cpu_usage'] = 0.0
        if 'memory_usage' not in kwargs:
            kwargs['memory_usage'] = 0
        if 'restart_policy' not in kwargs:
            kwargs['restart_policy'] = 'no'
        if 'auto_start' not in kwargs:
            kwargs['auto_start'] = False
        if 'created_at' not in kwargs:
            kwargs['created_at'] = datetime.utcnow()
        if 'updated_at' not in kwargs:
            kwargs['updated_at'] = datetime.utcnow()
        
        super().__init__(**kwargs)

    def __repr__(self):
        """String representation for debugging and logging."""
        return f'<Container {self.name} ({self.state})>'
    
    def to_dict(self):
        """
        Convert container to dictionary for API responses.
        
        Returns:
            dict: Container data including all fields and computed properties
        
        Note:
            - Timestamps converted to ISO format strings
            - Null values preserved for optional fields
            - Ports JSON returned as-is (parsed in Task 4)
        """
        return {
            'id': self.id,
            'container_id': self.container_id,
            'name': self.name,
            'state': self.state,
            'environment': self.environment,
            'image_name': self.image_name,
            'ports_json': self.ports_json,
            'cpu_limit': self.cpu_limit,
            'memory_limit': self.memory_limit,
            'cpu_usage': self.cpu_usage,
            'memory_usage': self.memory_usage,
            'restart_policy': self.restart_policy,
            'auto_start': self.auto_start,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'stopped_at': self.stopped_at.isoformat() if self.stopped_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @property
    def is_running(self):
        """
        Check if container is currently running.
        
        Returns:
            bool: True if state is 'running'
        """
        return self.state == 'running'
    
    @property
    def uptime_seconds(self):
        """
        Calculate container uptime in seconds.
        
        Returns:
            int: Seconds since container started, or 0 if not running
            
        Note:
            Returns 0 if container is not running or has no start time
        """
        if not self.is_running or not self.started_at:
            return 0
        return int((datetime.utcnow() - self.started_at).total_seconds())
    
    @property
    def memory_usage_mb(self):
        """
        Get memory usage in megabytes for display.
        
        Returns:
            float: Memory usage in MB, or 0.0 if not available
        """
        if not self.memory_usage:
            return 0.0
        return round(self.memory_usage / (1024 * 1024), 2)
    
    @property
    def memory_limit_mb(self):
        """
        Get memory limit in megabytes for display.
        
        Returns:
            float: Memory limit in MB, or None if unlimited
        """
        if not self.memory_limit:
            return None
        return round(self.memory_limit / (1024 * 1024), 2)
    
    def update_state(self, new_state, timestamp=None):
        """
        Update container state and set appropriate timestamp.
        
        Args:
            new_state (str): New container state
            timestamp (datetime, optional): Timestamp for state change
            
        Note:
            - Updates started_at when transitioning to 'running'
            - Updates stopped_at when transitioning to stopped states
            - Always updates updated_at timestamp
        """
        self.state = new_state
        
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        # Set appropriate lifecycle timestamp based on state
        if new_state == 'running':
            self.started_at = timestamp
        elif new_state in ('exited', 'dead'):
            self.stopped_at = timestamp
        
        self.updated_at = timestamp
    
    def update_resources(self, cpu_usage=None, memory_usage=None):
        """
        Update container resource usage metrics.
        
        Args:
            cpu_usage (float, optional): CPU usage percentage
            memory_usage (int, optional): Memory usage in bytes
            
        Note:
            Only updates provided values, leaves others unchanged
        """
        if cpu_usage is not None:
            self.cpu_usage = cpu_usage
        if memory_usage is not None:
            self.memory_usage = memory_usage
        
        self.updated_at = datetime.utcnow()
    
    @staticmethod
    def validate_state(state):
        """
        Validate container state value.
        
        Args:
            state (str): State to validate
            
        Returns:
            bool: True if state is valid
            
        Note:
            Valid states match Docker container states
        """
        valid_states = {
            'created', 'running', 'paused', 'restarting',
            'removing', 'exited', 'dead'
        }
        return state in valid_states
    
    @staticmethod
    def validate_restart_policy(policy):
        """
        Validate restart policy value.
        
        Args:
            policy (str): Policy to validate
            
        Returns:
            bool: True if policy is valid
        """
        valid_policies = {'no', 'on-failure', 'always', 'unless-stopped'}
        return policy in valid_policies