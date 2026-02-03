"""
DockerMate - Update History Model (Sprint 3)
============================================

Tracks every image-update or rollback operation performed on a container.
One row per event — used for the rollback capability (knowing what the
previous image was) and for audit/history display.

Columns:
    container_name  — snapshot of the container name at update time
    old_image       — repository:tag before the update
    new_image       — repository:tag after the update
    old_digest      — registry digest of the image that was replaced
    new_digest      — registry digest of the image that was installed
    status          — 'success' | 'failed' | 'rolled_back'
    error_message   — filled in when status == 'failed'
    updated_at      — timestamp the operation completed
"""

from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from .database import Base


class UpdateHistory(Base):
    __tablename__ = 'update_history'

    id             = Column(Integer, primary_key=True)
    container_id   = Column(String(64), nullable=False, index=True)
    container_name = Column(String(255), nullable=False)
    old_image      = Column(String(512), nullable=False)
    new_image      = Column(String(512), nullable=False)
    old_digest     = Column(String(255))
    new_digest     = Column(String(255))
    status         = Column(String(32), nullable=False, default='success')   # success | failed | rolled_back
    error_message  = Column(Text)
    updated_at     = Column(DateTime, default=func.now())

    def __repr__(self):
        return f"<UpdateHistory {self.container_name}: {self.old_image} → {self.new_image} [{self.status}]>"

    def to_dict(self):
        return {
            'id':              self.id,
            'container_id':    self.container_id,
            'container_name':  self.container_name,
            'old_image':       self.old_image,
            'new_image':       self.new_image,
            'old_digest':      self.old_digest,
            'new_digest':      self.new_digest,
            'status':          self.status,
            'error_message':   self.error_message,
            'updated_at':      self.updated_at.isoformat() if self.updated_at else None
        }
