"""
DockerMate - Docker SDK Client Wrapper

Provides a singleton Docker client with:
- Automatic connection management
- Health checking and reconnection
- Error handling and logging
- Context managers for safe operations

Usage:
    from backend.utils.docker_client import get_docker_client, docker_operation
    
    # Get client instance
    client = get_docker_client()
    containers = client.containers.list()
    
    # Safe operation with error handling
    @docker_operation
    def my_function():
        client = get_docker_client()
        return client.containers.list()

Educational Notes:
- Singleton pattern ensures one Docker connection per application
- Connection pooling handled by Docker SDK internally
- Unix socket communication (/var/run/docker.sock) is standard
- Error handling prevents cascading failures
"""

import logging
from typing import Optional
from functools import wraps
import docker
from docker.errors import DockerException, APIError, NotFound

from backend.utils.exceptions import DockerConnectionError

# Configure logging
logger = logging.getLogger(__name__)

# Global singleton instance
_docker_client: Optional[docker.DockerClient] = None
_connection_healthy: bool = False


def get_docker_client(force_reconnect: bool = False) -> docker.DockerClient:
    """
    Get singleton Docker client instance.
    
    Creates connection on first call, reuses on subsequent calls.
    Implements singleton pattern to avoid multiple connections.
    
    Args:
        force_reconnect: Force creation of new connection (for error recovery)
    
    Returns:
        docker.DockerClient: Connected Docker client
    
    Raises:
        DockerConnectionError: If connection cannot be established
    
    Educational:
        - Singleton pattern: One instance shared across application
        - from_env() reads DOCKER_HOST environment variable
        - Falls back to unix:///var/run/docker.sock if not set
        - Connection is lazy - doesn't verify until first API call
    """
    global _docker_client, _connection_healthy
    
    # Return existing client if healthy and not forcing reconnect
    if _docker_client is not None and _connection_healthy and not force_reconnect:
        logger.debug("Reusing existing Docker client connection")
        return _docker_client
    
    try:
        logger.info("Creating new Docker client connection...")
        
        # Create client from environment
        # This reads DOCKER_HOST, DOCKER_TLS_VERIFY, DOCKER_CERT_PATH
        # Defaults to unix:///var/run/docker.sock on Linux
        client = docker.from_env()
        
        # Verify connection with ping
        # This actually communicates with daemon
        client.ping()
        
        # Connection successful
        _docker_client = client
        _connection_healthy = True
        
        # Log Docker daemon info
        info = client.info()
        logger.info(f"Docker connection established - Version: {info.get('ServerVersion', 'unknown')}")
        logger.info(f"Docker daemon: {info.get('Name', 'unknown')} - OS: {info.get('OperatingSystem', 'unknown')}")
        
        return _docker_client
        
    except DockerException as e:
        _connection_healthy = False
        logger.error(f"Failed to connect to Docker daemon: {e}")
        raise DockerConnectionError(
            f"Cannot connect to Docker daemon. Is Docker running? Error: {e}"
        )
    except Exception as e:
        _connection_healthy = False
        logger.error(f"Unexpected error connecting to Docker: {e}")
        raise DockerConnectionError(
            f"Unexpected error connecting to Docker daemon: {e}"
        )


def check_docker_connection() -> bool:
    """
    Check if Docker daemon is accessible.
    
    Non-destructive health check that doesn't raise exceptions.
    Useful for status endpoints and monitoring.
    
    Returns:
        bool: True if Docker daemon is reachable, False otherwise
    
    Educational:
        - Health checks should be lightweight
        - ping() is cheaper than listing containers
        - Useful for /health endpoints
    """
    global _connection_healthy
    
    try:
        client = get_docker_client()
        client.ping()
        _connection_healthy = True
        return True
    except Exception as e:
        logger.warning(f"Docker health check failed: {e}")
        _connection_healthy = False
        return False


def close_docker_client() -> None:
    """
    Close Docker client connection.
    
    Should be called on application shutdown for clean closure.
    Will be automatically recreated on next get_docker_client() call.
    
    Educational:
        - Clean shutdown prevents resource leaks
        - Docker SDK handles connection cleanup internally
        - Resetting global state allows reconnection
    """
    global _docker_client, _connection_healthy
    
    if _docker_client is not None:
        try:
            logger.info("Closing Docker client connection")
            _docker_client.close()
        except Exception as e:
            logger.warning(f"Error closing Docker client: {e}")
        finally:
            _docker_client = None
            _connection_healthy = False


def docker_operation(func):
    """
    Decorator for Docker operations with automatic error handling.
    
    Wraps functions that use Docker SDK and:
    - Catches DockerException and converts to DockerConnectionError
    - Attempts reconnection on connection errors
    - Logs errors appropriately
    
    Usage:
        @docker_operation
        def list_containers():
            client = get_docker_client()
            return client.containers.list()
    
    Args:
        func: Function to wrap
    
    Returns:
        Wrapped function with error handling
    
    Educational:
        - Decorator pattern adds behavior without modifying function
        - @wraps preserves original function metadata
        - Centralized error handling reduces code duplication
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except NotFound as e:
            # Resource not found - reraise as-is
            # Caller should handle this (404 errors)
            logger.debug(f"Docker resource not found: {e}")
            raise
        except APIError as e:
            # Docker API error (e.g., container already running)
            # Reraise as-is - contains useful error info
            logger.warning(f"Docker API error in {func.__name__}: {e}")
            raise
        except DockerException as e:
            # Connection or other Docker errors
            logger.error(f"Docker operation failed in {func.__name__}: {e}")
            
            # Try to reconnect once
            try:
                logger.info("Attempting to reconnect to Docker daemon...")
                get_docker_client(force_reconnect=True)
                
                # Retry operation once
                logger.info("Retrying operation after reconnection...")
                return func(*args, **kwargs)
            except Exception as retry_error:
                logger.error(f"Retry failed: {retry_error}")
                raise DockerConnectionError(
                    f"Docker operation failed and retry unsuccessful: {e}"
                )
        except Exception as e:
            # Unexpected errors
            logger.error(f"Unexpected error in Docker operation {func.__name__}: {e}")
            raise
    
    return wrapper


# Educational example of context manager usage
class DockerClientContext:
    """
    Context manager for Docker client operations.
    
    Ensures proper cleanup even if errors occur.
    Alternative to decorator pattern.
    
    Usage:
        with DockerClientContext() as client:
            containers = client.containers.list()
    
    Educational:
        - Context managers guarantee cleanup (__exit__ always runs)
        - 'with' statement handles __enter__ and __exit__
        - Useful for resource management (files, connections, locks)
    """
    
    def __init__(self):
        self.client = None
    
    def __enter__(self):
        """Called when entering 'with' block."""
        self.client = get_docker_client()
        return self.client
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Called when exiting 'with' block (even on error)."""
        # Docker SDK client doesn't need explicit cleanup per-operation
        # Connection remains open for reuse
        # This is here for educational purposes and future extensions
        pass
