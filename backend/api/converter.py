"""
Docker Run to Compose Converter API

REST API endpoints for converting docker run commands to compose format.

Endpoints:
- POST /api/converter/run-to-compose - Convert single docker run command
- POST /api/converter/multiple-runs - Convert multiple commands to one compose file
"""

from flask import Blueprint, request, jsonify
from backend.services.compose_converter import ComposeConverter
from backend.auth.middleware import require_auth
import logging

logger = logging.getLogger(__name__)

converter_bp = Blueprint('converter', __name__, url_prefix='/api/converter')


@converter_bp.route('/run-to-compose', methods=['POST'])
@require_auth()
def run_to_compose():
    """
    Convert docker run command to compose YAML

    Body:
        {
            "command": "docker run -d -p 8080:80 nginx:alpine",
            "service_name": "web"  // Optional
        }

    Response:
        {
            "success": true,
            "compose_yaml": "version: '3.8'...",
            "service_name": "web",
            "warnings": ["list of unsupported flags"]
        }

    Docker CLI equivalent:
        N/A - this is a utility feature
    """
    try:
        data = request.get_json()

        if not data or 'command' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required field: command'
            }), 400

        converter = ComposeConverter()
        result = converter.convert_run_to_compose(
            data['command'],
            service_name=data.get('service_name')
        )

        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"Error converting command: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@converter_bp.route('/multiple-runs', methods=['POST'])
@require_auth()
def multiple_runs():
    """
    Convert multiple docker run commands to single compose file

    Body:
        {
            "commands": [
                {"command": "docker run -d nginx:alpine", "service_name": "web"},
                {"command": "docker run -d redis:alpine", "service_name": "cache"}
            ]
        }

    Response:
        {
            "success": true,
            "compose_yaml": "combined yaml",
            "services": ["web", "cache"],
            "warnings": []
        }
    """
    try:
        data = request.get_json()

        if not data or 'commands' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required field: commands'
            }), 400

        if not isinstance(data['commands'], list) or len(data['commands']) == 0:
            return jsonify({
                'success': False,
                'error': 'commands must be a non-empty list'
            }), 400

        # Convert to list of tuples
        commands = []
        for i, cmd in enumerate(data['commands']):
            if 'command' not in cmd:
                return jsonify({
                    'success': False,
                    'error': f'Missing command in entry {i}'
                }), 400

            service_name = cmd.get('service_name', f'service{i+1}')
            commands.append((cmd['command'], service_name))

        converter = ComposeConverter()
        result = converter.convert_multiple_runs(commands)

        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"Error converting commands: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
