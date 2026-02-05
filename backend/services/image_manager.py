"""
DockerMate - Image Manager Service (Sprint 3)
==============================================

High-level service layer for Docker image management with:
- Image listing and metadata tracking
- Image pulling from registries
- Image removal
- Update detection (comparing local vs registry digests)
- Database synchronization

Usage:
    from backend.services.image_manager import ImageManager

    manager = ImageManager()

    # List images
    images = manager.list_images()

    # Pull image
    image = manager.pull_image('nginx', 'latest')

    # Get image details
    image = manager.get_image('nginx:latest')

    # Remove image
    manager.remove_image('nginx:latest', force=False)

    # Check for updates
    updates = manager.check_for_updates()

Educational Notes:
- Service layer pattern separates business logic from API routes
- Database persistence tracks image metadata
- Update detection compares digests with registry
- Docker SDK integration for image operations
"""

import logging
import json
from typing import List, Dict, Optional, Any
from datetime import datetime

from sqlalchemy.orm import Session
from docker.errors import NotFound, APIError, ImageNotFound

from backend.utils.docker_client import get_docker_client, docker_operation
from backend.utils.exceptions import (
    ContainerOperationError,
    DockerConnectionError,
    ValidationError,
    ImageNotFoundError
)
from backend.models.database import SessionLocal
from backend.models.image import Image

# Configure logging
logger = logging.getLogger(__name__)


class ImageManager:
    """
    Service class for Docker image management.

    Provides high-level operations for image CRUD, pulling, and update detection.
    Maintains database state synchronized with Docker daemon.

    Design Principles:
    - Database-backed: Syncs image state to SQLite
    - Fail-fast: Validates before Docker operations
    - Educational: Shows CLI equivalents for learning

    Sprint 3 Implementation:
    - Full CRUD operations for images
    - Pull images from registries
    - Track image metadata
    - Update detection (future enhancement)
    """

    def __init__(self, db: Optional[Session] = None):
        """
        Initialize ImageManager.

        Args:
            db: Database session (optional, creates new if not provided)

        Educational:
            - Dependency injection allows testing with mock database
            - Default session creation for convenience in production
        """
        self.db = db or SessionLocal()
        self._owns_session = db is None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup database session if we own it."""
        if self._owns_session and self.db:
            self.db.close()

    # =========================================================================
    # READ OPERATIONS
    # =========================================================================

    def list_images(self) -> List[Dict[str, Any]]:
        """
        List all Docker images on the system.

        Queries Docker daemon for all images and syncs with database.
        Returns combined data from both sources.

        Returns:
            list: List of image dictionaries with metadata

        Educational:
            - Queries Docker daemon for current state
            - Syncs with database for persistence
            - CLI equivalent: docker images
        """
        logger.debug("Listing all Docker images")

        client = get_docker_client()
        docker_images = client.images.list()

        result = []
        for docker_image in docker_images:
            # Sync to database and get full metadata
            image_data = self._sync_database_state(docker_image)
            result.append(image_data)

        return result

    def get_image(self, name_or_id: str) -> Dict[str, Any]:
        """
        Get single image by name or ID.

        Args:
            name_or_id: Image name (repository:tag) or Docker ID

        Returns:
            dict: Image details with metadata

        Raises:
            ImageNotFoundError: Image doesn't exist

        Educational:
            - Accepts both name and ID for flexibility
            - Returns merged database + Docker state
            - CLI equivalent: docker inspect <image>
        """
        logger.debug(f"Getting image: {name_or_id}")

        client = get_docker_client()
        try:
            docker_image = client.images.get(name_or_id)
            return self._sync_database_state(docker_image)
        except NotFound:
            raise ImageNotFoundError(f"Image '{name_or_id}' not found")

    # =========================================================================
    # CREATE OPERATION (PULL)
    # =========================================================================

    @docker_operation
    def pull_image(
        self,
        repository: str,
        tag: str = 'latest',
        platform: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Pull an image from a Docker registry.

        Args:
            repository: Image repository (e.g., 'nginx', 'mysql')
            tag: Image tag (default: 'latest')
            platform: Platform (e.g., 'linux/amd64', optional)

        Returns:
            dict: Pulled image details

        Raises:
            ContainerOperationError: Pull failed
            ValidationError: Invalid input

        Educational:
            - Pulls from Docker Hub by default
            - Can pull from private registries (auth required)
            - Syncs to database after successful pull
            - CLI equivalent: docker pull <repository>:<tag>
        """
        logger.info(f"Pulling image: {repository}:{tag}")

        # Validate input
        if not repository or not repository.strip():
            raise ValidationError("Repository name cannot be empty")

        if not tag or not tag.strip():
            raise ValidationError("Tag cannot be empty")

        # Pull image
        client = get_docker_client()
        try:
            image_name = f"{repository}:{tag}"
            docker_image = client.images.pull(repository, tag=tag, platform=platform)
            logger.info(f"Successfully pulled image: {image_name}")

            # Sync to database
            return self._sync_database_state(docker_image)

        except APIError as e:
            raise ContainerOperationError(
                f"Failed to pull image {repository}:{tag}: {e.explanation}"
            )

    # =========================================================================
    # DELETE OPERATION
    # =========================================================================

    @docker_operation
    def remove_image(
        self,
        name_or_id: str,
        force: bool = False,
        noprune: bool = False
    ) -> Dict[str, str]:
        """
        Remove a Docker image.

        Args:
            name_or_id: Image name or ID
            force: Force removal even if containers are using it
            noprune: Don't delete untagged parents

        Returns:
            dict: Removal status

        Raises:
            ImageNotFoundError: Image doesn't exist
            ContainerOperationError: Removal failed

        Educational:
            - force=True removes image even if containers use it
            - noprune=True keeps parent layers
            - CLI equivalent: docker rmi [-f] <image>
        """
        logger.info(f"Removing image: {name_or_id} (force={force})")

        # Get image from database
        image = self.db.query(Image).filter(
            (Image.image_id == name_or_id) |
            ((Image.repository + ':' + Image.tag) == name_or_id)
        ).first()

        # Remove from Docker
        client = get_docker_client()
        try:
            client.images.remove(name_or_id, force=force, noprune=noprune)
            logger.info(f"Image removed from Docker: {name_or_id}")
        except NotFound:
            logger.warning(f"Image {name_or_id} not found in Docker (already removed)")
        except APIError as e:
            raise ContainerOperationError(
                f"Failed to remove image {name_or_id}: {e.explanation}"
            )

        # Remove from database if it exists
        if image:
            self.db.delete(image)
            self.db.commit()
            logger.info(f"Image removed from database: {name_or_id}")

        return {
            'status': 'removed',
            'message': f"Image '{name_or_id}' successfully removed"
        }

    # =========================================================================
    # TAG OPERATION
    # =========================================================================

    @docker_operation
    def tag_image(
        self,
        name_or_id: str,
        repository: str,
        tag: str = 'latest'
    ) -> Dict[str, Any]:
        """
        Tag an image with a new name.

        Args:
            name_or_id: Source image name or ID
            repository: Target repository name
            tag: Target tag (default: 'latest')

        Returns:
            dict: Tagged image details

        Raises:
            ImageNotFoundError: Source image doesn't exist
            ContainerOperationError: Tagging failed

        Educational:
            - Creates a new reference to the same image
            - Doesn't duplicate image data
            - CLI equivalent: docker tag <source> <target>:<tag>
        """
        logger.info(f"Tagging image: {name_or_id} as {repository}:{tag}")

        client = get_docker_client()
        try:
            docker_image = client.images.get(name_or_id)
            success = docker_image.tag(repository, tag=tag)

            if not success:
                raise ContainerOperationError(f"Failed to tag image {name_or_id}")

            logger.info(f"Successfully tagged image: {repository}:{tag}")

            # Get the newly tagged image and sync
            tagged_image = client.images.get(f"{repository}:{tag}")
            return self._sync_database_state(tagged_image)

        except NotFound:
            raise ImageNotFoundError(f"Image '{name_or_id}' not found")
        except APIError as e:
            raise ContainerOperationError(
                f"Failed to tag image: {e.explanation}"
            )

    # =========================================================================
    # UPDATE DETECTION
    # =========================================================================

    def check_for_updates(self) -> List[Dict[str, Any]]:
        """
        Check all local images against Docker Hub for newer digests.

        For each tracked image that has a known local digest and a valid
        repository name, fetches the current manifest digest from the registry
        and compares.  Sets update_available = True when they differ.

        Images that are skipped (no digest, <none> repo, private/unreachable
        registries) are simply left unchanged — the check is best-effort.

        Returns:
            list: Dicts for images that have update_available == True

        Educational:
            - Docker tags are mutable pointers; digests are immutable content hashes
            - "latest" can silently point to a different digest after a push
            - Comparing digests is the only reliable way to detect updates
            - CLI equivalent: docker pull --quiet <image> (pulls only if changed)
        """
        logger.info("Checking for image updates")
        from backend.utils.registry import get_remote_digest

        images_with_updates = []
        all_images = self.db.query(Image).all()

        for image in all_images:
            image.last_checked = datetime.utcnow()

            # Skip images we can't meaningfully check
            if image.repository in ('<none>', '') or image.tag in ('<none>', ''):
                continue

            remote_digest = get_remote_digest(image.repository, image.tag)
            if remote_digest is None:
                # Registry unreachable or image not public — skip silently
                continue

            if image.digest and image.digest != remote_digest:
                image.update_available = True
                logger.info(f"Update available: {image.repository}:{image.tag} "
                            f"(local={image.digest[:24]}… remote={remote_digest[:24]}…)")
            elif image.digest == remote_digest:
                image.update_available = False

            if image.update_available:
                images_with_updates.append(image.to_dict())

        self.db.commit()
        logger.info(f"Update check complete. {len(images_with_updates)} image(s) have updates")
        return images_with_updates

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _sync_database_state(self, docker_image) -> Dict[str, Any]:
        """
        Sync Docker image state to database.

        Creates or updates Image record in database with current
        state from Docker daemon.

        Args:
            docker_image: Docker SDK image object

        Returns:
            dict: Image data dictionary

        Educational:
            - Database keeps metadata even when image is removed
            - Timestamps track lifecycle events
            - Labels and digests stored for update detection
        """
        attrs = docker_image.attrs

        # Extract image details
        image_id = docker_image.id
        if image_id.startswith('sha256:'):
            image_id = image_id[7:]  # Remove 'sha256:' prefix

        # Extract repository and tag from RepoTags
        repo_tags = docker_image.tags
        if repo_tags:
            # Use first tag
            full_name = repo_tags[0]
            if ':' in full_name:
                repository, tag = full_name.rsplit(':', 1)
            else:
                repository = full_name
                tag = 'latest'
        else:
            # Untagged image
            repository = '<none>'
            tag = '<none>'

        # Extract digest from RepoDigests
        digest = None
        repo_digests = attrs.get('RepoDigests', [])
        if repo_digests:
            # Format: repository@sha256:digest
            digest = repo_digests[0].split('@')[-1] if '@' in repo_digests[0] else None

        # Extract size
        size_bytes = attrs.get('Size', 0)

        # Extract creation timestamp
        created_str = attrs.get('Created', '')
        created_at = None
        if created_str:
            try:
                created_at = datetime.fromisoformat(created_str.rstrip('Z'))
            except Exception:
                pass

        # Extract labels
        labels = attrs.get('Config', {}).get('Labels') or {}
        labels_json = json.dumps(labels)

        # Check if image exists in database
        existing = self.db.query(Image).filter(
            Image.image_id == image_id
        ).first()

        if existing:
            # Update existing record
            existing.repository = repository
            existing.tag = tag
            existing.digest = digest
            existing.size_bytes = size_bytes
            existing.labels_json = labels_json
            if created_at:
                existing.created_at = created_at

            image_record = existing
        else:
            # Create new record
            image_record = Image(
                image_id=image_id,
                repository=repository,
                tag=tag,
                digest=digest,
                size_bytes=size_bytes,
                labels_json=labels_json,
                created_at=created_at,
                pulled_at=datetime.utcnow()
            )
            self.db.add(image_record)

        self.db.commit()
        self.db.refresh(image_record)

        return image_record.to_dict()
