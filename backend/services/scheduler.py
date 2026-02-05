"""
DockerMate - Background Scheduler (Sprint 3)
=============================================

Periodic background tasks using stdlib threading.
No external dependencies required.

Current jobs:
    - check_image_updates: Runs every 6 hours to compare local image
      digests with the registry and flag images that have newer versions.

Usage:
    from backend.services.scheduler import start_scheduler

    start_scheduler()   # call once at app startup

Educational Notes:
    - Uses a daemon thread so it dies automatically when the main process exits.
    - Each job function catches its own exceptions so one failing job cannot
      crash the scheduler or the application.
    - Interval is configurable via the SCHEDULER_IMAGE_CHECK_HOURS env var.
"""

import logging
import os
import threading

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# How often (in hours) to check for image updates.  Override with env var.
IMAGE_CHECK_INTERVAL_HOURS = int(os.getenv('SCHEDULER_IMAGE_CHECK_HOURS', '6'))


# ---------------------------------------------------------------------------
# Job functions
# ---------------------------------------------------------------------------

def _check_image_updates():
    """Run the image-update check via ImageManager."""
    try:
        from backend.services.image_manager import ImageManager
        with ImageManager() as manager:
            updates = manager.check_for_updates()
        if updates:
            logger.info(f"Image update check: {len(updates)} image(s) have updates available")
        else:
            logger.debug("Image update check: all images up to date")
    except Exception as e:
        logger.error(f"Image update check failed: {e}", exc_info=True)


# ---------------------------------------------------------------------------
# Repeating-timer helper
# ---------------------------------------------------------------------------

class _RepeatingTimer(threading.Thread):
    """Daemon thread that calls *func* every *interval* seconds."""

    def __init__(self, interval: float, func, name: str = "scheduler-thread"):
        super().__init__(daemon=True, name=name)
        self.interval = interval
        self.func = func
        self._stop_event = threading.Event()

    def run(self):
        while not self._stop_event.wait(self.interval):
            self.func()

    def stop(self):
        self._stop_event.set()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_timer: _RepeatingTimer | None = None


def start_scheduler():
    """Start all background jobs.  Safe to call multiple times (no-op after first)."""
    global _timer
    if _timer is not None:
        return  # already running

    interval_seconds = IMAGE_CHECK_INTERVAL_HOURS * 3600
    logger.info(f"Starting background scheduler (image update check every {IMAGE_CHECK_INTERVAL_HOURS}h)")

    _timer = _RepeatingTimer(
        interval=interval_seconds,
        func=_check_image_updates,
        name="dockermate-image-updater"
    )
    _timer.start()


def stop_scheduler():
    """Stop the background scheduler (used in tests)."""
    global _timer
    if _timer is not None:
        _timer.stop()
        _timer = None
