"""
Container Health Model - Sprint 5 Tasks 5-7

Stores per-container health metrics for detailed resource tracking.

Schema:
    - Container-specific resource usage (CPU, memory, network, block I/O)
    - Health check status
    - Exit codes for failed containers
    - Timestamp-indexed for historical analysis

Usage:
    from backend.models.container_health import ContainerHealth

    metric = ContainerHealth(
        container_id='abc123...',
        container_name='nginx-web',
        cpu_usage_percent=15.3,
        memory_usage_bytes=134217728,
        status='running',
        health_status='healthy'
    )
    db.add(metric)
    db.commit()
"""

from sqlalchemy import Column, Integer, String, Float, BigInteger, DateTime, Index
from sqlalchemy.sql import func
from backend.models.database import Base


class ContainerHealth(Base):
    """Per-container health metrics collected periodically"""

    __tablename__ = 'container_health'

    # Primary key
    id = Column(Integer, primary_key=True)

    # Timestamp - when this metric was collected
    timestamp = Column(DateTime, server_default=func.now(), nullable=False, index=True)

    # Container identification
    container_id = Column(String(64), nullable=False, index=True)  # Docker container ID
    container_name = Column(String(255), nullable=False)  # Human-readable name

    # Resource usage (only available for running containers)
    cpu_usage_percent = Column(Float)  # CPU usage (0-100+ for multi-core)
    memory_usage_bytes = Column(BigInteger)  # Current memory usage
    memory_limit_bytes = Column(BigInteger)  # Memory limit
    memory_usage_percent = Column(Float)  # Memory usage as percentage of limit

    # Network I/O (cumulative since container start)
    network_rx_bytes = Column(BigInteger)  # Bytes received
    network_tx_bytes = Column(BigInteger)  # Bytes transmitted

    # Block I/O (cumulative since container start)
    block_read_bytes = Column(BigInteger)  # Bytes read from disk
    block_write_bytes = Column(BigInteger)  # Bytes written to disk

    # Health status
    status = Column(String(20))  # 'running', 'paused', 'exited', 'restarting', 'dead'
    health_status = Column(String(20))  # 'healthy', 'unhealthy', 'none' (if no HEALTHCHECK)
    exit_code = Column(Integer)  # Exit code if status == 'exited'

    # Indexes for efficient queries
    __table_args__ = (
        Index('ix_container_health_container_id', 'container_id'),
        Index('ix_container_health_timestamp', 'timestamp'),
    )

    def to_dict(self):
        """Convert to JSON-serializable dict for API responses"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,

            # Container info
            'container_id': self.container_id,
            'container_name': self.container_name,

            # Resource usage
            'cpu_percent': round(self.cpu_usage_percent, 2) if self.cpu_usage_percent is not None else None,
            'memory_mb': round(self.memory_usage_bytes / (1024**2), 2) if self.memory_usage_bytes else None,
            'memory_limit_mb': round(self.memory_limit_bytes / (1024**2), 2) if self.memory_limit_bytes else None,
            'memory_percent': round(self.memory_usage_percent, 2) if self.memory_usage_percent is not None else None,

            # Network I/O
            'network_rx_mb': round(self.network_rx_bytes / (1024**2), 2) if self.network_rx_bytes else None,
            'network_tx_mb': round(self.network_tx_bytes / (1024**2), 2) if self.network_tx_bytes else None,

            # Block I/O
            'block_read_mb': round(self.block_read_bytes / (1024**2), 2) if self.block_read_bytes else None,
            'block_write_mb': round(self.block_write_bytes / (1024**2), 2) if self.block_write_bytes else None,

            # Status
            'status': self.status,
            'health_status': self.health_status,
            'exit_code': self.exit_code
        }

    def __repr__(self):
        return f"<ContainerHealth(id={self.id}, container={self.container_name}, timestamp={self.timestamp}, cpu={self.cpu_usage_percent}%, mem={self.memory_usage_percent}%)>"
