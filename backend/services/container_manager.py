"""
DockerMate - Container Manager Service (Sprint 2 Task 4 + Task 7 Fixes)
=========================================================================

High-level service layer for container lifecycle management with:
- CRUD operations (create, read, update, delete)
- Lifecycle controls (start, stop, restart)
- Hardware-aware validation and limits enforcement
- Non-blocking health validation (async polling)
- Database state synchronization with full metadata extraction
- Comprehensive error handling

TASK 7 FIXES:
- Issue 3: Fixed _sync_database_state() to extract ports/volumes/env_vars
- Issue 4: Added get_container_health() for async health polling
- Removed blocking health validation from create_container()

Usage:
    from backend.services.container_manager import ContainerManager
    
    manager = ContainerManager()
    
    # Create container (returns immediately)
    container = manager.create_container(
        name='my-nginx',
        image='nginx:latest',
        environment='prod',
        auto_start=True,
        pull_if_missing=True
    )
    
    # Poll health status (non-blocking)
    health = manager.get_container_health('my-nginx')
    
    # Lifecycle operations
    manager.start_container('my-nginx')
    manager.stop_container('my-nginx')
    manager.restart_container('my-nginx')
    manager.delete_container('my-nginx', force=False)
    
    # Query operations
    containers = manager.list_containers(environment='prod', state='running')
    container = manager.get_container('my-nginx')
    
    # Update operations (Phase 1: labels only)
    manager.update_container('my-nginx', labels={'version': '1.2.0'})

Educational Notes:
- Service layer pattern separates business logic from API routes
- Hardware limits enforced via HostConfig from Task 1
- Docker SDK integration via DockerClient from Task 2
- Database persistence via Container model from Task 3
- Non-blocking health checks teach async monitoring patterns
- Error handling with custom exceptions for clear API responses
"""

import logging
import json
from typing import List, Dict, Optional, Any
from datetime import datetime

from sqlalchemy.orm import Session
from docker.errors import NotFound, APIError, ImageNotFound

from backend.utils.docker_client import get_docker_client, docker_operation
from backend.utils.exceptions import (
    ContainerNotFoundError,
    ContainerOperationError,
    DockerConnectionError,
    ValidationError
)
from backend.models.database import SessionLocal
from backend.models.container import Container
from backend.models.host_config import HostConfig

# Configure logging
logger = logging.getLogger(__name__)


class ContainerManager:
    """
    Service class for container lifecycle management.
    
    Provides high-level operations for container CRUD, lifecycle control,
    and validation. Enforces hardware limits and maintains database state.
    
    Design Principles:
    - Hardware-aware: Enforces limits based on detected profile
    - Database-backed: Syncs container state to SQLite
    - Fail-fast: Validates before Docker operations
    - Educational: Shows CLI equivalents for learning
    
    Phase 1 Implementation (Task 4):
    - Full CRUD operations
    - Lifecycle controls (start/stop/restart)
    - Labels-only updates (non-destructive)
    - Non-blocking health validation
    
    Phase 2 (Task 6):
    - Full update via recreate workflow
    - Port conflict detection
    - Advanced volume validation
    """
    
    def __init__(self, db: Optional[Session] = None):
        """
        Initialize ContainerManager.
        
        Args:
            db: Database session (optional, creates new if not provided)
        
        Educational:
            - Dependency injection allows testing with mock database
            - Default session creation for convenience in production
        """
        self.db = db or SessionLocal()
        self._owns_session = db is None
        
        # Cache host config for hardware limits
        self._host_config = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup database session if we own it."""
        if self._owns_session and self.db:
            self.db.close()
    
    def _get_host_config(self) -> HostConfig:
        """
        Get or cache host configuration for hardware limits.
        
        Returns:
            HostConfig: Hardware profile configuration
        
        Educational:
            - Lazy loading: Only fetches when needed
            - Caching: Avoids repeated database queries
            - Singleton pattern: HostConfig has single row (id=1)
        """
        if self._host_config is None:
            self._host_config = HostConfig.get_or_create(self.db)
        return self._host_config
    
    # =========================================================================
    # CREATE OPERATION
    # =========================================================================
    
    @docker_operation
    def create_container(
        self,
        name: str,
        image: str,
        environment: Optional[str] = None,
        ports: Optional[Dict[str, int]] = None,
        volumes: Optional[Dict[str, Dict[str, str]]] = None,
        env_vars: Optional[Dict[str, str]] = None,
        labels: Optional[Dict[str, str]] = None,
        restart_policy: str = 'no',
        auto_start: bool = True,
        pull_if_missing: bool = True,
        cpu_limit: Optional[float] = None,
        memory_limit: Optional[int] = None,
        network: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new container with validation and optional auto-start.
        
        TASK 7 FIX: Removed blocking health validation - now handled by
        async polling via get_container_health() endpoint.
        
        This is the primary container creation method. It:
        1. Validates creation request (name, hardware limits, etc.)
        2. Pulls image if missing and pull_if_missing=True
        3. Creates container via Docker SDK
        4. Auto-starts container if auto_start=True
        5. Syncs state to database with full metadata
        6. Returns immediately (no blocking health check)
        
        Args:
            name: Container name (must be unique)
            image: Docker image (e.g., 'nginx:latest')
            environment: Environment tag (e.g., 'dev', 'prod')
            ports: Port mappings {container_port: host_port}
            volumes: Volume mounts {host_path: {'bind': container_path, 'mode': 'rw'}}
            env_vars: Environment variables {key: value}
            labels: Container labels {key: value}
            restart_policy: Restart policy ('no', 'always', 'on-failure', 'unless-stopped')
            auto_start: Start container after creation (default: True)
            pull_if_missing: Pull image if not found locally (default: True)
            cpu_limit: CPU limit (cores, e.g., 1.5)
            memory_limit: Memory limit (bytes)
        
        Returns:
            dict: Container details including:
                - id: Docker container ID
                - name: Container name
                - state: Current state
                - ports: Port mappings (if any)
                - volumes: Volume mounts (if any)
                - env_vars: Environment variables (if any)
                - created_at: Creation timestamp
                - health_check_pending: True if auto_start enabled
        
        Raises:
            ValidationError: Invalid input or hardware limit exceeded
            ContainerOperationError: Docker operation failed
            DockerConnectionError: Cannot connect to Docker daemon
        
        Educational:
            - CLI equivalent: docker run [options] image
            - Auto-start matches Docker CLI default behavior
            - Returns immediately for better UX
            - Health check handled via separate polling endpoint
        """
        logger.info(f"Creating container: {name} from image: {image}")
        
        # Step 1: Validation
        self._validate_create_request(name, image, restart_policy)
        self._check_hardware_limits(cpu_limit, memory_limit)
        
        # Step 2: Get Docker client
        client = get_docker_client()
        
        # Step 3: Check image availability
        try:
            client.images.get(image)
            logger.debug(f"Image found locally: {image}")
        except ImageNotFound:
            if pull_if_missing:
                logger.info(f"Pulling image: {image}")
                try:
                    client.images.pull(image)
                    logger.info(f"Successfully pulled image: {image}")
                except Exception as e:
                    raise ContainerOperationError(
                        f"Failed to pull image {image}: {e}"
                    )
            else:
                raise ValidationError(
                    f"Image '{image}' not found locally. Set pull_if_missing=True to auto-pull."
                )
        
        # Step 4: Check name uniqueness
        try:
            existing = client.containers.get(name)
            raise ValidationError(
                f"Container with name '{name}' already exists (ID: {existing.short_id})"
            )
        except NotFound:
            pass  # Good - name is unique
        
        # Step 5: Prepare container configuration
        # Add DockerMate management labels
        docker_labels = labels or {}
        docker_labels['com.dockermate.managed'] = 'true'
        docker_labels['com.dockermate.version'] = '0.1.0'
        docker_labels['com.dockermate.created_at'] = datetime.now().isoformat()
        if environment:
            docker_labels['com.dockermate.environment'] = environment

        container_config = {
            'name': name,
            'image': image,
            'detach': True,
            'labels': docker_labels,
            'environment': env_vars or {},
        }
        
        # Add port mappings (format: {'80/tcp': 8080})
        if ports:
            container_config['ports'] = ports
        
        # Add volume mounts (format: {'/host': {'bind': '/container', 'mode': 'rw'}})
        if volumes:
            container_config['volumes'] = volumes
        
        # Add restart policy (direct parameter, not nested in host_config)
        if restart_policy and restart_policy != 'no':
            restart_config = self._build_restart_policy(restart_policy)
            container_config['restart_policy'] = restart_config
        
        # Add resource limits (use correct Docker SDK parameter names)
        if cpu_limit:
            # CPU limit in nano CPUs (1.0 = 1e9 nano CPUs)
            container_config['nano_cpus'] = int(cpu_limit * 1e9)
        
        if memory_limit:
            # Memory limit in bytes
            container_config['mem_limit'] = memory_limit

        if network:
            container_config['network'] = network

        # Step 6: Create container
        try:
            docker_container = client.containers.create(**container_config)
            logger.info(f"Container created: {name} (ID: {docker_container.short_id})")
        except APIError as e:
            raise ContainerOperationError(
                f"Failed to create container {name}: {e.explanation}"
            )
        
        # Step 7: Auto-start if requested
        if auto_start:
            try:
                docker_container.start()
                logger.info(f"Container started: {name}")
            except APIError as e:
                logger.error(f"Failed to start container {name}: {e}")
                # Container created but failed to start - still sync to DB
        
        # Step 8: Sync to database with full metadata extraction
        container_data = self._sync_database_state(docker_container, environment)
        
        # Step 9: Add flag for frontend health polling
        if auto_start:
            container_data['health_check_pending'] = True
            container_data['health_check_started_at'] = datetime.utcnow().isoformat()
        
        logger.info(f"Container creation complete: {name}")
        return container_data
    
    def _validate_create_request(self, name: str, image: str, restart_policy: str):
        """
        Validate container creation request.
        
        Args:
            name: Container name
            image: Docker image name
            restart_policy: Restart policy
        
        Raises:
            ValidationError: If validation fails
        
        Educational:
            - Fail-fast validation prevents wasted Docker API calls
            - Clear error messages help users fix issues quickly
            - Validates format and business rules
        """
        # Validate name format
        if not name or not name.strip():
            raise ValidationError("Container name cannot be empty")
        
        if len(name) > 255:
            raise ValidationError("Container name must be 255 characters or less")
        
        # Validate image format
        if not image or not image.strip():
            raise ValidationError("Image name cannot be empty")
        
        # Validate restart policy
        valid_policies = ['no', 'on-failure', 'always', 'unless-stopped']
        if restart_policy and restart_policy not in valid_policies:
            raise ValidationError(
                f"Invalid restart policy: {restart_policy}. "
                f"Must be one of: {', '.join(valid_policies)}"
            )
    
    def _check_hardware_limits(self, cpu_limit: Optional[float], memory_limit: Optional[int]):
        """
        Validate resource limits against hardware profile.
        
        Args:
            cpu_limit: Requested CPU cores
            memory_limit: Requested memory in bytes
        
        Raises:
            ValidationError: If limits exceed hardware capacity
        
        Educational:
            - Prevents resource exhaustion on home lab hardware
            - Teaches importance of resource management
            - Shows how to calculate available resources
        """
        host_config = self._get_host_config()

        if cpu_limit:
            # Use total system CPU cores as the limit
            max_cpu = host_config.cpu_cores
            if cpu_limit > max_cpu:
                raise ValidationError(
                    f"CPU limit {cpu_limit} cores exceeds system total of {max_cpu} cores "
                    f"(hardware profile: '{host_config.profile_name}')"
                )

        if memory_limit:
            # Convert total RAM from GB to bytes
            max_memory = int(host_config.ram_gb * 1024 * 1024 * 1024)  # GB to bytes
            if memory_limit > max_memory:
                memory_mb = memory_limit / (1024 * 1024)
                max_mb = int(host_config.ram_gb * 1024)  # GB to MB
                raise ValidationError(
                    f"Memory limit {memory_mb:.0f}MB exceeds system total of {max_mb}MB "
                    f"(hardware profile: '{host_config.profile_name}')"
                )
    
    def _build_restart_policy(self, policy: str) -> Dict[str, Any]:
        """
        Build restart policy configuration for Docker SDK.
        
        Args:
            policy: Restart policy name
        
        Returns:
            dict: Restart policy configuration
        
        Educational:
            - Docker SDK requires specific format for restart policies
            - 'on-failure' allows optional MaximumRetryCount
            - Different from CLI flags (--restart)
        """
        if policy == 'on-failure':
            return {'Name': 'on-failure', 'MaximumRetryCount': 5}
        else:
            return {'Name': policy}
    
    # =========================================================================
    # HEALTH CHECK (NON-BLOCKING)
    # =========================================================================
    
    def get_container_health(self, name_or_id: str) -> Dict[str, Any]:
        """
        Get immediate container health status (non-blocking).
        
        TASK 7 FIX: New method for async health polling by frontend.
        Replaces blocking _validate_health_status() in create_container().
        
        Used by frontend polling to check post-creation health.
        Returns current state without waiting.
        
        Args:
            name_or_id: Container name or ID
        
        Returns:
            dict: Health status {
                'healthy': bool,
                'running': bool,
                'status': str,
                'exit_code': int or None,
                'error': str or None,
                'health': str or None,
                'uptime_seconds': int or None
            }
        
        Raises:
            ContainerNotFoundError: Container doesn't exist
            ContainerOperationError: Docker operation failed
        
        Educational:
            - Shows real-time container state
            - Teaches difference between "started" vs "healthy"
            - Helps debug configuration issues
            - Demonstrates async monitoring patterns
            - CLI equivalent: docker inspect <container> | jq '.State'
        """
        logger.debug(f"Checking health for container: {name_or_id}")
        
        # Get container from database
        container = self.db.query(Container).filter(
            (Container.name == name_or_id) |
            (Container.container_id == name_or_id),
            Container.state != 'removed'
        ).first()
        
        if not container:
            raise ContainerNotFoundError(f"Container '{name_or_id}' not found")
        
        # Get Docker container
        client = get_docker_client()
        try:
            docker_container = client.containers.get(container.container_id)
            docker_container.reload()  # Get latest state
            
            # Extract status information
            status = docker_container.status
            attrs = docker_container.attrs
            state = attrs.get('State', {})
            
            # Calculate uptime if running
            uptime_seconds = None
            if state.get('Running') and state.get('StartedAt'):
                try:
                    started_at = datetime.fromisoformat(state.get('StartedAt').rstrip('Z'))
                    uptime_seconds = int((datetime.utcnow() - started_at).total_seconds())
                except Exception as e:
                    logger.warning(f"Failed to calculate uptime: {e}")
            
            health_status = {
                'healthy': status == 'running' and state.get('ExitCode', 0) == 0,
                'running': status == 'running',
                'status': status,
                'exit_code': state.get('ExitCode'),
                'error': state.get('Error'),
                'health': None,
                'uptime_seconds': uptime_seconds
            }
            
            # Check for health check status (if configured in image)
            health = state.get('Health', {})
            if health:
                health_status['health'] = health.get('Status', 'none')
                # Override healthy flag if health check exists
                if health.get('Status') in ['healthy', 'starting']:
                    health_status['healthy'] = health.get('Status') == 'healthy'
                elif health.get('Status') in ['unhealthy']:
                    health_status['healthy'] = False
            
            return health_status
            
        except NotFound:
            raise ContainerNotFoundError(
                f"Container '{name_or_id}' not found in Docker daemon"
            )
        except APIError as e:
            raise ContainerOperationError(
                f"Failed to check container health: {e.explanation}"
            )
    
    def _sync_database_state(
        self,
        docker_container,
        environment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sync Docker container state to database.
        
        TASK 7 FIX: Now extracts full metadata (ports, volumes, env_vars).
        
        Creates or updates Container record in database with current
        state from Docker daemon, including complete configuration metadata.
        
        Args:
            docker_container: Docker SDK container object
            environment: Environment tag override
        
        Returns:
            dict: Container data dictionary with full metadata
        
        Educational:
            - Database keeps metadata even when container is removed
            - Enables filtering and searching without Docker queries
            - Timestamps track lifecycle events
            - Structured data allows UI display without parsing
        """
        attrs = docker_container.attrs
        config = attrs.get('Config', {})
        state = attrs.get('State', {})
        network_settings = attrs.get('NetworkSettings', {})
        
        # TASK 7 FIX: Extract port mappings from Docker
        ports_list = []
        port_bindings = network_settings.get('Ports', {})
        seen_ports = set()  # Track to avoid IPv4/IPv6 duplicates

        for container_port, host_bindings in port_bindings.items():
            if host_bindings:
                # Parse protocol from container_port (e.g., "80/tcp" -> port=80, protocol=tcp)
                port_parts = container_port.split('/')
                port_num = port_parts[0]
                protocol = port_parts[1] if len(port_parts) > 1 else 'tcp'

                for binding in host_bindings:
                    host_port = binding.get('HostPort', '')
                    # Create unique key to avoid duplicates (IPv4 and IPv6 both map to same port)
                    port_key = f"{port_num}/{protocol}:{host_port}"

                    if port_key not in seen_ports:
                        seen_ports.add(port_key)
                        ports_list.append({
                            'container': port_num,  # Just the port number
                            'host': host_port,
                            'protocol': protocol,  # Protocol as separate field
                            'host_ip': binding.get('HostIp', '0.0.0.0')
                        })
        
        # TASK 7 FIX: Extract volume mounts from Docker
        volumes_list = []
        for mount in attrs.get('Mounts', []):
            volumes_list.append({
                'source': mount.get('Source', ''),
                'destination': mount.get('Destination', ''),
                'mode': mount.get('Mode', ''),
                'type': mount.get('Type', ''),
                'rw': mount.get('RW', True)
            })
        
        # TASK 7 FIX: Extract environment variables from Docker
        env_vars_list = config.get('Env', [])

        # Extract resource limits from Docker
        host_config = attrs.get('HostConfig', {})
        nano_cpus = host_config.get('NanoCpus', 0)
        cpu_limit = nano_cpus / 1e9 if nano_cpus else None  # Convert nano CPUs to cores
        memory_limit = host_config.get('Memory', 0) or None  # Bytes

        # Check if container already exists in database
        existing = self.db.query(Container).filter(
            Container.container_id == docker_container.id
        ).first()
        
        if existing:
            # Update existing record
            existing.name = docker_container.name.lstrip('/')
            existing.state = docker_container.status
            existing.image_name = config.get('Image', '')
            existing.restart_policy = attrs.get('HostConfig', {}).get(
                'RestartPolicy', {}
            ).get('Name', 'no')
            existing.ports_json = json.dumps(ports_list)  # TASK 7 FIX: Store ports
            existing.cpu_limit = cpu_limit  # Store resource limits
            existing.memory_limit = memory_limit
            existing.updated_at = datetime.utcnow()
            
            # Update timestamps based on state
            if state.get('Running'):
                if not existing.started_at or state.get('StartedAt'):
                    try:
                        existing.started_at = datetime.fromisoformat(
                            state.get('StartedAt', '').rstrip('Z')
                        )
                    except Exception:
                        existing.started_at = datetime.utcnow()
            elif state.get('Status') in ['exited', 'dead']:
                if state.get('FinishedAt'):
                    try:
                        existing.stopped_at = datetime.fromisoformat(
                            state.get('FinishedAt', '').rstrip('Z')
                        )
                    except Exception:
                        pass
            
            container_record = existing
        else:
            # Create new record
            created_at = datetime.utcnow()
            if attrs.get('Created'):
                try:
                    created_at = datetime.fromisoformat(attrs.get('Created').rstrip('Z'))
                except Exception:
                    pass
            
            container_record = Container(
                container_id=docker_container.id,
                name=docker_container.name.lstrip('/'),
                state=docker_container.status,
                environment=environment,
                image_name=config.get('Image', ''),
                restart_policy=attrs.get('HostConfig', {}).get(
                    'RestartPolicy', {}
                ).get('Name', 'no'),
                ports_json=json.dumps(ports_list),  # TASK 7 FIX: Store ports
                cpu_limit=cpu_limit,  # Store resource limits
                memory_limit=memory_limit,
                auto_start=False,  # Will be set by API if needed
                created_at=created_at
            )
            
            # Set started_at if running
            if state.get('Running') and state.get('StartedAt'):
                try:
                    container_record.started_at = datetime.fromisoformat(
                        state.get('StartedAt', '').rstrip('Z')
                    )
                except Exception:
                    pass
            
            self.db.add(container_record)
        
        self.db.commit()
        self.db.refresh(container_record)
        
        # TASK 7 FIX: Return dict with additional runtime metadata
        result = container_record.to_dict()
        result['ports'] = ports_list
        result['volumes'] = volumes_list
        result['env_vars'] = env_vars_list
        
        return result
    
    # =========================================================================
    # READ OPERATIONS
    # =========================================================================
    
    def get_container(self, name_or_id: str) -> Dict[str, Any]:
        """
        Get single container by name or ID.
        
        Args:
            name_or_id: Container name or Docker ID
        
        Returns:
            dict: Container details with full metadata
        
        Raises:
            ContainerNotFoundError: Container doesn't exist
        
        Educational:
            - Queries both database and Docker daemon
            - Returns merged state (DB metadata + Docker runtime)
            - CLI equivalent: docker inspect <container>
        """
        logger.debug(f"Getting container: {name_or_id}")
        
        # Try database first (faster)
        container = self.db.query(Container).filter(
            (Container.name == name_or_id) |
            (Container.container_id == name_or_id),
            Container.state != 'removed'
        ).first()
        
        if not container:
            raise ContainerNotFoundError(
                f"Container '{name_or_id}' not found in database"
            )
        
        # Get live state from Docker
        try:
            client = get_docker_client()
            docker_container = client.containers.get(container.container_id)
            
            # Update database with live state (includes full metadata)
            return self._sync_database_state(docker_container, container.environment)
            
        except NotFound:
            # Container exists in DB but not in Docker (was removed externally)
            logger.warning(
                f"Container {name_or_id} in database but not in Docker daemon"
            )
            container.state = 'removed'
            self.db.commit()
            return container.to_dict()
    
    def list_containers(
        self,
        all: bool = True,
        environment: Optional[str] = None,
        state: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List containers with optional filtering.
        
        Args:
            all: If True, include stopped containers
            environment: Filter by environment tag
            state: Filter by state (running, exited, etc.)
        
        Returns:
            list: List of container dictionaries
        
        Educational:
            - Database query is faster than Docker API for lists
            - Filters applied at database level (efficient)
            - CLI equivalent: docker ps -a --filter name=X
        """
        logger.debug(f"Listing containers: all={all}, env={environment}, state={state}")
        
        # Build query with filters
        query = self.db.query(Container).filter(Container.state != 'removed')
        
        if not all:
            query = query.filter(Container.state == 'running')
        
        if environment:
            query = query.filter(Container.environment == environment)
        
        if state:
            query = query.filter(Container.state == state)
        
        containers = query.all()
        
        # Convert to dicts and sync with Docker for live state
        result = []
        client = get_docker_client()
        
        for container in containers:
            try:
                docker_container = client.containers.get(container.container_id)
                # Sync updates database and returns full metadata
                result.append(self._sync_database_state(docker_container, container.environment))
            except NotFound:
                # Container removed externally
                container.state = 'removed'
                self.db.commit()
            except Exception as e:
                # Other errors - return stale data
                logger.warning(f"Failed to sync container {container.name}: {e}")
                result.append(container.to_dict())
        
        return result

    def list_all_docker_containers(
        self,
        all: bool = True,
        environment: Optional[str] = None,
        managed_only: bool = False,
        unmanaged_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        List ALL containers from Docker daemon, not just DockerMate-managed.

        FEATURE-005: Shows both managed and external containers with distinction.

        This method queries Docker directly for all containers and cross-references
        with the database to identify which are managed by DockerMate.

        DockerMate's own container is shown as EXTERNAL (no action buttons) which
        protects it from accidental damage while keeping UI simple (KISS principle).

        Args:
            all: If True, include stopped containers (default: True)
            environment: Filter by environment tag (only for managed containers)
            managed_only: If True, only show DockerMate-managed containers
            unmanaged_only: If True, only show external containers

        Returns:
            list: List of container dictionaries with 'managed' flag

        Educational:
            - Queries Docker daemon for all containers on host
            - Cross-references with database to identify managed containers
            - DockerMate container appears as external (protected from actions)
            - Shows both managed and external containers with distinction
            - CLI equivalent: docker ps -a
        """
        logger.debug(f"Listing all Docker containers: all={all}, env={environment}")

        client = get_docker_client()

        # Get all containers from Docker daemon
        docker_containers = client.containers.list(all=all)

        # Get managed container IDs from database
        managed_ids = {c.container_id for c in self.db.query(Container).all()}

        result = []
        for docker_container in docker_containers:
            # KISS: Show ALL containers including DockerMate
            # DockerMate will appear as external (no action buttons = protected)

            container_id = docker_container.id
            is_managed = container_id in managed_ids

            # Apply managed/unmanaged filter
            if managed_only and not is_managed:
                continue
            if unmanaged_only and is_managed:
                continue

            # Build basic container data
            attrs = docker_container.attrs
            config = attrs.get('Config', {})

            container_data = {
                'container_id': container_id,
                'name': docker_container.name,
                'image_name': config.get('Image', ''),
                'state': docker_container.status,
                'managed': is_managed,
                'created_at': attrs.get('Created', ''),
                'labels': docker_container.labels or {}
            }

            # If managed, augment with database metadata
            if is_managed:
                db_container = self.db.query(Container).filter_by(
                    container_id=container_id
                ).first()
                if db_container:
                    container_data['environment'] = db_container.environment
                    container_data['ports_json'] = db_container.ports_json
                    container_data['db_id'] = db_container.id

                    # Parse ports from JSON
                    try:
                        container_data['ports'] = json.loads(db_container.ports_json or '[]')
                    except:
                        container_data['ports'] = []
            else:
                # For unmanaged containers, extract ports from Docker directly
                network_settings = attrs.get('NetworkSettings', {})
                ports_list = []
                port_bindings = network_settings.get('Ports', {})
                seen_ports = set()

                for container_port, host_bindings in port_bindings.items():
                    if host_bindings:
                        port_parts = container_port.split('/')
                        port_num = port_parts[0]
                        protocol = port_parts[1] if len(port_parts) > 1 else 'tcp'

                        for binding in host_bindings:
                            host_port = binding.get('HostPort', '')
                            port_key = f"{port_num}/{protocol}:{host_port}"

                            if port_key not in seen_ports:
                                seen_ports.add(port_key)
                                ports_list.append({
                                    'container': port_num,
                                    'host': host_port,
                                    'protocol': protocol,
                                    'host_ip': binding.get('HostIp', '0.0.0.0')
                                })

                container_data['ports'] = ports_list
                container_data['environment'] = None

            # Apply environment filter (only for managed containers)
            # External containers (is_managed=False) are not filtered by environment
            if environment and is_managed and container_data.get('environment') != environment:
                continue

            result.append(container_data)

        return result

    def sync_managed_containers_to_database(self) -> Dict[str, Any]:
        """
        Sync containers with DockerMate labels to database.

        CRITICAL: Recovers managed containers after database reset/migration.
        Searches for containers with 'com.dockermate.managed=true' label
        that are not in the database and adds them.

        This solves the issue where:
        - Database is reset/migrated
        - Previously managed containers still exist in Docker
        - But they're not in the database anymore
        - So they appear as "external" instead of "managed"

        Returns:
            dict: Sync results with counts of recovered containers

        Educational:
            - Docker labels persist with containers
            - Database can be recreated from Docker labels
            - Critical for upgrades/migrations
            - CLI equivalent: docker ps --filter "label=com.dockermate.managed=true"
        """
        logger.info("Starting container sync to database...")

        client = get_docker_client()
        docker_containers = client.containers.list(all=True)

        # Get existing container IDs from database
        existing_ids = {c.container_id for c in self.db.query(Container).all()}

        recovered = []
        skipped = []

        for docker_container in docker_containers:
            container_id = docker_container.id
            labels = docker_container.labels or {}

            # Skip if already in database
            if container_id in existing_ids:
                continue

            # Check if this container was managed by DockerMate
            if labels.get('com.dockermate.managed') == 'true':
                logger.info(f"Recovering managed container: {docker_container.name}")

                # Extract environment from labels if available
                environment = labels.get('com.dockermate.environment')

                # Sync to database
                container_data = self._sync_database_state(docker_container, environment)
                recovered.append(container_data)
            else:
                skipped.append(docker_container.name)

        logger.info(f"Sync complete: {len(recovered)} containers recovered, {len(skipped)} external containers skipped")

        return {
            'recovered': len(recovered),
            'skipped': len(skipped),
            'recovered_containers': [c['name'] for c in recovered]
        }

    # =========================================================================
    # UPDATE OPERATION
    # =========================================================================
    
    def update_container(self, name_or_id: str, **kwargs) -> Dict[str, Any]:
        """
        Update container (Phase 1: labels only).
        
        Args:
            name_or_id: Container name or ID
            **kwargs: Update fields (currently only 'labels' supported)
        
        Returns:
            dict: Updated container details
        
        Raises:
            ValidationError: Invalid update request
            ContainerNotFoundError: Container doesn't exist
            ContainerOperationError: Update failed
        
        Educational:
            - Phase 1 only supports non-destructive label updates
            - Full updates require container recreation (Phase 2)
            - CLI equivalent: docker update --label key=value <container>
        """
        logger.info(f"Updating container: {name_or_id}")
        
        # Phase 1: Only labels supported
        allowed_fields = {'labels'}
        provided_fields = set(kwargs.keys())
        unsupported = provided_fields - allowed_fields
        
        if unsupported:
            raise ValidationError(
                f"Unsupported update fields: {', '.join(unsupported)}. "
                f"Phase 1 only supports: {', '.join(allowed_fields)}"
            )
        
        # Get container
        container = self.db.query(Container).filter(
            (Container.name == name_or_id) |
            (Container.container_id == name_or_id),
            Container.state != 'removed'
        ).first()
        
        if not container:
            raise ContainerNotFoundError(f"Container '{name_or_id}' not found")
        
        # Update labels via Docker API
        client = get_docker_client()
        try:
            docker_container = client.containers.get(container.container_id)
            
            if 'labels' in kwargs:
                # Docker SDK doesn't support label updates directly
                # We'd need to use low-level API or recreate container
                # For now, just update database
                logger.warning("Label updates require container recreation (Phase 2)")
                raise ValidationError("Label updates not yet implemented (Phase 2)")
            
            # Sync and return updated state
            return self._sync_database_state(docker_container, container.environment)
            
        except NotFound:
            raise ContainerNotFoundError(
                f"Container '{name_or_id}' not found in Docker daemon"
            )
        except APIError as e:
            raise ContainerOperationError(f"Failed to update container: {e.explanation}")
    
    # =========================================================================
    # IMAGE-UPDATE OPERATION  (Sprint 3 — Phase 2)
    # =========================================================================

    @docker_operation
    def update_container_image(self, name_or_id: str) -> Dict[str, Any]:
        """
        Pull the latest image for a managed container and recreate it.

        Steps:
            1. Read current container config from Docker (ports, volumes, env,
               restart policy, labels).
            2. Pull the new image (same repository:tag).
            3. Stop the running container.
            4. Remove the old container (keeps volumes unless explicitly pruned).
            5. Recreate with identical config but the freshly-pulled image.
            6. Start the new container.
            7. Write an UpdateHistory record.

        The old image is intentionally NOT removed — it stays around so that
        rollback can recreate from it if needed.

        Returns:
            dict with keys: container_id, name, old_image, new_image, status

        Raises:
            ContainerNotFoundError | ContainerOperationError | ValidationError
        """
        from backend.models.update_history import UpdateHistory

        # --- resolve container from DB (skip removed/dead entries) ---
        db_container = self.db.query(Container).filter(
            ((Container.name == name_or_id) |
             (Container.container_id == name_or_id)) &
            (Container.state != 'removed')
        ).order_by(Container.created_at.desc()).first()
        if not db_container:
            raise ContainerNotFoundError(f"Container '{name_or_id}' not found")

        client = get_docker_client()

        # --- read live config from Docker ---
        try:
            old_docker = client.containers.get(db_container.container_id)
        except NotFound:
            raise ContainerNotFoundError(f"Container '{name_or_id}' not found in Docker daemon")

        attrs   = old_docker.attrs
        config  = attrs.get('Config', {})
        host    = attrs.get('HostConfig', {})
        old_image_name = config.get('Image', db_container.image_name)

        # extract everything we need to recreate
        env_vars      = config.get('Env') or []
        labels        = config.get('Labels') or {}
        restart_name  = host.get('RestartPolicy', {}).get('Name', 'no')
        nano_cpus     = host.get('NanoCpus', 0)
        memory        = host.get('Memory', 0)

        # ports: Docker returns {container_port/proto: [{HostIp, HostPort}]}
        port_bindings = {}
        network_ports = attrs.get('NetworkSettings', {}).get('Ports') or {}
        for cport, bindings in network_ports.items():
            if bindings:
                port_bindings[cport] = bindings

        # volumes
        binds = host.get('Binds') or []

        # --- pull latest ---
        logger.info(f"Pulling latest {old_image_name} for update…")
        try:
            if ':' in old_image_name:
                repo, tag = old_image_name.rsplit(':', 1)
            else:
                repo, tag = old_image_name, 'latest'
            new_image_obj = client.images.pull(repo, tag=tag)
            new_digest = new_image_obj.attrs.get('RepoDigests', [None])[0]
        except APIError as e:
            self._record_update_history(db_container, old_image_name, old_image_name, status='failed', error=str(e))
            raise ContainerOperationError(f"Pull failed: {e.explanation}")

        # --- stop & remove old container ---
        try:
            if old_docker.status == 'running':
                old_docker.stop(timeout=10)
            old_docker.remove()
        except APIError as e:
            self._record_update_history(db_container, old_image_name, old_image_name, status='failed', error=str(e))
            raise ContainerOperationError(f"Failed to remove old container: {e.explanation}")

        # --- recreate ---
        create_kwargs = {
            'name':        db_container.name,
            'image':       old_image_name,
            'detach':      True,
            'environment': env_vars,
            'labels':      labels,
        }
        if port_bindings:
            create_kwargs['ports'] = port_bindings
        if binds:
            create_kwargs['volumes'] = binds
        if restart_name and restart_name != 'no':
            create_kwargs['restart_policy'] = {'Name': restart_name}
        if nano_cpus:
            create_kwargs['cpu_nano_cpus'] = nano_cpus
        if memory:
            create_kwargs['mem_limit'] = memory

        try:
            new_docker = client.containers.create(**create_kwargs)
            new_docker.start()
        except APIError as e:
            self._record_update_history(db_container, old_image_name, old_image_name, status='failed', error=str(e))
            raise ContainerOperationError(f"Failed to recreate container: {e.explanation}")

        # --- sync DB ---
        new_docker.reload()
        self._sync_database_state(new_docker, db_container.environment)

        # --- history record ---
        old_digest_str = None
        try:
            old_digests = client.images.get(old_image_name).attrs.get('RepoDigests', [])
            old_digest_str = old_digests[0] if old_digests else None
        except Exception:
            pass
        self._record_update_history(
            db_container, old_image_name, old_image_name,
            old_digest=old_digest_str,
            new_digest=new_digest,
            status='success'
        )

        logger.info(f"Container '{db_container.name}' updated successfully")
        return {
            'container_id': new_docker.id,
            'name':         db_container.name,
            'old_image':    old_image_name,
            'new_image':    old_image_name,
            'status':       'success'
        }

    # =========================================================================
    # ROLLBACK OPERATION  (Sprint 3)
    # =========================================================================

    @docker_operation
    def rollback_container(self, name_or_id: str) -> Dict[str, Any]:
        """
        Rollback a container to the image it had before its last update.

        Looks up the most recent successful UpdateHistory entry for this
        container and recreates it with old_image.  The current container
        is stopped and removed first (same as update flow).

        Returns:
            dict with keys: container_id, name, rolled_back_to, status

        Raises:
            ContainerNotFoundError | ContainerOperationError | ValidationError
        """
        from backend.models.update_history import UpdateHistory

        db_container = self.db.query(Container).filter(
            ((Container.name == name_or_id) |
             (Container.container_id == name_or_id)) &
            (Container.state != 'removed')
        ).order_by(Container.created_at.desc()).first()
        if not db_container:
            raise ContainerNotFoundError(f"Container '{name_or_id}' not found")

        # Find the last successful update to know what old_image was
        history = (
            self.db.query(UpdateHistory)
            .filter(UpdateHistory.container_name == db_container.name)
            .filter(UpdateHistory.status == 'success')
            .order_by(UpdateHistory.updated_at.desc())
            .first()
        )
        if not history:
            raise ValidationError(f"No update history found for '{db_container.name}' — nothing to roll back")

        target_image = history.old_image
        client = get_docker_client()

        # Verify the old image is still locally available
        try:
            client.images.get(target_image)
        except NotFound:
            raise ContainerOperationError(
                f"Rollback image '{target_image}' no longer exists locally. "
                f"Cannot roll back."
            )

        # --- read live config ---
        try:
            current_docker = client.containers.get(db_container.container_id)
        except NotFound:
            raise ContainerNotFoundError(f"Container '{name_or_id}' not in Docker daemon")

        attrs  = current_docker.attrs
        config = attrs.get('Config', {})
        host   = attrs.get('HostConfig', {})

        env_vars     = config.get('Env') or []
        labels       = config.get('Labels') or {}
        restart_name = host.get('RestartPolicy', {}).get('Name', 'no')
        nano_cpus    = host.get('NanoCpus', 0)
        memory       = host.get('Memory', 0)
        binds        = host.get('Binds') or []
        network_ports = attrs.get('NetworkSettings', {}).get('Ports') or {}
        port_bindings = {k: v for k, v in network_ports.items() if v}

        current_image = config.get('Image', db_container.image_name)

        # --- stop & remove ---
        try:
            if current_docker.status == 'running':
                current_docker.stop(timeout=10)
            current_docker.remove()
        except APIError as e:
            raise ContainerOperationError(f"Failed to remove current container: {e.explanation}")

        # --- recreate with old image ---
        create_kwargs = {
            'name':        db_container.name,
            'image':       target_image,
            'detach':      True,
            'environment': env_vars,
            'labels':      labels,
        }
        if port_bindings:
            create_kwargs['ports'] = port_bindings
        if binds:
            create_kwargs['volumes'] = binds
        if restart_name and restart_name != 'no':
            create_kwargs['restart_policy'] = {'Name': restart_name}
        if nano_cpus:
            create_kwargs['cpu_nano_cpus'] = nano_cpus
        if memory:
            create_kwargs['mem_limit'] = memory

        try:
            new_docker = client.containers.create(**create_kwargs)
            new_docker.start()
        except APIError as e:
            raise ContainerOperationError(f"Rollback recreate failed: {e.explanation}")

        # --- sync + history ---
        new_docker.reload()
        self._sync_database_state(new_docker, db_container.environment)

        # Mark the original update history entry as rolled_back
        history.status = 'rolled_back'
        self.db.commit()

        # Write a new history record for the rollback itself
        self._record_update_history(
            db_container, current_image, target_image,
            old_digest=history.new_digest,
            new_digest=history.old_digest,
            status='success'
        )

        logger.info(f"Container '{db_container.name}' rolled back to {target_image}")
        return {
            'container_id':   new_docker.id,
            'name':           db_container.name,
            'rolled_back_to': target_image,
            'status':         'success'
        }

    # =========================================================================
    # HELPER: record update history
    # =========================================================================

    def _record_update_history(self, db_container, old_image: str, new_image: str,
                               old_digest: str = None, new_digest: str = None,
                               status: str = 'success', error: str = None):
        """Write a single UpdateHistory row."""
        from backend.models.update_history import UpdateHistory
        record = UpdateHistory(
            container_id=db_container.container_id,
            container_name=db_container.name,
            old_image=old_image,
            new_image=new_image,
            old_digest=old_digest,
            new_digest=new_digest,
            status=status,
            error_message=error
        )
        self.db.add(record)
        self.db.commit()

    # =========================================================================
    # DELETE OPERATION
    # =========================================================================

    @docker_operation
    def delete_container(
        self,
        name_or_id: str,
        force: bool = False,
        remove_volumes: bool = False
    ) -> Dict[str, str]:
        """
        Delete container (stop if running, then remove).
        
        Args:
            name_or_id: Container name or ID
            force: Force remove running container
            remove_volumes: Remove associated volumes
        
        Returns:
            dict: Deletion status
        
        Raises:
            ContainerNotFoundError: Container doesn't exist
            ContainerOperationError: Deletion failed
        
        Educational:
            - Checks if container is running before removal
            - force=True equivalent to docker rm -f
            - remove_volumes=True equivalent to docker rm -v
            - CLI equivalent: docker rm [-f] [-v] <container>
        """
        logger.info(f"Deleting container: {name_or_id} (force={force}, remove_volumes={remove_volumes})")
        
        # Get container from database
        container = self.db.query(Container).filter(
            (Container.name == name_or_id) |
            (Container.container_id == name_or_id),
            Container.state != 'removed'
        ).first()
        
        if not container:
            raise ContainerNotFoundError(f"Container '{name_or_id}' not found")
        
        # Remove from Docker
        client = get_docker_client()
        try:
            docker_container = client.containers.get(container.container_id)
            
            # Check if running (safety check)
            if docker_container.status == 'running' and not force:
                raise ContainerOperationError(
                    f"Container '{name_or_id}' is running. "
                    f"Stop it first or use force=True"
                )
            
            # Remove container
            docker_container.remove(force=force, v=remove_volumes)
            logger.info(f"Container removed from Docker: {name_or_id}")
            
        except NotFound:
            logger.warning(
                f"Container {name_or_id} not found in Docker (already removed)"
            )
        except APIError as e:
            raise ContainerOperationError(
                f"Failed to remove container {name_or_id}: {e.explanation}"
            )
        
        # Update database state
        container.state = 'removed'
        container.stopped_at = datetime.utcnow()
        container.updated_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"Container deletion complete: {name_or_id}")
        return {
            'status': 'removed',
            'name': container.name,
            'message': f"Container '{container.name}' successfully removed"
        }
    
    # =========================================================================
    # LIFECYCLE OPERATIONS
    # =========================================================================
    
    @docker_operation
    def start_container(self, name_or_id: str) -> Dict[str, Any]:
        """
        Start a stopped container.
        
        Args:
            name_or_id: Container name or ID
        
        Returns:
            dict: Updated container details
        
        Raises:
            ContainerNotFoundError: Container doesn't exist
            ContainerOperationError: Start failed
        
        Educational:
            - Can only start containers in 'created' or 'exited' state
            - Updates started_at timestamp
            - CLI equivalent: docker start <container>
        """
        logger.info(f"Starting container: {name_or_id}")
        
        # Get container
        container = self.db.query(Container).filter(
            (Container.name == name_or_id) |
            (Container.container_id == name_or_id),
            Container.state != 'removed'
        ).first()
        
        if not container:
            raise ContainerNotFoundError(f"Container '{name_or_id}' not found")
        
        # Start via Docker
        client = get_docker_client()
        try:
            docker_container = client.containers.get(container.container_id)
            
            # Check current state
            if docker_container.status == 'running':
                logger.warning(f"Container {name_or_id} is already running")
                return self._sync_database_state(docker_container, container.environment)
            
            # Start container
            docker_container.start()
            logger.info(f"Container started: {name_or_id}")
            
            # Update database
            container.state = 'running'
            container.started_at = datetime.utcnow()
            container.updated_at = datetime.utcnow()
            self.db.commit()
            
            # Sync and return state
            return self._sync_database_state(docker_container, container.environment)
            
        except NotFound:
            raise ContainerNotFoundError(
                f"Container '{name_or_id}' not found in Docker daemon"
            )
        except APIError as e:
            raise ContainerOperationError(
                f"Failed to start container {name_or_id}: {e.explanation}"
            )
    
    @docker_operation
    def stop_container(self, name_or_id: str, timeout: int = 10) -> Dict[str, Any]:
        """
        Stop a running container.
        
        Args:
            name_or_id: Container name or ID
            timeout: Seconds to wait before force kill
        
        Returns:
            dict: Updated container details
        
        Raises:
            ContainerNotFoundError: Container doesn't exist
            ContainerOperationError: Stop failed
        
        Educational:
            - Sends SIGTERM, waits timeout, then SIGKILL
            - Updates stopped_at timestamp
            - CLI equivalent: docker stop -t <timeout> <container>
        """
        logger.info(f"Stopping container: {name_or_id} (timeout={timeout}s)")
        
        # Get container
        container = self.db.query(Container).filter(
            (Container.name == name_or_id) |
            (Container.container_id == name_or_id),
            Container.state != 'removed'
        ).first()
        
        if not container:
            raise ContainerNotFoundError(f"Container '{name_or_id}' not found")
        
        # Stop via Docker
        client = get_docker_client()
        try:
            docker_container = client.containers.get(container.container_id)
            
            # Check current state
            if docker_container.status != 'running':
                logger.warning(f"Container {name_or_id} is not running")
                return self._sync_database_state(docker_container, container.environment)
            
            # Stop container
            docker_container.stop(timeout=timeout)
            logger.info(f"Container stopped: {name_or_id}")
            
            # Update database
            container.state = 'exited'
            container.stopped_at = datetime.utcnow()
            container.updated_at = datetime.utcnow()
            self.db.commit()
            
            # Sync and return state
            return self._sync_database_state(docker_container, container.environment)
            
        except NotFound:
            raise ContainerNotFoundError(
                f"Container '{name_or_id}' not found in Docker daemon"
            )
        except APIError as e:
            raise ContainerOperationError(
                f"Failed to stop container {name_or_id}: {e.explanation}"
            )
    
    @docker_operation
    def restart_container(self, name_or_id: str, timeout: int = 10) -> Dict[str, Any]:
        """
        Restart a container (stop + start).
        
        Args:
            name_or_id: Container name or ID
            timeout: Seconds to wait before force kill during stop
        
        Returns:
            dict: Updated container details
        
        Raises:
            ContainerNotFoundError: Container doesn't exist
            ContainerOperationError: Restart failed
        
        Educational:
            - Equivalent to stop + start sequence
            - Uses Docker's atomic restart operation
            - Updates timestamps
            - CLI equivalent: docker restart -t <timeout> <container>
        """
        logger.info(f"Restarting container: {name_or_id} (timeout={timeout}s)")
        
        # Get container
        container = self.db.query(Container).filter(
            (Container.name == name_or_id) |
            (Container.container_id == name_or_id),
            Container.state != 'removed'
        ).first()
        
        if not container:
            raise ContainerNotFoundError(f"Container '{name_or_id}' not found")
        
        # Restart via Docker
        client = get_docker_client()
        try:
            # Use list with all=True to reliably get stopped containers
            containers = client.containers.list(all=True, filters={"id": container.container_id})
            if not containers:
                raise NotFound(f"Container {container.container_id} not found")
            docker_container = containers[0]
            docker_container.reload()  # Ensure we have latest state
            
            # Restart container
            docker_container.restart(timeout=timeout)
            logger.info(f"Container restarted: {name_or_id}")
            
            # Update database
            container.state = 'running'
            container.started_at = datetime.utcnow()
            container.updated_at = datetime.utcnow()
            self.db.commit()
            
            # Sync and return state
            return self._sync_database_state(docker_container, container.environment)
            
        except NotFound:
            raise ContainerNotFoundError(
                f"Container '{name_or_id}' not found in Docker daemon"
            )
        except APIError as e:
            raise ContainerOperationError(
                f"Failed to restart container {name_or_id}: {e.explanation}"
            )