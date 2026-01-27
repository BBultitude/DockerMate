"""
Unit Tests - Container Service

Tests for backend/services/container_service.py:
- Container listing with filters
- Container details retrieval
- Start/stop/restart operations
- Container removal
- Log and stats retrieval
- Data transformation methods

Educational Notes:
- Tests use mocking to avoid requiring Docker daemon
- Mock container objects simulate Docker SDK responses
- Tests verify business logic, not Docker SDK behavior
- Edge cases (not found, already running, etc.) are tested
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from docker.errors import NotFound, APIError

from backend.services.container_service import ContainerService
from backend.utils.exceptions import (
    ContainerNotFoundError,
    ContainerOperationError,
    DockerConnectionError
)


@pytest.fixture
def mock_container():
    """
    Fixture providing a mocked Docker container object.
    
    Simulates the Docker SDK container object with all necessary attributes.
    """
    container = MagicMock()
    container.id = '1234567890abcdef'
    container.name = 'test-container'
    container.status = 'running'
    container.image.tags = ['nginx:latest']
    container.labels = {'dockermate.environment': 'DEV'}
    container.attrs = {
        'Created': '2024-01-01T00:00:00Z',
        'State': {'Status': 'running'},
        'Config': {
            'Env': ['PATH=/usr/bin', 'DEBUG=true'],
            'Cmd': ['nginx', '-g', 'daemon off;'],
            'Entrypoint': None,
            'Hostname': 'test-container',
        },
        'HostConfig': {
            'RestartPolicy': {'Name': 'unless-stopped'},
        },
        'RestartCount': 0,
        'NetworkSettings': {
            'Ports': {
                '80/tcp': [{'HostIp': '0.0.0.0', 'HostPort': '8080'}]
            },
            'Networks': {
                'bridge': {
                    'IPAddress': '172.17.0.2',
                    'Gateway': '172.17.0.1',
                    'MacAddress': '02:42:ac:11:00:02',
                }
            }
        },
        'Mounts': [
            {
                'Type': 'volume',
                'Source': '/var/lib/docker/volumes/test/_data',
                'Destination': '/data',
                'Mode': 'rw',
                'RW': True,
            }
        ]
    }
    return container


@pytest.fixture
def service():
    """Fixture providing ContainerService instance."""
    return ContainerService()


class TestListContainers:
    """Test container listing operations."""
    
    @patch('backend.services.container_service.get_docker_client')
    def test_list_all_containers(self, mock_get_client, service, mock_container):
        """Test listing all containers."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.containers.list.return_value = [mock_container]
        mock_get_client.return_value = mock_client
        
        # Execute
        result = service.list_containers(all=True)
        
        # Verify
        assert len(result) == 1
        assert result[0]['name'] == 'test-container'
        assert result[0]['status'] == 'running'
        mock_client.containers.list.assert_called_once_with(all=True, filters={})
    
    @patch('backend.services.container_service.get_docker_client')
    def test_list_running_containers_only(self, mock_get_client, service, mock_container):
        """Test listing only running containers."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.containers.list.return_value = [mock_container]
        mock_get_client.return_value = mock_client
        
        # Execute
        result = service.list_containers(all=False)
        
        # Verify
        assert len(result) == 1
        mock_client.containers.list.assert_called_once_with(all=False, filters={})
    
    @patch('backend.services.container_service.get_docker_client')
    def test_list_containers_by_environment(self, mock_get_client, service, mock_container):
        """Test filtering containers by environment tag."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.containers.list.return_value = [mock_container]
        mock_get_client.return_value = mock_client
        
        # Execute
        result = service.list_containers(environment='DEV')
        
        # Verify
        assert len(result) == 1
        mock_client.containers.list.assert_called_once_with(
            all=False,
            filters={'label': 'dockermate.environment=DEV'}
        )
    
    @patch('backend.services.container_service.get_docker_client')
    def test_list_empty_containers(self, mock_get_client, service):
        """Test listing when no containers exist."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.containers.list.return_value = []
        mock_get_client.return_value = mock_client
        
        # Execute
        result = service.list_containers()
        
        # Verify
        assert result == []
    
    @patch('backend.services.container_service.get_docker_client')
    def test_list_containers_connection_error(self, mock_get_client, service):
        """Test handling of Docker connection error."""
        # Setup mock to raise connection error
        mock_get_client.side_effect = DockerConnectionError("Cannot connect")
        
        # Should raise DockerConnectionError
        with pytest.raises(DockerConnectionError):
            service.list_containers()


class TestGetContainer:
    """Test getting single container details."""
    
    @patch('backend.services.container_service.get_docker_client')
    def test_get_container_by_id(self, mock_get_client, service, mock_container):
        """Test getting container by ID."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.containers.get.return_value = mock_container
        mock_get_client.return_value = mock_client
        
        # Execute
        result = service.get_container('1234567890abcdef')
        
        # Verify
        assert result['name'] == 'test-container'
        assert result['full_id'] == '1234567890abcdef'
        assert 'environment' in result
        assert 'mounts' in result
        assert 'networks' in result
        mock_client.containers.get.assert_called_once_with('1234567890abcdef')
    
    @patch('backend.services.container_service.get_docker_client')
    def test_get_container_by_name(self, mock_get_client, service, mock_container):
        """Test getting container by name."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.containers.get.return_value = mock_container
        mock_get_client.return_value = mock_client
        
        # Execute
        result = service.get_container('test-container')
        
        # Verify
        assert result['name'] == 'test-container'
        mock_client.containers.get.assert_called_once_with('test-container')
    
    @patch('backend.services.container_service.get_docker_client')
    def test_get_container_not_found(self, mock_get_client, service):
        """Test handling of container not found."""
        # Setup mock to raise NotFound
        mock_client = MagicMock()
        mock_client.containers.get.side_effect = NotFound("Container not found")
        mock_get_client.return_value = mock_client
        
        # Should raise ContainerNotFoundError
        with pytest.raises(ContainerNotFoundError) as exc_info:
            service.get_container('nonexistent')
        
        assert 'not found' in str(exc_info.value).lower()


class TestStartContainer:
    """Test container start operation."""
    
    @patch('backend.services.container_service.get_docker_client')
    def test_start_stopped_container(self, mock_get_client, service, mock_container):
        """Test starting a stopped container."""
        # Setup mock - container is stopped
        mock_container.status = 'exited'
        mock_client = MagicMock()
        mock_client.containers.get.return_value = mock_container
        mock_get_client.return_value = mock_client
        
        # Execute
        result = service.start_container('test-container')
        
        # Verify
        assert result['name'] == 'test-container'
        mock_container.start.assert_called_once()
        mock_container.reload.assert_called()  # Should reload to get new status
    
    @patch('backend.services.container_service.get_docker_client')
    def test_start_already_running_container(self, mock_get_client, service, mock_container):
        """Test starting an already running container (idempotent)."""
        # Setup mock - container is already running
        mock_container.status = 'running'
        mock_client = MagicMock()
        mock_client.containers.get.return_value = mock_container
        mock_get_client.return_value = mock_client
        
        # Execute
        result = service.start_container('test-container')
        
        # Verify - should not call start()
        assert result['name'] == 'test-container'
        mock_container.start.assert_not_called()
    
    @patch('backend.services.container_service.get_docker_client')
    def test_start_container_not_found(self, mock_get_client, service):
        """Test starting non-existent container."""
        # Setup mock to raise NotFound
        mock_client = MagicMock()
        mock_client.containers.get.side_effect = NotFound("Container not found")
        mock_get_client.return_value = mock_client
        
        # Should raise ContainerNotFoundError
        with pytest.raises(ContainerNotFoundError):
            service.start_container('nonexistent')
    
    @patch('backend.services.container_service.get_docker_client')
    def test_start_container_api_error(self, mock_get_client, service, mock_container):
        """Test handling of API error during start."""
        # Setup mock - start raises APIError
        mock_container.status = 'exited'
        mock_container.start.side_effect = APIError("Port already in use")
        mock_client = MagicMock()
        mock_client.containers.get.return_value = mock_container
        mock_get_client.return_value = mock_client
        
        # Should raise ContainerOperationError
        with pytest.raises(ContainerOperationError) as exc_info:
            service.start_container('test-container')
        
        assert 'Failed to start' in str(exc_info.value)


class TestStopContainer:
    """Test container stop operation."""
    
    @patch('backend.services.container_service.get_docker_client')
    def test_stop_running_container(self, mock_get_client, service, mock_container):
        """Test stopping a running container."""
        # Setup mock - container is running
        mock_container.status = 'running'
        mock_client = MagicMock()
        mock_client.containers.get.return_value = mock_container
        mock_get_client.return_value = mock_client
        
        # Execute
        result = service.stop_container('test-container', timeout=10)
        
        # Verify
        assert result['name'] == 'test-container'
        mock_container.stop.assert_called_once_with(timeout=10)
        mock_container.reload.assert_called()
    
    @patch('backend.services.container_service.get_docker_client')
    def test_stop_already_stopped_container(self, mock_get_client, service, mock_container):
        """Test stopping an already stopped container (idempotent)."""
        # Setup mock - container already stopped
        mock_container.status = 'exited'
        mock_client = MagicMock()
        mock_client.containers.get.return_value = mock_container
        mock_get_client.return_value = mock_client
        
        # Execute
        result = service.stop_container('test-container')
        
        # Verify - should not call stop()
        assert result['name'] == 'test-container'
        mock_container.stop.assert_not_called()
    
    @patch('backend.services.container_service.get_docker_client')
    def test_stop_container_custom_timeout(self, mock_get_client, service, mock_container):
        """Test stop with custom timeout."""
        # Setup mock
        mock_container.status = 'running'
        mock_client = MagicMock()
        mock_client.containers.get.return_value = mock_container
        mock_get_client.return_value = mock_client
        
        # Execute with custom timeout
        service.stop_container('test-container', timeout=30)
        
        # Verify timeout passed correctly
        mock_container.stop.assert_called_once_with(timeout=30)
    
    @patch('backend.services.container_service.get_docker_client')
    def test_stop_container_not_found(self, mock_get_client, service):
        """Test stopping non-existent container."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.containers.get.side_effect = NotFound("Container not found")
        mock_get_client.return_value = mock_client
        
        # Should raise ContainerNotFoundError
        with pytest.raises(ContainerNotFoundError):
            service.stop_container('nonexistent')


class TestRestartContainer:
    """Test container restart operation."""
    
    @patch('backend.services.container_service.get_docker_client')
    def test_restart_container(self, mock_get_client, service, mock_container):
        """Test restarting a container."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.containers.get.return_value = mock_container
        mock_get_client.return_value = mock_client
        
        # Execute
        result = service.restart_container('test-container', timeout=10)
        
        # Verify
        assert result['name'] == 'test-container'
        mock_container.restart.assert_called_once_with(timeout=10)
        mock_container.reload.assert_called()
    
    @patch('backend.services.container_service.get_docker_client')
    def test_restart_container_not_found(self, mock_get_client, service):
        """Test restarting non-existent container."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.containers.get.side_effect = NotFound("Container not found")
        mock_get_client.return_value = mock_client
        
        # Should raise ContainerNotFoundError
        with pytest.raises(ContainerNotFoundError):
            service.restart_container('nonexistent')


class TestRemoveContainer:
    """Test container removal operation."""
    
    @patch('backend.services.container_service.get_docker_client')
    def test_remove_stopped_container(self, mock_get_client, service, mock_container):
        """Test removing a stopped container."""
        # Setup mock - container is stopped
        mock_container.status = 'exited'
        mock_client = MagicMock()
        mock_client.containers.get.return_value = mock_container
        mock_get_client.return_value = mock_client
        
        # Execute
        result = service.remove_container('test-container')
        
        # Verify
        assert result is True
        mock_container.remove.assert_called_once_with(force=False, v=False)
    
    @patch('backend.services.container_service.get_docker_client')
    def test_remove_running_container_without_force(self, mock_get_client, service, mock_container):
        """Test removing running container without force flag fails."""
        # Setup mock - container is running
        mock_container.status = 'running'
        mock_client = MagicMock()
        mock_client.containers.get.return_value = mock_container
        mock_get_client.return_value = mock_client
        
        # Should raise ContainerOperationError
        with pytest.raises(ContainerOperationError) as exc_info:
            service.remove_container('test-container', force=False)
        
        assert 'running' in str(exc_info.value).lower()
        mock_container.remove.assert_not_called()
    
    @patch('backend.services.container_service.get_docker_client')
    def test_remove_running_container_with_force(self, mock_get_client, service, mock_container):
        """Test force removing a running container."""
        # Setup mock - container is running
        mock_container.status = 'running'
        mock_client = MagicMock()
        mock_client.containers.get.return_value = mock_container
        mock_get_client.return_value = mock_client
        
        # Execute with force
        result = service.remove_container('test-container', force=True)
        
        # Verify
        assert result is True
        mock_container.remove.assert_called_once_with(force=True, v=False)
    
    @patch('backend.services.container_service.get_docker_client')
    def test_remove_container_with_volumes(self, mock_get_client, service, mock_container):
        """Test removing container with volumes."""
        # Setup mock
        mock_container.status = 'exited'
        mock_client = MagicMock()
        mock_client.containers.get.return_value = mock_container
        mock_get_client.return_value = mock_client
        
        # Execute
        result = service.remove_container('test-container', volumes=True)
        
        # Verify
        assert result is True
        mock_container.remove.assert_called_once_with(force=False, v=True)
    
    @patch('backend.services.container_service.get_docker_client')
    def test_remove_container_not_found(self, mock_get_client, service):
        """Test removing non-existent container."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.containers.get.side_effect = NotFound("Container not found")
        mock_get_client.return_value = mock_client
        
        # Should raise ContainerNotFoundError
        with pytest.raises(ContainerNotFoundError):
            service.remove_container('nonexistent')


class TestGetContainerLogs:
    """Test container log retrieval."""
    
    @patch('backend.services.container_service.get_docker_client')
    def test_get_logs(self, mock_get_client, service, mock_container):
        """Test getting container logs."""
        # Setup mock
        mock_container.logs.return_value = b"2024-01-01 Log line 1\n2024-01-01 Log line 2\n"
        mock_client = MagicMock()
        mock_client.containers.get.return_value = mock_container
        mock_get_client.return_value = mock_client
        
        # Execute
        result = service.get_container_logs('test-container', tail=100)
        
        # Verify
        assert "Log line 1" in result
        assert "Log line 2" in result
        mock_container.logs.assert_called_once_with(tail=100, since=None, timestamps=True)
    
    @patch('backend.services.container_service.get_docker_client')
    def test_get_logs_with_since(self, mock_get_client, service, mock_container):
        """Test getting logs with since parameter."""
        # Setup mock
        mock_container.logs.return_value = b"Recent log\n"
        mock_client = MagicMock()
        mock_client.containers.get.return_value = mock_container
        mock_get_client.return_value = mock_client
        
        # Execute
        result = service.get_container_logs('test-container', since='2024-01-01T00:00:00Z')
        
        # Verify
        mock_container.logs.assert_called_once_with(
            tail=100,
            since='2024-01-01T00:00:00Z',
            timestamps=True
        )


class TestGetContainerStats:
    """Test container statistics retrieval."""
    
    @patch('backend.services.container_service.get_docker_client')
    def test_get_stats(self, mock_get_client, service, mock_container):
        """Test getting container stats."""
        # Setup mock with stats data
        mock_stats = {
            'cpu_stats': {
                'cpu_usage': {'total_usage': 2000000000},
                'system_cpu_usage': 10000000000,
                'online_cpus': 4
            },
            'precpu_stats': {
                'cpu_usage': {'total_usage': 1000000000},
                'system_cpu_usage': 9000000000
            },
            'memory_stats': {
                'usage': 524288000,  # 500 MB
                'limit': 1073741824  # 1 GB
            },
            'networks': {
                'eth0': {
                    'rx_bytes': 1024000,
                    'tx_bytes': 512000
                }
            }
        }
        mock_container.stats.return_value = mock_stats
        mock_client = MagicMock()
        mock_client.containers.get.return_value = mock_container
        mock_get_client.return_value = mock_client
        
        # Execute
        result = service.get_container_stats('test-container')
        
        # Verify
        assert 'cpu_percent' in result
        assert 'memory_usage_mb' in result
        assert 'memory_limit_mb' in result
        assert 'memory_percent' in result
        assert result['memory_usage_mb'] == 500.0
        assert result['memory_limit_mb'] == 1024.0
        mock_container.stats.assert_called_once_with(stream=False)


class TestDataTransformation:
    """Test helper methods for data transformation."""
    
    def test_container_to_dict(self, service, mock_container):
        """Test basic container to dict conversion."""
        result = service._container_to_dict(mock_container)
        
        assert result['id'] == '1234567890ab'  # Short ID (12 chars)
        assert result['name'] == 'test-container'
        assert result['image'] == 'nginx:latest'
        assert result['status'] == 'running'
        assert 'ports' in result
        assert 'labels' in result
    
    def test_container_to_dict_detailed(self, service, mock_container):
        """Test detailed container to dict conversion."""
        result = service._container_to_dict_detailed(mock_container)
        
        assert result['full_id'] == '1234567890abcdef'
        assert 'environment' in result
        assert 'command' in result
        assert 'mounts' in result
        assert 'networks' in result
        assert 'restart_policy' in result
    
    def test_extract_ports(self, service, mock_container):
        """Test port extraction."""
        result = service._extract_ports(mock_container)
        
        assert '80/tcp' in result
        assert result['80/tcp'] == '0.0.0.0:8080'
    
    def test_extract_mounts(self, service, mock_container):
        """Test mount extraction."""
        result = service._extract_mounts(mock_container)
        
        assert len(result) == 1
        assert result[0]['type'] == 'volume'
        assert result[0]['destination'] == '/data'
        assert result[0]['rw'] is True
    
    def test_extract_networks(self, service, mock_container):
        """Test network extraction."""
        result = service._extract_networks(mock_container)
        
        assert 'bridge' in result
        assert result['bridge']['ip_address'] == '172.17.0.2'
        assert result['bridge']['gateway'] == '172.17.0.1'
