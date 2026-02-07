"""
DockerMate Backend Package

This package contains all backend logic for DockerMate:
- API endpoints (REST API)
- Authentication & session management
- SSL/TLS certificate handling
- Docker management operations
- Database models
- Utilities and helpers
- Background schedulers

Author: DockerMate Team
License: MIT
"""

import os

# Read version from VERSION file (single source of truth)
_version_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'VERSION')
try:
    with open(_version_file, 'r') as f:
        __version__ = f.read().strip()
except FileNotFoundError:
    __version__ = "1.0.0"  # Fallback

__author__ = "DockerMate Team"
