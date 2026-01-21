"""
DockerMate Database Models Package

SQLAlchemy ORM models for SQLite database:
- User (authentication)
- Session (session management)
- Container (container metadata)
- Network (network configuration)
- Environment (environment tags: PRD/UAT/DEV/SANDBOX)
- HostConfig (hardware profile, settings)
- IPReservation (network IPAM)
- UpdateCheck (update detection)
- UpdateHistory (update tracking)
- HealthCheck (health monitoring)
- LogAnalysis (log analysis results)
- SSLCertificate (SSL cert tracking)
- SecurityEvent (security audit log)

All models include created_at/updated_at timestamps for audit trail.
"""
