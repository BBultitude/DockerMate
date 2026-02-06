"""
DockerMate - Volume Manager Service (Sprint 5 Task 1)
======================================================

Service layer for Docker volume lifecycle management with:
- Volume CRUD operations (list, get, create, delete)
- Management operations (adopt, release, prune)
- Usage tracking (which containers use which volumes)
- Database synchronization

Key responsibilities
---------------------
* CRUD against the Docker daemon (via the SDK) and mirror state into the
  ``volumes`` DB table for the UI.
* Track volume usage by inspecting container mounts.
* Support adopt/release workflow for external volumes.
* Provide prune operation to clean up unused volumes.

Usage
-----
    from backend.services.volume_manager import VolumeManager

    manager = VolumeManager()
    volumes = manager.list_volumes()
    manager.create_volume(name='data-vol', driver='local')
    manager.delete_volume('data-vol', force=False)
"""

import logging
import json
import re
from typing import List, Dict, Optional, Any

from sqlalchemy.orm import Session
from docker.errors import NotFound, APIError

from backend.models.database import SessionLocal
from backend.models.volume import Volume
from backend.utils.docker_client import get_docker_client
from backend.utils.exceptions import (
    VolumeNotFoundError,
    VolumeInUseError,
    ValidationError,
    DockerConnectionError
)

logger = logging.getLogger(__name__)


class VolumeManager:
    """
    Service class for Docker volume management.

    Provides high-level operations for volume CRUD, adoption, and cleanup.
    Maintains database state synchronized with Docker daemon.

    Design Principles:
    - Database-backed: Syncs volume state to SQLite
    - Usage-aware: Tracks which containers use volumes
    - Fail-fast: Validates before Docker operations
    """

    def __init__(self, db: Optional[Session] = None):
        """
        Initialize VolumeManager.

        Args:
            db: Database session (optional, creates new if not provided)
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

    def list_volumes(self, include_external: bool = True, driver_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        List all Docker volumes with usage statistics.

        Args:
            include_external: Include volumes not managed by DockerMate
            driver_filter: Filter by driver type (e.g., 'local')

        Returns:
            dict: {
                'success': True,
                'volumes': [...],
                'count': N
            }

        Educational:
            - Queries Docker daemon for current state
            - Enriches with container usage information
            - CLI equivalent: docker volume ls
        """
        logger.debug(f"Listing volumes (include_external={include_external}, driver_filter={driver_filter})")

        try:
            client = get_docker_client()
            docker_volumes = client.volumes.list()

            # Build volume usage map (volume_name -> list of container info)
            usage_map = self._build_volume_usage_map()

            # Process each volume
            result = []
            for docker_volume in docker_volumes:
                volume_data = self._sync_database_state(docker_volume)

                # Add usage information
                volume_name = volume_data['name']
                usage = usage_map.get(volume_name, [])
                volume_data['containers_using'] = len(usage)
                volume_data['container_names'] = [c['name'] for c in usage]
                volume_data['mount_details'] = usage

                # Apply filters
                if not include_external and not volume_data['managed']:
                    continue
                if driver_filter and volume_data['driver'] != driver_filter:
                    continue

                result.append(volume_data)

            # Sort by name
            result.sort(key=lambda v: v['name'])

            return {
                'success': True,
                'volumes': result,
                'count': len(result)
            }

        except Exception as e:
            logger.error(f"Failed to list volumes: {e}")
            raise DockerConnectionError(f"Failed to list volumes: {str(e)}")

    def get_volume(self, name_or_id: str) -> Dict[str, Any]:
        """
        Get single volume with full details.

        Args:
            name_or_id: Volume name or Docker ID

        Returns:
            dict: Volume details with usage information

        Raises:
            VolumeNotFoundError: Volume doesn't exist

        Educational:
            - Accepts both name and ID for flexibility
            - Returns merged database + Docker state
            - CLI equivalent: docker volume inspect <name>
        """
        logger.debug(f"Getting volume: {name_or_id}")

        try:
            client = get_docker_client()

            # Try to get volume by name first, then by ID
            try:
                docker_volume = client.volumes.get(name_or_id)
            except NotFound:
                # Try searching by volume_id in database
                db_volume = self.db.query(Volume).filter(
                    Volume.volume_id == name_or_id
                ).first()
                if db_volume:
                    docker_volume = client.volumes.get(db_volume.name)
                else:
                    raise VolumeNotFoundError(f"Volume not found: {name_or_id}")

            # Get volume data and usage
            volume_data = self._sync_database_state(docker_volume)

            # Add detailed usage information
            usage = self._get_volume_usage(volume_data['name'])
            volume_data['containers_using'] = len(usage)
            volume_data['container_names'] = [c['name'] for c in usage]
            volume_data['mount_details'] = usage

            return {
                'success': True,
                'volume': volume_data
            }

        except VolumeNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get volume {name_or_id}: {e}")
            raise DockerConnectionError(f"Failed to get volume: {str(e)}")

    # =========================================================================
    # CREATE/DELETE OPERATIONS
    # =========================================================================

    def create_volume(self, name: str, driver: str = 'local', labels: Optional[Dict] = None,
                     options: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Create new volume and sync to database.

        Args:
            name: Volume name (alphanumeric + hyphens/underscores)
            driver: Volume driver (default: 'local')
            labels: Optional labels dict
            options: Optional driver-specific options dict

        Returns:
            dict: Created volume details

        Raises:
            ValidationError: Invalid volume name
            ContainerOperationError: Volume already exists

        Educational:
            - Validates name format before creation
            - Syncs to database with managed=True
            - CLI equivalent: docker volume create --driver local myvolume
        """
        logger.info(f"Creating volume: {name} (driver={driver})")

        # Validate name
        self._validate_volume_name(name)

        try:
            client = get_docker_client()

            # Check if volume already exists
            try:
                existing = client.volumes.get(name)
                raise ValidationError(f"Volume already exists: {name}")
            except NotFound:
                pass  # Good, doesn't exist

            # Create volume
            docker_volume = client.volumes.create(
                name=name,
                driver=driver,
                labels=labels or {},
                driver_opts=options or {}
            )

            # Sync to database with managed=True
            volume_data = self._sync_database_state(docker_volume, managed=True)

            # Add empty usage info
            volume_data['containers_using'] = 0
            volume_data['container_names'] = []
            volume_data['mount_details'] = []

            logger.info(f"Volume created successfully: {name}")
            return {
                'success': True,
                'volume': volume_data,
                'message': f"Volume '{name}' created successfully"
            }

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to create volume {name}: {e}")
            raise DockerConnectionError(f"Failed to create volume: {str(e)}")

    def delete_volume(self, name_or_id: str, force: bool = False) -> Dict[str, Any]:
        """
        Delete volume with safety checks.

        Args:
            name_or_id: Volume name or Docker ID
            force: Delete even if in use (stops containers first)

        Returns:
            dict: Success message

        Raises:
            VolumeNotFoundError: Volume doesn't exist
            VolumeInUseError: Volume is in use and force=False

        Educational:
            - Checks usage before deletion
            - Requires force=True if in use
            - Removes from database
            - CLI equivalent: docker volume rm myvolume
        """
        logger.info(f"Deleting volume: {name_or_id} (force={force})")

        try:
            client = get_docker_client()

            # Get volume to find its name
            volume_info = self.get_volume(name_or_id)
            volume_name = volume_info['volume']['name']

            # Check usage
            usage = self._get_volume_usage(volume_name)

            if usage and not force:
                container_names = [c['name'] for c in usage]
                raise VolumeInUseError(
                    f"Volume is in use by containers: {', '.join(container_names)}. "
                    f"Use force=true to delete anyway."
                )

            # If force and in use, stop containers first
            if usage and force:
                logger.warning(f"Force deleting volume in use by {len(usage)} containers")
                for container_info in usage:
                    try:
                        container = client.containers.get(container_info['id'])
                        container.stop(timeout=5)
                        logger.info(f"Stopped container {container_info['name']}")
                    except Exception as e:
                        logger.warning(f"Failed to stop container {container_info['name']}: {e}")

            # Delete from Docker
            docker_volume = client.volumes.get(volume_name)
            docker_volume.remove(force=force)

            # Remove from database
            db_volume = self.db.query(Volume).filter(
                (Volume.name == volume_name) | (Volume.volume_id == name_or_id)
            ).first()
            if db_volume:
                self.db.delete(db_volume)
                self.db.commit()

            logger.info(f"Volume deleted successfully: {volume_name}")
            return {
                'success': True,
                'message': f"Volume '{volume_name}' deleted successfully"
            }

        except (VolumeNotFoundError, VolumeInUseError):
            raise
        except NotFound:
            raise VolumeNotFoundError(f"Volume not found: {name_or_id}")
        except Exception as e:
            logger.error(f"Failed to delete volume {name_or_id}: {e}")
            self.db.rollback()
            raise DockerConnectionError(f"Failed to delete volume: {str(e)}")

    # =========================================================================
    # MANAGEMENT OPERATIONS
    # =========================================================================

    def adopt_volume(self, name_or_id: str) -> Dict[str, Any]:
        """
        Adopt external volume into DockerMate management.

        Args:
            name_or_id: Volume name or Docker ID

        Returns:
            dict: Adopted volume details

        Raises:
            VolumeNotFoundError: Volume doesn't exist

        Educational:
            - Metadata-only operation (like adopt_network)
            - Sets managed=True in database
            - Volume remains in Docker unchanged
        """
        logger.info(f"Adopting volume: {name_or_id}")

        try:
            client = get_docker_client()

            # Get volume from Docker
            try:
                docker_volume = client.volumes.get(name_or_id)
            except NotFound:
                raise VolumeNotFoundError(f"Volume not found: {name_or_id}")

            # Sync to database with managed=True
            volume_data = self._sync_database_state(docker_volume, managed=True)

            logger.info(f"Volume adopted successfully: {volume_data['name']}")
            return {
                'success': True,
                'volume': volume_data,
                'message': f"Volume '{volume_data['name']}' is now managed by DockerMate"
            }

        except VolumeNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to adopt volume {name_or_id}: {e}")
            raise DockerConnectionError(f"Failed to adopt volume: {str(e)}")

    def release_volume(self, name_or_id: str) -> Dict[str, Any]:
        """
        Release volume from DockerMate management.

        Args:
            name_or_id: Volume name or Docker ID

        Returns:
            dict: Success message

        Educational:
            - Metadata-only - volume remains in Docker
            - Removes from database
            - Volume can still be adopted again later
        """
        logger.info(f"Releasing volume: {name_or_id}")

        try:
            # Find in database
            db_volume = self.db.query(Volume).filter(
                (Volume.name == name_or_id) | (Volume.volume_id == name_or_id)
            ).first()

            if not db_volume:
                raise VolumeNotFoundError(f"Volume not found in database: {name_or_id}")

            volume_name = db_volume.name

            # Remove from database
            self.db.delete(db_volume)
            self.db.commit()

            logger.info(f"Volume released successfully: {volume_name}")
            return {
                'success': True,
                'message': f"Volume '{volume_name}' is no longer managed by DockerMate"
            }

        except VolumeNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to release volume {name_or_id}: {e}")
            self.db.rollback()
            raise DockerConnectionError(f"Failed to release volume: {str(e)}")

    def prune_unused_volumes(self) -> Dict[str, Any]:
        """
        Remove all unused volumes.

        Returns:
            dict: {
                'success': True,
                'volumes_deleted': [...],
                'space_reclaimed': bytes
            }

        Educational:
            - Removes volumes not mounted to any container
            - Updates database
            - CLI equivalent: docker volume prune -f
        """
        logger.info("Pruning unused volumes")

        try:
            client = get_docker_client()

            # Get usage map
            usage_map = self._build_volume_usage_map()

            # Get all volumes
            docker_volumes = client.volumes.list()

            deleted_volumes = []
            space_reclaimed = 0

            for docker_volume in docker_volumes:
                volume_name = docker_volume.name

                # Skip if in use
                if volume_name in usage_map:
                    logger.debug(f"Skipping in-use volume: {volume_name}")
                    continue

                try:
                    # Get size if available
                    attrs = docker_volume.attrs
                    size = 0
                    if 'UsageData' in attrs and attrs['UsageData']:
                        size = attrs['UsageData'].get('Size', 0)

                    # Delete volume
                    docker_volume.remove()
                    deleted_volumes.append(volume_name)
                    space_reclaimed += size

                    # Remove from database
                    db_volume = self.db.query(Volume).filter(
                        Volume.name == volume_name
                    ).first()
                    if db_volume:
                        self.db.delete(db_volume)

                    logger.info(f"Pruned volume: {volume_name}")

                except Exception as e:
                    logger.warning(f"Failed to prune volume {volume_name}: {e}")
                    continue

            self.db.commit()

            logger.info(f"Pruned {len(deleted_volumes)} volumes, reclaimed {space_reclaimed} bytes")
            return {
                'success': True,
                'volumes_deleted': deleted_volumes,
                'count': len(deleted_volumes),
                'space_reclaimed': space_reclaimed,
                'message': f"Pruned {len(deleted_volumes)} unused volumes"
            }

        except Exception as e:
            logger.error(f"Failed to prune volumes: {e}")
            self.db.rollback()
            raise DockerConnectionError(f"Failed to prune volumes: {str(e)}")

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _sync_database_state(self, docker_volume, managed: Optional[bool] = None) -> Dict[str, Any]:
        """
        Sync Docker volume to database record.

        Args:
            docker_volume: Docker SDK volume object
            managed: Override managed flag (None = keep existing)

        Returns:
            dict: Volume data for API response
        """
        # Extract volume metadata
        attrs = docker_volume.attrs
        volume_id = attrs.get('Name', '')  # Docker uses Name as the ID for volumes
        name = docker_volume.name
        driver = attrs.get('Driver', 'local')
        mount_point = attrs.get('Mountpoint', '')

        # Extract labels and options
        labels = attrs.get('Labels') or {}
        options = attrs.get('Options') or {}

        # Extract size if available
        size_bytes = None
        if 'UsageData' in attrs and attrs['UsageData']:
            size_bytes = attrs['UsageData'].get('Size')

        # Query database for existing record
        db_volume = self.db.query(Volume).filter(
            (Volume.volume_id == volume_id) | (Volume.name == name)
        ).first()

        if db_volume:
            # Update existing record
            db_volume.name = name
            db_volume.volume_id = volume_id
            db_volume.driver = driver
            db_volume.mount_point = mount_point
            db_volume.labels_json = json.dumps(labels)
            db_volume.options_json = json.dumps(options)
            db_volume.size_bytes = size_bytes
            if managed is not None:
                db_volume.managed = managed
        else:
            # Create new record
            db_volume = Volume(
                volume_id=volume_id,
                name=name,
                driver=driver,
                mount_point=mount_point,
                labels_json=json.dumps(labels),
                options_json=json.dumps(options),
                size_bytes=size_bytes,
                managed=managed if managed is not None else False
            )
            self.db.add(db_volume)

        self.db.commit()
        self.db.refresh(db_volume)

        return db_volume.to_dict()

    def _build_volume_usage_map(self) -> Dict[str, List[Dict]]:
        """
        Build map of volume_name -> list of containers using it.

        Returns:
            dict: {volume_name: [{id, name, mount_path, read_only}, ...]}
        """
        usage_map = {}

        try:
            client = get_docker_client()
            containers = client.containers.list(all=True)

            for container in containers:
                # Inspect mounts
                mounts = container.attrs.get('Mounts', [])
                for mount in mounts:
                    # Only track named volumes (Type=volume), not bind mounts
                    if mount.get('Type') != 'volume':
                        continue

                    volume_name = mount.get('Name')
                    if not volume_name:
                        continue

                    if volume_name not in usage_map:
                        usage_map[volume_name] = []

                    usage_map[volume_name].append({
                        'id': container.id,
                        'name': container.name,
                        'mount_path': mount.get('Destination', ''),
                        'read_only': mount.get('RW', True) == False
                    })

        except Exception as e:
            logger.warning(f"Failed to build volume usage map: {e}")

        return usage_map

    def _get_volume_usage(self, volume_name: str) -> List[Dict]:
        """
        Get list of containers using this volume.

        Args:
            volume_name: Name of the volume

        Returns:
            list: [{id, name, mount_path, read_only}, ...]
        """
        usage_map = self._build_volume_usage_map()
        return usage_map.get(volume_name, [])

    def _validate_volume_name(self, name: str):
        """
        Validate volume name format.

        Args:
            name: Volume name to validate

        Raises:
            ValidationError: Invalid name format

        Educational:
            - Volume names: alphanumeric + hyphens/underscores/dots
            - Length: 1-255 characters
            - Cannot start with hyphen or dot
        """
        if not name:
            raise ValidationError("Volume name cannot be empty")

        if len(name) > 255:
            raise ValidationError("Volume name cannot exceed 255 characters")

        # Docker volume name pattern: [a-zA-Z0-9][a-zA-Z0-9_.-]*
        pattern = r'^[a-zA-Z0-9][a-zA-Z0-9_.-]*$'
        if not re.match(pattern, name):
            raise ValidationError(
                "Volume name must start with alphanumeric character and contain only "
                "alphanumeric characters, hyphens, underscores, and dots"
            )
