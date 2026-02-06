# Sprint 5 Tasks 5-7: Health Monitoring Expansion Plan

## Overview
Expand the existing health monitoring system to include historical metrics tracking, resource usage alerts, container-level health monitoring, and an enhanced dashboard with trend visualization.

## Current State Analysis

### Existing Implementation:
- **Endpoint**: `GET /api/system/health` in `backend/api/system.py`
- **Frontend**: `/health` page in `frontend/templates/health.html`
- **Checks**: 6 domains (database, docker, containers, images, networks, volumes, dockermate)
- **Output**: Snapshot-based warnings with domain tags
- **Refresh**: 10-second polling interval

### Limitations:
- No historical data - only current snapshot
- No resource usage monitoring (CPU, memory, disk)
- No per-container health details
- No alerting or notification system
- No trend analysis or prediction
- No persistent metrics storage

## Architecture Pattern

Follow established DockerMate patterns:
```
Background Worker → Metrics Collection → Database Storage → API Endpoints → Enhanced UI
```

## Implementation Tasks

---

### Task 5.1: Health Metrics Database Model

**File**: `backend/models/health_metric.py` (new file, ~150 lines)

**Model Structure**:
```python
class HealthMetric(Base):
    __tablename__ = 'health_metrics'

    # Primary key
    id = Column(Integer, primary_key=True)

    # Timestamp
    timestamp = Column(DateTime, server_default=func.now(), nullable=False, index=True)

    # System-level metrics
    cpu_usage_percent = Column(Float)  # Overall CPU usage
    memory_usage_percent = Column(Float)  # Overall memory usage
    memory_used_bytes = Column(BigInteger)
    memory_total_bytes = Column(BigInteger)
    disk_usage_percent = Column(Float)  # /var/lib/docker usage
    disk_used_bytes = Column(BigInteger)
    disk_total_bytes = Column(BigInteger)

    # Docker resource counts
    containers_running = Column(Integer)
    containers_stopped = Column(Integer)
    containers_total = Column(Integer)
    images_total = Column(Integer)
    networks_total = Column(Integer)
    volumes_total = Column(Integer)

    # Health status snapshot
    overall_status = Column(String(20))  # healthy, warning, unhealthy
    warning_count = Column(Integer, default=0)

    # Indexes for efficient querying
    __table_args__ = (
        Index('ix_health_metrics_timestamp', 'timestamp'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'cpu_usage_percent': self.cpu_usage_percent,
            'memory_usage_percent': self.memory_usage_percent,
            'memory_used_mb': round(self.memory_used_bytes / (1024**2), 2) if self.memory_used_bytes else None,
            'disk_usage_percent': self.disk_usage_percent,
            'containers_running': self.containers_running,
            'containers_total': self.containers_total,
            'overall_status': self.overall_status,
            'warning_count': self.warning_count
        }
```

**File**: `backend/models/container_health.py` (new file, ~120 lines)

**Model for Container-Level Health Tracking**:
```python
class ContainerHealth(Base):
    __tablename__ = 'container_health'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, server_default=func.now(), nullable=False, index=True)

    # Container identification
    container_id = Column(String(64), nullable=False, index=True)
    container_name = Column(String(255), nullable=False)

    # Resource usage
    cpu_usage_percent = Column(Float)
    memory_usage_bytes = Column(BigInteger)
    memory_limit_bytes = Column(BigInteger)
    memory_usage_percent = Column(Float)

    # Network I/O
    network_rx_bytes = Column(BigInteger)  # Received
    network_tx_bytes = Column(BigInteger)  # Transmitted

    # Block I/O
    block_read_bytes = Column(BigInteger)
    block_write_bytes = Column(BigInteger)

    # Health status
    status = Column(String(20))  # running, paused, exited, unhealthy
    health_status = Column(String(20))  # healthy, unhealthy, none (if no healthcheck)
    exit_code = Column(Integer)

    __table_args__ = (
        Index('ix_container_health_container_id', 'container_id'),
        Index('ix_container_health_timestamp', 'timestamp'),
    )

    def to_dict(self):
        return {
            'timestamp': self.timestamp.isoformat(),
            'container_name': self.container_name,
            'cpu_percent': self.cpu_usage_percent,
            'memory_mb': round(self.memory_usage_bytes / (1024**2), 2) if self.memory_usage_bytes else None,
            'memory_percent': self.memory_usage_percent,
            'status': self.status,
            'health_status': self.health_status
        }
```

---

### Task 5.2: Alembic Migration

**File**: `migrations/versions/{hash}_add_health_monitoring_models.py`

```python
"""Add health monitoring models for Sprint 5 Tasks 5-7

Revision ID: {generated_hash}
Revises: {previous_migration}
Create Date: {timestamp}
"""

def upgrade() -> None:
    # Guard against double-creation
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Create health_metrics table
    if 'health_metrics' not in inspector.get_table_names():
        op.create_table(
            'health_metrics',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('timestamp', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column('cpu_usage_percent', sa.Float()),
            sa.Column('memory_usage_percent', sa.Float()),
            sa.Column('memory_used_bytes', sa.BigInteger()),
            sa.Column('memory_total_bytes', sa.BigInteger()),
            sa.Column('disk_usage_percent', sa.Float()),
            sa.Column('disk_used_bytes', sa.BigInteger()),
            sa.Column('disk_total_bytes', sa.BigInteger()),
            sa.Column('containers_running', sa.Integer()),
            sa.Column('containers_stopped', sa.Integer()),
            sa.Column('containers_total', sa.Integer()),
            sa.Column('images_total', sa.Integer()),
            sa.Column('networks_total', sa.Integer()),
            sa.Column('volumes_total', sa.Integer()),
            sa.Column('overall_status', sa.String(20)),
            sa.Column('warning_count', sa.Integer(), server_default='0'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_health_metrics_timestamp', 'health_metrics', ['timestamp'])

    # Create container_health table
    if 'container_health' not in inspector.get_table_names():
        op.create_table(
            'container_health',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('timestamp', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column('container_id', sa.String(64), nullable=False),
            sa.Column('container_name', sa.String(255), nullable=False),
            sa.Column('cpu_usage_percent', sa.Float()),
            sa.Column('memory_usage_bytes', sa.BigInteger()),
            sa.Column('memory_limit_bytes', sa.BigInteger()),
            sa.Column('memory_usage_percent', sa.Float()),
            sa.Column('network_rx_bytes', sa.BigInteger()),
            sa.Column('network_tx_bytes', sa.BigInteger()),
            sa.Column('block_read_bytes', sa.BigInteger()),
            sa.Column('block_write_bytes', sa.BigInteger()),
            sa.Column('status', sa.String(20)),
            sa.Column('health_status', sa.String(20)),
            sa.Column('exit_code', sa.Integer()),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_container_health_container_id', 'container_health', ['container_id'])
        op.create_index('ix_container_health_timestamp', 'container_health', ['timestamp'])

def downgrade() -> None:
    op.drop_index('ix_container_health_timestamp', 'container_health')
    op.drop_index('ix_container_health_container_id', 'container_health')
    op.drop_table('container_health')
    op.drop_index('ix_health_metrics_timestamp', 'health_metrics')
    op.drop_table('health_metrics')
```

---

### Task 5.3: Health Metrics Collector Service

**File**: `backend/services/health_collector.py` (new file, ~500 lines)

**Purpose**: Background service to collect and store health metrics

```python
import psutil
import docker
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.models.health_metric import HealthMetric
from backend.models.container_health import ContainerHealth
from backend.models.database import SessionLocal

logger = logging.getLogger(__name__)

class HealthCollector:
    """Collects system and container health metrics for historical tracking"""

    def __init__(self):
        self.client = docker.from_env()

    def collect_system_metrics(self, db: Session) -> dict:
        """Collect system-wide health metrics

        Returns metrics dict and stores to database
        """
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory usage
            mem = psutil.virtual_memory()
            memory_percent = mem.percent
            memory_used = mem.used
            memory_total = mem.total

            # Disk usage for /var/lib/docker
            disk = psutil.disk_usage('/var/lib/docker')
            disk_percent = disk.percent
            disk_used = disk.used
            disk_total = disk.total

            # Docker resource counts
            containers = self.client.containers.list(all=True)
            running = len([c for c in containers if c.status == 'running'])
            stopped = len([c for c in containers if c.status != 'running'])
            total_containers = len(containers)

            images = self.client.images.list()
            networks = self.client.networks.list()
            volumes = self.client.volumes.list()

            # Get current health status from API
            from backend.api.system import health_check
            # Note: Can't call Flask route directly, need to call underlying logic
            # For now, derive simple status from metrics
            overall_status = 'healthy'
            if cpu_percent > 90 or memory_percent > 90 or disk_percent > 90:
                overall_status = 'warning'
            if cpu_percent > 95 or memory_percent > 95 or disk_percent > 95:
                overall_status = 'unhealthy'

            # Create metric record
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
                images_total=len(images),
                networks_total=len(networks),
                volumes_total=len(volumes),
                overall_status=overall_status,
                warning_count=0  # Could derive from health check
            )

            db.add(metric)
            db.commit()

            logger.info(f"Collected system metrics: CPU {cpu_percent}%, MEM {memory_percent}%, DISK {disk_percent}%")

            return metric.to_dict()

        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            db.rollback()
            return {}

    def collect_container_metrics(self, db: Session) -> list:
        """Collect per-container health metrics

        Returns list of container metrics and stores to database
        """
        metrics = []

        try:
            containers = self.client.containers.list(all=True)

            for container in containers:
                try:
                    # Skip DockerMate itself
                    if 'dockermate' in container.name.lower():
                        continue

                    # Get container stats (running containers only)
                    cpu_percent = None
                    memory_usage = None
                    memory_limit = None
                    memory_percent = None
                    net_rx = None
                    net_tx = None
                    block_read = None
                    block_write = None

                    if container.status == 'running':
                        stats = container.stats(stream=False)

                        # Calculate CPU percentage
                        cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                                    stats['precpu_stats']['cpu_usage']['total_usage']
                        system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                                       stats['precpu_stats']['system_cpu_usage']
                        cpu_count = stats['cpu_stats'].get('online_cpus', 1)

                        if system_delta > 0:
                            cpu_percent = (cpu_delta / system_delta) * cpu_count * 100.0

                        # Memory
                        memory_usage = stats['memory_stats'].get('usage', 0)
                        memory_limit = stats['memory_stats'].get('limit', 0)
                        if memory_limit > 0:
                            memory_percent = (memory_usage / memory_limit) * 100.0

                        # Network I/O
                        networks = stats.get('networks', {})
                        net_rx = sum(n.get('rx_bytes', 0) for n in networks.values())
                        net_tx = sum(n.get('tx_bytes', 0) for n in networks.values())

                        # Block I/O
                        blkio = stats.get('blkio_stats', {}).get('io_service_bytes_recursive', [])
                        block_read = sum(item['value'] for item in blkio if item['op'] == 'Read')
                        block_write = sum(item['value'] for item in blkio if item['op'] == 'Write')

                    # Get health status
                    health_status = 'none'
                    try:
                        health = container.attrs.get('State', {}).get('Health')
                        if health:
                            health_status = health.get('Status', 'none')
                    except Exception:
                        pass

                    # Exit code
                    exit_code = None
                    if container.status == 'exited':
                        exit_code = container.attrs.get('State', {}).get('ExitCode')

                    # Create container health record
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

                except Exception as e:
                    logger.warning(f"Failed to collect metrics for container {container.name}: {e}")
                    continue

            db.commit()
            logger.info(f"Collected metrics for {len(metrics)} containers")

        except Exception as e:
            logger.error(f"Failed to collect container metrics: {e}")
            db.rollback()

        return metrics

    def cleanup_old_metrics(self, db: Session, retention_days: int = 7):
        """Remove metrics older than retention period"""
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
            logger.info(f"Cleaned up {deleted_system} system metrics and {deleted_container} container metrics older than {retention_days} days")

        except Exception as e:
            logger.error(f"Failed to cleanup old metrics: {e}")
            db.rollback()
```

---

### Task 5.4: Background Metrics Collection Thread

**File**: `backend/services/metrics_worker.py` (new file, ~150 lines)

**Purpose**: Run metrics collection in background thread

```python
import threading
import time
import logging
from backend.services.health_collector import HealthCollector
from backend.models.database import SessionLocal

logger = logging.getLogger(__name__)

class MetricsWorker:
    """Background worker thread for periodic health metrics collection"""

    def __init__(self, interval_seconds=60):
        self.interval = interval_seconds
        self.collector = HealthCollector()
        self.running = False
        self.thread = None

    def start(self):
        """Start the background metrics collection thread"""
        if self.running:
            logger.warning("MetricsWorker already running")
            return

        self.running = True
        self.thread = threading.Thread(target=self._collect_loop, daemon=True)
        self.thread.start()
        logger.info(f"MetricsWorker started with {self.interval}s interval")

    def stop(self):
        """Stop the background thread"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("MetricsWorker stopped")

    def _collect_loop(self):
        """Main collection loop"""
        while self.running:
            try:
                db = SessionLocal()

                # Collect system-wide metrics
                self.collector.collect_system_metrics(db)

                # Collect per-container metrics
                self.collector.collect_container_metrics(db)

                # Cleanup old metrics (daily)
                import random
                if random.random() < (1.0 / 1440):  # ~once per day at 60s interval
                    self.collector.cleanup_old_metrics(db, retention_days=7)

                db.close()

            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")

            # Sleep for interval
            time.sleep(self.interval)

# Global worker instance
_metrics_worker = None

def start_metrics_worker(interval_seconds=60):
    """Start the global metrics worker"""
    global _metrics_worker
    if _metrics_worker is None:
        _metrics_worker = MetricsWorker(interval_seconds)
        _metrics_worker.start()
    return _metrics_worker

def stop_metrics_worker():
    """Stop the global metrics worker"""
    global _metrics_worker
    if _metrics_worker:
        _metrics_worker.stop()
        _metrics_worker = None
```

---

### Task 5.5: Enhanced Health API Endpoints

**File**: `backend/api/system.py` (modify existing file)

Add new endpoints for historical metrics:

```python
@system_bp.route('/health/metrics', methods=['GET'])
def get_health_metrics():
    """Get historical health metrics

    Query params:
        - hours (int): Number of hours of history (default 24, max 168 = 7 days)
        - interval (str): Data point interval - '1min', '5min', '15min', '1hour' (default '5min')

    Returns:
        {
            'success': True,
            'metrics': [
                {
                    'timestamp': '2026-02-06T10:00:00',
                    'cpu_usage_percent': 45.2,
                    'memory_usage_percent': 62.1,
                    'disk_usage_percent': 38.5,
                    'containers_running': 12,
                    'overall_status': 'healthy'
                },
                ...
            ],
            'summary': {
                'avg_cpu': 43.5,
                'max_cpu': 78.2,
                'avg_memory': 61.3,
                'max_memory': 72.4
            }
        }
    """
    from flask import request
    from datetime import datetime, timedelta
    from backend.models.health_metric import HealthMetric

    try:
        hours = min(int(request.args.get('hours', 24)), 168)
        interval = request.args.get('interval', '5min')

        # Calculate interval in minutes
        interval_minutes = {
            '1min': 1,
            '5min': 5,
            '15min': 15,
            '1hour': 60
        }.get(interval, 5)

        db = SessionLocal()
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        # Query metrics
        all_metrics = db.query(HealthMetric).filter(
            HealthMetric.timestamp >= cutoff
        ).order_by(HealthMetric.timestamp.asc()).all()

        # Downsample to requested interval
        metrics = []
        last_timestamp = None
        for m in all_metrics:
            if last_timestamp is None or \
               (m.timestamp - last_timestamp).total_seconds() >= (interval_minutes * 60):
                metrics.append(m.to_dict())
                last_timestamp = m.timestamp

        # Calculate summary statistics
        if metrics:
            cpu_values = [m['cpu_usage_percent'] for m in metrics if m['cpu_usage_percent']]
            mem_values = [m['memory_usage_percent'] for m in metrics if m['memory_usage_percent']]

            summary = {
                'avg_cpu': round(sum(cpu_values) / len(cpu_values), 2) if cpu_values else 0,
                'max_cpu': round(max(cpu_values), 2) if cpu_values else 0,
                'avg_memory': round(sum(mem_values) / len(mem_values), 2) if mem_values else 0,
                'max_memory': round(max(mem_values), 2) if mem_values else 0
            }
        else:
            summary = {'avg_cpu': 0, 'max_cpu': 0, 'avg_memory': 0, 'max_memory': 0}

        db.close()

        return jsonify({
            'success': True,
            'metrics': metrics,
            'summary': summary,
            'hours': hours,
            'interval': interval
        }), 200

    except Exception as e:
        logger.error(f"Failed to get health metrics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@system_bp.route('/health/containers/<container_id>', methods=['GET'])
def get_container_health(container_id):
    """Get health metrics for specific container

    Query params:
        - hours (int): Hours of history (default 24)

    Returns historical metrics for one container
    """
    from flask import request
    from datetime import datetime, timedelta
    from backend.models.container_health import ContainerHealth

    try:
        hours = min(int(request.args.get('hours', 24)), 168)

        db = SessionLocal()
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        metrics = db.query(ContainerHealth).filter(
            ContainerHealth.container_id == container_id,
            ContainerHealth.timestamp >= cutoff
        ).order_by(ContainerHealth.timestamp.asc()).all()

        db.close()

        return jsonify({
            'success': True,
            'container_id': container_id,
            'metrics': [m.to_dict() for m in metrics],
            'count': len(metrics)
        }), 200

    except Exception as e:
        logger.error(f"Failed to get container health: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

---

### Task 5.6: Enhanced Health Dashboard UI

**File**: `frontend/templates/health.html` (major expansion, ~1200 lines total)

Add new sections:

1. **Resource Usage Graphs** (CPU, Memory, Disk over time)
2. **Container Health Table** (per-container metrics)
3. **Alerts & Trends** section

Key additions:

```html
<!-- After stats row, add graphs section -->
<div class="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
    <!-- CPU Usage Graph -->
    <div class="bg-slate-800 rounded-lg border border-slate-700 p-4">
        <h3 class="text-white font-semibold mb-3">CPU Usage (24h)</h3>
        <canvas x-ref="cpuChart"></canvas>
    </div>

    <!-- Memory Usage Graph -->
    <div class="bg-slate-800 rounded-lg border border-slate-700 p-4">
        <h3 class="text-white font-semibold mb-3">Memory Usage (24h)</h3>
        <canvas x-ref="memoryChart"></canvas>
    </div>

    <!-- Disk Usage Graph -->
    <div class="bg-slate-800 rounded-lg border border-slate-700 p-4">
        <h3 class="text-white font-semibold mb-3">Disk Usage (24h)</h3>
        <canvas x-ref="diskChart"></canvas>
    </div>
</div>

<!-- Container Health Table -->
<div class="bg-slate-800 rounded-lg border border-slate-700 p-6 mb-6">
    <h3 class="text-white font-semibold mb-4">Container Resource Usage</h3>
    <table class="w-full text-sm">
        <thead class="text-slate-400 border-b border-slate-700">
            <tr>
                <th class="text-left py-2">Container</th>
                <th class="text-right py-2">CPU %</th>
                <th class="text-right py-2">Memory</th>
                <th class="text-right py-2">Network I/O</th>
                <th class="text-center py-2">Health</th>
                <th class="text-center py-2">Status</th>
            </tr>
        </thead>
        <tbody class="text-slate-300">
            <template x-for="container in containerMetrics" :key="container.container_name">
                <tr class="border-b border-slate-700">
                    <td class="py-2" x-text="container.container_name"></td>
                    <td class="text-right" x-text="formatPercent(container.cpu_percent)"></td>
                    <td class="text-right" x-text="formatBytes(container.memory_mb * 1024 * 1024)"></td>
                    <td class="text-right">-</td>
                    <td class="text-center">
                        <span :class="container.health_status === 'healthy' ? 'text-green-400' :
                                      container.health_status === 'unhealthy' ? 'text-red-400' :
                                      'text-slate-500'"
                              x-text="container.health_status"></span>
                    </td>
                    <td class="text-center">
                        <span class="px-2 py-0.5 rounded text-xs"
                              :class="container.status === 'running' ? 'bg-green-900 text-green-300' : 'bg-slate-700 text-slate-400'"
                              x-text="container.status"></span>
                    </td>
                </tr>
            </template>
        </tbody>
    </table>
</div>
```

**Alpine.js Component Updates**:

```javascript
function healthPage() {
    return {
        // Existing state...
        loading: true,
        status: 'healthy',
        checks: {},
        warnings: [],
        lastChecked: '',

        // New state for metrics
        metricsHistory: [],
        metricsSummary: {},
        containerMetrics: [],
        charts: {
            cpu: null,
            memory: null,
            disk: null
        },

        async init() {
            await this.loadHealth();
            await this.loadMetricsHistory();
            await this.loadContainerMetrics();
            this.initCharts();

            // Refresh every 10 seconds
            setInterval(async () => {
                await this.loadHealth();
                await this.loadContainerMetrics();
            }, 10000);

            // Refresh history every 60 seconds
            setInterval(async () => {
                await this.loadMetricsHistory();
                this.updateCharts();
            }, 60000);
        },

        async loadMetricsHistory() {
            try {
                const r = await fetch('/api/system/health/metrics?hours=24&interval=5min');
                const d = await r.json();
                if (d.success) {
                    this.metricsHistory = d.metrics;
                    this.metricsSummary = d.summary;
                }
            } catch (e) {
                console.error('Failed to load metrics history:', e);
            }
        },

        async loadContainerMetrics() {
            try {
                // Get current container stats from Docker
                const r = await fetch('/api/containers');
                const d = await r.json();
                if (d.success) {
                    // Extract current metrics from container list
                    this.containerMetrics = d.containers.filter(c => c.state === 'running').map(c => ({
                        container_name: c.name,
                        cpu_percent: null,  // Will be populated from stats API
                        memory_mb: null,
                        status: c.state,
                        health_status: c.health || 'none'
                    }));
                }
            } catch (e) {
                console.error('Failed to load container metrics:', e);
            }
        },

        initCharts() {
            // Initialize Chart.js charts (requires Chart.js CDN)
            const timestamps = this.metricsHistory.map(m => new Date(m.timestamp).toLocaleTimeString());

            // CPU Chart
            this.charts.cpu = new Chart(this.$refs.cpuChart, {
                type: 'line',
                data: {
                    labels: timestamps,
                    datasets: [{
                        label: 'CPU %',
                        data: this.metricsHistory.map(m => m.cpu_usage_percent),
                        borderColor: 'rgb(59, 130, 246)',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100
                        }
                    }
                }
            });

            // Similar for memory and disk charts...
        },

        updateCharts() {
            // Update chart data with new metrics
            if (this.charts.cpu) {
                const timestamps = this.metricsHistory.map(m => new Date(m.timestamp).toLocaleTimeString());
                this.charts.cpu.data.labels = timestamps;
                this.charts.cpu.data.datasets[0].data = this.metricsHistory.map(m => m.cpu_usage_percent);
                this.charts.cpu.update();
            }
            // Similar for memory and disk...
        },

        formatPercent(value) {
            return value != null ? `${value.toFixed(1)}%` : '-';
        },

        formatBytes(bytes) {
            if (!bytes) return '-';
            const mb = bytes / (1024 * 1024);
            if (mb < 1024) return `${mb.toFixed(1)} MB`;
            return `${(mb / 1024).toFixed(1)} GB`;
        }
    };
}
```

---

### Task 5.7: Start Metrics Worker on App Startup

**File**: `app.py` (modify existing file)

Add metrics worker startup:

```python
# After database initialization, before app.run()

# Start background metrics collection worker
if not app.config.get('TESTING'):
    logger.info("Starting health metrics collection worker...")
    try:
        from backend.services.metrics_worker import start_metrics_worker
        start_metrics_worker(interval_seconds=60)  # Collect every 60 seconds
        logger.info("✓ Metrics worker started")
    except Exception as e:
        logger.warning(f"Failed to start metrics worker: {e}")
        logger.warning("Health monitoring will work but historical metrics won't be collected")
```

**File**: `app_dev.py` (same modification)

---

## Dependencies

### New Python Packages:

Add to `requirements.txt`:
```
psutil==5.9.8       # System resource monitoring
```

### New JavaScript Libraries:

Add to `frontend/templates/base.html` (in head section):
```html
<!-- Chart.js for graphs -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
```

---

## Implementation Order

1. **Task 5.1**: Create health metric models (`backend/models/health_metric.py`, `backend/models/container_health.py`)
2. **Task 5.2**: Generate and apply Alembic migration
3. **Task 5.3**: Implement HealthCollector service (`backend/services/health_collector.py`)
4. **Task 5.4**: Create MetricsWorker background thread (`backend/services/metrics_worker.py`)
5. **Task 5.5**: Add new API endpoints to `backend/api/system.py`
6. **Task 5.6**: Enhance health dashboard UI with graphs and container table
7. **Task 5.7**: Integrate metrics worker into app startup (`app.py`, `app_dev.py`)

---

## Testing & Verification

### Manual Testing:

```bash
# 1. Start DockerMate dev environment
docker-compose -f docker-compose.dev.yml up --build

# 2. Wait 2-3 minutes for metrics to collect

# 3. Check health metrics API
curl -k https://localhost:5000/api/system/health/metrics?hours=1 | jq .

# Expected: Array of metrics with timestamps, CPU, memory, disk data

# 4. Check database for stored metrics
docker exec dockermate-dev sqlite3 /app/data/dockermate.db \
  "SELECT COUNT(*) FROM health_metrics;"

# Expected: Count > 0 (should have ~2-3 records after 2-3 minutes)

# 5. Visit health dashboard
# Open https://localhost:5000/health
# Expected: See graphs showing CPU/memory/disk trends

# 6. Check container metrics
docker exec dockermate-dev sqlite3 /app/data/dockermate.db \
  "SELECT container_name, cpu_usage_percent FROM container_health LIMIT 5;"

# 7. Verify cleanup (run after 8 days)
docker exec dockermate-dev sqlite3 /app/data/dockermate.db \
  "SELECT COUNT(*) FROM health_metrics WHERE timestamp < datetime('now', '-7 days');"
# Expected: 0 (old records cleaned up)
```

### Load Testing:

```bash
# Create load to generate interesting metrics
docker run -d --name stress-test progrium/stress \
  --cpu 2 --io 1 --vm 2 --vm-bytes 256M --timeout 60s

# Wait 1 minute, then check health dashboard
# Expected: CPU and memory graphs show spike
```

---

## Success Criteria

- ✅ HealthMetric and ContainerHealth models created with proper indexes
- ✅ Alembic migration applied successfully
- ✅ HealthCollector service collects system and container metrics
- ✅ MetricsWorker runs in background thread, collects every 60 seconds
- ✅ `/api/system/health/metrics` endpoint returns historical data
- ✅ `/api/system/health/containers/<id>` endpoint returns per-container history
- ✅ Health dashboard displays CPU/memory/disk graphs
- ✅ Container resource usage table shows current metrics
- ✅ Graphs update every 60 seconds with new data
- ✅ Old metrics cleaned up after 7 days
- ✅ psutil dependency installed
- ✅ Chart.js integrated into base template
- ✅ Metrics worker starts on app startup
- ✅ No regressions in existing health checks

---

## Estimated Effort

- **Models + Migration**: 1-2 hours
- **HealthCollector Service**: 3-4 hours
- **MetricsWorker Thread**: 1 hour
- **API Endpoints**: 2 hours
- **Dashboard UI Enhancements**: 4-5 hours (charts, table, styling)
- **Integration & Testing**: 2 hours

**Total: 13-16 hours** (2-3 days of focused work)

---

## Notes

- Metrics collection runs every 60 seconds by default (configurable)
- Historical data retained for 7 days (configurable)
- Cleanup runs probabilistically (~once per day)
- Chart.js chosen for simple, lightweight graphing
- psutil works on Linux/macOS/Windows for cross-platform compatibility
- Container stats only available for running containers
- Background thread is daemon thread - won't block app shutdown
- Consider adding email/webhook alerts in future sprint
- For production, consider using Prometheus + Grafana for more advanced monitoring

---

## Future Enhancements (Post-Sprint 5)

- Email/webhook alerts when metrics exceed thresholds
- Configurable alert rules in UI
- Export metrics to Prometheus format
- Anomaly detection (ML-based)
- Custom dashboard widgets
- Metric retention configurable per user
- Multi-node support (if DockerMate runs across multiple hosts)
