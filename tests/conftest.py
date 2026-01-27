"""
Pytest Configuration
====================
Minimal configuration for DockerMate test suite.

This conftest only provides:
- Path setup for imports
- No global fixtures (each test file defines its own)

Note: Individual test files define their own db_session fixtures
to avoid conflicts and allow custom configuration per test suite.
"""

import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))