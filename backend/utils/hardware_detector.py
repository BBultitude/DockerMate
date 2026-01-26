"""
Hardware Detection Utility

Detects system hardware and classifies into predefined profiles.
Used to automatically configure container limits and feature availability.

Hardware Profiles (2024):
    RASPBERRY_PI: <= 4 cores, <= 8GB RAM
        - Max 15 containers
        - Update checks: 12h
        - Health checks: 15m
        - Limited features
        
    LOW_END: <= 4 cores, <= 16GB RAM
        - Max 20 containers
        - Update checks: 8h
        - Health checks: 10m
        - Basic features
        
    MEDIUM_SERVER: <= 16 cores, <= 64GB RAM (Typical Home Lab)
        - Max 50 containers
        - Update checks: 6h
        - Health checks: 5m
        - All features enabled
        
    HIGH_END: <= 32 cores, <= 128GB RAM
        - Max 100 containers
        - Update checks: 4h
        - Health checks: 3m
        - All features enabled
        
    ENTERPRISE: > 32 cores, > 128GB RAM
        - Max 200 containers
        - Update checks: 2h
        - Health checks: 2m
        - All features enabled

Usage:
    from backend.utils.hardware_detector import detect_hardware_profile
    
    # Detect and get profile
    profile = detect_hardware_profile()
    print(f"Detected: {profile['profile_name']}")
    
    # Update database
    from backend.models.host_config import HostConfig
    config = HostConfig.get_or_create(db)
    update_host_config(db, config)
"""

import os
import platform
import psutil
from typing import Dict, Any


# Hardware Profile Definitions
RASPBERRY_PI_PROFILE = {
    'profile_name': 'RASPBERRY_PI',
    'max_containers': 15,
    'update_check_interval': 43200,  # 12 hours
    'health_check_interval': 900,    # 15 minutes
    'enable_continuous_monitoring': False,
    'enable_log_analysis': False,
    'enable_auto_update': False,
    'network_size_limit': '/25',  # Max 126 IPs
    'container_limit_warning_threshold': 75,
    'container_limit_critical_threshold': 90,
}

LOW_END_PROFILE = {
    'profile_name': 'LOW_END',
    'max_containers': 20,
    'update_check_interval': 28800,  # 8 hours
    'health_check_interval': 600,    # 10 minutes
    'enable_continuous_monitoring': True,
    'enable_log_analysis': False,
    'enable_auto_update': True,
    'network_size_limit': '/24',  # Max 254 IPs
    'container_limit_warning_threshold': 75,
    'container_limit_critical_threshold': 90,
}

MEDIUM_SERVER_PROFILE = {
    'profile_name': 'MEDIUM_SERVER',
    'max_containers': 50,
    'update_check_interval': 21600,  # 6 hours
    'health_check_interval': 300,    # 5 minutes
    'enable_continuous_monitoring': True,
    'enable_log_analysis': True,
    'enable_auto_update': True,
    'network_size_limit': '/24',  # Max 254 IPs
    'container_limit_warning_threshold': 75,
    'container_limit_critical_threshold': 90,
}

HIGH_END_PROFILE = {
    'profile_name': 'HIGH_END',
    'max_containers': 100,
    'update_check_interval': 14400,  # 4 hours
    'health_check_interval': 180,    # 3 minutes
    'enable_continuous_monitoring': True,
    'enable_log_analysis': True,
    'enable_auto_update': True,
    'network_size_limit': '/22',  # Max 1022 IPs
    'container_limit_warning_threshold': 80,
    'container_limit_critical_threshold': 95,
}

ENTERPRISE_PROFILE = {
    'profile_name': 'ENTERPRISE',
    'max_containers': 200,
    'update_check_interval': 7200,   # 2 hours
    'health_check_interval': 120,    # 2 minutes
    'enable_continuous_monitoring': True,
    'enable_log_analysis': True,
    'enable_auto_update': True,
    'network_size_limit': '/22',  # Max 1022 IPs
    'container_limit_warning_threshold': 85,
    'container_limit_critical_threshold': 95,
}


def check_raspberry_pi() -> bool:
    """
    Check if running on Raspberry Pi
    
    Returns:
        bool: True if Raspberry Pi detected
    """
    try:
        # Check for Raspberry Pi specific files
        if os.path.exists('/proc/device-tree/model'):
            with open('/proc/device-tree/model', 'r') as f:
                model = f.read().lower()
                if 'raspberry pi' in model:
                    return True
        
        # Check CPU info for ARM architecture (common on Pi)
        if platform.machine().startswith('arm') or platform.machine().startswith('aarch'):
            # Additional Pi-specific checks
            if os.path.exists('/sys/firmware/devicetree/base/model'):
                with open('/sys/firmware/devicetree/base/model', 'r') as f:
                    model = f.read().lower()
                    if 'raspberry pi' in model:
                        return True
    except Exception:
        pass
    
    return False


def get_cpu_cores() -> int:
    """
    Get total logical CPU cores
    
    Returns:
        int: Number of logical CPU cores
    """
    try:
        return psutil.cpu_count(logical=True)
    except Exception:
        return 4  # Safe default


def get_ram_gb() -> float:
    """
    Get total RAM in gigabytes
    
    Returns:
        float: Total RAM in GB (rounded to 2 decimal places)
    """
    try:
        total_bytes = psutil.virtual_memory().total
        total_gb = total_bytes / (1024 ** 3)
        return round(total_gb, 2)
    except Exception:
        return 8.0  # Safe default


def classify_hardware_profile(cpu_cores: int, ram_gb: float, is_pi: bool) -> Dict[str, Any]:
    """
    Classify hardware into a profile based on specs
    
    Args:
        cpu_cores: Number of logical CPU cores
        ram_gb: Total RAM in gigabytes
        is_pi: True if Raspberry Pi detected
        
    Returns:
        dict: Profile configuration
    """
    # Raspberry Pi gets special profile regardless of specs
    if is_pi:
        return RASPBERRY_PI_PROFILE.copy()
    
    # Classify by CPU and RAM
    if cpu_cores <= 4 and ram_gb <= 16:
        return LOW_END_PROFILE.copy()
    elif cpu_cores <= 16 and ram_gb <= 64:
        return MEDIUM_SERVER_PROFILE.copy()
    elif cpu_cores <= 32 and ram_gb <= 128:
        return HIGH_END_PROFILE.copy()
    else:
        return ENTERPRISE_PROFILE.copy()


def detect_hardware_profile() -> Dict[str, Any]:
    """
    Detect hardware and return appropriate profile
    
    Returns:
        dict: Complete hardware profile with detected specs
            {
                'cpu_cores': int,
                'ram_gb': float,
                'is_raspberry_pi': bool,
                'profile_name': str,
                'max_containers': int,
                'update_check_interval': int,
                'health_check_interval': int,
                'enable_continuous_monitoring': bool,
                'enable_log_analysis': bool,
                'enable_auto_update': bool,
                'network_size_limit': str,
                'container_limit_warning_threshold': int,
                'container_limit_critical_threshold': int,
            }
    """
    # Detect hardware
    cpu_cores = get_cpu_cores()
    ram_gb = get_ram_gb()
    is_pi = check_raspberry_pi()
    
    # Get profile
    profile = classify_hardware_profile(cpu_cores, ram_gb, is_pi)
    
    # Add detected specs to profile
    profile['cpu_cores'] = cpu_cores
    profile['ram_gb'] = ram_gb
    profile['is_raspberry_pi'] = is_pi
    
    return profile


def update_host_config(db, host_config):
    """
    Update HostConfig model with detected hardware profile
    
    Args:
        db: Database session
        host_config: HostConfig model instance
        
    Returns:
        HostConfig: Updated instance
    """
    profile = detect_hardware_profile()
    
    # Update all fields
    host_config.profile_name = profile['profile_name']
    host_config.cpu_cores = profile['cpu_cores']
    host_config.ram_gb = profile['ram_gb']
    host_config.is_raspberry_pi = profile['is_raspberry_pi']
    host_config.max_containers = profile['max_containers']
    host_config.container_limit_warning_threshold = profile['container_limit_warning_threshold']
    host_config.container_limit_critical_threshold = profile['container_limit_critical_threshold']
    host_config.enable_continuous_monitoring = profile['enable_continuous_monitoring']
    host_config.enable_log_analysis = profile['enable_log_analysis']
    host_config.enable_auto_update = profile['enable_auto_update']
    host_config.update_check_interval = profile['update_check_interval']
    host_config.health_check_interval = profile['health_check_interval']
    host_config.network_size_limit = profile['network_size_limit']
    
    db.commit()
    db.refresh(host_config)
    
    return host_config


def get_profile_description(profile_name: str) -> str:
    """
    Get human-readable description of a hardware profile
    
    Args:
        profile_name: Profile name (e.g., 'MEDIUM_SERVER')
        
    Returns:
        str: Description of the profile
    """
    descriptions = {
        'RASPBERRY_PI': (
            'Raspberry Pi - Limited resources detected. '
            'Some features disabled for optimal performance. '
            'Recommended for small home labs (5-10 containers).'
        ),
        'LOW_END': (
            'Low-End System - Basic Docker host. '
            'Suitable for small home labs (10-15 containers). '
            'Background features limited to conserve resources.'
        ),
        'MEDIUM_SERVER': (
            'Medium Server - Typical home lab setup. '
            'All features enabled, suitable for 20-40 containers. '
            'Recommended configuration for most users.'
        ),
        'HIGH_END': (
            'High-End Server - Powerful system. '
            'All features enabled with aggressive update checking. '
            'Suitable for large home labs (50-80 containers).'
        ),
        'ENTERPRISE': (
            'Enterprise System - Maximum capabilities. '
            'All features enabled with maximum limits. '
            'Suitable for production environments (100+ containers).'
        ),
    }
    return descriptions.get(profile_name, 'Unknown profile')
