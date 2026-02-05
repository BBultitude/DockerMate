"""
Shared Flask extensions for DockerMate.

Extensions are created here and initialised with the app via init_app()
in app.py to avoid circular imports.
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
)

# Shared counter for container/network mutation operations.
# All POST/PATCH/DELETE endpoints on the containers and networks blueprints
# share this single counter: 30 operations per minute per source IP.
mutation_limit = limiter.shared_limit("30 per minute", scope="mutation_ops")
