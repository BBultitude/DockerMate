"""
Stack Manager Service

Manages Docker Compose stacks (multi-container applications).
Parses docker-compose.yml files and deploys them using Docker SDK.

Features:
- Parse and validate docker-compose.yml files
- Deploy stacks (create networks, volumes, containers)
- Start/stop/restart entire stacks
- Delete stacks with cleanup
- Track stack status and resources
- Support for environment variable overrides

Design:
- Parse YAML using PyYAML
- Create resources using Docker SDK (not docker-compose CLI)
- Store compose files in database and /app/stacks directory
- Track all created resources for cleanup
"""

import yaml
import os
import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from backend.models.stack import Stack
from backend.utils.docker_client import get_docker_client
from backend.utils.exceptions import (
    StackNotFoundError,
    ValidationError,
    StackDeploymentError
)
import docker
from docker.errors import APIError, NotFound
import logging

logger = logging.getLogger(__name__)

_DOCKERMATE_STACK_LABEL = 'com.dockermate.stack'


class StackManager:
    """
    Manages Docker Compose stacks

    Handles parsing, deployment, and lifecycle management of multi-container
    applications defined in docker-compose.yml files.
    """

    def __init__(self, db: Session):
        """
        Initialize StackManager

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.client = get_docker_client()

    def list_stacks(self, include_external=False) -> dict:
        """
        List all stacks

        Args:
            include_external: Include external (unmanaged) stacks

        Returns:
            dict: {
                'success': True,
                'stacks': [{stack details}, ...],
                'count': N
            }
        """
        try:
            # Query stacks from database
            query = self.db.query(Stack)
            if not include_external:
                query = query.filter(Stack.managed == True)

            stacks = query.order_by(Stack.name).all()

            # Enrich with live status
            stack_list = []
            for stack in stacks:
                stack_dict = stack.to_dict()

                # Check actual container status
                running_count = 0
                stopped_count = 0
                container_ids = json.loads(stack.container_ids_json) if stack.container_ids_json else []

                for container_id in container_ids:
                    try:
                        container = self.client.containers.get(container_id)
                        if container.status == 'running':
                            running_count += 1
                        else:
                            stopped_count += 1
                    except NotFound:
                        stopped_count += 1  # Container was deleted

                stack_dict['running_services'] = running_count
                stack_dict['stopped_services'] = stopped_count
                stack_dict['total_services'] = running_count + stopped_count

                stack_list.append(stack_dict)

            return {
                'success': True,
                'stacks': stack_list,
                'count': len(stack_list)
            }

        except Exception as e:
            logger.error(f"Error listing stacks: {e}")
            return {
                'success': False,
                'error': str(e),
                'stacks': [],
                'count': 0
            }

    def get_stack(self, name_or_id: str) -> dict:
        """
        Get single stack with detailed status

        Args:
            name_or_id: Stack name or database ID

        Returns:
            dict: Stack details with service status

        Raises:
            StackNotFoundError: If stack not found
        """
        # Find stack
        try:
            stack_id = int(name_or_id)
            stack = self.db.query(Stack).filter(Stack.id == stack_id).first()
        except ValueError:
            stack = self.db.query(Stack).filter(Stack.name == name_or_id).first()

        if not stack:
            raise StackNotFoundError(f"Stack '{name_or_id}' not found")

        # Get detailed container status
        stack_dict = stack.to_dict()
        container_ids = json.loads(stack.container_ids_json) if stack.container_ids_json else []

        services = []
        for container_id in container_ids:
            try:
                container = self.client.containers.get(container_id)
                services.append({
                    'id': container.id[:12],
                    'name': container.name,
                    'status': container.status,
                    'image': container.image.tags[0] if container.image.tags else container.image.id[:12],
                    'ports': container.ports
                })
            except NotFound:
                # Container was deleted
                services.append({
                    'id': container_id[:12],
                    'name': 'unknown',
                    'status': 'deleted',
                    'image': 'unknown',
                    'ports': {}
                })

        stack_dict['service_details'] = services

        return {
            'success': True,
            'stack': stack_dict
        }

    def _sanitize_name(self, name: str) -> str:
        """
        Sanitize stack name for Docker resource names

        Replaces spaces and invalid characters with hyphens.
        Docker names can only contain: [a-zA-Z0-9][a-zA-Z0-9_.-]

        Args:
            name: Original name

        Returns:
            str: Sanitized name safe for Docker
        """
        import re
        # Replace spaces and invalid chars with hyphens
        sanitized = re.sub(r'[^a-zA-Z0-9_.-]', '-', name)
        # Remove leading/trailing hyphens
        sanitized = sanitized.strip('-')
        # Collapse multiple hyphens
        sanitized = re.sub(r'-+', '-', sanitized)
        return sanitized

    def create_stack(self, name: str, compose_yaml: str, description: str = None, env_vars: dict = None) -> dict:
        """
        Create a new stack from docker-compose.yml content

        Args:
            name: Unique stack name (will be sanitized for Docker)
            compose_yaml: docker-compose.yml file content
            description: Optional description
            env_vars: Optional environment variable overrides

        Returns:
            dict: {
                'success': True,
                'stack': {stack details},
                'message': 'Stack created successfully'
            }

        Raises:
            ValidationError: If name exists or YAML invalid
        """
        # Sanitize name for Docker compatibility
        name = self._sanitize_name(name)

        # Validate name
        if self.db.query(Stack).filter(Stack.name == name).first():
            raise ValidationError(f"Stack '{name}' already exists")

        # Parse and validate YAML
        try:
            compose_data = yaml.safe_load(compose_yaml)
        except yaml.YAMLError as e:
            raise ValidationError(f"Invalid YAML: {e}")

        if not isinstance(compose_data, dict):
            raise ValidationError("Compose file must be a YAML object")

        if 'services' not in compose_data:
            raise ValidationError("Compose file must have 'services' section")

        # Extract metadata
        compose_version = compose_data.get('version', '3.8')
        services = list(compose_data.get('services', {}).keys())

        # Store compose file on filesystem
        from config import Config
        stack_dir = os.path.join(Config.STACKS_DIR, name)
        os.makedirs(stack_dir, exist_ok=True)
        file_path = os.path.join(stack_dir, 'docker-compose.yml')

        with open(file_path, 'w') as f:
            f.write(compose_yaml)

        # Create database record
        stack = Stack(
            name=name,
            description=description,
            compose_yaml=compose_yaml,
            compose_version=compose_version,
            status='stopped',
            file_path=file_path,
            services_json=json.dumps(services),
            container_ids_json=json.dumps([]),
            network_names_json=json.dumps([]),
            volume_names_json=json.dumps([]),
            env_vars_json=json.dumps(env_vars or {}),
            managed=True,
            auto_start=False
        )

        self.db.add(stack)
        self.db.commit()
        self.db.refresh(stack)

        logger.info(f"Stack '{name}' created with {len(services)} services")

        return {
            'success': True,
            'stack': stack.to_dict(),
            'message': f"Stack '{name}' created with {len(services)} services"
        }

    def update_stack(self, name_or_id: str, compose_yaml: str, description: str = None, redeploy: bool = False) -> dict:
        """
        Update a stack's compose YAML and optionally redeploy

        Args:
            name_or_id: Stack name or ID
            compose_yaml: New docker-compose.yml content
            description: Optional new description
            redeploy: If True, stop and redeploy the stack with new config

        Returns:
            dict: Update result

        Raises:
            StackNotFoundError: If stack not found
            ValidationError: If YAML invalid
            StackDeploymentError: If redeploy fails
        """
        # Find stack
        try:
            stack_id = int(name_or_id)
            stack = self.db.query(Stack).filter(Stack.id == stack_id).first()
        except ValueError:
            stack = self.db.query(Stack).filter(Stack.name == name_or_id).first()

        if not stack:
            raise StackNotFoundError(f"Stack '{name_or_id}' not found")

        # Parse and validate YAML
        try:
            compose_data = yaml.safe_load(compose_yaml)
        except yaml.YAMLError as e:
            raise ValidationError(f"Invalid YAML: {e}")

        if not isinstance(compose_data, dict):
            raise ValidationError("Compose file must be a YAML object")

        if 'services' not in compose_data:
            raise ValidationError("Compose file must have 'services' section")

        # Extract metadata
        compose_version = compose_data.get('version', stack.compose_version)
        services = list(compose_data.get('services', {}).keys())

        # Update database record
        stack.compose_yaml = compose_yaml
        if description is not None:
            stack.description = description
        stack.compose_version = compose_version
        stack.services_json = json.dumps(services)

        # Update file on filesystem
        if stack.file_path and os.path.exists(stack.file_path):
            with open(stack.file_path, 'w') as f:
                f.write(compose_yaml)

        self.db.commit()
        self.db.refresh(stack)

        logger.info(f"Stack '{stack.name}' updated with {len(services)} services")

        result = {
            'success': True,
            'stack': stack.to_dict(),
            'message': f"Stack '{stack.name}' updated successfully"
        }

        # Redeploy if requested
        if redeploy:
            # Stop existing containers
            if stack.status == 'running':
                self.stop_stack(stack.id)

            # Redeploy with new config
            deploy_result = self.deploy_stack(stack.id)
            result['deployed'] = deploy_result.get('deployed')
            result['message'] = f"Stack '{stack.name}' updated and redeployed"

        return result

    def deploy_stack(self, name_or_id: str) -> dict:
        """
        Deploy a stack (create and start all services)

        This parses the compose file and creates networks, volumes, and containers.

        Args:
            name_or_id: Stack name or ID

        Returns:
            dict: Deployment result with created resources

        Raises:
            StackNotFoundError: If stack not found
            StackDeploymentError: If deployment fails
        """
        # Find stack
        try:
            stack_id = int(name_or_id)
            stack = self.db.query(Stack).filter(Stack.id == stack_id).first()
        except ValueError:
            stack = self.db.query(Stack).filter(Stack.name == name_or_id).first()

        if not stack:
            raise StackNotFoundError(f"Stack '{name_or_id}' not found")

        logger.info(f"Deploying stack '{stack.name}'...")
        stack.status = 'deploying'
        self.db.commit()

        try:
            # Parse compose file
            compose_data = yaml.safe_load(stack.compose_yaml)
            env_vars = json.loads(stack.env_vars_json) if stack.env_vars_json else {}

            # Deploy in order: networks → volumes → services
            created_networks = self._create_networks(stack.name, compose_data.get('networks', {}))
            created_volumes = self._create_volumes(stack.name, compose_data.get('volumes', {}))
            created_containers = self._create_services(stack.name, compose_data['services'], env_vars, created_networks)

            # Update stack with created resources
            stack.container_ids_json = json.dumps([c.id for c in created_containers])
            stack.network_names_json = json.dumps(created_networks)
            stack.volume_names_json = json.dumps(created_volumes)
            stack.status = 'running'
            stack.deployed_at = datetime.now(timezone.utc)
            self.db.commit()

            # Sync stack resources to their respective database tables (Sprint 5+ - Auto-import)
            self._sync_stack_resources_to_database(created_networks, created_volumes)

            logger.info(f"Stack '{stack.name}' deployed successfully: {len(created_containers)} containers, {len(created_networks)} networks, {len(created_volumes)} volumes")

            return {
                'success': True,
                'stack': stack.to_dict(),
                'deployed': {
                    'containers': len(created_containers),
                    'networks': len(created_networks),
                    'volumes': len(created_volumes)
                },
                'message': f"Stack '{stack.name}' deployed successfully"
            }

        except Exception as e:
            logger.error(f"Stack deployment failed: {e}")
            stack.status = 'failed'
            self.db.commit()
            raise StackDeploymentError(f"Deployment failed: {e}")

    def _create_networks(self, stack_name: str, networks_spec: dict) -> list:
        """Create networks defined in compose file"""
        created = []
        sanitized_stack_name = self._sanitize_name(stack_name)

        for network_name, network_config in networks_spec.items():
            full_name = f"{sanitized_stack_name}_{network_name}"

            try:
                # Check if network already exists
                self.client.networks.get(full_name)
                logger.info(f"Network '{full_name}' already exists")
            except NotFound:
                # Create network
                driver = network_config.get('driver', 'bridge') if isinstance(network_config, dict) else 'bridge'
                self.client.networks.create(
                    name=full_name,
                    driver=driver,
                    labels={_DOCKERMATE_STACK_LABEL: stack_name}
                )
                logger.info(f"Created network '{full_name}'")

            created.append(full_name)

        return created

    def _create_volumes(self, stack_name: str, volumes_spec: dict) -> list:
        """Create volumes defined in compose file"""
        created = []
        sanitized_stack_name = self._sanitize_name(stack_name)

        for volume_name, volume_config in volumes_spec.items():
            full_name = f"{sanitized_stack_name}_{volume_name}"

            try:
                # Check if volume already exists
                self.client.volumes.get(full_name)
                logger.info(f"Volume '{full_name}' already exists")
            except NotFound:
                # Create volume
                driver = volume_config.get('driver', 'local') if isinstance(volume_config, dict) else 'local'
                self.client.volumes.create(
                    name=full_name,
                    driver=driver,
                    labels={_DOCKERMATE_STACK_LABEL: stack_name}
                )
                logger.info(f"Created volume '{full_name}'")

            created.append(full_name)

        return created

    def _ensure_image_available(self, image: str) -> None:
        """Pull image if not present locally."""
        try:
            self.client.images.get(image)
        except NotFound:
            logger.info(f"Pulling image '{image}'...")
            self.client.images.pull(image)

    def _parse_compose_ports(self, port_specs: list) -> dict:
        """Convert compose ports list to Docker port bindings dict."""
        ports = {}
        for port_spec in port_specs:
            if isinstance(port_spec, str):
                parts = port_spec.split(':')
                if len(parts) == 2:
                    ports[parts[1]] = parts[0]
            elif isinstance(port_spec, int):
                ports[str(port_spec)] = str(port_spec)
        return ports

    def _parse_compose_environment(self, service_config: dict, env_vars: dict) -> dict:
        """Normalize compose environment (list or dict) and merge stack overrides."""
        environment = service_config.get('environment', {})
        if isinstance(environment, list):
            environment = {
                k: v for item in environment if '=' in item
                for k, v in [item.split('=', 1)]
            }
        environment.update(env_vars)
        return environment

    def _parse_compose_volumes(self, volume_specs: list, sanitized_stack_name: str) -> dict:
        """Convert compose volume specs to Docker volumes dict."""
        volumes = {}
        for volume_spec in volume_specs:
            if ':' not in volume_spec:
                continue
            parts = volume_spec.split(':')
            source, target = parts[0], parts[1]
            mode = parts[2] if len(parts) > 2 else 'rw'
            is_bind_mount = source.startswith('/') or source.startswith('.') or source.startswith('~')
            if is_bind_mount:
                if source.startswith('.'):
                    logger.warning(f"Relative volume path '{source}' not supported - skipping.")
                    continue
                volumes[source] = {'bind': target, 'mode': mode}
            else:
                volumes[f"{sanitized_stack_name}_{source}"] = {'bind': target, 'mode': mode}
        return volumes

    def _build_service_container_config(self, service_name: str, service_config: dict,
                                        env_vars: dict, stack_name: str,
                                        container_name: str, sanitized_stack_name: str) -> dict:
        """Build the container.create() config dict for a single compose service."""
        image = service_config['image']
        container_config: dict = {
            'name': container_name,
            'image': image,
            'detach': True,
            'labels': {
                _DOCKERMATE_STACK_LABEL: stack_name,
                'com.dockermate.service': service_name,
                'com.dockermate.managed': 'true',
            },
        }
        if 'ports' in service_config:
            ports = self._parse_compose_ports(service_config['ports'])
            if ports:
                container_config['ports'] = ports
        environment = self._parse_compose_environment(service_config, env_vars)
        if environment:
            container_config['environment'] = environment
        if 'command' in service_config and isinstance(service_config['command'], (str, list)):
            container_config['command'] = service_config['command']
        if 'entrypoint' in service_config and isinstance(service_config['entrypoint'], (str, list)):
            container_config['entrypoint'] = service_config['entrypoint']
        if 'volumes' in service_config:
            volumes = self._parse_compose_volumes(service_config['volumes'], sanitized_stack_name)
            if volumes:
                container_config['volumes'] = volumes
        restart_policy = service_config.get('restart', 'no')
        if restart_policy != 'no':
            container_config['restart_policy'] = {'Name': restart_policy}
        return container_config

    def _connect_and_start_service(self, container, networks: list, container_name: str) -> None:
        """Connect a container to networks then start it."""
        for network_name in (networks or []):
            try:
                self.client.networks.get(network_name).connect(container)
            except Exception as e:
                logger.warning(f"Failed to connect to network '{network_name}': {e}")
        container.start()
        logger.info(f"Started container '{container_name}'")

    def _create_services(self, stack_name: str, services_spec: dict, env_vars: dict, networks: list) -> list:
        """
        Create containers for all services defined in compose file.

        Supports: image, ports, environment, volumes, networks, restart, command, entrypoint.
        """
        created_containers = []
        sanitized_stack_name = self._sanitize_name(stack_name)

        for service_name, service_config in services_spec.items():
            container_name = f"{sanitized_stack_name}_{service_name}_1"

            try:
                existing = self.client.containers.get(container_name)
                logger.info(f"Container '{container_name}' already exists")
                created_containers.append(existing)
                continue
            except NotFound:
                pass

            image = service_config.get('image')
            if not image:
                logger.warning(f"Service '{service_name}' has no image, skipping")
                continue

            self._ensure_image_available(image)
            container_config = self._build_service_container_config(
                service_name, service_config, env_vars,
                stack_name, container_name, sanitized_stack_name
            )

            try:
                container = self.client.containers.create(**container_config)
                self._connect_and_start_service(container, networks, container_name)
                created_containers.append(container)
            except APIError as e:
                logger.error(f"Failed to create container '{container_name}': {e}")
                raise

        return created_containers

    def _sync_network_record(self, network_name: str, Network) -> None:
        """Upsert a stack-created network into the database as managed=True."""
        try:
            docker_network = self.client.networks.get(network_name)
            db_network = self.db.query(Network).filter(
                Network.network_id == docker_network.id
            ).first()
            if db_network:
                db_network.managed = True
                logger.info(f"Updated network '{network_name}' to managed=True")
            else:
                attrs = docker_network.attrs
                ipam = attrs.get('IPAM', {}).get('Config', [])
                db_network = Network(
                    network_id=docker_network.id,
                    name=docker_network.name,
                    driver=attrs.get('Driver', 'bridge'),
                    subnet=ipam[0].get('Subnet') if ipam else None,
                    gateway=ipam[0].get('Gateway') if ipam else None,
                    managed=True,
                )
                self.db.add(db_network)
                logger.info(f"Created database record for network '{network_name}'")
        except Exception as e:
            logger.warning(f"Failed to sync network '{network_name}': {e}")

    def _sync_stack_resources_to_database(self, network_names: list, volume_names: list) -> None:
        """
        Sync stack-created resources to their respective database tables.

        After deploying a stack, resources are created in Docker with DockerMate labels
        but not yet synced to the Container/Volume/Network database tables. This method
        imports them as managed resources so they appear in their respective pages.

        Args:
            network_names: List of network names created by stack
            volume_names: List of volume names created by stack

        Educational:
            - Stack resources already have 'com.dockermate.stack' labels
            - Containers have 'com.dockermate.managed=true' label
            - This method syncs them to database with managed=True
            - Allows viewing/managing stack resources from their respective pages
        """
        logger.info("Syncing stack resources to database...")

        try:
            # Import manager services
            from backend.services.container_manager import ContainerManager
            from backend.services.volume_manager import VolumeManager
            from backend.models.network import Network

            # Sync networks to database
            for network_name in network_names:
                self._sync_network_record(network_name, Network)

            # Sync volumes to database
            volume_manager = VolumeManager(self.db)
            for volume_name in volume_names:
                try:
                    docker_volume = self.client.volumes.get(volume_name)
                    # Use VolumeManager's private sync method with managed=True
                    volume_manager._sync_database_state(docker_volume, managed=True)
                    logger.info(f"Synced volume '{volume_name}' to database as managed")
                except Exception as e:
                    logger.warning(f"Failed to sync volume '{volume_name}': {e}")

            # Sync containers to database
            # ContainerManager's sync method finds all containers with com.dockermate.managed=true label
            container_manager = ContainerManager(self.db)
            container_sync_result = container_manager.sync_managed_containers_to_database()
            synced_count = container_sync_result.get('recovered', 0)
            if synced_count > 0:
                logger.info(f"Synced {synced_count} containers to database (recovered from labels)")
            else:
                logger.info("No new containers to sync (all already in database)")

            # Commit all changes
            self.db.commit()
            logger.info("✓ Stack resources synced to database successfully")

        except Exception as e:
            logger.error(f"Error syncing stack resources to database: {e}")
            self.db.rollback()
            # Don't raise - deployment succeeded, sync failure is non-critical

    def stop_stack(self, name_or_id: str) -> dict:
        """
        Stop all containers in a stack

        Args:
            name_or_id: Stack name or ID

        Returns:
            dict: Stop result

        Raises:
            StackNotFoundError: If stack not found
        """
        # Find stack
        try:
            stack_id = int(name_or_id)
            stack = self.db.query(Stack).filter(Stack.id == stack_id).first()
        except ValueError:
            stack = self.db.query(Stack).filter(Stack.name == name_or_id).first()

        if not stack:
            raise StackNotFoundError(f"Stack '{name_or_id}' not found")

        container_ids = json.loads(stack.container_ids_json) if stack.container_ids_json else []
        stopped_count = 0

        for container_id in container_ids:
            try:
                container = self.client.containers.get(container_id)
                if container.status == 'running':
                    container.stop(timeout=10)
                    stopped_count += 1
            except NotFound:
                pass  # Container already removed

        stack.status = 'stopped'
        self.db.commit()

        logger.info(f"Stopped {stopped_count} containers in stack '{stack.name}'")

        return {
            'success': True,
            'stack': stack.name,
            'stopped': stopped_count,
            'message': f"Stopped {stopped_count} containers"
        }

    def start_stack(self, name_or_id: str) -> dict:
        """
        Start all containers in a stack

        Args:
            name_or_id: Stack name or ID

        Returns:
            dict: Start result

        Raises:
            StackNotFoundError: If stack not found
        """
        # Find stack
        try:
            stack_id = int(name_or_id)
            stack = self.db.query(Stack).filter(Stack.id == stack_id).first()
        except ValueError:
            stack = self.db.query(Stack).filter(Stack.name == name_or_id).first()

        if not stack:
            raise StackNotFoundError(f"Stack '{name_or_id}' not found")

        container_ids = json.loads(stack.container_ids_json) if stack.container_ids_json else []
        started_count = 0

        for container_id in container_ids:
            try:
                container = self.client.containers.get(container_id)
                if container.status != 'running':
                    container.start()
                    started_count += 1
            except NotFound:
                pass  # Container was removed

        stack.status = 'running'
        self.db.commit()

        logger.info(f"Started {started_count} containers in stack '{stack.name}'")

        return {
            'success': True,
            'stack': stack.name,
            'started': started_count,
            'message': f"Started {started_count} containers"
        }

    def _remove_stack_containers(self, container_ids: list) -> int:
        removed = 0
        for container_id in container_ids:
            try:
                container = self.client.containers.get(container_id)
                container.stop(timeout=10)
                container.remove()
                removed += 1
            except NotFound:
                pass
        return removed

    def _remove_stack_networks(self, network_names: list) -> int:
        removed = 0
        for network_name in network_names:
            try:
                network = self.client.networks.get(network_name)
                network.remove()
                removed += 1
            except NotFound:
                pass
        return removed

    def _remove_stack_volumes(self, volume_names: list) -> int:
        removed = 0
        for volume_name in volume_names:
            try:
                volume = self.client.volumes.get(volume_name)
                volume.remove()
                removed += 1
            except NotFound:
                pass
        return removed

    def _cleanup_stack_directory(self, file_path: str) -> None:
        if not file_path or not os.path.exists(file_path):
            return
        os.remove(file_path)
        stack_dir = os.path.dirname(file_path)
        if os.path.exists(stack_dir) and not os.listdir(stack_dir):
            os.rmdir(stack_dir)

    def delete_stack(self, name_or_id: str, remove_volumes: bool = False) -> dict:
        """
        Delete a stack and all its resources

        Args:
            name_or_id: Stack name or ID
            remove_volumes: Also remove volumes (default: False)

        Returns:
            dict: Deletion result

        Raises:
            StackNotFoundError: If stack not found
        """
        try:
            stack_id = int(name_or_id)
            stack = self.db.query(Stack).filter(Stack.id == stack_id).first()
        except ValueError:
            stack = self.db.query(Stack).filter(Stack.name == name_or_id).first()

        if not stack:
            raise StackNotFoundError(f"Stack '{name_or_id}' not found")

        container_ids = json.loads(stack.container_ids_json) if stack.container_ids_json else []
        network_names = json.loads(stack.network_names_json) if stack.network_names_json else []
        removed_containers = self._remove_stack_containers(container_ids)
        removed_networks = self._remove_stack_networks(network_names)

        removed_volumes = 0
        if remove_volumes:
            volume_names = json.loads(stack.volume_names_json) if stack.volume_names_json else []
            removed_volumes = self._remove_stack_volumes(volume_names)

        self._cleanup_stack_directory(stack.file_path)

        self.db.delete(stack)
        self.db.commit()

        logger.info(f"Deleted stack '{stack.name}': {removed_containers} containers, {removed_networks} networks, {removed_volumes} volumes")

        return {
            'success': True,
            'stack': stack.name,
            'removed': {
                'containers': removed_containers,
                'networks': removed_networks,
                'volumes': removed_volumes
            },
            'message': f"Stack '{stack.name}' deleted successfully"
        }
