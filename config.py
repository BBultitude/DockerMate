"""
DockerMate Configuration Management

Centralizes all configuration with environment variable support.

Environment Variables:
- DOCKERMATE_DATA_DIR: Data directory (default: /app/data)
- DOCKERMATE_DATABASE_PATH: SQLite database path
- DOCKERMATE_SSL_MODE: SSL mode (self-signed|letsencrypt|custom)
- DOCKERMATE_SESSION_EXPIRY: Session expiry duration (default: 8h)
- DOCKERMATE_REMEMBER_ME_EXPIRY: Remember me duration (default: 7d)
- DOCKERMATE_HARDWARE_PROFILE: Override auto-detection
- DOCKERMATE_HOST_ENVIRONMENT: Host environment (PRD|UAT|DEV|SANDBOX|MIXED)

Author: DockerMate Team
License: MIT
"""

import os
from typing import Dict

class Config:
    """
    Application configuration
    
    All configuration is centralized here with sensible defaults
    for home lab deployments.
    """
    
    # ============================================
    # Paths
    # ============================================
    BASE_DIR = os.getenv('DOCKERMATE_BASE_DIR', '/app')
    DATA_DIR = os.getenv('DOCKERMATE_DATA_DIR', os.path.join(BASE_DIR, 'data'))
    SSL_DIR = os.path.join(DATA_DIR, 'ssl')
    STACKS_DIR = os.path.join(BASE_DIR, 'stacks')
    EXPORTS_DIR = os.path.join(BASE_DIR, 'exports')
    
    # ============================================
    # Database
    # ============================================
    DATABASE_PATH = os.getenv(
        'DOCKERMATE_DATABASE_PATH', 
        os.path.join(DATA_DIR, 'dockermate.db')
    )
    
    # ============================================
    # Security
    # ============================================
    SSL_MODE = os.getenv('DOCKERMATE_SSL_MODE', 'self-signed')
    SESSION_EXPIRY = os.getenv('DOCKERMATE_SESSION_EXPIRY', '8h')
    REMEMBER_ME_EXPIRY = os.getenv('DOCKERMATE_REMEMBER_ME_EXPIRY', '7d')
    
    # Bcrypt work factor (12 is good balance for home lab hardware)
    BCRYPT_WORK_FACTOR = 12
    
    # ============================================
    # Hardware & Environment
    # ============================================
    HARDWARE_PROFILE = os.getenv('DOCKERMATE_HARDWARE_PROFILE', 'auto')
    HOST_ENVIRONMENT = os.getenv('DOCKERMATE_HOST_ENVIRONMENT', 'MIXED')
    
    # ============================================
    # Update & Monitoring Intervals
    # ============================================
    # These will be adjusted based on detected hardware profile
    UPDATE_CHECK_INTERVAL = os.getenv('DOCKERMATE_UPDATE_CHECK_INTERVAL', '6h')
    HEALTH_CHECK_INTERVAL = os.getenv('DOCKERMATE_HEALTH_CHECK_INTERVAL', '5m')
    
    # ============================================
    # Docker
    # ============================================
    DOCKER_SOCKET = '/var/run/docker.sock'
    
    @staticmethod
    def parse_duration(duration_str: str) -> int:
        """
        Parse duration string to seconds
        
        Args:
            duration_str: Duration string (e.g., '8h', '7d', '30m')
        
        Returns:
            int: Duration in seconds
        
        Examples:
            >>> Config.parse_duration('8h')
            28800
            >>> Config.parse_duration('7d')
            604800
            >>> Config.parse_duration('30m')
            1800
        
        Supported units:
        - 's' or no suffix: seconds
        - 'm': minutes
        - 'h': hours
        - 'd': days
        """
        if not duration_str:
            return 0
        
        # If it's already an integer, return it
        try:
            return int(duration_str)
        except ValueError:
            pass
        
        # Parse string with unit
        unit = duration_str[-1].lower()
        try:
            value = int(duration_str[:-1])
        except ValueError:
            raise ValueError(f"Invalid duration format: {duration_str}")
        
        # Convert to seconds
        if unit == 's':
            return value
        elif unit == 'm':
            return value * 60
        elif unit == 'h':
            return value * 3600
        elif unit == 'd':
            return value * 86400
        else:
            # Assume seconds if no unit
            try:
                return int(duration_str)
            except ValueError:
                raise ValueError(f"Invalid duration format: {duration_str}")
    
    @staticmethod
    def get_session_expiry_seconds() -> int:
        """
        Get session expiry in seconds
        
        Returns:
            int: Session expiry in seconds (default: 8 hours)
        """
        return Config.parse_duration(Config.SESSION_EXPIRY)
    
    @staticmethod
    def get_remember_me_expiry_seconds() -> int:
        """
        Get remember me expiry in seconds
        
        Returns:
            int: Remember me expiry in seconds (default: 7 days)
        """
        return Config.parse_duration(Config.REMEMBER_ME_EXPIRY)
    
    @staticmethod
    def ensure_directories():
        """
        Ensure all required directories exist
        
        This should be called on application startup to create
        any missing directories.
        
        Verification:
            ls -la /app/data
        """
        directories = [
            Config.DATA_DIR,
            Config.SSL_DIR,
            Config.STACKS_DIR,
            Config.EXPORTS_DIR,
            os.path.join(Config.DATA_DIR, 'backups')
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    @staticmethod
    def get_config_dict() -> Dict:
        """
        Get configuration as dictionary
        
        Useful for debugging and displaying current configuration.
        
        Returns:
            dict: Configuration key-value pairs
        """
        return {
            'BASE_DIR': Config.BASE_DIR,
            'DATA_DIR': Config.DATA_DIR,
            'SSL_DIR': Config.SSL_DIR,
            'DATABASE_PATH': Config.DATABASE_PATH,
            'SSL_MODE': Config.SSL_MODE,
            'SESSION_EXPIRY': Config.SESSION_EXPIRY,
            'REMEMBER_ME_EXPIRY': Config.REMEMBER_ME_EXPIRY,
            'HARDWARE_PROFILE': Config.HARDWARE_PROFILE,
            'HOST_ENVIRONMENT': Config.HOST_ENVIRONMENT,
            'UPDATE_CHECK_INTERVAL': Config.UPDATE_CHECK_INTERVAL,
            'HEALTH_CHECK_INTERVAL': Config.HEALTH_CHECK_INTERVAL
        }
