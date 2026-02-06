"""
Volume Model — Sprint 5 Task 1

Tracks Docker volumes created or discovered by DockerMate.
Stores driver, mount point, labels, and options metadata alongside the
live Docker volume ID so the UI can display volume information and usage
without hitting the Docker daemon on every page load.

Columns
-------
volume_id   : Docker-assigned hex ID (stable identifier)
name        : Human-readable name; must be unique inside Docker
driver      : local | nfs | cifs | etc. (default: local)
mount_point : Physical path where volume data is stored
labels_json : JSON string of Docker labels (key-value metadata)
options_json: JSON string of driver-specific options
size_bytes  : Volume size in bytes (nullable - not all drivers report this)
managed     : True when DockerMate created it; False for pre-existing volumes
created_at  : Timestamp when volume was first tracked
updated_at  : Timestamp of last metadata update
"""

from sqlalchemy import Column, Integer, String, BigInteger, Boolean, DateTime, Text, Index
from sqlalchemy.sql import func
from backend.models.database import Base
import json


class Volume(Base):
    __tablename__ = 'volumes'

    # Primary key
    id = Column(Integer, primary_key=True)

    # Docker identifiers
    volume_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)

    # Core fields
    driver = Column(String(50), nullable=False, default='local')
    mount_point = Column(String(500))  # /var/lib/docker/volumes/{name}/_data

    # Metadata (stored as JSON strings)
    labels_json = Column(Text)  # JSON string of labels
    options_json = Column(Text)  # JSON string of driver options

    # Size tracking (optional - may not be available from Docker)
    size_bytes = Column(BigInteger)  # Nullable - not all drivers report size

    # Management tracking
    managed = Column(Boolean, default=True, nullable=False)  # DockerMate-created vs external

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Indexes
    __table_args__ = (
        Index('ix_volumes_driver', 'driver'),
        Index('ix_volumes_managed', 'managed'),
    )

    def __repr__(self):
        return f"<Volume {self.name} ({self.driver})>"

    def to_dict(self):
        """
        Convert volume to dictionary for API responses.

        Returns:
            dict: Volume data suitable for JSON serialization

        Educational:
            - Converts datetime objects to ISO format strings
            - Parses JSON strings back to objects for labels/options
            - Includes all fields needed for UI display
        """
        # Parse labels and options from JSON strings
        labels = {}
        if self.labels_json:
            try:
                labels = json.loads(self.labels_json)
            except (json.JSONDecodeError, TypeError):
                labels = {}

        options = {}
        if self.options_json:
            try:
                options = json.loads(self.options_json)
            except (json.JSONDecodeError, TypeError):
                options = {}

        return {
            'id': self.id,
            'volume_id': self.volume_id,
            'name': self.name,
            'driver': self.driver,
            'mount_point': self.mount_point,
            'labels': labels,
            'options': options,
            'size_bytes': self.size_bytes,
            'managed': self.managed,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
