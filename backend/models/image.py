"""
DockerMate - Image Model (Sprint 3)
====================================

Database model for tracking Docker images with update detection.

This model stores information about Docker images pulled to the local system,
including metadata for update checking and lifecycle tracking.

Educational Notes:
- Images are identified by SHA256 digest (immutable)
- repository:tag combination can change over time (mutable)
- Tracking pulled_at and last_checked enables update notifications
- Storing digest allows comparison with registry for updates
"""

from sqlalchemy import Column, Integer, String, BigInteger, DateTime, Boolean, Text
from sqlalchemy.sql import func
from .database import Base


class Image(Base):
    """
    Docker image record for local image tracking and update management.

    Attributes:
        id: Primary key
        image_id: Docker's SHA256 image ID (unique identifier)
        repository: Image repository name (e.g., "nginx", "mysql")
        tag: Image tag (e.g., "latest", "8.0", "alpine")
        previous_tag: Tag before becoming dangling (<none>)
        digest: SHA256 content digest for update detection
        size_bytes: Image size in bytes
        created_at: When the image was created (from Docker metadata)
        pulled_at: When we pulled/imported this image
        last_checked: Last time we checked for updates
        update_available: Flag indicating newer version exists in registry
        labels_json: JSON string of Docker labels

    Educational:
        - image_id is Docker's internal ID (sha256:abc123...)
        - digest is the manifest digest used for update checks
        - repository + tag form the user-friendly image reference
        - Labels can contain metadata like maintainer, version, etc.
    """

    __tablename__ = 'images'

    # Primary key
    id = Column(Integer, primary_key=True)

    # Docker identifiers
    image_id = Column(String(64), unique=True, nullable=False, index=True)
    repository = Column(String(255), nullable=False, index=True)
    tag = Column(String(255), nullable=False, index=True)
    previous_tag = Column(String(255), nullable=True)  # Tag before becoming <none>
    digest = Column(String(255))  # SHA256 digest for update detection

    # Size and metadata
    size_bytes = Column(BigInteger)
    labels_json = Column(Text)  # JSON of Docker labels

    # Timestamps
    created_at = Column(DateTime)  # When image was created (from Docker)
    pulled_at = Column(DateTime, default=func.now())  # When we pulled it
    last_checked = Column(DateTime)  # Last time we checked for updates

    # Update tracking
    update_available = Column(Boolean, default=False)

    def __repr__(self):
        """String representation for debugging."""
        return f"<Image {self.repository}:{self.tag} ({self.image_id[:12]})>"

    def to_dict(self):
        """
        Convert image to dictionary for API responses.

        Returns:
            dict: Image data suitable for JSON serialization

        Educational:
            - Converts datetime objects to ISO format strings
            - Includes all fields needed for UI display
            - Size converted to human-readable format in frontend
        """
        return {
            'id': self.id,
            'image_id': self.image_id,
            'repository': self.repository,
            'tag': self.tag,
            'previous_tag': self.previous_tag,
            'full_name': f"{self.repository}:{self.tag}",
            'digest': self.digest,
            'size_bytes': self.size_bytes,
            'labels_json': self.labels_json,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'pulled_at': self.pulled_at.isoformat() if self.pulled_at else None,
            'last_checked': self.last_checked.isoformat() if self.last_checked else None,
            'update_available': self.update_available
        }
