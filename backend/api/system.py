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
    System health check endpoint (expanded Sprint 5 — FEAT-019).

    GET /api/system/health

    Checks every managed-resource domain and returns structured,
    domain-tagged warnings so both the dashboard card and the full
    health page can render them.

    Success Response (200):
    {
        "success": true,
        "status": "healthy",          // "healthy" | "warning" | "unhealthy"
        "checks": {
            "database":   "ok",       // "ok" | "warning" | "error"
            "docker":     "ok",
            "containers": "ok",
            "images":     "ok",
            "networks":   "ok",
            "dockermate": "ok"
        },
        "warnings": [
            { "domain": "containers", "message": "..." },
            ...
        ]
    }
    """
    import sqlalchemy
    checks = {}
    warnings = []

    # ------------------------------------------------------------------
    # Infrastructure: database + docker daemon
    # ------------------------------------------------------------------
    db = None
    try:
        db = SessionLocal()
        db.execute(sqlalchemy.text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        logger.error(f"Health check — database: {e}")
        checks["database"] = "error"
        warnings.append({"domain": "infrastructure", "message": "Database connection failed"})
    finally:
        if db:
            db.close()

    client = None
    try:
        from backend.utils.docker_client import get_docker_client
        client = get_docker_client()
        client.ping()
        checks["docker"] = "ok"
    except Exception as e:
        logger.error(f"Health check — docker: {e}")
        checks["docker"] = "error"
        warnings.append({"domain": "infrastructure", "message": "Docker daemon is not reachable"})

    # ------------------------------------------------------------------
    # Containers: exited non-zero, failing health-checks
    # ------------------------------------------------------------------
    checks["containers"] = "ok"
    if client:
        try:
            all_containers = client.containers.list(all=True)
            exited_nonzero = []
            unhealthy = []
            for c in all_containers:
                if 'dockermate' in (c.name or '').lower():
                    continue
                if c.status == 'exited':
                    try:
                        c.reload()
                        if c.attrs.get('State', {}).get('ExitCode', 0) != 0:
                            exited_nonzero.append(c.name.lstrip('/'))
                    except Exception:
                        pass
                # Health-check failures (only present when a HEALTHCHECK is defined)
                try:
                    health = c.attrs.get('State', {}).get('Health')
                    if health and health.get('Status') == 'unhealthy':
                        unhealthy.append(c.name.lstrip('/'))
                except Exception:
                    pass

            if exited_nonzero or unhealthy:
                checks["containers"] = "warning"
                if exited_nonzero:
                    warnings.append({"domain": "containers",
                                     "message": f"{len(exited_nonzero)} container(s) exited with non-zero exit code"})
                if unhealthy:
                    warnings.append({"domain": "containers",
                                     "message": f"{len(unhealthy)} container(s) failing health check: {', '.join(unhealthy)}"})
        except Exception as e:
            logger.warning(f"Containers health check: {e}")

    # ------------------------------------------------------------------
    # Images: dangling + updates available
    # ------------------------------------------------------------------
    checks["images"] = "ok"
    try:
        dangling_count = 0
        if client:
            for img in client.images.list():
                if not img.tags or img.tags == ['<none>:<none>']:
                    dangling_count += 1

        from backend.models.image import Image
        db = SessionLocal()
        updates_available = db.query(Image).filter(Image.update_available == True).count()
        db.close()

        if dangling_count or updates_available:
            checks["images"] = "warning"
            if dangling_count:
                warnings.append({"domain": "images", "message": f"{dangling_count} dangling image(s) present"})
            if updates_available:
                warnings.append({"domain": "images", "message": f"{updates_available} image(s) with updates available"})
    except Exception as e:
        logger.warning(f"Images health check: {e}")

    # ------------------------------------------------------------------
    # Networks: oversized detection
    # ------------------------------------------------------------------
    checks["networks"] = "ok"
    try:
        from backend.services.network_manager import NetworkManager
        with NetworkManager() as mgr:
            networks = mgr.list_networks()
        oversized = [n for n in networks if n.get('oversized')]
        if oversized:
            checks["networks"] = "warning"
            warnings.append({"domain": "networks",
                             "message": f"{len(oversized)} oversized network(s): {', '.join(n['name'] for n in oversized)}"})
    except Exception as e:
        logger.warning(f"Networks health check: {e}")

    # ------------------------------------------------------------------
    # DockerMate: capacity check
    # ------------------------------------------------------------------
    checks["dockermate"] = "ok"
    try:
        db = SessionLocal()
        config = HostConfig.get_or_create(db)
        if client:
            total = len(client.containers.list(all=True))
            pct = round((total / config.max_containers) * 100) if config.max_containers else 0
            if pct >= 80:
                checks["dockermate"] = "warning"
                warnings.append({"domain": "dockermate",
                                 "message": f"Capacity at {pct}% ({total}/{config.max_containers} containers)"})
        db.close()
    except Exception as e:
        logger.warning(f"DockerMate capacity check: {e}")

    # ------------------------------------------------------------------
    # Derive overall status
    # ------------------------------------------------------------------
    if "error" in checks.values():
        status = "unhealthy"
    elif "warning" in checks.values():
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