"""
DockerMate Scheduler Package

Background job scheduling using APScheduler:
- Periodic update checks (configurable interval)
- Health monitoring (hardware-aware intervals)
- SSL certificate renewal (Let's Encrypt)
- Database maintenance (cleanup old data)

Intervals are adjusted based on hardware profile:
- Raspberry Pi: Less frequent (12h updates, 15m health)
- Medium Server: Balanced (6h updates, 5m health)
- High-End: More frequent (3h updates, 2m health)
"""
