"""
DockerMate - Container API Endpoints (Sprint 2 Task 5)
=======================================================

RESTful API endpoints for container management with:
- CRUD operations (create, read, update, delete)
- Lifecycle actions (start, stop, restart)
- Request validation with port conflict detection
- Consistent error handling and response format
- Hardware-aware validation

Authentication Note:
    The @require_auth(api=True) decorators are currently commented out for 
    unit testing purposes. Authentication will be properly integrated when
    the blueprint is registered in app.py with before_request handlers or
    by uncommenting the decorators after testing is complete.

Endpoints:
    POST   /api/containers              Create container
    GET    /api/containers              List containers (with filters)
    GET    /api/containers/<id>         Get single container
    PATCH  /api/containers/<id>         Update container (Phase 1: labels)
    DELETE /api/containers/<id>         Delete container
    POST   /api/containers/<id>/start   Start container
    POST   /api/containers/<id>/stop    Stop container
    POST   /api/containers/<id>/restart Restart container

Usage:
    In app.py::
    
        from backend.api.containers import containers_bp
        app.register_blueprint(containers_bp)

Educational Notes:
- API layer handles HTTP concerns (validation, status codes, JSON)
- Service layer (ContainerManager) handles business logic
- Middleware handles authentication automatically
- Clear separation of concerns for maintainability

CLI Equivalents Shown:
- Each endpoint docstring shows equivalent Docker CLI command
- Helps users learn Docker while using DockerMate
- Educational value aligned with project goals
"""

import logging
from typing import Dict, Any, Optional, List
from flask import Blueprint, request, jsonify

from backend.auth.middleware import require_auth
from backend.services.container_manager import ContainerManager
from backend.utils.exceptions import (
    ContainerNotFoundError,
    ContainerOperationError,
    ValidationError,
    DockerConnectionError
)
from backend.models.database import SessionLocal
from backend.models.container import Container

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint for container routes
containers_bp = Blueprint('containers', __name__, url_prefix='/api/containers')


# =============================================================================
# Validation Helpers
# =============================================================================

def validate_create_request(data: Dict[str, Any]) -> None:
    """
    Validate container creation request data.
    
    Args:
        data: Request JSON data
        
    Raises:
        ValidationError: If validation fails
        
    Validates:
        - Required fields present
        - Field types correct
        - Port format valid
        - Volume format valid
        - Environment variable format valid
        - Port conflicts with existing containers
    """
    # Required fields
    if not data.get('name'):
        raise ValidationError("Container name is required")
    
    if not data.get('image'):
        raise ValidationError("Container image is required")
    
    # Validate name format (Docker naming rules)
    name = data['name']
    if not name.replace('-', '').replace('_', '').isalnum():
        raise ValidationError(
            "Container name must contain only alphanumeric characters, hyphens, and underscores"
        )
    
    # Validate ports format if provided
    if 'ports' in data and data['ports']:
        if not isinstance(data['ports'], dict):
            raise ValidationError("Ports must be a dictionary mapping container:host")
        
        for container_port, host_port in data['ports'].items():
            # Validate port numbers
            try:
                host_port_int = int(host_port)
                if not (1 <= host_port_int <= 65535):
                    raise ValidationError(f"Host port {host_port} must be between 1 and 65535")
            except (ValueError, TypeError):
                raise ValidationError(f"Invalid host port: {host_port}")
            
            # Validate container port format
            if '/' not in container_port:
                raise ValidationError(
                    f"Container port must include protocol (e.g., '80/tcp'): {container_port}"
                )
    
    # Check for port conflicts with existing containers
    if 'ports' in data and data['ports']:
        _check_port_conflicts(data['ports'])
    
    # Validate volumes format if provided
    if 'volumes' in data and data['volumes']:
        if not isinstance(data['volumes'], dict):
            raise ValidationError("Volumes must be a dictionary mapping host:container")
        
        for host_path, container_config in data['volumes'].items():
            if not isinstance(container_config, dict):
                raise ValidationError(
                    f"Volume config must be a dictionary with 'bind' and 'mode' keys: {host_path}"
                )
            
            if 'bind' not in container_config:
                raise ValidationError(
                    f"Volume config must include 'bind' key (container path): {host_path}"
                )
    
    # Validate environment variables format if provided
    if 'env_vars' in data and data['env_vars']:
        if not isinstance(data['env_vars'], dict):
            raise ValidationError("Environment variables must be a dictionary")
        
        for key, value in data['env_vars'].items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise ValidationError("Environment variable keys and values must be strings")
    
    # Validate restart policy if provided
    if 'restart_policy' in data and data['restart_policy']:
        valid_policies = ['no', 'on-failure', 'always', 'unless-stopped']
        if data['restart_policy'] not in valid_policies:
            raise ValidationError(
                f"Invalid restart policy: {data['restart_policy']}. "
                f"Must be one of: {', '.join(valid_policies)}"
            )
    
    # Validate resource limits if provided
    if 'cpu_limit' in data and data['cpu_limit'] is not None:
        try:
            cpu_limit = float(data['cpu_limit'])
            if cpu_limit <= 0:
                raise ValidationError("CPU limit must be greater than 0")
        except (ValueError, TypeError):
            raise ValidationError(f"Invalid CPU limit: {data['cpu_limit']}")
    
    if 'memory_limit' in data and data['memory_limit'] is not None:
        try:
            memory_limit = int(data['memory_limit'])
            if memory_limit <= 0:
                raise ValidationError("Memory limit must be greater than 0")
        except (ValueError, TypeError):
            raise ValidationError(f"Invalid memory limit: {data['memory_limit']}")


def _check_port_conflicts(ports: Dict[str, int], exclude_container_id: Optional[str] = None) -> None:
    """
    Check if any host ports are already in use by other containers.
    
    Args:
        ports: Dictionary mapping container ports to host ports
        exclude_container_id: Container ID to exclude from check (for updates)
        
    Raises:
        ValidationError: If port conflict detected
        
    Educational:
        - Prevents confusing Docker errors about port conflicts
        - Shows which container is using the port
        - Provides clear remediation guidance
    """
    db = SessionLocal()
    try:
        # Extract host ports from request
        requested_host_ports = set(int(host_port) for host_port in ports.values())
        
        # Query all running containers with port mappings
        query = db.query(Container).filter(
            Container.state.in_(['running', 'created', 'restarting']),
            Container.ports_json.isnot(None)
        )
        
        # Exclude current container if updating
        if exclude_container_id:
            query = query.filter(Container.container_id != exclude_container_id)
        
        existing_containers = query.all()
        
        # Check for conflicts
        conflicts = []
        for container in existing_containers:
            if container.ports_json:
                import json
                try:
                    existing_ports = json.loads(container.ports_json)
                    for port_mapping in existing_ports:
                        existing_host_port = int(port_mapping.get('host', 0))
                        if existing_host_port in requested_host_ports:
                            conflicts.append({
                                'port': existing_host_port,
                                'container_name': container.name,
                                'container_id': container.container_id[:12]
                            })
                except (json.JSONDecodeError, ValueError, TypeError):
                    # Skip malformed port data
                    continue
        
        # Raise error if conflicts found
        if conflicts:
            conflict_details = [
                f"Port {c['port']} (used by {c['container_name']})"
                for c in conflicts
            ]
            raise ValidationError(
                f"Port conflict detected: {', '.join(conflict_details)}. "
                f"Stop or remove the conflicting container(s) first."
            )
    
    finally:
        db.close()


def validate_update_request(data: Dict[str, Any]) -> None:
    """
    Validate container update request data (Phase 1: labels only).
    
    Args:
        data: Request JSON data
        
    Raises:
        ValidationError: If validation fails
        
    Note:
        Phase 1 only supports label updates (non-destructive).
        Full updates via recreate workflow deferred to Task 6.
    """
    if not data:
        raise ValidationError("Update request body cannot be empty")
    
    # Phase 1: Only labels are supported
    allowed_fields = {'labels'}
    provided_fields = set(data.keys())
    unsupported_fields = provided_fields - allowed_fields
    
    if unsupported_fields:
        raise ValidationError(
            f"Unsupported update fields: {', '.join(unsupported_fields)}. "
            f"Phase 1 only supports updating: labels. "
            f"Full updates will be available in the UI (Task 6)."
        )
    
    # Validate labels format
    if 'labels' in data:
        if not isinstance(data['labels'], dict):
            raise ValidationError("Labels must be a dictionary")
        
        for key, value in data['labels'].items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise ValidationError("Label keys and values must be strings")


# =============================================================================
# CRUD Endpoints
# =============================================================================

@containers_bp.route('', methods=['POST'])
# @require_auth(api=True)  # TODO: Re-enable when integrated in app.py
def create_container():
    """
    Create a new container with validation and optional auto-start.
    
    POST /api/containers
    Content-Type: application/json
    
    Request Body:
    {
        "name": "my-nginx",                    # Required
        "image": "nginx:latest",               # Required
        "environment": "prod",                 # Optional (dev, test, prod, staging)
        "ports": {                             # Optional
            "80/tcp": 8080,
            "443/tcp": 8443
        },
        "volumes": {                           # Optional
            "/host/path": {
                "bind": "/container/path",
                "mode": "rw"
            }
        },
        "env_vars": {                          # Optional
            "MYSQL_ROOT_PASSWORD": "secret",
            "MYSQL_DATABASE": "myapp"
        },
        "labels": {                            # Optional
            "version": "1.0.0",
            "team": "backend"
        },
        "restart_policy": "unless-stopped",   # Optional (default: unless-stopped) - no, on-failure, always, unless-stopped
        "auto_start": true,                   # Optional (default: true)
        "pull_if_missing": true,              # Optional (default: true)
        "cpu_limit": 1.5,                     # Optional (cores)
        "memory_limit": 536870912             # Optional (bytes) - frontend converts MB→bytes before sending
    }
    
    Success Response (201):
    {
        "success": true,
        "data": {
            "id": 1,
            "container_id": "a1b2c3d4e5f6",
            "name": "my-nginx",
            "state": "running",
            "image_name": "nginx:latest",
            "environment": "prod",
            "health_status": {
                "healthy": true,
                "running": true,
                "exit_code": 0
            }
        }
    }
    
    Error Responses:
    - 400: Validation error (missing fields, invalid format, port conflict)
    - 401: Unauthorized (no valid session)
    - 409: Conflict (container name already exists)
    - 500: Server error (Docker daemon error, database error)
    
    CLI Equivalent:
        docker run -d \\
          --name my-nginx \\
          -p 8080:80 \\
          -p 8443:443 \\
          -v /host/path:/container/path:rw \\
          -e MYSQL_ROOT_PASSWORD=secret \\
          -e MYSQL_DATABASE=myapp \\
          --label version=1.0.0 \\
          --label team=backend \\
          --restart unless-stopped \\
          --cpus="1.5" \\
          --memory="512m" \\
          nginx:latest
    
    Educational Notes:
        - auto_start=true is like `docker run` (starts immediately)
        - auto_start=false is like `docker create` (creates but doesn't start)
        - pull_if_missing=true automatically pulls image if not present
        - Hardware limits enforced based on system profile (Task 1)
        - Health check runs 10-20 seconds after start (FEAT-011)
    """
    try:
        # Parse request body
        try:
            data = request.get_json(force=True)
        except Exception:
            raise ValidationError("Invalid JSON in request body")
        
        if not data:
            raise ValidationError("Request body is required")
        
        # Validate request
        validate_create_request(data)
        
        # Create container via service
        with ContainerManager() as manager:
            container = manager.create_container(
                name=data['name'],
                image=data['image'],
                environment=data.get('environment'),
                ports=data.get('ports'),
                volumes=data.get('volumes'),
                env_vars=data.get('env_vars'),
                labels=data.get('labels'),
                restart_policy=data.get('restart_policy', 'unless-stopped'),  # Match frontend default
                auto_start=data.get('auto_start', True),
                pull_if_missing=data.get('pull_if_missing', True),
                cpu_limit=data.get('cpu_limit'),
                memory_limit=data.get('memory_limit')
            )
        
        logger.info(f"Container created via API: {data['name']}")
        
        return jsonify({
            "success": True,
            "data": container
        }), 201
    
    except ValidationError as e:
        logger.warning(f"Container creation validation failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "ValidationError"
        }), 400
    
    except ContainerOperationError as e:
        logger.error(f"Container creation failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "ContainerOperationError"
        }), 500
    
    except DockerConnectionError as e:
        logger.error(f"Docker connection failed: {e}")
        return jsonify({
            "success": False,
            "error": "Cannot connect to Docker daemon. Is Docker running?",
            "error_type": "DockerConnectionError"
        }), 500
    
    except Exception as e:
        logger.exception(f"Unexpected error creating container: {e}")
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred",
            "error_type": "ServerError"
        }), 500


@containers_bp.route('', methods=['GET'])
# @require_auth(api=True)  # TODO: Re-enable when integrated in app.py
def list_containers():
    """
    List containers with optional filtering.
    
    GET /api/containers?environment=prod&state=running
    
    Query Parameters:
        environment (optional): Filter by environment tag (dev, test, prod, staging)
        state (optional): Filter by state (running, exited, created, etc.)
        all (optional): Include stopped containers (default: true for API)
    
    Success Response (200):
    {
        "success": true,
        "data": [
            {
                "id": 1,
                "container_id": "a1b2c3d4e5f6",
                "name": "my-nginx",
                "state": "running",
                "image_name": "nginx:latest",
                "environment": "prod",
                "created_at": "2025-01-27T10:30:00Z",
                "started_at": "2025-01-27T10:30:05Z"
            },
            ...
        ],
        "count": 5,
        "filters": {
            "environment": "prod",
            "state": "running"
        }
    }
    
    Error Responses:
    - 401: Unauthorized (no valid session)
    - 500: Server error (Docker daemon error, database error)
    
    CLI Equivalent:
        # All containers
        docker ps -a
        
        # Running containers only
        docker ps
        
        # Filtered by label (environment)
        docker ps --filter "label=environment=prod"
    
    Educational Notes:
        - API defaults to showing all containers (including stopped)
        - Filters are applied at service layer for consistency
        - Results come from database (fast) with Docker sync
    """
    try:
        # Parse query parameters
        environment = request.args.get('environment')
        state = request.args.get('state')
        include_all = request.args.get('all', 'true').lower() == 'true'
        
        # List containers via service
        with ContainerManager() as manager:
            containers = manager.list_containers(
            environment=environment,
            state=state,
            all=include_all
        )
        
        # Build response
        response_data = {
            "success": True,
            "data": containers,
            "count": len(containers)
        }
        
        # Include filter info if filters applied
        filters = {}
        if environment:
            filters['environment'] = environment
        if state:
            filters['state'] = state
        if filters:
            response_data['filters'] = filters
        
        return jsonify(response_data), 200
    
    except ContainerOperationError as e:
        logger.error(f"Failed to list containers: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "ContainerOperationError"
        }), 500
    
    except DockerConnectionError as e:
        logger.error(f"Docker connection failed: {e}")
        return jsonify({
            "success": False,
            "error": "Cannot connect to Docker daemon. Is Docker running?",
            "error_type": "DockerConnectionError"
        }), 500
    
    except Exception as e:
        logger.exception(f"Unexpected error listing containers: {e}")
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred",
            "error_type": "ServerError"
        }), 500


@containers_bp.route('/<container_id>', methods=['GET'])
# @require_auth(api=True)  # TODO: Re-enable when integrated in app.py
def get_container(container_id: str):
    """
    Get detailed information about a specific container.
    
    GET /api/containers/<id>
    
    Path Parameters:
        container_id: Container ID or name
    
    Success Response (200):
    {
        "success": true,
        "data": {
            "id": 1,
            "container_id": "a1b2c3d4e5f6789012345678901234567890123456789012345678901234",
            "name": "my-nginx",
            "state": "running",
            "image_name": "nginx:latest",
            "environment": "prod",
            "ports": [
                {"host": "8080", "container": "80", "protocol": "tcp"}
            ],
            "volumes": [...],
            "env_vars": {...},
            "labels": {...},
            "restart_policy": "unless-stopped",
            "cpu_limit": 1.5,
            "memory_limit": 536870912,
            "cpu_usage": 2.5,
            "memory_usage": 134217728,
            "created_at": "2025-01-27T10:30:00Z",
            "started_at": "2025-01-27T10:30:05Z",
            "updated_at": "2025-01-27T10:30:05Z"
        }
    }
    
    Error Responses:
    - 401: Unauthorized (no valid session)
    - 404: Container not found
    - 500: Server error (Docker daemon error, database error)
    
    CLI Equivalent:
        docker inspect my-nginx
    
    Educational Notes:
        - Returns both database state and Docker runtime info
        - Container ID can be full (64 chars) or short (12 chars)
        - Name-based lookup also supported (e.g., "my-nginx")
    """
    try:
        # Get container via service
        with ContainerManager() as manager:
            container = manager.get_container(container_id)
        
        return jsonify({
            "success": True,
            "data": container
        }), 200
    
    except ContainerNotFoundError as e:
        logger.warning(f"Container not found: {container_id}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "NotFoundError"
        }), 404
    
    except ContainerOperationError as e:
        logger.error(f"Failed to get container {container_id}: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "ContainerOperationError"
        }), 500
    
    except DockerConnectionError as e:
        logger.error(f"Docker connection failed: {e}")
        return jsonify({
            "success": False,
            "error": "Cannot connect to Docker daemon. Is Docker running?",
            "error_type": "DockerConnectionError"
        }), 500
    
    except Exception as e:
        logger.exception(f"Unexpected error getting container {container_id}: {e}")
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred",
            "error_type": "ServerError"
        }), 500


@containers_bp.route('/<name_or_id>/health', methods=['GET'])
# @require_auth(api=True)  # TODO: Re-enable when integrated in app.py
def get_container_health(name_or_id: str):
    """
    Get container health status (non-blocking, async polling).
    
    TASK 7 FIX: New endpoint for frontend health monitoring.
    Replaces blocking health check in create_container().
    
    GET /api/containers/<id>/health
    
    Path Parameters:
        name_or_id: Container ID or name
    
    Success Response (200):
    {
        "success": true,
        "data": {
            "healthy": true,
            "running": true,
            "status": "running",
            "exit_code": null,
            "error": null,
            "health": "healthy",
            "uptime_seconds": 45
        }
    }
    
    Error Responses:
    - 404: Container not found
    - 500: Docker operation failed
    
    CLI Equivalent:
        docker inspect <container> | jq '.State.Health'
    
    Educational Notes:
        - Non-blocking: Returns immediately with current state
        - Frontend polls this every 2 seconds for health monitoring
        - Teaches difference between "started" vs "healthy"
        - Shows how containers can crash after starting
        - Demonstrates proper async monitoring patterns
    
    Health Status Meanings:
        - healthy=true, running=true: Container started and running normally
        - healthy=false, running=false: Container crashed (check exit_code/error)
        - healthy=true, health="starting": Health check configured but not ready
        - healthy=false, health="unhealthy": Health check failed
    """
    logger.info(f"Health check requested for container: {name_or_id}")
    
    try:
        with ContainerManager() as manager:
            health = manager.get_container_health(name_or_id)
        
        return jsonify({
            "success": True,
            "data": health
        }), 200
    
    except ContainerNotFoundError as e:
        logger.warning(f"Container not found for health check: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "ContainerNotFoundError"
        }), 404
    
    except ContainerOperationError as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "ContainerOperationError"
        }), 500
    
    except DockerConnectionError as e:
        logger.error(f"Docker connection failed: {e}")
        return jsonify({
            "success": False,
            "error": "Cannot connect to Docker daemon",
            "error_type": "DockerConnectionError"
        }), 500
    
    except Exception as e:
        logger.exception(f"Unexpected error during health check: {e}")
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred",
            "error_type": "ServerError"
        }), 500


@containers_bp.route('/<container_id>', methods=['PATCH'])
# @require_auth(api=True)  # TODO: Re-enable when integrated in app.py
def update_container(container_id: str):
    """
    Update container configuration (Phase 1: labels only).
    
    PATCH /api/containers/<id>
    Content-Type: application/json
    
    Path Parameters:
        container_id: Container ID or name
    
    Request Body (Phase 1):
    {
        "labels": {
            "version": "1.2.0",
            "team": "frontend"
        }
    }
    
    Success Response (200):
    {
        "success": true,
        "data": {
            "id": 1,
            "container_id": "a1b2c3d4e5f6",
            "name": "my-nginx",
            "labels": {
                "version": "1.2.0",
                "team": "frontend"
            },
            ...
        }
    }
    
    Error Responses:
    - 400: Validation error (unsupported fields, invalid format)
    - 401: Unauthorized (no valid session)
    - 404: Container not found
    - 500: Server error (Docker daemon error, database error)
    
    CLI Equivalent:
        # Update labels
        docker update \\
          --label-add version=1.2.0 \\
          --label-add team=frontend \\
          my-nginx
    
    Phase 1 vs Phase 2:
        - Phase 1 (Task 5): Labels only (non-destructive, instant)
        - Phase 2 (Task 6): Full updates via recreate workflow in UI
          (ports, volumes, environment, etc. - requires container recreation)
    
    Educational Notes:
        - Label updates don't require container restart
        - Other changes (ports, volumes) require recreation (Phase 2)
        - Phase 2 will add UI-guided recreate workflow for safety
    """
    try:
        # Parse request body
        try:
            data = request.get_json(force=True)
        except Exception:
            raise ValidationError("Invalid JSON in request body")
        
        # Validate request (handles empty body check)
        validate_update_request(data)
        
        # Update container via service
        with ContainerManager() as manager:
            container = manager.update_container(
                container_id,
                labels=data.get('labels')
            )
        
        logger.info(f"Container updated via API: {container_id}")
        
        return jsonify({
            "success": True,
            "data": container
        }), 200
    
    except ValidationError as e:
        logger.warning(f"Container update validation failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "ValidationError"
        }), 400
    
    except ContainerNotFoundError as e:
        logger.warning(f"Container not found: {container_id}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "NotFoundError"
        }), 404
    
    except ContainerOperationError as e:
        logger.error(f"Failed to update container {container_id}: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "ContainerOperationError"
        }), 500
    
    except DockerConnectionError as e:
        logger.error(f"Docker connection failed: {e}")
        return jsonify({
            "success": False,
            "error": "Cannot connect to Docker daemon. Is Docker running?",
            "error_type": "DockerConnectionError"
        }), 500
    
    except Exception as e:
        logger.exception(f"Unexpected error updating container {container_id}: {e}")
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred",
            "error_type": "ServerError"
        }), 500


@containers_bp.route('/<container_id>', methods=['DELETE'])
# @require_auth(api=True)  # TODO: Re-enable when integrated in app.py
def delete_container(container_id: str):
    """
    Delete a container (stop and remove).
    
    DELETE /api/containers/<id>?force=true&remove_volumes=false
    
    Path Parameters:
        container_id: Container ID or name
    
    Query Parameters:
        force (optional): Force remove running container (default: false)
        remove_volumes (optional): Remove associated volumes (default: false)
    
    Success Response (200):
    {
        "success": true,
        "message": "Container 'my-nginx' deleted successfully"
    }
    
    Error Responses:
    - 400: Validation error (container running and force=false)
    - 401: Unauthorized (no valid session)
    - 404: Container not found
    - 500: Server error (Docker daemon error, database error)
    
    CLI Equivalent:
        # Stop and remove
        docker stop my-nginx && docker rm my-nginx
        
        # Force remove (running container)
        docker rm -f my-nginx
        
        # Remove with volumes
        docker rm -v my-nginx
    
    Educational Notes:
        - Default behavior requires container to be stopped first (safe)
        - force=true skips stop step (like docker rm -f)
        - remove_volumes=true deletes volumes (data loss risk!)
        - Production environments typically use force=false for safety
    """
    try:
        # Parse query parameters
        force = request.args.get('force', 'false').lower() == 'true'
        remove_volumes = request.args.get('remove_volumes', 'false').lower() == 'true'
        
        # Delete container via service
        with ContainerManager() as manager:
            result = manager.delete_container(
                container_id,
                force=force,
                remove_volumes=remove_volumes
            )
        
        logger.info(f"Container deleted via API: {container_id} (force={force}, volumes={remove_volumes})")
        
        return jsonify({
            "success": True,
            "message": result.get('message', f"Container '{container_id}' deleted successfully")
        }), 200
    
    except ContainerNotFoundError as e:
        logger.warning(f"Container not found: {container_id}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "NotFoundError"
        }), 404
    
    except ValidationError as e:
        logger.warning(f"Container deletion validation failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "ValidationError"
        }), 400
    
    except ContainerOperationError as e:
        logger.error(f"Failed to delete container {container_id}: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "ContainerOperationError"
        }), 500
    
    except DockerConnectionError as e:
        logger.error(f"Docker connection failed: {e}")
        return jsonify({
            "success": False,
            "error": "Cannot connect to Docker daemon. Is Docker running?",
            "error_type": "DockerConnectionError"
        }), 500
    
    except Exception as e:
        logger.exception(f"Unexpected error deleting container {container_id}: {e}")
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred",
            "error_type": "ServerError"
        }), 500


# =============================================================================
# Lifecycle Action Endpoints
# =============================================================================

@containers_bp.route('/<container_id>/start', methods=['POST'])
# @require_auth(api=True)  # TODO: Re-enable when integrated in app.py
def start_container(container_id: str):
    """
    Start a stopped container.
    
    POST /api/containers/<id>/start
    
    Path Parameters:
        container_id: Container ID or name
    
    Success Response (200):
    {
        "success": true,
        "message": "Container 'my-nginx' started successfully",
        "data": {
            "id": 1,
            "container_id": "a1b2c3d4e5f6",
            "name": "my-nginx",
            "state": "running",
            "started_at": "2025-01-27T11:00:00Z"
        }
    }
    
    Error Responses:
    - 400: Validation error (container already running)
    - 401: Unauthorized (no valid session)
    - 404: Container not found
    - 500: Server error (Docker daemon error, database error)
    
    CLI Equivalent:
        docker start my-nginx
    
    Educational Notes:
        - Starting a container resumes it from stopped state
        - Container keeps its ID, name, and all configuration
        - Mounts and networks reconnect automatically
    """
    try:
        # Start container via service
        with ContainerManager() as manager:
            container = manager.start_container(container_id)
        
        logger.info(f"Container started via API: {container_id}")
        
        return jsonify({
            "success": True,
            "message": f"Container '{container['name']}' started successfully",
            "data": container
        }), 200
    
    except ContainerNotFoundError as e:
        logger.warning(f"Container not found: {container_id}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "NotFoundError"
        }), 404
    
    except ValidationError as e:
        logger.warning(f"Container start validation failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "ValidationError"
        }), 400
    
    except ContainerOperationError as e:
        logger.error(f"Failed to start container {container_id}: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "ContainerOperationError"
        }), 500
    
    except DockerConnectionError as e:
        logger.error(f"Docker connection failed: {e}")
        return jsonify({
            "success": False,
            "error": "Cannot connect to Docker daemon. Is Docker running?",
            "error_type": "DockerConnectionError"
        }), 500
    
    except Exception as e:
        logger.exception(f"Unexpected error starting container {container_id}: {e}")
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred",
            "error_type": "ServerError"
        }), 500


@containers_bp.route('/<container_id>/stop', methods=['POST'])
# @require_auth(api=True)  # TODO: Re-enable when integrated in app.py
def stop_container(container_id: str):
    """
    Stop a running container gracefully.
    
    POST /api/containers/<id>/stop?timeout=10
    
    Path Parameters:
        container_id: Container ID or name
    
    Query Parameters:
        timeout (optional): Seconds to wait before killing (default: 10)
    
    Success Response (200):
    {
        "success": true,
        "message": "Container 'my-nginx' stopped successfully",
        "data": {
            "id": 1,
            "container_id": "a1b2c3d4e5f6",
            "name": "my-nginx",
            "state": "exited",
            "stopped_at": "2025-01-27T11:05:00Z"
        }
    }
    
    Error Responses:
    - 400: Validation error (container already stopped)
    - 401: Unauthorized (no valid session)
    - 404: Container not found
    - 500: Server error (Docker daemon error, database error)
    
    CLI Equivalent:
        docker stop my-nginx
        
        # With custom timeout
        docker stop -t 30 my-nginx
    
    Educational Notes:
        - Stop sends SIGTERM (graceful shutdown)
        - After timeout, sends SIGKILL (forced shutdown)
        - Default 10 second timeout matches Docker CLI
        - Stopped containers can be started again
    """
    try:
        # Parse query parameters
        timeout = request.args.get('timeout', 10)
        try:
            timeout = int(timeout)
            if timeout < 0:
                raise ValidationError("Timeout must be non-negative")
        except ValueError:
            raise ValidationError(f"Invalid timeout value: {timeout}")
        
        # Stop container via service
        with ContainerManager() as manager:
            container = manager.stop_container(container_id, timeout=timeout)
        
        logger.info(f"Container stopped via API: {container_id} (timeout={timeout}s)")
        
        return jsonify({
            "success": True,
            "message": f"Container '{container['name']}' stopped successfully",
            "data": container
        }), 200
    
    except ContainerNotFoundError as e:
        logger.warning(f"Container not found: {container_id}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "NotFoundError"
        }), 404
    
    except ValidationError as e:
        logger.warning(f"Container stop validation failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "ValidationError"
        }), 400
    
    except ContainerOperationError as e:
        logger.error(f"Failed to stop container {container_id}: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "ContainerOperationError"
        }), 500
    
    except DockerConnectionError as e:
        logger.error(f"Docker connection failed: {e}")
        return jsonify({
            "success": False,
            "error": "Cannot connect to Docker daemon. Is Docker running?",
            "error_type": "DockerConnectionError"
        }), 500
    
    except Exception as e:
        logger.exception(f"Unexpected error stopping container {container_id}: {e}")
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred",
            "error_type": "ServerError"
        }), 500


@containers_bp.route('/<container_id>/restart', methods=['POST'])
# @require_auth(api=True)  # TODO: Re-enable when integrated in app.py
def restart_container(container_id: str):
    """
    Restart a container (stop + start).
    
    POST /api/containers/<id>/restart?timeout=10
    
    Path Parameters:
        container_id: Container ID or name
    
    Query Parameters:
        timeout (optional): Seconds to wait before killing during stop (default: 10)
    
    Success Response (200):
    {
        "success": true,
        "message": "Container 'my-nginx' restarted successfully",
        "data": {
            "id": 1,
            "container_id": "a1b2c3d4e5f6",
            "name": "my-nginx",
            "state": "running",
            "stopped_at": "2025-01-27T11:10:00Z",
            "started_at": "2025-01-27T11:10:05Z"
        }
    }
    
    Error Responses:
    - 401: Unauthorized (no valid session)
    - 404: Container not found
    - 500: Server error (Docker daemon error, database error)
    
    CLI Equivalent:
        docker restart my-nginx
        
        # With custom timeout
        docker restart -t 30 my-nginx
    
    Educational Notes:
        - Restart is equivalent to stop + start
        - Useful for applying configuration changes
        - Container keeps its ID, name, and all configuration
        - Works on both running and stopped containers
    """
    try:
        # Parse query parameters
        timeout = request.args.get('timeout', 10)
        try:
            timeout = int(timeout)
            if timeout < 0:
                raise ValidationError("Timeout must be non-negative")
        except ValueError:
            raise ValidationError(f"Invalid timeout value: {timeout}")
        
        # Restart container via service
        with ContainerManager() as manager:
            container = manager.restart_container(container_id, timeout=timeout)
        
        logger.info(f"Container restarted via API: {container_id} (timeout={timeout}s)")
        
        return jsonify({
            "success": True,
            "message": f"Container '{container['name']}' restarted successfully",
            "data": container
        }), 200
    
    except ContainerNotFoundError as e:
        logger.warning(f"Container not found: {container_id}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "NotFoundError"
        }), 404
    
    except ValidationError as e:
        logger.warning(f"Container restart validation failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "ValidationError"
        }), 400
    
    except ContainerOperationError as e:
        logger.error(f"Failed to restart container {container_id}: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "ContainerOperationError"
        }), 500
    
    except DockerConnectionError as e:
        logger.error(f"Docker connection failed: {e}")
        return jsonify({
            "success": False,
            "error": "Cannot connect to Docker daemon. Is Docker running?",
            "error_type": "DockerConnectionError"
        }), 500
    
    except Exception as e:
        logger.exception(f"Unexpected error restarting container {container_id}: {e}")
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred",
            "error_type": "ServerError"
        }), 500