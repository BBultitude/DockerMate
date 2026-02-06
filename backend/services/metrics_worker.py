"""
Metrics Worker - Sprint 5 Tasks 5-7

Background worker thread for periodic health metrics collection.

Features:
    - Runs in daemon thread (doesn't block app shutdown)
    - Collects system and container metrics at configurable interval
    - Automatic cleanup of old metrics (daily)
    - Graceful start/stop

Usage:
    from backend.services.metrics_worker import start_metrics_worker, stop_metrics_worker

    # Start worker (typically in app startup)
    worker = start_metrics_worker(interval_seconds=60)

    # Stop worker (typically in app shutdown)
    stop_metrics_worker()

Educational Notes:
    - Thread-based background processing
    - Separate database session per collection cycle
    - Error handling prevents worker crash
    - Daemon thread automatically terminates with main process
"""

import threading
import time
import logging
import random
from backend.services.health_collector import HealthCollector
from backend.models.database import SessionLocal

logger = logging.getLogger(__name__)


class MetricsWorker:
    """Background worker thread for periodic health metrics collection"""

    def __init__(self, interval_seconds: int = 60):
        """Initialize metrics worker

        Args:
            interval_seconds: Collection interval in seconds (default 60)
        """
        self.interval = interval_seconds
        self.collector = HealthCollector()
        self.running = False
        self.thread = None

    def start(self):
        """Start the background metrics collection thread"""
        if self.running:
            logger.warning("MetricsWorker already running")
            return

        if not self.collector.client:
            logger.error("Cannot start MetricsWorker: Docker client unavailable")
            return

        self.running = True
        self.thread = threading.Thread(target=self._collect_loop, daemon=True, name="MetricsWorker")
        self.thread.start()
        logger.info(f"✓ MetricsWorker started with {self.interval}s collection interval")

    def stop(self):
        """Stop the background thread gracefully

        Waits up to 5 seconds for current collection to complete
        """
        if not self.running:
            logger.debug("MetricsWorker not running")
            return

        logger.info("Stopping MetricsWorker...")
        self.running = False

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
            if self.thread.is_alive():
                logger.warning("MetricsWorker did not stop within timeout")
            else:
                logger.info("✓ MetricsWorker stopped")

    def _collect_loop(self):
        """Main collection loop

        Runs continuously while self.running is True.
        Collects metrics, then sleeps for interval.

        Error handling:
            - Catches and logs all exceptions
            - Continues running after errors
            - Prevents worker crash from stopping metrics collection
        """
        logger.info("MetricsWorker collection loop started")

        while self.running:
            db = None

            try:
                # Create new database session for this collection cycle
                db = SessionLocal()

                # Collect system-wide metrics
                try:
                    self.collector.collect_system_metrics(db)
                except Exception as sys_error:
                    logger.error(f"Error collecting system metrics: {sys_error}")

                # Collect per-container metrics
                try:
                    self.collector.collect_container_metrics(db)
                except Exception as cont_error:
                    logger.error(f"Error collecting container metrics: {cont_error}")

                # Cleanup old metrics (probabilistically ~once per day)
                # At 60s interval: 1440 collections per day
                # Probability: 1/1440 = 0.000694
                if random.random() < (1.0 / 1440):
                    try:
                        logger.info("Running daily metrics cleanup...")
                        self.collector.cleanup_old_metrics(db, retention_days=7)
                    except Exception as cleanup_error:
                        logger.error(f"Error during metrics cleanup: {cleanup_error}")

            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}", exc_info=True)

            finally:
                # Always close database session
                if db:
                    try:
                        db.close()
                    except Exception as close_error:
                        logger.error(f"Error closing database session: {close_error}")

            # Sleep for interval (check self.running periodically for fast shutdown)
            sleep_interval = 0
            while sleep_interval < self.interval and self.running:
                time.sleep(min(1, self.interval - sleep_interval))
                sleep_interval += 1

        logger.info("MetricsWorker collection loop stopped")


# ===== Global Worker Instance =====

_metrics_worker = None


def start_metrics_worker(interval_seconds: int = 60) -> MetricsWorker:
    """Start the global metrics worker

    This creates and starts a singleton metrics worker instance.
    If already running, returns existing instance.

    Args:
        interval_seconds: Collection interval in seconds (default 60)

    Returns:
        MetricsWorker: The running worker instance

    Usage:
        # In app.py startup
        from backend.services.metrics_worker import start_metrics_worker
        worker = start_metrics_worker(interval_seconds=60)
    """
    global _metrics_worker

    if _metrics_worker is not None:
        logger.warning("MetricsWorker already exists, returning existing instance")
        return _metrics_worker

    _metrics_worker = MetricsWorker(interval_seconds)
    _metrics_worker.start()
    return _metrics_worker


def stop_metrics_worker():
    """Stop the global metrics worker

    Gracefully stops the background worker thread.
    Call this during application shutdown if needed.

    Usage:
        # In app.py shutdown handler (optional - daemon thread auto-terminates)
        from backend.services.metrics_worker import stop_metrics_worker
        stop_metrics_worker()
    """
    global _metrics_worker

    if _metrics_worker is not None:
        _metrics_worker.stop()
        _metrics_worker = None
    else:
        logger.debug("No MetricsWorker to stop")


def get_metrics_worker() -> MetricsWorker:
    """Get the global metrics worker instance

    Returns:
        MetricsWorker or None: The running worker instance, or None if not started

    Usage:
        from backend.services.metrics_worker import get_metrics_worker
        worker = get_metrics_worker()
        if worker:
            print(f"Worker running with {worker.interval}s interval")
    """
    return _metrics_worker
