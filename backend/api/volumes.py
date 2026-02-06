"""
DockerMate - Volumes API Blueprint (Sprint 5 Task 1)
====================================================

REST API endpoints for Docker volume management.

Endpoints:
    GET    /api/volumes              - List all volumes
    GET    /api/volumes/<id>         - Get volume details
    POST   /api/volumes              - Create new volume
    DELETE /api/volumes/<id>         - Delete volume
    POST   /api/volumes/<id>/adopt   - Adopt external volume
    DELETE /api/volumes/<id>/adopt   - Release volume from management
    POST   /api/volumes/prune        - Prune unused volumes

Educational Notes:
- Follows REST conventions (GET/POST/DELETE verbs)
- JSON request/response format
- Error handling with appropriate HTTP status codes
- Service layer separation (VolumeManager does the work)
"""

import logging
from flask import Blueprint, request, jsonify

from backend.services.volume_manager import VolumeManager
from backend.utils.exceptions import (
    VolumeNotFoundError,
    VolumeInUseError,
    ValidationError,
    DockerConnectionError
)
from backend.extensions import limiter

# Configure logging
logger = logging.getLogger(__name__)

# Create Blueprint
volumes_bp = Blueprint('volumes', __name__, url_prefix='/api/volumes')


@volumes_bp.route('', methods=['GET'])
def list_volumes():
    """
    List all Docker volumes.

    GET /api/volumes
    Query params:
        - include_external (bool): Show unmanaged volumes (default: true)
        - driver (str): Filter by driver type

    Success Response (200):
    {
        "success": true,
        "volumes": [
            {
                "id": 1,
                "volume_id": "abc123",
                "name": "nginx-data",
                "driver": "local",
                "managed": true,
                "size_bytes": 1234567,
                "containers_using": 2,
                "container_names": ["nginx-web", "nginx-backup"],
                "created_at": "2026-02-06T..."
            },
            ...
        ],
        "count": 5
    }

    Error Responses:
    - 500: Server error (Docker daemon error, database error)

    CLI Equivalent:
        docker volume ls
    """
    try:
        # Parse query parameters
        include_external = request.args.get('include_external', 'true').lower() == 'true'
        driver_filter = request.args.get('driver')

        with VolumeManager() as manager:
            result = manager.list_volumes(
                include_external=include_external,
                driver_filter=driver_filter
            )

        return jsonify(result), 200

    except DockerConnectionError as e:
        logger.error(f"Docker connection error: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "DockerConnectionError"
        }), 500

    except Exception as e:
        logger.exception("Unexpected error listing volumes")
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred",
            "error_type": "ServerError"
        }), 500


@volumes_bp.route('/<path:volume_id>', methods=['GET'])
def get_volume(volume_id):
    """
    Get single volume with details.

    GET /api/volumes/<volume_id>

    Success Response (200):
    {
        "success": true,
        "volume": {
            "id": 1,
            "volume_id": "abc123",
            "name": "nginx-data",
            "driver": "local",
            "mount_point": "/var/lib/docker/volumes/nginx-data/_data",
            "labels": {"env": "prod"},
            "options": {},
            "size_bytes": 1234567,
            "managed": true,
            "containers_using": 1,
            "container_names": ["nginx-web"],
            "mount_details": [
                {
                    "id": "container123",
                    "name": "nginx-web",
                    "mount_path": "/usr/share/nginx/html",
                    "read_only": false
                }
            ],
            "created_at": "2026-02-06T..."
        }
    }

    Error Responses:
    - 404: Volume not found
    - 500: Server error

    CLI Equivalent:
        docker volume inspect <volume_id>
    """
    try:
        with VolumeManager() as manager:
            result = manager.get_volume(volume_id)

        return jsonify(result), 200

    except VolumeNotFoundError as e:
        logger.warning(f"Volume not found: {volume_id}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "VolumeNotFoundError"
        }), 404

    except DockerConnectionError as e:
        logger.error(f"Docker connection error: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "DockerConnectionError"
        }), 500

    except Exception as e:
        logger.exception(f"Unexpected error getting volume {volume_id}")
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred",
            "error_type": "ServerError"
        }), 500


@volumes_bp.route('', methods=['POST'])
@limiter.limit("30 per minute", scope="mutation_limit")
def create_volume():
    """
    Create new volume.

    POST /api/volumes
    Body: {
        "name": "myvolume",
        "driver": "local",
        "labels": {"env": "prod"},
        "options": {}
    }

    Success Response (201):
    {
        "success": true,
        "volume": {...},
        "message": "Volume 'myvolume' created successfully"
    }

    Error Responses:
    - 400: Validation error
    - 500: Server error

    CLI Equivalent:
        docker volume create --driver local myvolume
    """
    try:
        data = request.get_json()

        # Validate required fields
        if not data or 'name' not in data:
            return jsonify({
                "success": False,
                "error": "Missing required field: name",
                "error_type": "ValidationError"
            }), 400

        name = data['name']
        driver = data.get('driver', 'local')
        labels = data.get('labels', {})
        options = data.get('options', {})

        with VolumeManager() as manager:
            result = manager.create_volume(
                name=name,
                driver=driver,
                labels=labels,
                options=options
            )

        return jsonify(result), 201

    except ValidationError as e:
        logger.warning(f"Validation error creating volume: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "ValidationError"
        }), 400

    except DockerConnectionError as e:
        logger.error(f"Docker connection error: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "DockerConnectionError"
        }), 500

    except Exception as e:
        logger.exception("Unexpected error creating volume")
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred",
            "error_type": "ServerError"
        }), 500


@volumes_bp.route('/<path:volume_id>', methods=['DELETE'])
@limiter.limit("30 per minute", scope="mutation_limit")
def delete_volume(volume_id):
    """
    Delete volume.

    DELETE /api/volumes/<volume_id>
    Query params:
        - force (bool): Delete even if in use (default: false)

    Success Response (200):
    {
        "success": true,
        "message": "Volume 'myvolume' deleted successfully"
    }

    Error Responses:
    - 404: Volume not found
    - 409: Volume in use (force=false)
    - 500: Server error

    CLI Equivalent:
        docker volume rm myvolume
    """
    try:
        force = request.args.get('force', 'false').lower() == 'true'

        with VolumeManager() as manager:
            result = manager.delete_volume(volume_id, force=force)

        return jsonify(result), 200

    except VolumeNotFoundError as e:
        logger.warning(f"Volume not found: {volume_id}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "VolumeNotFoundError"
        }), 404

    except VolumeInUseError as e:
        logger.warning(f"Volume in use: {volume_id}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "VolumeInUseError"
        }), 409

    except DockerConnectionError as e:
        logger.error(f"Docker connection error: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "DockerConnectionError"
        }), 500

    except Exception as e:
        logger.exception(f"Unexpected error deleting volume {volume_id}")
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred",
            "error_type": "ServerError"
        }), 500


@volumes_bp.route('/<path:volume_id>/adopt', methods=['POST'])
@limiter.limit("30 per minute", scope="mutation_limit")
def adopt_volume(volume_id):
    """
    Adopt external volume into management.

    POST /api/volumes/<volume_id>/adopt

    Success Response (200):
    {
        "success": true,
        "volume": {...},
        "message": "Volume 'myvolume' is now managed by DockerMate"
    }

    Error Responses:
    - 404: Volume not found
    - 500: Server error

    Educational:
        - Metadata-only operation
        - Sets managed=True in database
        - Volume remains in Docker unchanged
    """
    try:
        with VolumeManager() as manager:
            result = manager.adopt_volume(volume_id)

        return jsonify(result), 200

    except VolumeNotFoundError as e:
        logger.warning(f"Volume not found: {volume_id}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "VolumeNotFoundError"
        }), 404

    except DockerConnectionError as e:
        logger.error(f"Docker connection error: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "DockerConnectionError"
        }), 500

    except Exception as e:
        logger.exception(f"Unexpected error adopting volume {volume_id}")
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred",
            "error_type": "ServerError"
        }), 500


@volumes_bp.route('/<path:volume_id>/adopt', methods=['DELETE'])
@limiter.limit("30 per minute", scope="mutation_limit")
def release_volume(volume_id):
    """
    Release volume from management.

    DELETE /api/volumes/<volume_id>/adopt

    Success Response (200):
    {
        "success": true,
        "message": "Volume 'myvolume' is no longer managed by DockerMate"
    }

    Error Responses:
    - 404: Volume not found
    - 500: Server error

    Educational:
        - Metadata-only operation
        - Removes from database
        - Volume remains in Docker unchanged
    """
    try:
        with VolumeManager() as manager:
            result = manager.release_volume(volume_id)

        return jsonify(result), 200

    except VolumeNotFoundError as e:
        logger.warning(f"Volume not found: {volume_id}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "VolumeNotFoundError"
        }), 404

    except DockerConnectionError as e:
        logger.error(f"Docker connection error: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "DockerConnectionError"
        }), 500

    except Exception as e:
        logger.exception(f"Unexpected error releasing volume {volume_id}")
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred",
            "error_type": "ServerError"
        }), 500


@volumes_bp.route('/prune', methods=['POST'])
@limiter.limit("30 per minute", scope="mutation_limit")
def prune_volumes():
    """
    Remove all unused volumes.

    POST /api/volumes/prune

    Success Response (200):
    {
        "success": true,
        "volumes_deleted": ["vol1", "vol2"],
        "count": 2,
        "space_reclaimed": 1234567,
        "message": "Pruned 2 unused volumes"
    }

    Error Responses:
    - 500: Server error

    CLI Equivalent:
        docker volume prune -f
    """
    try:
        with VolumeManager() as manager:
            result = manager.prune_unused_volumes()

        return jsonify(result), 200

    except DockerConnectionError as e:
        logger.error(f"Docker connection error: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "DockerConnectionError"
        }), 500

    except Exception as e:
        logger.exception("Unexpected error pruning volumes")
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred",
            "error_type": "ServerError"
        }), 500
