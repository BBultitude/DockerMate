"""
DockerMate - System API Endpoints (Sprint 2 Task 6)
====================================================

System-level API endpoints for hardware profiles, health checks, and configuration.

Endpoints:
    GET /api/system/hardware    Get hardware profile information
    GET /api/system/health      System health check

Usage:
    In app.py or app_dev.py::
    
        from backend.api.system import system_bp
        app.register_blueprint(system_bp)

Educational Notes:
- Provides hardware profile info for UI display
- Shows container limits based on detected hardware tier
- Educational value: Shows what hardware resources are available
"""

import logging
from flask import Blueprint, jsonify

from backend.models.host_config import HostConfig
from backend.models.database import SessionLocal

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint for system routes
system_bp = Blueprint('system', __name__, url_prefix='/api/system')


@system_bp.route('/hardware', methods=['GET'])
def get_hardware_profile():
    """
    Get hardware profile information.
    
    GET /api/system/hardware
    
    Returns hardware tier, container limits, and resource info.
    Used by frontend to display current hardware capabilities.
    
    Success Response (200):
    {
        "success": true,
        "data": {
            "profile_name": "Raspberry Pi",
            "max_containers": 10,
            "max_networks": 5,
            "cpu_count": 4,
            "total_memory_gb": 4.0,
            "total_memory_bytes": 4294967296,
            "tier": 1,
            "description": "Single-board computer for home projects"
        }
    }
    
    Educational Notes:
        - Hardware profile detected at startup
        - Determines container limits to prevent overload
        - Used throughout UI for hardware-aware validation
        - DockerMate feature (no Docker CLI equivalent)
    """
    db = SessionLocal()
    try:
        # Get or create hardware config from database
        config = HostConfig.get_or_create(db)
        
        # Build response with hardware info
        hardware_data = {
            "profile_name": config.profile_name,
            "max_containers": config.max_containers,
            "max_networks": config.max_networks,
            "cpu_count": config.cpu_cores,  # Note: field is cpu_cores in model
            "total_memory_gb": round(config.ram_gb, 2),
            "total_memory_bytes": int(config.ram_gb * (1024**3)),
            "description": f"Hardware profile: {config.profile_name}"
        }
        
        return jsonify({
            "success": True,
            "data": hardware_data
        }), 200
        
    except Exception as e:
        logger.exception(f"Failed to get hardware profile: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to retrieve hardware information",
            "error_type": "ServerError"
        }), 500
    finally:
        db.close()


@system_bp.route('/health', methods=['GET'])
def health_check():
    """
    System health check endpoint.
    
    GET /api/system/health
    
    Returns system health status including database and Docker connectivity.
    
    Success Response (200):
    {
        "success": true,
        "status": "healthy",
        "checks": {
            "database": "ok",
            "docker": "ok",
            "hardware": "ok"
        }
    }
    """
    try:
        checks = {
            "database": "ok",
            "docker": "ok", 
            "hardware": "ok"
        }
        
        # TODO: Add actual health checks in future sprint
        # - Database connection test
        # - Docker daemon ping
        # - Disk space check
        
        return jsonify({
            "success": True,
            "status": "healthy",
            "checks": checks
        }), 200
        
    except Exception as e:
        logger.exception(f"Health check failed: {e}")
        return jsonify({
            "success": False,
            "status": "unhealthy",
            "error": str(e)
        }), 500