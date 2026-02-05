"""
Network Model — Sprint 4

Tracks Docker networks created or discovered by DockerMate.
Stores IPAM metadata (subnet, gateway) alongside the live Docker network ID
so the UI can display and reason about IP allocation without hitting the
Docker daemon on every page load.

Columns
-------
network_id  : Docker-assigned hex ID (stable across restarts)
name        : Human-readable name; must be unique inside Docker
driver      : bridge | overlay | macvlan | ipvlan | host | none
subnet      : CIDR block assigned to the network (may be NULL for host/none)
gateway     : First IP in the subnet (auto-assigned by Docker if omitted)
ip_range    : Optional restricted CIDR within the subnet
purpose     : Free-text description provided by the user
managed     : True when DockerMate created it; False for pre-existing networks
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from backend.models.database import Base


class Network(Base):
    __tablename__ = 'networks'

    id = Column(Integer, primary_key=True)
    network_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    driver = Column(String(50), nullable=False, default='bridge')
    subnet = Column(String(45), nullable=True)       # e.g. "172.20.0.0/16"
    gateway = Column(String(45), nullable=True)      # e.g. "172.20.0.1"
    ip_range = Column(String(45), nullable=True)
    purpose = Column(String(255), nullable=True)
    managed = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    def __repr__(self):
        return f"<Network {self.name} ({self.subnet or 'no subnet'})>"

    def to_dict(self):
        return {
            'id': self.id,
            'network_id': self.network_id,
            'name': self.name,
            'driver': self.driver,
            'subnet': self.subnet,
            'gateway': self.gateway,
            'ip_range': self.ip_range,
            'purpose': self.purpose,
            'managed': self.managed,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
