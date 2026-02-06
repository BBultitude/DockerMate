"""
Stack Model - Docker Compose Stack Management

Represents a Docker Compose stack (multi-container application).
Stores the compose file content and tracks deployed services.

Design:
- Stack name must be unique
- Compose YAML stored in database for versioning
- File also stored on filesystem at /app/stacks/{name}/docker-compose.yml
- Status tracked: pending, deploying, running, stopped, failed
- Tracks all containers/networks/volumes created by this stack
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Index
from sqlalchemy.sql import func
from backend.models.database import Base
import json
from datetime import datetime


class Stack(Base):
    """
    Docker Compose Stack Model

    Represents a multi-container application defined by docker-compose.yml
    """
    __tablename__ = 'stacks'

    # Primary key
    id = Column(Integer, primary_key=True)

    # Stack identification
    name = Column(String(255), unique=True, nullable=False, index=True)  # e.g., "wordpress-blog"
    description = Column(Text)  # User-provided description

    # Compose file content
    compose_yaml = Column(Text, nullable=False)  # Full docker-compose.yml content
    compose_version = Column(String(10))  # e.g., "3.8", "3.9"

    # Deployment status
    status = Column(String(20), default='stopped', nullable=False)  # pending, deploying, running, stopped, failed

    # File location
    file_path = Column(String(500))  # Path to compose file on filesystem

    # Tracking
    services_json = Column(Text)  # JSON array of service names defined in compose file
    container_ids_json = Column(Text)  # JSON array of container IDs created by this stack
    network_names_json = Column(Text)  # JSON array of network names created by this stack
    volume_names_json = Column(Text)  # JSON array of volume names created by this stack

    # Management
    managed = Column(Boolean, default=True, nullable=False)  # Created by DockerMate vs external
    auto_start = Column(Boolean, default=False, nullable=False)  # Start on DockerMate startup

    # Environment variables (stored as JSON)
    env_vars_json = Column(Text)  # JSON object of environment variables to override

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    deployed_at = Column(DateTime)  # Last successful deployment

    # Indexes
    __table_args__ = (
        Index('ix_stacks_status', 'status'),
        Index('ix_stacks_managed', 'managed'),
    )

    def to_dict(self):
        """
        Convert Stack to dictionary for API responses

        Returns:
            dict: Stack data with parsed JSON fields
        """
        # Parse JSON fields
        services = json.loads(self.services_json) if self.services_json else []
        container_ids = json.loads(self.container_ids_json) if self.container_ids_json else []
        network_names = json.loads(self.network_names_json) if self.network_names_json else []
        volume_names = json.loads(self.volume_names_json) if self.volume_names_json else []
        env_vars = json.loads(self.env_vars_json) if self.env_vars_json else {}

        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'compose_yaml': self.compose_yaml,
            'compose_version': self.compose_version,
            'status': self.status,
            'file_path': self.file_path,
            'services': services,
            'service_count': len(services),
            'container_ids': container_ids,
            'network_names': network_names,
            'volume_names': volume_names,
            'env_vars': env_vars,
            'managed': self.managed,
            'auto_start': self.auto_start,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'deployed_at': self.deployed_at.isoformat() if self.deployed_at else None
        }

    def __repr__(self):
        return f"<Stack(name='{self.name}', status='{self.status}', services={len(json.loads(self.services_json) if self.services_json else [])})>"
