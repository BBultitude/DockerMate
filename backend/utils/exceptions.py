"""
DockerMate - Custom Exception Classes

Provides application-specific exceptions for:
- Docker connection errors
- Container operation errors
- Resource not found errors

Usage:
    from backend.utils.exceptions import DockerConnectionError
    
    if not docker_available:
        raise DockerConnectionError("Cannot connect to Docker daemon")

Educational Notes:
- Custom exceptions improve error handling clarity
- Allows catching specific error types
- Better error messages for users
- Separates Docker errors from application logic errors
"""


class DockerMateException(Exception):
    """
    Base exception for all DockerMate errors.
    
    All custom exceptions inherit from this.
    Allows catching any DockerMate-specific error with one except clause.
    
    Educational:
        - Exception hierarchy provides flexible error handling
        - Base class useful for catch-all error handlers
        - Follows Python convention (e.g., requests.RequestException)
    """
    pass


class DockerConnectionError(DockerMateException):
    """
    Raised when Docker daemon is unreachable.
    
    Common causes:
    - Docker service not running
    - Permission denied on /var/run/docker.sock
    - DOCKER_HOST misconfigured
    - Network issues (if using remote Docker)
    
    Educational:
        - Connection errors should be user-friendly
        - Include troubleshooting hints in message
        - Different from APIError (daemon is reachable but operation failed)
    """
    pass


class ContainerNotFoundError(DockerMateException):
    """
    Raised when requested container doesn't exist.
    
    Common causes:
    - Container was deleted
    - Wrong container ID/name provided
    - Container exists but not visible (permission issue)
    
    Educational:
        - 404-style errors map to HTTP status codes
        - Should not be treated as critical error
        - User may need to refresh their view
    """
    pass


class ContainerOperationError(DockerMateException):
    """
    Raised when container operation fails.
    
    Common causes:
    - Container already in requested state (start running container)
    - Resource conflicts (port already bound)
    - Invalid configuration
    - Insufficient permissions
    
    Educational:
        - Operational errors are recoverable
        - Usually indicates user action needed
        - Error message should guide user to solution
    """
    pass


class ImageNotFoundError(DockerMateException):
    """
    Raised when requested image doesn't exist.
    
    Common causes:
    - Image not pulled yet
    - Typo in image name
    - Private registry requires authentication
    - Tag doesn't exist
    
    Educational:
        - Image errors prevent container creation
        - Should suggest pulling image
        - Registry errors need different handling
    """
    pass


class NetworkNotFoundError(DockerMateException):
    """
    Raised when requested network doesn't exist.
    
    Common causes:
    - Network was deleted
    - Wrong network ID/name provided
    - Network exists but not visible
    
    Educational:
        - Network errors affect container connectivity
        - Should suggest creating network
        - Bridge networks can be auto-created
    """
    pass


class VolumeNotFoundError(DockerMateException):
    """
    Raised when requested volume doesn't exist.

    Common causes:
    - Volume was deleted
    - Wrong volume name provided
    - Volume exists but not visible

    Educational:
        - Volume errors prevent data persistence
        - Should suggest creating volume
        - Named volumes vs bind mounts have different behavior
    """
    pass


class VolumeInUseError(DockerMateException):
    """
    Raised when attempting to delete a volume that is in use.

    Common causes:
    - Volume is mounted to running containers
    - Volume is mounted to stopped containers
    - Need to unmount before deletion

    Educational:
        - Docker prevents deletion of in-use volumes
        - Should list which containers are using it
        - Force flag can override if containers stopped
    """
    pass


class ValidationError(DockerMateException):
    """
    Raised when input validation fails.
    
    Common causes:
    - Invalid container name format
    - Invalid IP address
    - Invalid CIDR notation
    - Out of range values
    
    Educational:
        - Validation errors prevent invalid operations
        - Should provide clear error message
        - Fail fast before calling Docker API
    """
    pass


class ConfigurationError(DockerMateException):
    """
    Raised when system configuration is invalid.
    
    Common causes:
    - Missing required configuration
    - Invalid configuration values
    - Conflicting settings
    
    Educational:
        - Configuration errors are setup issues
        - Should only occur during initialization
        - Clear messages help troubleshooting
    """
    pass


class AuthenticationError(DockerMateException):
    """
    Raised when authentication fails.
    
    Common causes:
    - Invalid credentials
    - Session expired
    - No session provided
    
    Educational:
        - Auth errors should not leak sensitive info
        - Generic messages prevent user enumeration
        - HTTP 401 status code mapping
    """
    pass


class PermissionError(DockerMateException):
    """
    Raised when user lacks required permissions.

    Common causes:
    - Not in docker group
    - Read-only access
    - Resource access denied

    Educational:
        - Permission errors map to HTTP 403
        - Different from authentication (401)
        - Should suggest permission fixes
    """
    pass


class StackNotFoundError(DockerMateException):
    """
    Raised when requested Docker Compose stack doesn't exist.

    Common causes:
    - Stack was deleted
    - Wrong stack name/ID provided
    - Stack exists but not tracked by DockerMate

    Educational:
        - Stacks are multi-container applications
        - Stack tracking is in DockerMate database
        - External stacks can be imported
    """
    pass


class StackDeploymentError(DockerMateException):
    """
    Raised when stack deployment fails.

    Common causes:
    - Invalid compose file syntax
    - Missing required images
    - Port conflicts
    - Resource constraints
    - Network/volume creation failures

    Educational:
        - Deployment errors need detailed messages
        - Partial deployments should be cleaned up
        - Should provide rollback guidance
    """
    pass
