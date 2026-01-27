"""
DockerMate - Container Service Layer

Provides high-level container operations:
- List containers (running or all)
- Get container details
- Start/stop/restart containers
- Remove containers
- Get container stats and logs

Usage:
    from backend.services.container_service import ContainerService
    
    service = ContainerService()
    containers = service.list_containers(all=True)
    service.start_container('nginx-web')

Educational Notes:
- Service layer separates business logic from API routes
- Converts Docker SDK objects to dictionaries for API responses
- Centralizes error handling and logging
- Makes testing easier (can mock service instead of Docker SDK)
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from docker.errors import NotFound, APIError

from backend.utils.docker_client import get_docker_client, docker_operation
from backend.utils.exceptions import (
    ContainerNotFoundError,
    ContainerOperationError,
    DockerConnectionError
)

# Configure logging
logger = logging.getLogger(__name__)


class ContainerService:
    """
    Service class for container operations.
    
    Wraps Docker SDK with:
    - Error handling and logging
    - Data transformation (Docker objects → dicts)
    - Business logic (validation, checks)
    
    Educational:
        - Service pattern separates concerns
        - Single Responsibility Principle (only container logic)
        - Easy to mock for testing
        - Can add caching, validation, authorization here
    """
    
    @docker_operation
    def list_containers(self, all: bool = False, environment: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List containers with optional filtering.
        
        Args:
            all: If True, include stopped containers. If False, only running.
            environment: Optional environment tag to filter by (e.g., "PRD", "DEV")
        
        Returns:
            List of container dictionaries with essential info
        
        Raises:
            DockerConnectionError: If Docker daemon is unreachable
        
        Educational:
            - all=False matches 'docker ps' behavior
            - all=True matches 'docker ps -a'
            - Filtering by labels enables environment segregation
            - Returns simplified data structure for API consumption
        """
        try:
            client = get_docker_client()
            
            # Build filters
            filters = {}
            if environment:
                # Filter by environment label
                filters['label'] = f'dockermate.environment={environment}'
            
            # Get containers from Docker
            containers = client.containers.list(all=all, filters=filters)
            
            logger.info(f"Listed {len(containers)} containers (all={all}, environment={environment})")
            
            # Convert to dictionaries
            return [self._container_to_dict(container) for container in containers]
            
        except Exception as e:
            logger.error(f"Error listing containers: {e}")
            raise
    
    @docker_operation
    def get_container(self, container_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific container.
        
        Args:
            container_id: Container ID or name
        
        Returns:
            Dictionary with container details
        
        Raises:
            ContainerNotFoundError: If container doesn't exist
            DockerConnectionError: If Docker daemon is unreachable
        
        Educational:
            - Can use ID or name (Docker SDK handles both)
            - Returns more detail than list_containers()
            - Includes mounts, networks, environment variables
        """
        try:
            client = get_docker_client()
            container = client.containers.get(container_id)
            
            logger.debug(f"Retrieved container: {container.name}")
            
            # Return detailed dict
            return self._container_to_dict_detailed(container)
            
        except NotFound:
            logger.warning(f"Container not found: {container_id}")
            raise ContainerNotFoundError(f"Container '{container_id}' not found")
        except Exception as e:
            logger.error(f"Error getting container {container_id}: {e}")
            raise
    
    @docker_operation
    def start_container(self, container_id: str) -> Dict[str, Any]:
        """
        Start a stopped container.
        
        Args:
            container_id: Container ID or name
        
        Returns:
            Updated container dictionary
        
        Raises:
            ContainerNotFoundError: If container doesn't exist
            ContainerOperationError: If start fails (e.g., already running)
            DockerConnectionError: If Docker daemon is unreachable
        
        Educational:
            - Idempotent: Starting running container succeeds
            - Docker handles port conflicts, network setup
            - Returns immediately (doesn't wait for healthy)
        """
        try:
            client = get_docker_client()
            container = client.containers.get(container_id)
            
            # Check current state
            container.reload()  # Refresh status
            if container.status == 'running':
                logger.info(f"Container {container.name} already running")
                return self._container_to_dict(container)
            
            # Start container
            logger.info(f"Starting container: {container.name}")
            container.start()
            container.reload()  # Refresh to get new status
            
            logger.info(f"Container {container.name} started successfully")
            return self._container_to_dict(container)
            
        except NotFound:
            logger.warning(f"Container not found: {container_id}")
            raise ContainerNotFoundError(f"Container '{container_id}' not found")
        except APIError as e:
            logger.error(f"Failed to start container {container_id}: {e}")
            raise ContainerOperationError(f"Failed to start container: {e}")
        except Exception as e:
            logger.error(f"Error starting container {container_id}: {e}")
            raise
    
    @docker_operation
    def stop_container(self, container_id: str, timeout: int = 10) -> Dict[str, Any]:
        """
        Stop a running container gracefully.
        
        Args:
            container_id: Container ID or name
            timeout: Seconds to wait before force-killing (default: 10)
        
        Returns:
            Updated container dictionary
        
        Raises:
            ContainerNotFoundError: If container doesn't exist
            ContainerOperationError: If stop fails
            DockerConnectionError: If Docker daemon is unreachable
        
        Educational:
            - Graceful stop sends SIGTERM, waits, then SIGKILL
            - timeout gives app time to clean up (flush buffers, close connections)
            - 10 seconds is reasonable for most containers
            - Stopping stopped container succeeds (idempotent)
        """
        try:
            client = get_docker_client()
            container = client.containers.get(container_id)
            
            # Check current state
            container.reload()
            if container.status != 'running':
                logger.info(f"Container {container.name} not running (status: {container.status})")
                return self._container_to_dict(container)
            
            # Stop container
            logger.info(f"Stopping container: {container.name} (timeout: {timeout}s)")
            container.stop(timeout=timeout)
            container.reload()  # Refresh to get new status
            
            logger.info(f"Container {container.name} stopped successfully")
            return self._container_to_dict(container)
            
        except NotFound:
            logger.warning(f"Container not found: {container_id}")
            raise ContainerNotFoundError(f"Container '{container_id}' not found")
        except APIError as e:
            logger.error(f"Failed to stop container {container_id}: {e}")
            raise ContainerOperationError(f"Failed to stop container: {e}")
        except Exception as e:
            logger.error(f"Error stopping container {container_id}: {e}")
            raise
    
    @docker_operation
    def restart_container(self, container_id: str, timeout: int = 10) -> Dict[str, Any]:
        """
        Restart a container (stop then start).
        
        Args:
            container_id: Container ID or name
            timeout: Seconds to wait before force-killing during stop
        
        Returns:
            Updated container dictionary
        
        Raises:
            ContainerNotFoundError: If container doesn't exist
            ContainerOperationError: If restart fails
            DockerConnectionError: If Docker daemon is unreachable
        
        Educational:
            - Equivalent to stop + start
            - Useful for reloading configuration
            - Network connections reset, volumes persist
        """
        try:
            client = get_docker_client()
            container = client.containers.get(container_id)
            
            logger.info(f"Restarting container: {container.name} (timeout: {timeout}s)")
            container.restart(timeout=timeout)
            container.reload()  # Refresh to get new status
            
            logger.info(f"Container {container.name} restarted successfully")
            return self._container_to_dict(container)
            
        except NotFound:
            logger.warning(f"Container not found: {container_id}")
            raise ContainerNotFoundError(f"Container '{container_id}' not found")
        except APIError as e:
            logger.error(f"Failed to restart container {container_id}: {e}")
            raise ContainerOperationError(f"Failed to restart container: {e}")
        except Exception as e:
            logger.error(f"Error restarting container {container_id}: {e}")
            raise
    
    @docker_operation
    def remove_container(self, container_id: str, force: bool = False, volumes: bool = False) -> bool:
        """
        Remove a container.
        
        Args:
            container_id: Container ID or name
            force: If True, force remove even if running
            volumes: If True, remove associated anonymous volumes
        
        Returns:
            True if removed successfully
        
        Raises:
            ContainerNotFoundError: If container doesn't exist
            ContainerOperationError: If remove fails (e.g., container running and force=False)
            DockerConnectionError: If Docker daemon is unreachable
        
        Educational:
            - force=True needed to remove running containers
            - volumes=True removes anonymous volumes only (not named volumes)
            - Named volumes and bind mounts are preserved
            - Removal is permanent - no undo
        """
        try:
            client = get_docker_client()
            container = client.containers.get(container_id)
            
            container_name = container.name
            container_status = container.status
            
            logger.info(f"Removing container: {container_name} (force={force}, volumes={volumes})")
            
            # Warn if trying to remove running container without force
            if container_status == 'running' and not force:
                raise ContainerOperationError(
                    f"Cannot remove running container '{container_name}'. "
                    f"Stop it first or use force=True"
                )
            
            # Remove container
            container.remove(force=force, v=volumes)
            
            logger.info(f"Container {container_name} removed successfully")
            return True
            
        except NotFound:
            logger.warning(f"Container not found: {container_id}")
            raise ContainerNotFoundError(f"Container '{container_id}' not found")
        except APIError as e:
            logger.error(f"Failed to remove container {container_id}: {e}")
            raise ContainerOperationError(f"Failed to remove container: {e}")
        except Exception as e:
            logger.error(f"Error removing container {container_id}: {e}")
            raise
    
    @docker_operation
    def get_container_logs(self, container_id: str, tail: int = 100, since: Optional[str] = None) -> str:
        """
        Get container logs.
        
        Args:
            container_id: Container ID or name
            tail: Number of lines from end of logs (default: 100)
            since: Unix timestamp or datetime string to get logs after
        
        Returns:
            Log text as string
        
        Raises:
            ContainerNotFoundError: If container doesn't exist
            DockerConnectionError: If Docker daemon is unreachable
        
        Educational:
            - Logs are from STDOUT and STDERR of container's main process
            - tail=100 prevents overwhelming response
            - since parameter useful for log streaming
            - Logs persist after container stops (until removed)
        """
        try:
            client = get_docker_client()
            container = client.containers.get(container_id)
            
            logger.debug(f"Getting logs for container: {container.name} (tail={tail})")
            
            # Get logs
            logs = container.logs(tail=tail, since=since, timestamps=True)
            
            # Decode bytes to string
            return logs.decode('utf-8')
            
        except NotFound:
            logger.warning(f"Container not found: {container_id}")
            raise ContainerNotFoundError(f"Container '{container_id}' not found")
        except Exception as e:
            logger.error(f"Error getting logs for container {container_id}: {e}")
            raise
    
    @docker_operation
    def get_container_stats(self, container_id: str) -> Dict[str, Any]:
        """
        Get real-time resource usage stats.
        
        Args:
            container_id: Container ID or name
        
        Returns:
            Dictionary with CPU, memory, network, and I/O stats
        
        Raises:
            ContainerNotFoundError: If container doesn't exist
            DockerConnectionError: If Docker daemon is unreachable
        
        Educational:
            - stats() returns generator, we get one snapshot with stream=False
            - CPU percentage calculated from nanoseconds
            - Memory includes cache, buffer, RSS
            - Useful for health monitoring and alerts
        """
        try:
            client = get_docker_client()
            container = client.containers.get(container_id)
            
            logger.debug(f"Getting stats for container: {container.name}")
            
            # Get one stats snapshot (stream=False)
            stats = container.stats(stream=False)
            
            # Extract key metrics
            return self._parse_stats(stats)
            
        except NotFound:
            logger.warning(f"Container not found: {container_id}")
            raise ContainerNotFoundError(f"Container '{container_id}' not found")
        except Exception as e:
            logger.error(f"Error getting stats for container {container_id}: {e}")
            raise
    
    # ========================================
    # Helper Methods (Data Transformation)
    # ========================================
    
    def _container_to_dict(self, container) -> Dict[str, Any]:
        """
        Convert Docker container object to simplified dictionary.
        
        Used by list operations for quick overview.
        
        Educational:
            - Extracts only essential info for list views
            - Standardized format for API responses
            - Avoids exposing entire Docker SDK object
        """
        return {
            'id': container.id[:12],  # Short ID (first 12 chars)
            'name': container.name,
            'image': container.image.tags[0] if container.image.tags else container.image.id[:12],
            'status': container.status,
            'state': container.attrs.get('State', {}).get('Status', 'unknown'),
            'created': container.attrs.get('Created', ''),
            'ports': self._extract_ports(container),
            'labels': container.labels,
        }
    
    def _container_to_dict_detailed(self, container) -> Dict[str, Any]:
        """
        Convert Docker container object to detailed dictionary.
        
        Used by get operations for full container details.
        
        Educational:
            - Includes everything from _container_to_dict() plus more
            - Environment variables, mounts, networks
            - Full configuration for display or export
        """
        base = self._container_to_dict(container)
        
        # Add detailed information
        base.update({
            'full_id': container.id,
            'environment': container.attrs.get('Config', {}).get('Env', []),
            'command': container.attrs.get('Config', {}).get('Cmd', []),
            'entrypoint': container.attrs.get('Config', {}).get('Entrypoint', []),
            'hostname': container.attrs.get('Config', {}).get('Hostname', ''),
            'mounts': self._extract_mounts(container),
            'networks': self._extract_networks(container),
            'restart_policy': container.attrs.get('HostConfig', {}).get('RestartPolicy', {}),
            'restart_count': container.attrs.get('RestartCount', 0),
        })
        
        return base
    
    def _extract_ports(self, container) -> Dict[str, str]:
        """
        Extract port mappings in human-readable format.
        
        Example: {'80/tcp': '0.0.0.0:8080'}
        """
        ports = {}
        port_bindings = container.attrs.get('NetworkSettings', {}).get('Ports', {})
        
        for container_port, host_bindings in port_bindings.items():
            if host_bindings:
                # Format: 0.0.0.0:8080
                host_ip = host_bindings[0].get('HostIp', '0.0.0.0')
                host_port = host_bindings[0].get('HostPort', '')
                ports[container_port] = f"{host_ip}:{host_port}"
        
        return ports
    
    def _extract_mounts(self, container) -> List[Dict[str, str]]:
        """
        Extract volume/bind mount information.
        
        Returns list of mount dictionaries with source, destination, mode.
        """
        mounts = []
        for mount in container.attrs.get('Mounts', []):
            mounts.append({
                'type': mount.get('Type', ''),
                'source': mount.get('Source', ''),
                'destination': mount.get('Destination', ''),
                'mode': mount.get('Mode', ''),
                'rw': mount.get('RW', True),
            })
        return mounts
    
    def _extract_networks(self, container) -> Dict[str, Dict[str, str]]:
        """
        Extract network information.
        
        Returns dict with network name as key, network details as value.
        """
        networks = {}
        network_settings = container.attrs.get('NetworkSettings', {}).get('Networks', {})
        
        for network_name, network_info in network_settings.items():
            networks[network_name] = {
                'ip_address': network_info.get('IPAddress', ''),
                'gateway': network_info.get('Gateway', ''),
                'mac_address': network_info.get('MacAddress', ''),
            }
        
        return networks
    
    def _parse_stats(self, stats: Dict) -> Dict[str, Any]:
        """
        Parse Docker stats into human-readable metrics.
        
        Educational:
            - CPU calculation: delta_cpu / delta_system * num_cpus * 100
            - Memory includes cached pages that can be reclaimed
            - Network stats are cumulative since container start
        """
        # CPU percentage calculation
        cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                    stats['precpu_stats']['cpu_usage']['total_usage']
        system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                      stats['precpu_stats']['system_cpu_usage']
        num_cpus = stats['cpu_stats'].get('online_cpus', 1)
        
        cpu_percent = 0.0
        if system_delta > 0 and cpu_delta > 0:
            cpu_percent = (cpu_delta / system_delta) * num_cpus * 100.0
        
        # Memory stats
        memory_stats = stats['memory_stats']
        memory_usage = memory_stats.get('usage', 0)
        memory_limit = memory_stats.get('limit', 0)
        memory_percent = 0.0
        if memory_limit > 0:
            memory_percent = (memory_usage / memory_limit) * 100.0
        
        return {
            'cpu_percent': round(cpu_percent, 2),
            'memory_usage_mb': round(memory_usage / (1024 * 1024), 2),
            'memory_limit_mb': round(memory_limit / (1024 * 1024), 2),
            'memory_percent': round(memory_percent, 2),
            'network_rx_bytes': stats['networks'].get('eth0', {}).get('rx_bytes', 0),
            'network_tx_bytes': stats['networks'].get('eth0', {}).get('tx_bytes', 0),
        }
