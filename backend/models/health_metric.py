"""
Health Metric Model - Sprint 5 Tasks 5-7

Stores historical system-wide health metrics for trend analysis and alerting.

Schema:
    - Timestamp-indexed metrics collected every 60 seconds
    - System resource usage (CPU, memory, disk)
    - Docker resource counts (containers, images, networks, volumes)
    - Overall health status snapshot
    - 7-day retention policy (cleaned up by metrics worker)

Usage:
    from backend.models.health_metric import HealthMetric

    metric = HealthMetric(
        cpu_usage_percent=45.2,
        memory_usage_percent=62.1,
        containers_running=12,
        overall_status='healthy'
    )
    db.add(metric)
    db.commit()
"""

from sqlalchemy import Column, Integer, String, Float, BigInteger, DateTime, Index
from sqlalchemy.sql import func
from backend.models.database import Base


class HealthMetric(Base):
    """System-wide health metrics collected periodically"""

    __tablename__ = 'health_metrics'

    # Primary key
    id = Column(Integer, primary_key=True)

    # Timestamp - when this metric snapshot was taken
    timestamp = Column(DateTime, server_default=func.now(), nullable=False, index=True)

    # System-level resource usage
    cpu_usage_percent = Column(Float)  # Overall CPU usage (0-100)
    memory_usage_percent = Column(Float)  # Overall memory usage (0-100)
    memory_used_bytes = Column(BigInteger)  # Bytes of RAM used
    memory_total_bytes = Column(BigInteger)  # Total RAM available
    disk_usage_percent = Column(Float)  # /var/lib/docker disk usage (0-100)
    disk_used_bytes = Column(BigInteger)  # Bytes of disk used
    disk_total_bytes = Column(BigInteger)  # Total disk space

    # Docker resource counts
    containers_running = Column(Integer)  # Number of running containers
    containers_stopped = Column(Integer)  # Number of stopped containers
    containers_total = Column(Integer)  # Total containers (running + stopped)
    images_total = Column(Integer)  # Total images
    networks_total = Column(Integer)  # Total networks
    volumes_total = Column(Integer)  # Total volumes

    # Health status snapshot
    overall_status = Column(String(20))  # 'healthy', 'warning', 'unhealthy'
    warning_count = Column(Integer, default=0)  # Number of warnings at this timestamp

    # Indexes for efficient time-range queries
    __table_args__ = (
        Index('ix_health_metrics_timestamp', 'timestamp'),
    )

    def to_dict(self):
        """Convert to JSON-serializable dict for API responses"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,

            # Resource usage
            'cpu_usage_percent': round(self.cpu_usage_percent, 2) if self.cpu_usage_percent is not None else None,
            'memory_usage_percent': round(self.memory_usage_percent, 2) if self.memory_usage_percent is not None else None,
            'memory_used_mb': round(self.memory_used_bytes / (1024**2), 2) if self.memory_used_bytes else None,
            'memory_total_mb': round(self.memory_total_bytes / (1024**2), 2) if self.memory_total_bytes else None,
            'disk_usage_percent': round(self.disk_usage_percent, 2) if self.disk_usage_percent is not None else None,
            'disk_used_gb': round(self.disk_used_bytes / (1024**3), 2) if self.disk_used_bytes else None,
            'disk_total_gb': round(self.disk_total_bytes / (1024**3), 2) if self.disk_total_bytes else None,

            # Resource counts
            'containers_running': self.containers_running,
            'containers_stopped': self.containers_stopped,
            'containers_total': self.containers_total,
            'images_total': self.images_total,
            'networks_total': self.networks_total,
            'volumes_total': self.volumes_total,

            # Status
            'overall_status': self.overall_status,
            'warning_count': self.warning_count
        }

    def __repr__(self):
        return f"<HealthMetric(id={self.id}, timestamp={self.timestamp}, status={self.overall_status}, cpu={self.cpu_usage_percent}%, mem={self.memory_usage_percent}%)>"
