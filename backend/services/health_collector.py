"""
Health Collector Service - Sprint 5 Tasks 5-7

Collects system-wide and per-container health metrics for historical tracking.

Features:
    - System resource usage (CPU, memory, disk)
    - Docker resource counts (containers, images, networks, volumes)
    - Per-container metrics (CPU, memory, network I/O, block I/O)
    - Automatic cleanup of old metrics (7-day retention)

Usage:
    from backend.services.health_collector import HealthCollector
    from backend.models.database import SessionLocal

    collector = HealthCollector()
    db = SessionLocal()

    # Collect system metrics
    system_metrics = collector.collect_system_metrics(db)

    # Collect container metrics
    container_metrics = collector.collect_container_metrics(db)

    # Cleanup old metrics
    collector.cleanup_old_metrics(db, retention_days=7)

    db.close()

Educational Notes:
    - Uses psutil for system resource monitoring
    - Docker SDK for container stats
    - Stores metrics in database for historical analysis
    - Background worker calls these methods periodically
"""

import logging
import psutil
import docker
from datetime import datetime, timedelta
from typing import Dict, List
from sqlalchemy.orm import Session

from backend.models.health_metric import HealthMetric
from backend.models.container_health import ContainerHealth

logger = logging.getLogger(__name__)


class HealthCollector:
    """Collects system and container health metrics for historical tracking"""

    def __init__(self):
        """Initialize Docker client for container metrics collection"""
        try:
            self.client = docker.from_env()
        except Exception as e:
            logger.error(f"Failed to initialize Docker client in HealthCollector: {e}")
            self.client = None

    def collect_system_metrics(self, db: Session) -> Dict:
        """Collect system-wide health metrics and store to database

        Collects:
            - CPU usage percentage
            - Memory usage (bytes and percentage)
            - Disk usage for /var/lib/docker (bytes and percentage)
            - Docker resource counts (containers, images, networks, volumes)
            - Overall health status

        Args:
            db: SQLAlchemy database session

        Returns:
            dict: Collected metrics in JSON-serializable format

        Raises:
            Exception: Logs error but doesn't raise to prevent worker crash
        """
        try:
            # ===== System Resource Usage =====

            # CPU usage (1-second interval for accuracy)
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory usage
            mem = psutil.virtual_memory()
            memory_percent = mem.percent
            memory_used = mem.used
            memory_total = mem.total

            # Disk usage for /var/lib/docker
            try:
                disk = psutil.disk_usage('/var/lib/docker')
                disk_percent = disk.percent
                disk_used = disk.used
                disk_total = disk.total
            except Exception as disk_error:
                # If /var/lib/docker not accessible, use root partition
                logger.warning(f"Cannot access /var/lib/docker, using /: {disk_error}")
                disk = psutil.disk_usage('/')
                disk_percent = disk.percent
                disk_used = disk.used
                disk_total = disk.total

            # ===== Docker Resource Counts =====

            running = 0
            stopped = 0
            total_containers = 0
            total_images = 0
            total_networks = 0
            total_volumes = 0

            if self.client:
                try:
                    # Container counts
                    containers = self.client.containers.list(all=True)
                    running = len([c for c in containers if c.status == 'running'])
                    stopped = len([c for c in containers if c.status != 'running'])
                    total_containers = len(containers)

                    # Other resource counts
                    images = self.client.images.list()
                    total_images = len(images)

                    networks = self.client.networks.list()
                    total_networks = len(networks)

                    volumes = self.client.volumes.list()
                    total_volumes = len(volumes)

                except Exception as docker_error:
                    logger.warning(f"Failed to collect Docker resource counts: {docker_error}")

            # ===== Derive Health Status =====

            overall_status = 'healthy'
            warning_count = 0

            # Warning thresholds
            if cpu_percent > 80 or memory_percent > 80 or disk_percent > 80:
                overall_status = 'warning'
                warning_count = sum([
                    cpu_percent > 80,
                    memory_percent > 80,
                    disk_percent > 80
                ])

            # Unhealthy thresholds
            if cpu_percent > 95 or memory_percent > 95 or disk_percent > 95:
                overall_status = 'unhealthy'
                warning_count += sum([
                    cpu_percent > 95,
                    memory_percent > 95,
                    disk_percent > 95
                ])

            # ===== Store to Database =====

            metric = HealthMetric(
                cpu_usage_percent=cpu_percent,
                memory_usage_percent=memory_percent,
                memory_used_bytes=memory_used,
                memory_total_bytes=memory_total,
                disk_usage_percent=disk_percent,
                disk_used_bytes=disk_used,
                disk_total_bytes=disk_total,
                containers_running=running,
                containers_stopped=stopped,
                containers_total=total_containers,
                images_total=total_images,
                networks_total=total_networks,
                volumes_total=total_volumes,
                overall_status=overall_status,
                warning_count=warning_count
            )

            db.add(metric)
            db.commit()
            db.refresh(metric)

            logger.info(f"Collected system metrics: CPU {cpu_percent:.1f}%, MEM {memory_percent:.1f}%, DISK {disk_percent:.1f}%, STATUS {overall_status}")

            return metric.to_dict()

        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}", exc_info=True)
            db.rollback()
            return {}

    def collect_container_metrics(self, db: Session) -> List[Dict]:
        """Collect per-container health metrics and store to database

        Collects (for running containers only):
            - CPU usage percentage
            - Memory usage (bytes, limit, percentage)
            - Network I/O (rx/tx bytes)
            - Block I/O (read/write bytes)
            - Health check status
            - Exit code (for exited containers)

        Args:
            db: SQLAlchemy database session

        Returns:
            list: List of container metrics in JSON-serializable format

        Raises:
            Exception: Logs error but doesn't raise to prevent worker crash
        """
        metrics = []

        if not self.client:
            logger.warning("Docker client not available, skipping container metrics collection")
            return metrics

        try:
            containers = self.client.containers.list(all=True)

            for container in containers:
                try:
                    # Skip DockerMate itself to avoid circular metrics
                    if 'dockermate' in container.name.lower():
                        continue

                    # Initialize metrics (will be None for non-running containers)
                    cpu_percent = None
                    memory_usage = None
                    memory_limit = None
                    memory_percent = None
                    net_rx = None
                    net_tx = None
                    block_read = None
                    block_write = None

                    # ===== Collect Stats for Running Containers =====

                    if container.status == 'running':
                        try:
                            # Get stats (stream=False for single snapshot)
                            stats = container.stats(stream=False)

                            # Calculate CPU percentage
                            # Formula: (cpu_delta / system_delta) * num_cpus * 100
                            cpu_stats = stats.get('cpu_stats', {})
                            precpu_stats = stats.get('precpu_stats', {})

                            cpu_delta = cpu_stats.get('cpu_usage', {}).get('total_usage', 0) - \
                                        precpu_stats.get('cpu_usage', {}).get('total_usage', 0)
                            system_delta = cpu_stats.get('system_cpu_usage', 0) - \
                                           precpu_stats.get('system_cpu_usage', 0)
                            cpu_count = cpu_stats.get('online_cpus', 1)

                            if system_delta > 0 and cpu_delta >= 0:
                                cpu_percent = (cpu_delta / system_delta) * cpu_count * 100.0

                            # Memory stats
                            mem_stats = stats.get('memory_stats', {})
                            memory_usage = mem_stats.get('usage', 0)
                            memory_limit = mem_stats.get('limit', 0)

                            if memory_limit > 0 and memory_usage >= 0:
                                memory_percent = (memory_usage / memory_limit) * 100.0

                            # Network I/O (sum across all interfaces)
                            networks = stats.get('networks', {})
                            if networks:
                                net_rx = sum(iface.get('rx_bytes', 0) for iface in networks.values())
                                net_tx = sum(iface.get('tx_bytes', 0) for iface in networks.values())

                            # Block I/O
                            blkio = stats.get('blkio_stats', {}).get('io_service_bytes_recursive', [])
                            if blkio:
                                block_read = sum(item.get('value', 0) for item in blkio if item.get('op') == 'Read')
                                block_write = sum(item.get('value', 0) for item in blkio if item.get('op') == 'Write')

                        except Exception as stats_error:
                            logger.debug(f"Failed to get stats for container {container.name}: {stats_error}")
                            # Continue with None values

                    # ===== Health Check Status =====

                    health_status = 'none'
                    try:
                        container.reload()
                        health = container.attrs.get('State', {}).get('Health')
                        if health:
                            health_status = health.get('Status', 'none')
                    except Exception:
                        pass

                    # ===== Exit Code =====

                    exit_code = None
                    if container.status == 'exited':
                        try:
                            exit_code = container.attrs.get('State', {}).get('ExitCode')
                        except Exception:
                            pass

                    # ===== Store to Database =====

                    container_metric = ContainerHealth(
                        container_id=container.id,
                        container_name=container.name,
                        cpu_usage_percent=cpu_percent,
                        memory_usage_bytes=memory_usage,
                        memory_limit_bytes=memory_limit,
                        memory_usage_percent=memory_percent,
                        network_rx_bytes=net_rx,
                        network_tx_bytes=net_tx,
                        block_read_bytes=block_read,
                        block_write_bytes=block_write,
                        status=container.status,
                        health_status=health_status,
                        exit_code=exit_code
                    )

                    db.add(container_metric)
                    metrics.append(container_metric.to_dict())

                except Exception as container_error:
                    logger.debug(f"Failed to collect metrics for container {container.name}: {container_error}")
                    continue

            # Commit all container metrics at once
            db.commit()

            logger.info(f"Collected metrics for {len(metrics)} containers")

        except Exception as e:
            logger.error(f"Failed to collect container metrics: {e}", exc_info=True)
            db.rollback()

        return metrics

    def cleanup_old_metrics(self, db: Session, retention_days: int = 7):
        """Remove metrics older than retention period

        Deletes:
            - System metrics older than retention_days
            - Container metrics older than retention_days

        Args:
            db: SQLAlchemy database session
            retention_days: Number of days to retain metrics (default 7)

        Raises:
            Exception: Logs error but doesn't raise to prevent worker crash
        """
        try:
            cutoff = datetime.utcnow() - timedelta(days=retention_days)

            # Delete old system metrics
            deleted_system = db.query(HealthMetric).filter(
                HealthMetric.timestamp < cutoff
            ).delete()

            # Delete old container metrics
            deleted_container = db.query(ContainerHealth).filter(
                ContainerHealth.timestamp < cutoff
            ).delete()

            db.commit()

            if deleted_system > 0 or deleted_container > 0:
                logger.info(f"Cleaned up {deleted_system} system metrics and {deleted_container} container metrics older than {retention_days} days")

        except Exception as e:
            logger.error(f"Failed to cleanup old metrics: {e}", exc_info=True)
            db.rollback()
