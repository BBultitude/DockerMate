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
    db = None
    try:
        # Get database session
        db = SessionLocal()
        
        # Get or create hardware config from database
        config = HostConfig.get_or_create(db)
        
        # If config exists but profile is UNKNOWN, it hasn't been detected yet
        if config.profile_name == 'UNKNOWN' or config.cpu_cores == 0:
            logger.warning("Hardware profile not detected yet - returning defaults")
            # Try to detect hardware now
            try:
                from backend.utils.hardware_detector import update_host_config
                config = update_host_config(db, config)
                db.commit()
                db.refresh(config)
            except Exception as detect_error:
                logger.error(f"Hardware detection failed: {detect_error}")
                # Return basic defaults if detection fails
                hardware_data = {
                    "profile_name": "UNKNOWN",
                    "max_containers": 50,
                    "cpu_count": 0,
                    "total_memory_gb": 0.0,
                    "total_memory_bytes": 0,
                    "description": "Hardware profile not yet detected"
                }
                return jsonify({
                    "success": True,
                    "data": hardware_data,
                    "warning": "Hardware profile not yet detected"
                }), 200
        
        # Build response with hardware info
        hardware_data = {
            "profile_name": config.profile_name,
            "max_containers": config.max_containers,
            "cpu_count": config.cpu_cores,
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
            "error": f"Failed to retrieve hardware information: {str(e)}",
            "error_type": "ServerError"
        }), 500
    finally:
        if db:
            db.close()


@system_bp.route('/health', methods=['GET'])
def health_check():
    """
    System health check endpoint.

    GET /api/system/health

    Performs live checks against the database and Docker daemon.
    Returns per-check status plus any warnings worth surfacing
    to the dashboard health card.

    Success Response (200):
    {
        "success": true,
        "status": "healthy",          // "healthy" | "warning" | "unhealthy"
        "checks": {
            "database": "ok",         // "ok" | "error"
            "docker": "ok",           // "ok" | "error"
        },
        "warnings": []                // list of human-readable warning strings
    }
    """
    checks = {}
    warnings = []

    # --- Database connectivity ---
    db = None
    try:
        db = SessionLocal()
        # A lightweight query — just proves the connection works
        db.execute(__import__('sqlalchemy').text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        logger.error(f"Health check — database: {e}")
        checks["database"] = "error"
        warnings.append("Database connection failed")
    finally:
        if db:
            db.close()

    # --- Docker daemon connectivity ---
    try:
        from backend.utils.docker_client import get_docker_client
        client = get_docker_client()
        client.ping()
        checks["docker"] = "ok"
    except Exception as e:
        logger.error(f"Health check — docker: {e}")
        checks["docker"] = "error"
        warnings.append("Docker daemon is not reachable")

    # --- Exited containers (worth flagging) ---
    try:
        from backend.utils.docker_client import get_docker_client
        client = get_docker_client()
        exited = client.containers.list(all=True, filters={"status": "exited"})
        # Filter out DockerMate's own container
        exited = [c for c in exited if 'dockermate' not in (c.name or '').lower()]
        if exited:
            warnings.append(f"{len(exited)} container(s) exited — check Containers page")
    except Exception:
        pass  # non-fatal; docker check above already covers connectivity

    # --- Capacity warning ---
    try:
        db = SessionLocal()
        config = HostConfig.get_or_create(db)
        from backend.utils.docker_client import get_docker_client
        client = get_docker_client()
        total = len(client.containers.list(all=True))
        pct = round((total / config.max_containers) * 100) if config.max_containers else 0
        if pct >= 80:
            warnings.append(f"Capacity at {pct}% ({total}/{config.max_containers} containers)")
    except Exception:
        pass
    finally:
        if db:
            db.close()

    # Derive overall status
    if checks.get("database") == "error" or checks.get("docker") == "error":
        status = "unhealthy"
    elif warnings:
        status = "warning"
    else:
        status = "healthy"

    return jsonify({
        "success": True,
        "status": status,
        "checks": checks,
        "warnings": warnings
    }), 200


@system_bp.route('/networks', methods=['GET'])
def get_networks():
    """
    List Docker networks on the host.

    GET /api/system/networks

    Lightweight endpoint — queries Docker daemon directly.  No database
    model required until Sprint 4 adds full network management.

    Success Response (200):
    {
        "success": true,
        "data": [
            {"name": "bridge", "driver": "bridge", "id": "abc123..."},
            ...
        ],
        "count": 4
    }
    """
    try:
        from backend.utils.docker_client import get_docker_client
        client = get_docker_client()
        networks = client.networks.list()

        data = []
        for net in networks:
            data.append({
                "name": net.name,
                "driver": net.attrs.get("Driver", "unknown"),
                "id": net.id
            })

        return jsonify({
            "success": True,
            "data": data,
            "count": len(data)
        }), 200

    except Exception as e:
        logger.exception(f"Failed to list networks: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to retrieve network information",
            "error_type": "ServerError"
        }), 500