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

    # Maps flag aliases to (result_key, is_list) where is_list=True means append, False means set
    _SINGLE_VALUE_FLAGS: Dict[str, str] = {
        '--name': 'name',
        '--network': 'network', '--net': 'network',
        '--restart': 'restart',
        '-m': 'memory', '--memory': 'memory',
        '--cpus': 'cpus',
    }
    _LIST_APPEND_FLAGS: Dict[str, str] = {
        '-p': 'ports', '--publish': 'ports',
        '-v': 'volumes', '--volume': 'volumes',
    }

    def _strip_docker_prefix(self, command: str) -> str:
        command = command.strip()
        if command.startswith('docker container run'):
            return command[20:].strip()
        if command.startswith('docker run'):
            return command[10:].strip()
        return command

    def _init_parse_result(self) -> Dict:
        return {
            'image': None, 'ports': [], 'volumes': [], 'environment': {},
            'name': None, 'network': None, 'restart': None,
            'memory': None, 'cpus': None, 'labels': {}, 'warnings': [], 'detach': False,
        }

    def _handle_env_token(self, result: Dict, tokens: list, i: int) -> int:
        env = tokens[i]
        if '=' in env:
            key, value = env.split('=', 1)
            result['environment'][key] = value
        else:
            result['environment'][env] = ''
        return i + 1

    def _handle_label_token(self, result: Dict, tokens: list, i: int) -> int:
        label = tokens[i]
        if '=' in label:
            key, value = label.split('=', 1)
            result['labels'][key] = value
        return i + 1

    def _dispatch_token(self, result: Dict, tokens: list, token: str, i: int):
        """Handle one token from a docker run command. Returns new index, or None if image was found."""
        if token in ('-d', '--detach'):
            result['detach'] = True
            return i
        if token in ('-i', '--interactive', '-t', '--tty'):
            result['warnings'].append(f"Flag {token} (interactive/tty) not applicable in compose")
            return i
        if token == '--rm':
            result['warnings'].append("Flag --rm (auto-remove) not directly supported in compose")
            return i
        if token in self._LIST_APPEND_FLAGS and i < len(tokens):
            result[self._LIST_APPEND_FLAGS[token]].append(tokens[i])
            return i + 1
        if token in self._SINGLE_VALUE_FLAGS and i < len(tokens):
            result[self._SINGLE_VALUE_FLAGS[token]] = tokens[i]
            return i + 1
        if token in ('-e', '--env') and i < len(tokens):
            return self._handle_env_token(result, tokens, i)
        if token in ('-l', '--label') and i < len(tokens):
            return self._handle_label_token(result, tokens, i)
        if token.startswith('-'):
            result['warnings'].append(f"Unsupported flag: {token}")
            if i < len(tokens) and not tokens[i].startswith('-'):
                return i + 1
            return i
        return None  # Image token found

    def _parse_docker_run(self, command: str) -> Dict:
        """
        Parse docker run command and extract configuration.

        Returns:
            dict with keys: image, ports, volumes, environment, name, network,
            restart, memory, cpus, labels, warnings, detach
        """
        command = self._strip_docker_prefix(command)
        try:
            tokens = shlex.split(command)
        except ValueError as e:
            raise ValueError(f"Invalid command syntax: {e}")

        result = self._init_parse_result()
        i = 0
        while i < len(tokens):
            token = tokens[i]
            i += 1
            new_i = self._dispatch_token(result, tokens, token, i)
            if new_i is None:
                result['image'] = token
                if i < len(tokens):
                    result['command'] = tokens[i:]
                break
            i = new_i

        if not result['image']:
            raise ValueError("No image specified in docker run command")
        return result

    def _build_resources_deploy(self, parsed: Dict):
        """Build the deploy.resources section, or return None if no limits specified."""
        if not parsed['memory'] and not parsed['cpus']:
            return None
        limits = {}
        if parsed['memory']:
            limits['memory'] = parsed['memory']
        if parsed['cpus']:
            limits['cpus'] = parsed['cpus']
        if not limits:
            return None
        return {'resources': {'limits': limits}}

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
        deploy = self._build_resources_deploy(parsed)
        if deploy:
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
