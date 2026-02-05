"""
IP Reservation Model — Sprint 4 Task 4

Each row represents a single reserved IP address inside a Docker network.
Rows with the same ``range_name`` belong to a logical reservation block
(e.g. ".10–.19 for web services").

Columns
-------
network_id   : FK → networks.id  (the SQLAlchemy auto-increment PK)
ip_address   : The reserved IPv4 address (unique per network)
container_id : FK → containers.id when the IP is actively assigned;
               NULL when the slot is reserved but unoccupied
range_name   : Human-readable label that groups IPs into a block
               (e.g. "Web services").  NULL for single-IP reservations.
description  : Free-text note about the reserved block
"""

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from backend.models.database import Base


class IPReservation(Base):
    __tablename__ = 'ip_reservations'

    id = Column(Integer, primary_key=True)
    network_id = Column(Integer, ForeignKey('networks.id', ondelete='CASCADE'), nullable=False, index=True)
    ip_address = Column(String(45), nullable=False)
    container_id = Column(Integer, ForeignKey('containers.id', ondelete='SET NULL'), nullable=True)
    range_name = Column(String(255), nullable=True)
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('network_id', 'ip_address', name='uq_reservation_network_ip'),
    )

    def __repr__(self):
        return f"<IPReservation {self.ip_address} on network {self.network_id} [{self.range_name or 'single'}]>"

    def to_dict(self):
        return {
            'id': self.id,
            'network_id': self.network_id,
            'ip_address': self.ip_address,
            'container_id': self.container_id,
            'range_name': self.range_name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
