"""
DockerMate - Docker Registry Digest Fetcher
============================================

Fetches the current manifest digest for a public image from Docker Hub
using the standard v2 registry API.  No external dependencies — uses
urllib from the standard library.

Flow (Docker Hub only, public images):
    1. POST  https://auth.docker.io/token   → bearer token
    2. GET   https://registry-1.docker.io/v2/<repo>/manifests/<tag>
             with Authorization: Bearer <token>
             → Docker-Content-Digest header contains sha256:...

For official images (e.g. "nginx") the repository name sent to the
registry must be prefixed with "library/" (e.g. "library/nginx").

Usage:
    from backend.utils.registry import get_remote_digest

    digest = get_remote_digest("nginx", "latest")
    # "sha256:abc123..."  or None on failure
"""

import json
import logging
import urllib.request
import urllib.error
from typing import Optional

logger = logging.getLogger(__name__)

# Docker Hub endpoints
_AUTH_URL      = "https://auth.docker.io/token"
_REGISTRY_URL  = "https://registry-1.docker.io"

# Accept header that tells the registry to return a manifest we can digest
_MANIFEST_ACCEPT = (
    "application/vnd.docker.distribution.manifest.v2+json, "
    "application/vnd.docker.distribution.manifest.list.v2+json"
)

# Network timeout in seconds
_TIMEOUT = 10


def _qualify_repo(repository: str) -> str:
    """Prepend 'library/' to official single-name images."""
    return repository if '/' in repository else f"library/{repository}"


def _get_token(repository: str) -> Optional[str]:
    """Get an anonymous bearer token scoped to the given repository."""
    qualified = _qualify_repo(repository)
    url = f"{_AUTH_URL}?service=registry.docker.io&scope=repository:{qualified}:pull"
    try:
        req  = urllib.request.Request(url)
        resp = urllib.request.urlopen(req, timeout=_TIMEOUT)
        return json.loads(resp.read())["token"]
    except Exception as e:
        logger.warning(f"registry token fetch failed for {repository}: {e}")
        return None


def get_remote_digest(repository: str, tag: str = "latest") -> Optional[str]:
    """
    Fetch the current manifest digest for *repository:tag* from Docker Hub.

    Returns the full digest string (e.g. "sha256:abc123…") or None if the
    request fails for any reason (network error, 404, private image, etc.).

    This is intentionally best-effort — a None return just means the update
    check is skipped for that image; it does not surface as an error.
    """
    token = _get_token(repository)
    if not token:
        return None

    qualified = _qualify_repo(repository)
    url = f"{_REGISTRY_URL}/v2/{qualified}/manifests/{tag}"

    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", _MANIFEST_ACCEPT)

    try:
        resp = urllib.request.urlopen(req, timeout=_TIMEOUT)
        # The digest we care about is in the response header
        return resp.headers.get("Docker-Content-Digest")
    except urllib.error.HTTPError as e:
        logger.debug(f"registry manifest fetch {repository}:{tag} → HTTP {e.code}")
        return None
    except Exception as e:
        logger.warning(f"registry manifest fetch failed for {repository}:{tag}: {e}")
        return None
