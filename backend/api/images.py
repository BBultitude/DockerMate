"""
DockerMate - Images API Blueprint (Sprint 3)
=============================================

REST API endpoints for Docker image management.

Endpoints:
    GET    /api/images              - List all images
    GET    /api/images/<id>         - Get image details
    POST   /api/images/pull         - Pull image from registry
    DELETE /api/images/<id>         - Remove image
    POST   /api/images/<id>/tag     - Tag image
    GET    /api/images/updates      - Check for available updates

Educational Notes:
- Follows REST conventions (GET/POST/DELETE verbs)
- JSON request/response format
- Error handling with appropriate HTTP status codes
- Service layer separation (ImageManager does the work)
"""

import logging
from flask import Blueprint, request, jsonify

from backend.services.image_manager import ImageManager
from backend.utils.exceptions import (
    ImageNotFoundError,
    ContainerOperationError,
    ValidationError,
    DockerConnectionError
)

# Configure logging
logger = logging.getLogger(__name__)

# Create Blueprint
images_bp = Blueprint('images', __name__, url_prefix='/api/images')


@images_bp.route('', methods=['GET'])
def list_images():
    """
    List all Docker images.

    GET /api/images

    Success Response (200):
    {
        "success": true,
        "data": [
            {
                "id": 1,
                "image_id": "abc123...",
                "repository": "nginx",
                "tag": "latest",
                "full_name": "nginx:latest",
                "size_bytes": 142000000,
                "created_at": "2025-01-27T10:30:00Z",
                "pulled_at": "2025-02-01T15:00:00Z",
                "update_available": false
            },
            ...
        ],
        "count": 5
    }

    Error Responses:
    - 500: Server error (Docker daemon error, database error)

    CLI Equivalent:
        docker images
    """
    try:
        with ImageManager() as manager:
            images = manager.list_images()

        return jsonify({
            "success": True,
            "data": images,
            "count": len(images)
        }), 200

    except DockerConnectionError as e:
        logger.error(f"Docker connection error: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "DockerConnectionError"
        }), 500

    except Exception as e:
        logger.exception("Unexpected error listing images")
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred",
            "error_type": "ServerError"
        }), 500


@images_bp.route('/<path:name_or_id>', methods=['GET'])
def get_image(name_or_id: str):
    """
    Get details for a specific image.

    GET /api/images/<name_or_id>

    Args:
        name_or_id: Image name (repository:tag) or Docker ID

    Success Response (200):
    {
        "success": true,
        "data": {
            "id": 1,
            "image_id": "abc123...",
            "repository": "nginx",
            "tag": "latest",
            "full_name": "nginx:latest",
            "digest": "sha256:...",
            "size_bytes": 142000000,
            "labels_json": "{}",
            "created_at": "2025-01-27T10:30:00Z",
            "pulled_at": "2025-02-01T15:00:00Z",
            "last_checked": null,
            "update_available": false
        }
    }

    Error Responses:
    - 404: Image not found
    - 500: Server error

    CLI Equivalent:
        docker inspect <image>
    """
    try:
        with ImageManager() as manager:
            image = manager.get_image(name_or_id)

        return jsonify({
            "success": True,
            "data": image
        }), 200

    except ImageNotFoundError as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "ImageNotFoundError"
        }), 404

    except Exception as e:
        logger.exception(f"Error getting image {name_or_id}")
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred",
            "error_type": "ServerError"
        }), 500


@images_bp.route('/pull', methods=['POST'])
def pull_image():
    """
    Pull an image from a Docker registry.

    POST /api/images/pull

    Request Body:
    {
        "repository": "nginx",
        "tag": "latest",
        "platform": "linux/amd64"  // optional
    }

    Success Response (200):
    {
        "success": true,
        "data": {
            "id": 1,
            "image_id": "abc123...",
            "repository": "nginx",
            "tag": "latest",
            "full_name": "nginx:latest",
            "size_bytes": 142000000
        },
        "message": "Image nginx:latest pulled successfully"
    }

    Error Responses:
    - 400: Validation error (missing repository, invalid tag)
    - 500: Pull failed (network error, image not found in registry)

    CLI Equivalent:
        docker pull nginx:latest
    """
    try:
        data = request.get_json()

        # Validate required fields
        repository = data.get('repository')
        if not repository:
            return jsonify({
                "success": False,
                "error": "Repository name is required",
                "error_type": "ValidationError"
            }), 400

        tag = data.get('tag', 'latest')
        platform = data.get('platform')

        # Pull image
        with ImageManager() as manager:
            image = manager.pull_image(repository, tag, platform)

        return jsonify({
            "success": True,
            "data": image,
            "message": f"Image {repository}:{tag} pulled successfully"
        }), 200

    except ValidationError as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "ValidationError"
        }), 400

    except ContainerOperationError as e:
        logger.error(f"Failed to pull image: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "ContainerOperationError"
        }), 500

    except Exception as e:
        logger.exception("Unexpected error pulling image")
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred",
            "error_type": "ServerError"
        }), 500


@images_bp.route('/<path:name_or_id>', methods=['DELETE'])
def remove_image(name_or_id: str):
    """
    Remove a Docker image.

    DELETE /api/images/<name_or_id>?force=true

    Query Parameters:
        force (optional): Force removal even if containers are using it (default: false)
        noprune (optional): Don't delete untagged parents (default: false)

    Success Response (200):
    {
        "success": true,
        "message": "Image 'nginx:latest' successfully removed"
    }

    Error Responses:
    - 404: Image not found
    - 500: Removal failed (image in use, permission denied)

    CLI Equivalent:
        docker rmi [-f] nginx:latest
    """
    try:
        force = request.args.get('force', 'false').lower() == 'true'
        noprune = request.args.get('noprune', 'false').lower() == 'true'

        with ImageManager() as manager:
            result = manager.remove_image(name_or_id, force, noprune)

        return jsonify({
            "success": True,
            "message": result['message']
        }), 200

    except ImageNotFoundError as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "ImageNotFoundError"
        }), 404

    except ContainerOperationError as e:
        logger.error(f"Failed to remove image: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "ContainerOperationError"
        }), 500

    except Exception as e:
        logger.exception(f"Unexpected error removing image {name_or_id}")
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred",
            "error_type": "ServerError"
        }), 500


@images_bp.route('/<path:name_or_id>/tag', methods=['POST'])
def tag_image(name_or_id: str):
    """
    Tag an image with a new name.

    POST /api/images/<name_or_id>/tag

    Request Body:
    {
        "repository": "my-nginx",
        "tag": "v1.0"
    }

    Success Response (200):
    {
        "success": true,
        "data": {
            "id": 2,
            "image_id": "abc123...",
            "repository": "my-nginx",
            "tag": "v1.0",
            "full_name": "my-nginx:v1.0"
        },
        "message": "Image tagged successfully"
    }

    Error Responses:
    - 400: Validation error (missing repository)
    - 404: Source image not found
    - 500: Tagging failed

    CLI Equivalent:
        docker tag nginx:latest my-nginx:v1.0
    """
    try:
        data = request.get_json()

        # Validate required fields
        repository = data.get('repository')
        if not repository:
            return jsonify({
                "success": False,
                "error": "Repository name is required",
                "error_type": "ValidationError"
            }), 400

        tag = data.get('tag', 'latest')

        # Tag image
        with ImageManager() as manager:
            image = manager.tag_image(name_or_id, repository, tag)

        return jsonify({
            "success": True,
            "data": image,
            "message": "Image tagged successfully"
        }), 200

    except ValidationError as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "ValidationError"
        }), 400

    except ImageNotFoundError as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "ImageNotFoundError"
        }), 404

    except ContainerOperationError as e:
        logger.error(f"Failed to tag image: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "ContainerOperationError"
        }), 500

    except Exception as e:
        logger.exception(f"Unexpected error tagging image {name_or_id}")
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred",
            "error_type": "ServerError"
        }), 500


@images_bp.route('/updates', methods=['GET'])
def check_updates():
    """
    Check all images for available updates.

    GET /api/images/updates

    Success Response (200):
    {
        "success": true,
        "data": [
            {
                "id": 1,
                "repository": "nginx",
                "tag": "latest",
                "update_available": true
            }
        ],
        "count": 1,
        "message": "Update check complete"
    }

    Error Responses:
    - 500: Server error

    Educational:
        This is a placeholder implementation. Full update detection
        requires registry API integration to compare digests.
    """
    try:
        with ImageManager() as manager:
            updates = manager.check_for_updates()

        return jsonify({
            "success": True,
            "data": updates,
            "count": len(updates),
            "message": "Update check complete"
        }), 200

    except Exception as e:
        logger.exception("Error checking for updates")
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred",
            "error_type": "ServerError"
        }), 500
