"""
Stack API Blueprint

REST API endpoints for Docker Compose stack management.

Endpoints:
- GET /api/stacks - List all stacks
- GET /api/stacks/<id> - Get stack details
- POST /api/stacks - Create new stack
- POST /api/stacks/<id>/deploy - Deploy stack
- POST /api/stacks/<id>/start - Start stack
- POST /api/stacks/<id>/stop - Stop stack
- DELETE /api/stacks/<id> - Delete stack
"""

from flask import Blueprint, request, jsonify
from backend.services.stack_manager import StackManager
from backend.models.database import SessionLocal
from backend.auth.middleware import require_auth
from backend.extensions import limiter
from backend.utils.exceptions import (
    StackNotFoundError,
    ValidationError,
    StackDeploymentError
)
import logging

logger = logging.getLogger(__name__)

stacks_bp = Blueprint('stacks', __name__, url_prefix='/api/stacks')


@stacks_bp.route('', methods=['GET'])
@require_auth()
def list_stacks():
    """
    List all Docker Compose stacks

    Query params:
        - include_external (bool): Show unmanaged stacks

    Response:
        {
            "success": true,
            "stacks": [{stack details}, ...],
            "count": N
        }

    Docker CLI equivalent:
        docker compose ls
    """
    db = SessionLocal()
    try:
        manager = StackManager(db)
        include_external = request.args.get('include_external', 'false').lower() == 'true'
        result = manager.list_stacks(include_external=include_external)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error listing stacks: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }), 500
    finally:
        db.close()


@stacks_bp.route('/<stack_id>', methods=['GET'])
@require_auth()
def get_stack(stack_id):
    """
    Get single stack with detailed status

    Response:
        {
            "success": true,
            "stack": {stack details with service status}
        }

    Docker CLI equivalent:
        docker compose -p <stack_name> ps
    """
    db = SessionLocal()
    try:
        manager = StackManager(db)
        result = manager.get_stack(stack_id)
        return jsonify(result)
    except StackNotFoundError as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': 'StackNotFoundError'
        }), 404
    except Exception as e:
        logger.error(f"Error getting stack: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }), 500
    finally:
        db.close()


@stacks_bp.route('', methods=['POST'])
@require_auth()
@limiter.limit("30 per minute", scope="mutation_limit")
def create_stack():
    """
    Create new stack from docker-compose.yml

    Body:
        {
            "name": "my-stack",
            "compose_yaml": "version: '3.8'...",
            "description": "Optional description",
            "env_vars": {"KEY": "value"}  // Optional overrides
        }

    Response:
        {
            "success": true,
            "stack": {stack details},
            "message": "Stack created successfully"
        }

    Docker CLI equivalent:
        docker compose -f docker-compose.yml -p <name> config --no-interpolate
    """
    db = SessionLocal()
    try:
        data = request.get_json()

        if not data or 'name' not in data or 'compose_yaml' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: name, compose_yaml'
            }), 400

        manager = StackManager(db)
        result = manager.create_stack(
            name=data['name'],
            compose_yaml=data['compose_yaml'],
            description=data.get('description'),
            env_vars=data.get('env_vars')
        )
        return jsonify(result), 201
    except ValidationError as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': 'ValidationError'
        }), 400
    except Exception as e:
        logger.error(f"Error creating stack: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }), 500
    finally:
        db.close()


@stacks_bp.route('/<stack_id>', methods=['PUT'])
@require_auth()
@limiter.limit("30 per minute", scope="mutation_limit")
def update_stack(stack_id):
    """
    Update stack compose YAML and optionally redeploy

    Body:
        {
            "compose_yaml": "version: '3.8'...",
            "description": "Optional new description",
            "redeploy": true  // Optional: redeploy after update
        }

    Response:
        {
            "success": true,
            "stack": {stack details},
            "message": "Stack updated successfully"
        }

    Docker CLI equivalent:
        docker compose -p <stack_name> up -d --force-recreate
    """
    db = SessionLocal()
    try:
        data = request.get_json()
        if not data or 'compose_yaml' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required field: compose_yaml'
            }), 400

        manager = StackManager(db)
        result = manager.update_stack(
            stack_id,
            compose_yaml=data['compose_yaml'],
            description=data.get('description'),
            redeploy=data.get('redeploy', False)
        )
        return jsonify(result)
    except StackNotFoundError as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': 'StackNotFoundError'
        }), 404
    except ValidationError as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': 'ValidationError'
        }), 400
    except StackDeploymentError as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': 'StackDeploymentError'
        }), 500
    except Exception as e:
        logger.error(f"Error updating stack: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }), 500
    finally:
        db.close()


@stacks_bp.route('/<stack_id>/deploy', methods=['POST'])
@require_auth()
@limiter.limit("10 per minute", scope="mutation_limit")
def deploy_stack(stack_id):
    """
    Deploy a stack (create and start all services)

    Response:
        {
            "success": true,
            "stack": {stack details},
            "deployed": {
                "containers": N,
                "networks": N,
                "volumes": N
            },
            "message": "Stack deployed successfully"
        }

    Docker CLI equivalent:
        docker compose -p <stack_name> up -d
    """
    db = SessionLocal()
    try:
        manager = StackManager(db)
        result = manager.deploy_stack(stack_id)
        return jsonify(result)
    except StackNotFoundError as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': 'StackNotFoundError'
        }), 404
    except StackDeploymentError as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': 'StackDeploymentError'
        }), 500
    except Exception as e:
        logger.error(f"Error deploying stack: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }), 500
    finally:
        db.close()


@stacks_bp.route('/<stack_id>/start', methods=['POST'])
@require_auth()
@limiter.limit("30 per minute", scope="mutation_limit")
def start_stack(stack_id):
    """
    Start all containers in a stack

    Response:
        {
            "success": true,
            "stack": "stack-name",
            "started": N,
            "message": "Started N containers"
        }

    Docker CLI equivalent:
        docker compose -p <stack_name> start
    """
    db = SessionLocal()
    try:
        manager = StackManager(db)
        result = manager.start_stack(stack_id)
        return jsonify(result)
    except StackNotFoundError as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': 'StackNotFoundError'
        }), 404
    except Exception as e:
        logger.error(f"Error starting stack: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }), 500
    finally:
        db.close()


@stacks_bp.route('/<stack_id>/stop', methods=['POST'])
@require_auth()
@limiter.limit("30 per minute", scope="mutation_limit")
def stop_stack(stack_id):
    """
    Stop all containers in a stack

    Response:
        {
            "success": true,
            "stack": "stack-name",
            "stopped": N,
            "message": "Stopped N containers"
        }

    Docker CLI equivalent:
        docker compose -p <stack_name> stop
    """
    db = SessionLocal()
    try:
        manager = StackManager(db)
        result = manager.stop_stack(stack_id)
        return jsonify(result)
    except StackNotFoundError as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': 'StackNotFoundError'
        }), 404
    except Exception as e:
        logger.error(f"Error stopping stack: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }), 500
    finally:
        db.close()


@stacks_bp.route('/<stack_id>', methods=['DELETE'])
@require_auth()
@limiter.limit("30 per minute", scope="mutation_limit")
def delete_stack(stack_id):
    """
    Delete a stack and all its resources

    Query params:
        - remove_volumes (bool): Also remove volumes (default: false)

    Response:
        {
            "success": true,
            "stack": "stack-name",
            "removed": {
                "containers": N,
                "networks": N,
                "volumes": N
            },
            "message": "Stack deleted successfully"
        }

    Docker CLI equivalent:
        docker compose -p <stack_name> down [-v]
    """
    db = SessionLocal()
    try:
        remove_volumes = request.args.get('remove_volumes', 'false').lower() == 'true'
        manager = StackManager(db)
        result = manager.delete_stack(stack_id, remove_volumes=remove_volumes)
        return jsonify(result)
    except StackNotFoundError as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': 'StackNotFoundError'
        }), 404
    except Exception as e:
        logger.error(f"Error deleting stack: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }), 500
    finally:
        db.close()
