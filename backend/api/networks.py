"""
DockerMate - Networks API Blueprint (Sprint 4)
===============================================

REST endpoints for Docker network management.

Endpoints
---------
    GET    /api/networks                  List all networks
    POST   /api/networks                  Create a network
    GET    /api/networks/<network_id>     Get network details + containers
    DELETE /api/networks/<network_id>     Delete a network
    GET    /api/networks/recommend        Get hardware-aware subnet recommendations
    POST   /api/networks/validate-subnet  Validate a CIDR block

Usage
-----
    In app_dev.py or app.py::

        from backend.api.networks import networks_bp
        app.register_blueprint(networks_bp)
"""

import logging
from flask import Blueprint, jsonify, request

from backend.services.network_manager import NetworkManager

logger = logging.getLogger(__name__)

networks_bp = Blueprint('networks', __name__, url_prefix='/api/networks')


# ------------------------------------------------------------------
# List networks
# ------------------------------------------------------------------

@networks_bp.route('', methods=['GET'])
def list_networks():
    """
    GET /api/networks

    Returns every Docker network on the host, enriched with:
    - container count
    - managed flag (created via DockerMate vs pre-existing)
    - oversized warning flag
    """
    try:
        with NetworkManager() as manager:
            networks = manager.list_networks()
        return jsonify({'success': True, 'data': networks, 'count': len(networks)}), 200
    except Exception as e:
        logger.exception(f"list_networks failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ------------------------------------------------------------------
# Create network
# ------------------------------------------------------------------

@networks_bp.route('', methods=['POST'])
def create_network():
    """
    POST /api/networks

    Body (JSON):
        name        (str)  — required, must be unique
        driver      (str)  — optional, default "bridge"
        subnet      (str)  — optional CIDR, e.g. "172.20.0.0/24"
        gateway     (str)  — optional, auto-assigned if omitted
        ip_range    (str)  — optional CIDR within subnet
        purpose     (str)  — optional description
    """
    data = request.get_json(silent=True) or {}

    name = data.get('name', '').strip()
    driver = data.get('driver', 'bridge')
    subnet = data.get('subnet') or None
    gateway = data.get('gateway') or None
    ip_range = data.get('ip_range') or None
    purpose = data.get('purpose') or None

    if not name:
        return jsonify({'success': False, 'error': 'Network name is required'}), 400

    try:
        with NetworkManager() as manager:
            result = manager.create_network(
                name=name,
                driver=driver,
                subnet=subnet,
                gateway=gateway,
                ip_range=ip_range,
                purpose=purpose,
            )

        if result['success']:
            return jsonify(result), 201
        return jsonify(result), 400

    except Exception as e:
        logger.exception(f"create_network failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ------------------------------------------------------------------
# Subnet recommendations  (must come before /<network_id> routes)
# ------------------------------------------------------------------

@networks_bp.route('/recommend', methods=['GET'])
def recommend_subnets():
    """
    GET /api/networks/recommend

    Returns small/large subnet recommendations based on the host's
    hardware profile, using a free base address that doesn't collide
    with any existing network.
    """
    try:
        with NetworkManager() as manager:
            rec = manager.recommend_subnets()
        return jsonify({'success': True, 'data': rec}), 200

    except Exception as e:
        logger.exception(f"recommend_subnets failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ------------------------------------------------------------------
# Validate subnet  (must come before /<network_id> routes)
# ------------------------------------------------------------------

@networks_bp.route('/validate-subnet', methods=['POST'])
def validate_subnet():
    """
    POST /api/networks/validate-subnet

    Body (JSON):
        subnet  (str)  — CIDR to validate

    Returns ``{'valid': true}`` or ``{'valid': false, 'reason': '...'}``.
    Live-checked against the Docker daemon for overlap.
    """
    data = request.get_json(silent=True) or {}
    subnet = data.get('subnet', '')

    if not subnet:
        return jsonify({'valid': False, 'reason': 'Subnet is required'}), 400

    try:
        with NetworkManager() as manager:
            result = manager.validate_subnet(subnet)
        return jsonify(result), 200

    except Exception as e:
        logger.exception(f"validate_subnet failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ------------------------------------------------------------------
# Auto-generated network documentation
# ------------------------------------------------------------------

@networks_bp.route('/docs', methods=['GET'])
def generate_docs():
    """
    GET /api/networks/docs

    Returns a Markdown report documenting every network on the host:
    metadata, connected containers, reserved IP ranges, and utilisation
    stats.  Copy-paste ready.
    """
    try:
        with NetworkManager() as manager:
            markdown = manager.generate_docs()
        return jsonify({'success': True, 'markdown': markdown}), 200

    except Exception as e:
        logger.exception(f"generate_docs failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ------------------------------------------------------------------
# Get single network
# ------------------------------------------------------------------

@networks_bp.route('/<network_id>', methods=['GET'])
def get_network(network_id):
    """
    GET /api/networks/<network_id>

    Returns full network details including the list of containers
    currently attached and their IP addresses on this network.
    """
    try:
        with NetworkManager() as manager:
            network = manager.get_network(network_id)

        if not network:
            return jsonify({'success': False, 'error': 'Network not found'}), 404

        return jsonify({'success': True, 'data': network}), 200

    except Exception as e:
        logger.exception(f"get_network failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ------------------------------------------------------------------
# IP allocations (reservations + live assignments)
# ------------------------------------------------------------------

@networks_bp.route('/<network_id>/ips', methods=['GET'])
def get_ip_allocations(network_id):
    """
    GET /api/networks/<network_id>/ips

    Returns the full IP-allocation picture for one network:
    - Subnet geometry (usable range, totals)
    - Live assigned IPs (from Docker)
    - Reserved IP ranges (from DB)
    - Free IP count and utilisation percentage
    """
    try:
        with NetworkManager() as manager:
            result = manager.get_ip_allocations(network_id)

        if not result:
            return jsonify({'success': False, 'error': 'Network not found or has no subnet'}), 404

        return jsonify({'success': True, 'data': result}), 200

    except Exception as e:
        logger.exception(f"get_ip_allocations failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ------------------------------------------------------------------
# Reserve an IP range
# ------------------------------------------------------------------

@networks_bp.route('/<network_id>/reserve', methods=['POST'])
def reserve_ips(network_id):
    """
    POST /api/networks/<network_id>/reserve

    Body (JSON):
        range_name   (str)  — required, label for the block (e.g. "Web services")
        start_ip     (str)  — required, first IP in the range
        end_ip       (str)  — required, last IP in the range
        description  (str)  — optional, human-readable note
    """
    data = request.get_json(silent=True) or {}

    range_name = data.get('range_name', '').strip()
    start_ip = data.get('start_ip', '').strip()
    end_ip = data.get('end_ip', '').strip()
    description = data.get('description') or None

    if not range_name:
        return jsonify({'success': False, 'error': 'Range name is required'}), 400
    if not start_ip or not end_ip:
        return jsonify({'success': False, 'error': 'start_ip and end_ip are required'}), 400

    try:
        with NetworkManager() as manager:
            result = manager.reserve_ip_range(
                network_id=network_id,
                range_name=range_name,
                start_ip=start_ip,
                end_ip=end_ip,
                description=description,
            )

        if result['success']:
            return jsonify(result), 201
        return jsonify(result), 400

    except Exception as e:
        logger.exception(f"reserve_ips failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ------------------------------------------------------------------
# Delete a reservation range
# ------------------------------------------------------------------

@networks_bp.route('/<network_id>/reserve/<range_name>', methods=['DELETE'])
def delete_reservation(network_id, range_name):
    """
    DELETE /api/networks/<network_id>/reserve/<range_name>

    Removes all reserved IPs in the named block from the given network.
    """
    try:
        with NetworkManager() as manager:
            result = manager.delete_reservation(network_id, range_name)

        if result['success']:
            return jsonify(result), 200
        return jsonify(result), 400

    except Exception as e:
        logger.exception(f"delete_reservation failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ------------------------------------------------------------------
# Connect / disconnect containers
# ------------------------------------------------------------------

@networks_bp.route('/<network_id>/connect', methods=['POST'])
def connect_container(network_id):
    """
    POST /api/networks/<network_id>/connect

    Body (JSON):
        container_id  (str)  — Docker container ID or name
    """
    data = request.get_json(silent=True) or {}
    container_id = data.get('container_id', '').strip()

    if not container_id:
        return jsonify({'success': False, 'error': 'container_id is required'}), 400

    try:
        with NetworkManager() as manager:
            result = manager.connect_container(network_id, container_id)

        if result['success']:
            return jsonify(result), 200
        return jsonify(result), 400

    except Exception as e:
        logger.exception(f"connect_container failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@networks_bp.route('/<network_id>/connect/<container_id>', methods=['DELETE'])
def disconnect_container(network_id, container_id):
    """
    DELETE /api/networks/<network_id>/connect/<container_id>

    Detach the specified container from the network.
    """
    try:
        with NetworkManager() as manager:
            result = manager.disconnect_container(network_id, container_id)

        if result['success']:
            return jsonify(result), 200
        return jsonify(result), 400

    except Exception as e:
        logger.exception(f"disconnect_container failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ------------------------------------------------------------------
# Delete network
# ------------------------------------------------------------------

@networks_bp.route('/<network_id>', methods=['DELETE'])
def delete_network(network_id):
    """
    DELETE /api/networks/<network_id>

    Refuses to delete:
    - Docker default networks (bridge, host, none)
    - Networks with containers still attached
    """
    try:
        with NetworkManager() as manager:
            result = manager.delete_network(network_id)

        if result['success']:
            return jsonify(result), 200
        return jsonify(result), 400

    except Exception as e:
        logger.exception(f"delete_network failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
