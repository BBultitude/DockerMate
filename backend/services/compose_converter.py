"""
Docker Run to Compose Converter Service

Converts docker run commands to docker-compose.yml format.

Features:
- Parse docker run command arguments
- Extract: image, ports, volumes, environment, networks, restart policy, resources
- Generate valid compose YAML
- Handle common flags and options

Usage:
    converter = ComposeConverter()
    result = converter.convert_run_to_compose(
        "docker run -d -p 8080:80 --name web nginx:alpine"
    )
    print(result['compose_yaml'])
"""

import re
import shlex
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class ComposeConverter:
    """
    Converts docker run commands to docker-compose.yml format
    """

    def __init__(self):
        """Initialize converter"""
        pass

    def convert_run_to_compose(self, docker_run_command: str, service_name: str = None) -> Dict:
        """
        Convert docker run command to compose YAML

        Args:
            docker_run_command: Full docker run command
            service_name: Optional service name (defaults to container name or 'app')

        Returns:
            dict: {
                'success': True,
                'compose_yaml': 'version: 3.8...',
                'service_name': 'web',
                'warnings': ['list of warnings']
            }

        Example:
            >>> converter = ComposeConverter()
            >>> result = converter.convert_run_to_compose(
            ...     "docker run -d -p 8080:80 --name web nginx:alpine"
            ... )
            >>> print(result['compose_yaml'])
            version: '3.8'
            services:
              web:
                image: nginx:alpine
                ports:
                  - "8080:80"
        """
        try:
            # Parse command
            parsed = self._parse_docker_run(docker_run_command)

            # Use provided service name or extract from command
            if not service_name:
                service_name = parsed.get('name', 'app')

            # Build compose structure
            compose_data = self._build_compose_structure(parsed, service_name)

            # Generate YAML
            compose_yaml = self._generate_yaml(compose_data)

            return {
                'success': True,
                'compose_yaml': compose_yaml,
                'service_name': service_name,
                'warnings': parsed.get('warnings', [])
            }
        except Exception as e:
            logger.error(f"Conversion failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'compose_yaml': None,
                'service_name': None,
                'warnings': []
            }

    def _parse_docker_run(self, command: str) -> Dict:
        """
        Parse docker run command and extract configuration

        Returns:
            dict: Parsed configuration with keys:
                - image: Image name
                - ports: List of port mappings
                - volumes: List of volume mounts
                - environment: Dict of env vars
                - name: Container name
                - network: Network name
                - restart: Restart policy
                - memory: Memory limit
                - cpus: CPU limit
                - labels: Dict of labels
                - warnings: List of unsupported flags
        """
        # Remove 'docker run' prefix
        command = command.strip()
        if command.startswith('docker run'):
            command = command[10:].strip()
        elif command.startswith('docker container run'):
            command = command[20:].strip()

        # Split command into tokens
        try:
            tokens = shlex.split(command)
        except ValueError as e:
            raise ValueError(f"Invalid command syntax: {e}")

        result = {
            'image': None,
            'ports': [],
            'volumes': [],
            'environment': {},
            'name': None,
            'network': None,
            'restart': None,
            'memory': None,
            'cpus': None,
            'labels': {},
            'warnings': [],
            'detach': False
        }

        i = 0
        while i < len(tokens):
            token = tokens[i]

            # Flags that take no arguments
            if token in ['-d', '--detach']:
                result['detach'] = True
                i += 1
                continue

            if token in ['-i', '--interactive', '-t', '--tty']:
                result['warnings'].append(f"Flag {token} (interactive/tty) not applicable in compose")
                i += 1
                continue

            if token == '--rm':
                result['warnings'].append("Flag --rm (auto-remove) not directly supported in compose")
                i += 1
                continue

            # Flags that take one argument
            if token in ['-p', '--publish']:
                if i + 1 < len(tokens):
                    result['ports'].append(tokens[i + 1])
                    i += 2
                    continue

            if token in ['-v', '--volume']:
                if i + 1 < len(tokens):
                    result['volumes'].append(tokens[i + 1])
                    i += 2
                    continue

            if token in ['-e', '--env']:
                if i + 1 < len(tokens):
                    env = tokens[i + 1]
                    if '=' in env:
                        key, value = env.split('=', 1)
                        result['environment'][key] = value
                    else:
                        result['environment'][env] = ''
                    i += 2
                    continue

            if token in ['--name']:
                if i + 1 < len(tokens):
                    result['name'] = tokens[i + 1]
                    i += 2
                    continue

            if token in ['--network', '--net']:
                if i + 1 < len(tokens):
                    result['network'] = tokens[i + 1]
                    i += 2
                    continue

            if token in ['--restart']:
                if i + 1 < len(tokens):
                    result['restart'] = tokens[i + 1]
                    i += 2
                    continue

            if token in ['-m', '--memory']:
                if i + 1 < len(tokens):
                    result['memory'] = tokens[i + 1]
                    i += 2
                    continue

            if token in ['--cpus']:
                if i + 1 < len(tokens):
                    result['cpus'] = tokens[i + 1]
                    i += 2
                    continue

            if token in ['-l', '--label']:
                if i + 1 < len(tokens):
                    label = tokens[i + 1]
                    if '=' in label:
                        key, value = label.split('=', 1)
                        result['labels'][key] = value
                    i += 2
                    continue

            # Unsupported flags
            if token.startswith('-'):
                result['warnings'].append(f"Unsupported flag: {token}")
                # Skip this flag and its potential argument
                i += 1
                if i < len(tokens) and not tokens[i].startswith('-'):
                    i += 1
                continue

            # Last non-flag token is the image (and potentially command)
            result['image'] = token
            i += 1

            # Remaining tokens are the command
            if i < len(tokens):
                result['command'] = tokens[i:]
            break

        if not result['image']:
            raise ValueError("No image specified in docker run command")

        return result

    def _build_compose_structure(self, parsed: Dict, service_name: str) -> Dict:
        """
        Build compose file structure from parsed data

        Args:
            parsed: Parsed docker run configuration
            service_name: Service name to use

        Returns:
            dict: Compose file structure
        """
        service_config = {
            'image': parsed['image']
        }

        # Ports
        if parsed['ports']:
            service_config['ports'] = parsed['ports']

        # Volumes
        if parsed['volumes']:
            service_config['volumes'] = parsed['volumes']

        # Environment
        if parsed['environment']:
            service_config['environment'] = parsed['environment']

        # Restart policy
        if parsed['restart']:
            service_config['restart'] = parsed['restart']

        # Network
        networks_section = None
        if parsed['network'] and parsed['network'] != 'bridge':
            service_config['networks'] = [parsed['network']]
            networks_section = {
                parsed['network']: {
                    'external': True
                }
            }

        # Resources
        if parsed['memory'] or parsed['cpus']:
            deploy = {}
            resources = {}
            limits = {}

            if parsed['memory']:
                limits['memory'] = parsed['memory']
            if parsed['cpus']:
                limits['cpus'] = parsed['cpus']

            if limits:
                resources['limits'] = limits
                deploy['resources'] = resources
                service_config['deploy'] = deploy

        # Labels
        if parsed['labels']:
            service_config['labels'] = parsed['labels']

        # Command
        if 'command' in parsed:
            service_config['command'] = ' '.join(parsed['command'])

        # Build complete structure
        compose = {
            'version': '3.8',
            'services': {
                service_name: service_config
            }
        }

        if networks_section:
            compose['networks'] = networks_section

        return compose

    def _generate_yaml(self, compose_data: Dict) -> str:
        """
        Generate YAML string from compose structure

        Args:
            compose_data: Compose file structure

        Returns:
            str: Formatted YAML string
        """
        import yaml

        # Use safe_dump with nice formatting
        yaml_str = yaml.dump(
            compose_data,
            default_flow_style=False,
            sort_keys=False,
            indent=2,
            width=1000  # Prevent line wrapping
        )

        return yaml_str

    def convert_multiple_runs(self, commands: List[Tuple[str, str]]) -> Dict:
        """
        Convert multiple docker run commands into a single compose file

        Args:
            commands: List of (command, service_name) tuples

        Returns:
            dict: {
                'success': True,
                'compose_yaml': 'combined yaml',
                'services': ['service1', 'service2'],
                'warnings': ['combined warnings']
            }
        """
        all_services = {}
        all_networks = {}
        all_warnings = []

        for command, service_name in commands:
            result = self.convert_run_to_compose(command, service_name)

            if not result['success']:
                return {
                    'success': False,
                    'error': f"Failed to convert service '{service_name}': {result.get('error')}",
                    'compose_yaml': None
                }

            # Parse generated YAML to extract service config
            import yaml
            compose_data = yaml.safe_load(result['compose_yaml'])

            # Merge services
            all_services.update(compose_data['services'])

            # Merge networks
            if 'networks' in compose_data:
                all_networks.update(compose_data['networks'])

            # Collect warnings
            all_warnings.extend(result.get('warnings', []))

        # Build combined compose file
        combined = {
            'version': '3.8',
            'services': all_services
        }

        if all_networks:
            combined['networks'] = all_networks

        # Generate final YAML
        import yaml
        compose_yaml = yaml.dump(
            combined,
            default_flow_style=False,
            sort_keys=False,
            indent=2,
            width=1000
        )

        return {
            'success': True,
            'compose_yaml': compose_yaml,
            'services': list(all_services.keys()),
            'warnings': all_warnings
        }
