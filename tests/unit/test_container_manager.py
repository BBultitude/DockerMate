"""
Unit Tests - Container Manager Service (Sprint 2 Task 4)
=========================================================

Comprehensive tests for backend/services/container_manager.py covering:
- Container creation with validation and health checks
- Read operations (get, list with filters)
- Update operations (Phase 1: labels only)
- Delete operations with force/volume options
- Lifecycle operations (start, stop, restart)
- Hardware limit validation
- Error handling and edge cases
- Database synchronization

Test Strategy:
- Mock Docker SDK to avoid requiring Docker daemon
- Use in-memory SQLite for database tests
- Test validation logic independently
- Test error handling paths
- Verify database state updates

Educational Notes:
- Tests use pytest fixtures for setup/teardown
- MagicMock creates fake Docker objects
- Assertions verify expected behavior
- Edge cases ensure robustness
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime, timedelta
from docker.errors import NotFound, APIError, ImageNotFound
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models.database import Base
from backend.models.container import Container
from backend.models.host_config import HostConfig
from backend.services.container_manager import ContainerManager
from backend.utils.exceptions import (
    ContainerNotFoundError,
    ContainerOperationError,
    ValidationError
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture(scope='function')
def db_session():
    """
    Create in-memory database session for testing.
    
    Provides isolated database for each test.
    """
    # Create in-memory SQLite
    engine = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(engine)
    
    # Create session
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    # Create host config (required by ContainerManager)
    host_config = HostConfig(
        id=1,
        profile_name='MEDIUM_SERVER',
        cpu_cores=8,
        ram_gb=32.0,
        max_containers=50,
        container_limit_warning_threshold=75,
        container_limit_critical_threshold=90
    )
    session.add(host_config)
    session.commit()
    
    yield session
    
    # Cleanup
    session.rollback()
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def mock_docker_client():
    """
    Mock Docker client for testing without Docker daemon.
    """
    client = MagicMock()
    
    # Setup default behaviors
    client.ping.return_value = True
    client.info.return_value = {
        'ServerVersion': '24.0.0',
        'Name': 'test-docker',
        'OperatingSystem': 'Linux'
    }
    
    return client


@pytest.fixture
def mock_docker_container():
    """
    Mock Docker container object with typical attributes.
    """
    container = MagicMock()
    container.id = 'abc123def456' * 5 + 'abcd'  # 64 chars
    container.short_id = 'abc123def456'[:12]
    container.name = '/test-container'
    container.status = 'running'
    container.labels = {}
    
    # Mock attrs (what Docker SDK returns from inspect)
    container.attrs = {
        'Id': container.id,
        'Name': '/test-container',
        'Created': '2024-01-20T10:00:00.000000000Z',
        'State': {
            'Status': 'running',
            'Running': True,
            'Paused': False,
            'Restarting': False,
            'OOMKilled': False,
            'Dead': False,
            'Pid': 1234,
            'ExitCode': 0,
            'Error': '',
            'StartedAt': '2024-01-20T10:00:05.000000000Z',
            'FinishedAt': '0001-01-01T00:00:00Z'
        },
        'Config': {
            'Image': 'nginx:latest',
            'Env': [],
            'Cmd': None,
            'Labels': {}
        },
        'HostConfig': {
            'RestartPolicy': {'Name': 'no', 'MaximumRetryCount': 0}
        }
    }
    
    return container


# =============================================================================
# Test Container Creation
# =============================================================================

class TestCreateContainer:
    """Test container creation with all validation and health checks."""
    
    @patch('backend.services.container_manager.get_docker_client')
    @patch('backend.services.container_manager.time.sleep')  # Skip health check wait
    def test_create_container_basic(
        self, mock_sleep, mock_get_client, db_session, mock_docker_client, mock_docker_container
    ):
        """Test basic container creation with minimal parameters."""
        # Setup mocks
        mock_get_client.return_value = mock_docker_client
        mock_docker_client.images.get.return_value = MagicMock()  # Image exists
        mock_docker_client.containers.create.return_value = mock_docker_container
        
        # Create manager
        manager = ContainerManager(db=db_session)
        
        # Create container
        result = manager.create_container(
            name='test-nginx',
            image='nginx:latest',
            auto_start=False  # Skip auto-start for this test
        )
        
        # Verify Docker SDK calls
        mock_docker_client.images.get.assert_called_once_with('nginx:latest')
        mock_docker_client.containers.create.assert_called_once()
        
        # Verify result
        assert result['name'] == 'test-container'
        assert result['state'] == 'running'
        assert result['image_name'] == 'nginx:latest'
        
        # Verify database record
        container = db_session.query(Container).filter(
            Container.name == 'test-container'
        ).first()
        assert container is not None
        assert container.container_id == mock_docker_container.id
    
    @patch('backend.services.container_manager.get_docker_client')
    @patch('backend.services.container_manager.time.sleep')
    @patch('backend.services.container_manager.random.uniform', return_value=10.0)
    def test_create_container_with_auto_start_and_health_check(
        self, mock_random, mock_sleep, mock_get_client, 
        db_session, mock_docker_client, mock_docker_container
    ):
        """Test container creation with auto-start and health validation."""
        # Setup mocks
        mock_get_client.return_value = mock_docker_client
        mock_docker_client.images.get.return_value = MagicMock()
        mock_docker_client.containers.create.return_value = mock_docker_container
        
        # Create manager
        manager = ContainerManager(db=db_session)
        
        # Create container with auto-start
        result = manager.create_container(
            name='test-nginx',
            image='nginx:latest',
            auto_start=True
        )
        
        # Verify start was called
        mock_docker_container.start.assert_called_once()
        
        # Verify health check wait occurred
        mock_sleep.assert_called_once_with(10.0)
        mock_docker_container.reload.assert_called_once()
        
        # Verify health status in result
        assert 'health_status' in result
        assert result['health_status']['running'] is True
        assert result['health_status']['healthy'] is True
    
    @patch('backend.services.container_manager.get_docker_client')
    def test_create_container_with_image_pull(
        self, mock_get_client, db_session, mock_docker_client, mock_docker_container
    ):
        """Test container creation with automatic image pull."""
        # Setup mocks - image not found initially
        mock_get_client.return_value = mock_docker_client
        mock_docker_client.images.get.side_effect = ImageNotFound('Image not found')
        mock_docker_client.images.pull.return_value = MagicMock()
        mock_docker_client.containers.create.return_value = mock_docker_container
        
        # Create manager
        manager = ContainerManager(db=db_session)
        
        # Create container with pull_if_missing=True
        result = manager.create_container(
            name='test-nginx',
            image='nginx:latest',
            auto_start=False,
            pull_if_missing=True
        )
        
        # Verify image pull was attempted
        mock_docker_client.images.get.assert_called_once_with('nginx:latest')
        mock_docker_client.images.pull.assert_called_once_with('nginx:latest')
    
    @patch('backend.services.container_manager.get_docker_client')
    def test_create_container_with_full_config(
        self, mock_get_client, db_session, mock_docker_client, mock_docker_container
    ):
        """Test container creation with all configuration options."""
        # Setup mocks
        mock_get_client.return_value = mock_docker_client
        mock_docker_client.images.get.return_value = MagicMock()
        mock_docker_client.containers.create.return_value = mock_docker_container
        
        # Create manager
        manager = ContainerManager(db=db_session)
        
        # Create container with full config
        result = manager.create_container(
            name='test-nginx',
            image='nginx:latest',
            environment='prod',
            ports={'80/tcp': 8080, '443/tcp': 8443},
            volumes={'/data': {'bind': '/usr/share/nginx/html', 'mode': 'ro'}},
            env_vars={'NGINX_HOST': 'example.com', 'NGINX_PORT': '80'},
            labels={'version': '1.0', 'environment': 'production'},
            restart_policy='unless-stopped',
            cpu_limit=2.0,
            memory_limit=1073741824,  # 1GB in bytes
            auto_start=False
        )
        
        # Verify create was called with correct config
        create_call = mock_docker_client.containers.create.call_args
        config = create_call[1]
        
        assert config['name'] == 'test-nginx'
        assert config['image'] == 'nginx:latest'
        assert config['ports'] == {'80/tcp': 8080, '443/tcp': 8443}
        assert config['volumes'] == {'/data': {'bind': '/usr/share/nginx/html', 'mode': 'ro'}}
        assert config['environment'] == {'NGINX_HOST': 'example.com', 'NGINX_PORT': '80'}
        assert config['labels'] == {'version': '1.0', 'environment': 'production'}
        
        # Verify host_config contains restart policy and resource limits
        assert 'host_config' in config
        assert 'RestartPolicy' in config['host_config']
        assert config['host_config']['RestartPolicy']['Name'] == 'unless-stopped'
        assert 'NanoCpus' in config['host_config']
        assert config['host_config']['NanoCpus'] == 2000000000  # 2.0 cores
        assert 'Memory' in config['host_config']
        assert config['host_config']['Memory'] == 1073741824  # 1GB
    
    def test_create_container_validation_empty_name(self, db_session):
        """Test validation rejects empty container name."""
        manager = ContainerManager(db=db_session)
        
        with pytest.raises(ValidationError) as exc:
            manager.create_container(name='', image='nginx:latest')
        
        assert 'cannot be empty' in str(exc.value).lower()
    
    def test_create_container_validation_duplicate_name(self, db_session):
        """Test validation rejects duplicate container name."""
        # Create existing container in database
        existing = Container(
            container_id='existing123' * 5 + 'abcd',
            name='test-nginx',
            state='running',
            image_name='nginx:latest'
        )
        db_session.add(existing)
        db_session.commit()
        
        # Try to create duplicate
        manager = ContainerManager(db=db_session)
        
        with pytest.raises(ValidationError) as exc:
            manager.create_container(name='test-nginx', image='nginx:latest')
        
        assert 'already exists' in str(exc.value).lower()
    
    def test_create_container_validation_invalid_restart_policy(self, db_session):
        """Test validation rejects invalid restart policy."""
        manager = ContainerManager(db=db_session)
        
        with pytest.raises(ValidationError) as exc:
            manager.create_container(
                name='test-nginx',
                image='nginx:latest',
                restart_policy='invalid-policy'
            )
        
        assert 'invalid restart policy' in str(exc.value).lower()
    
    def test_create_container_hardware_limit_exceeded(self, db_session):
        """Test hardware limit validation blocks creation when limit exceeded."""
        # Update host config to low limit
        host_config = db_session.query(HostConfig).first()
        host_config.max_containers = 2
        db_session.commit()
        
        # Create 2 existing containers
        for i in range(2):
            container = Container(
                container_id=f'container{i}' + '123' * 20,
                name=f'container-{i}',
                state='running',
                image_name='nginx:latest'
            )
            db_session.add(container)
        db_session.commit()
        
        # Try to create 3rd container (exceeds limit)
        manager = ContainerManager(db=db_session)
        
        with pytest.raises(ValidationError) as exc:
            manager.create_container(name='container-3', image='nginx:latest')
        
        assert 'limit exceeded' in str(exc.value).lower()
    
    @patch('backend.services.container_manager.get_docker_client')
    def test_create_container_docker_error(
        self, mock_get_client, db_session, mock_docker_client
    ):
        """Test error handling when Docker operation fails."""
        # Setup mocks to fail
        mock_get_client.return_value = mock_docker_client
        mock_docker_client.images.get.return_value = MagicMock()
        mock_docker_client.containers.create.side_effect = APIError(
            'Container creation failed'
        )
        
        # Create manager
        manager = ContainerManager(db=db_session)
        
        # Try to create container
        with pytest.raises(ContainerOperationError) as exc:
            manager.create_container(name='test-nginx', image='nginx:latest')
        
        assert 'failed to create' in str(exc.value).lower()


# =============================================================================
# Test Read Operations
# =============================================================================

class TestReadOperations:
    """Test container retrieval and listing."""
    
    @patch('backend.services.container_manager.get_docker_client')
    def test_get_container_by_name(
        self, mock_get_client, db_session, mock_docker_client, mock_docker_container
    ):
        """Test getting container by name."""
        # Create container in database
        container = Container(
            container_id=mock_docker_container.id,
            name='test-nginx',
            state='running',
            image_name='nginx:latest'
        )
        db_session.add(container)
        db_session.commit()
        
        # Setup mocks
        mock_get_client.return_value = mock_docker_client
        mock_docker_client.containers.get.return_value = mock_docker_container
        
        # Get container
        manager = ContainerManager(db=db_session)
        result = manager.get_container('test-nginx')
        
        # Verify
        assert result['name'] == 'test-container'
        mock_docker_client.containers.get.assert_called_once_with(mock_docker_container.id)
    
    @patch('backend.services.container_manager.get_docker_client')
    def test_get_container_by_id(
        self, mock_get_client, db_session, mock_docker_client, mock_docker_container
    ):
        """Test getting container by Docker ID."""
        # Create container in database
        container = Container(
            container_id=mock_docker_container.id,
            name='test-nginx',
            state='running',
            image_name='nginx:latest'
        )
        db_session.add(container)
        db_session.commit()
        
        # Setup mocks
        mock_get_client.return_value = mock_docker_client
        mock_docker_client.containers.get.return_value = mock_docker_container
        
        # Get container
        manager = ContainerManager(db=db_session)
        result = manager.get_container(mock_docker_container.id)
        
        # Verify
        assert result['name'] == 'test-container'
    
    def test_get_container_not_found(self, db_session):
        """Test error when container doesn't exist."""
        manager = ContainerManager(db=db_session)
        
        with pytest.raises(ContainerNotFoundError):
            manager.get_container('nonexistent')
    
    def test_list_containers_all(self, db_session):
        """Test listing all containers."""
        # Create test containers
        containers = [
            Container(
                container_id=f'container{i}' + '123' * 20,
                name=f'container-{i}',
                state='running' if i % 2 == 0 else 'exited',
                environment='dev' if i < 2 else 'prod',
                image_name='nginx:latest'
            )
            for i in range(4)
        ]
        for container in containers:
            db_session.add(container)
        db_session.commit()
        
        # List all containers
        manager = ContainerManager(db=db_session)
        results = manager.list_containers(all=True)
        
        # Verify
        assert len(results) == 4
    
    def test_list_containers_running_only(self, db_session):
        """Test listing only running containers."""
        # Create test containers
        containers = [
            Container(
                container_id=f'container{i}' + '123' * 20,
                name=f'container-{i}',
                state='running' if i % 2 == 0 else 'exited',
                image_name='nginx:latest'
            )
            for i in range(4)
        ]
        for container in containers:
            db_session.add(container)
        db_session.commit()
        
        # List running only
        manager = ContainerManager(db=db_session)
        results = manager.list_containers(all=False)
        
        # Verify only running containers returned
        assert len(results) == 2
        assert all(c['state'] == 'running' for c in results)
    
    def test_list_containers_by_environment(self, db_session):
        """Test filtering containers by environment tag."""
        # Create test containers
        containers = [
            Container(
                container_id=f'container{i}' + '123' * 20,
                name=f'container-{i}',
                state='running',
                environment='dev' if i < 2 else 'prod',
                image_name='nginx:latest'
            )
            for i in range(4)
        ]
        for container in containers:
            db_session.add(container)
        db_session.commit()
        
        # List dev containers
        manager = ContainerManager(db=db_session)
        results = manager.list_containers(environment='dev')
        
        # Verify
        assert len(results) == 2
        assert all(c['environment'] == 'dev' for c in results)
    
    def test_list_containers_by_state(self, db_session):
        """Test filtering containers by state."""
        # Create test containers
        containers = [
            Container(
                container_id=f'container{i}' + '123' * 20,
                name=f'container-{i}',
                state='running' if i % 2 == 0 else 'exited',
                image_name='nginx:latest'
            )
            for i in range(4)
        ]
        for container in containers:
            db_session.add(container)
        db_session.commit()
        
        # List exited containers
        manager = ContainerManager(db=db_session)
        results = manager.list_containers(state='exited')
        
        # Verify
        assert len(results) == 2
        assert all(c['state'] == 'exited' for c in results)


# =============================================================================
# Test Update Operation (Phase 1: Labels Only)
# =============================================================================

class TestUpdateContainer:
    """Test container update operations (Phase 1: labels only)."""
    
    @patch('backend.services.container_manager.get_docker_client')
    def test_update_container_labels(
        self, mock_get_client, db_session, mock_docker_client, mock_docker_container
    ):
        """Test updating container labels."""
        # Create container in database
        container = Container(
            container_id=mock_docker_container.id,
            name='test-nginx',
            state='running',
            image_name='nginx:latest'
        )
        db_session.add(container)
        db_session.commit()
        
        # Setup mocks
        mock_get_client.return_value = mock_docker_client
        mock_docker_client.containers.get.return_value = mock_docker_container
        
        # Update labels
        manager = ContainerManager(db=db_session)
        result = manager.update_container(
            'test-nginx',
            labels={'version': '2.0', 'env': 'production'}
        )
        
        # Verify database timestamp updated
        db_session.refresh(container)
        assert container.updated_at is not None
    
    def test_update_container_not_found(self, db_session):
        """Test error when updating nonexistent container."""
        manager = ContainerManager(db=db_session)
        
        with pytest.raises(ContainerNotFoundError):
            manager.update_container('nonexistent', labels={'test': 'value'})


# =============================================================================
# Test Delete Operation
# =============================================================================

class TestDeleteContainer:
    """Test container deletion."""
    
    @patch('backend.services.container_manager.get_docker_client')
    def test_delete_stopped_container(
        self, mock_get_client, db_session, mock_docker_client, mock_docker_container
    ):
        """Test deleting a stopped container."""
        # Setup container as stopped
        mock_docker_container.status = 'exited'
        
        # Create container in database
        container = Container(
            container_id=mock_docker_container.id,
            name='test-nginx',
            state='exited',
            image_name='nginx:latest'
        )
        db_session.add(container)
        db_session.commit()
        
        # Setup mocks
        mock_get_client.return_value = mock_docker_client
        mock_docker_client.containers.get.return_value = mock_docker_container
        
        # Delete container
        manager = ContainerManager(db=db_session)
        result = manager.delete_container('test-nginx')
        
        # Verify Docker remove called
        mock_docker_container.remove.assert_called_once_with(force=False, v=False)
        
        # Verify result
        assert result['status'] == 'removed'
        
        # Verify database updated
        db_session.refresh(container)
        assert container.state == 'removed'
        assert container.stopped_at is not None
    
    @patch('backend.services.container_manager.get_docker_client')
    def test_delete_running_container_without_force(
        self, mock_get_client, db_session, mock_docker_client, mock_docker_container
    ):
        """Test deleting running container without force fails."""
        # Setup container as running
        mock_docker_container.status = 'running'
        
        # Create container in database
        container = Container(
            container_id=mock_docker_container.id,
            name='test-nginx',
            state='running',
            image_name='nginx:latest'
        )
        db_session.add(container)
        db_session.commit()
        
        # Setup mocks
        mock_get_client.return_value = mock_docker_client
        mock_docker_client.containers.get.return_value = mock_docker_container
        
        # Try to delete without force
        manager = ContainerManager(db=db_session)
        
        with pytest.raises(ContainerOperationError) as exc:
            manager.delete_container('test-nginx', force=False)
        
        assert 'running' in str(exc.value).lower()
        assert 'force' in str(exc.value).lower()
    
    @patch('backend.services.container_manager.get_docker_client')
    def test_delete_running_container_with_force(
        self, mock_get_client, db_session, mock_docker_client, mock_docker_container
    ):
        """Test force deleting a running container."""
        # Setup container as running
        mock_docker_container.status = 'running'
        
        # Create container in database
        container = Container(
            container_id=mock_docker_container.id,
            name='test-nginx',
            state='running',
            image_name='nginx:latest'
        )
        db_session.add(container)
        db_session.commit()
        
        # Setup mocks
        mock_get_client.return_value = mock_docker_client
        mock_docker_client.containers.get.return_value = mock_docker_container
        
        # Delete with force
        manager = ContainerManager(db=db_session)
        result = manager.delete_container('test-nginx', force=True)
        
        # Verify Docker remove called with force
        mock_docker_container.remove.assert_called_once_with(force=True, v=False)
        assert result['status'] == 'removed'
    
    @patch('backend.services.container_manager.get_docker_client')
    def test_delete_container_with_volumes(
        self, mock_get_client, db_session, mock_docker_client, mock_docker_container
    ):
        """Test deleting container with volume removal."""
        # Setup container as stopped
        mock_docker_container.status = 'exited'
        
        # Create container in database
        container = Container(
            container_id=mock_docker_container.id,
            name='test-nginx',
            state='exited',
            image_name='nginx:latest'
        )
        db_session.add(container)
        db_session.commit()
        
        # Setup mocks
        mock_get_client.return_value = mock_docker_client
        mock_docker_client.containers.get.return_value = mock_docker_container
        
        # Delete with volume removal
        manager = ContainerManager(db=db_session)
        manager.delete_container('test-nginx', remove_volumes=True)
        
        # Verify volumes removed
        mock_docker_container.remove.assert_called_once_with(force=False, v=True)


# =============================================================================
# Test Lifecycle Operations
# =============================================================================

class TestLifecycleOperations:
    """Test container start, stop, and restart operations."""
    
    @patch('backend.services.container_manager.get_docker_client')
    def test_start_container(
        self, mock_get_client, db_session, mock_docker_client, mock_docker_container
    ):
        """Test starting a stopped container."""
        # Setup container as stopped
        mock_docker_container.status = 'exited'
        
        # Create container in database
        container = Container(
            container_id=mock_docker_container.id,
            name='test-nginx',
            state='exited',
            image_name='nginx:latest'
        )
        db_session.add(container)
        db_session.commit()
        
        # Setup mocks
        mock_get_client.return_value = mock_docker_client
        mock_docker_client.containers.get.return_value = mock_docker_container
        
        # Mock the start operation to update status
        def mock_start():
            mock_docker_container.status = 'running'
            mock_docker_container.attrs['State']['Status'] = 'running'
            mock_docker_container.attrs['State']['Running'] = True
        
        mock_docker_container.start.side_effect = mock_start
        
        # Start container
        manager = ContainerManager(db=db_session)
        result = manager.start_container('test-nginx')
        
        # Verify Docker start called
        mock_docker_container.start.assert_called_once()
        
        # Verify database updated
        db_session.refresh(container)
        assert container.state == 'running'
        assert container.started_at is not None
    
    @patch('backend.services.container_manager.get_docker_client')
    def test_start_already_running_container(
        self, mock_get_client, db_session, mock_docker_client, mock_docker_container
    ):
        """Test starting an already running container (no-op)."""
        # Setup container as running
        mock_docker_container.status = 'running'
        
        # Create container in database
        container = Container(
            container_id=mock_docker_container.id,
            name='test-nginx',
            state='running',
            image_name='nginx:latest'
        )
        db_session.add(container)
        db_session.commit()
        
        # Setup mocks
        mock_get_client.return_value = mock_docker_client
        mock_docker_client.containers.get.return_value = mock_docker_container
        
        # Try to start
        manager = ContainerManager(db=db_session)
        result = manager.start_container('test-nginx')
        
        # Verify start not called (already running)
        mock_docker_container.start.assert_not_called()
    
    @patch('backend.services.container_manager.get_docker_client')
    def test_stop_container(
        self, mock_get_client, db_session, mock_docker_client, mock_docker_container
    ):
        """Test stopping a running container."""
        # Setup container as running
        mock_docker_container.status = 'running'
        
        # Create container in database
        container = Container(
            container_id=mock_docker_container.id,
            name='test-nginx',
            state='running',
            image_name='nginx:latest'
        )
        db_session.add(container)
        db_session.commit()
        
        # Setup mocks
        mock_get_client.return_value = mock_docker_client
        mock_docker_client.containers.get.return_value = mock_docker_container
        
        # Mock the stop operation to update status
        def mock_stop(timeout):
            mock_docker_container.status = 'exited'
            mock_docker_container.attrs['State']['Status'] = 'exited'
            mock_docker_container.attrs['State']['Running'] = False
        
        mock_docker_container.stop.side_effect = mock_stop
        
        # Stop container
        manager = ContainerManager(db=db_session)
        result = manager.stop_container('test-nginx', timeout=5)
        
        # Verify Docker stop called with timeout
        mock_docker_container.stop.assert_called_once_with(timeout=5)
        
        # Verify database updated
        db_session.refresh(container)
        assert container.state == 'exited'
        assert container.stopped_at is not None
    
    @patch('backend.services.container_manager.get_docker_client')
    def test_restart_container(
        self, mock_get_client, db_session, mock_docker_client, mock_docker_container
    ):
        """Test restarting a container."""
        # Create container in database
        container = Container(
            container_id=mock_docker_container.id,
            name='test-nginx',
            state='running',
            image_name='nginx:latest'
        )
        db_session.add(container)
        db_session.commit()
        
        # Setup mocks
        mock_get_client.return_value = mock_docker_client
        mock_docker_client.containers.get.return_value = mock_docker_container
        
        # Restart container
        manager = ContainerManager(db=db_session)
        result = manager.restart_container('test-nginx', timeout=5)
        
        # Verify Docker restart called
        mock_docker_container.restart.assert_called_once_with(timeout=5)
        
        # Verify database updated
        db_session.refresh(container)
        assert container.state == 'running'
        assert container.started_at is not None


# =============================================================================
# Test Context Manager
# =============================================================================

class TestContextManager:
    """Test ContainerManager as context manager."""
    
    def test_context_manager_cleanup(self, db_session):
        """Test that context manager closes session properly."""
        # Create manager without providing session
        # (it will create its own and should clean it up)
        with patch('backend.services.container_manager.SessionLocal') as mock_session_factory:
            mock_session = MagicMock()
            mock_session_factory.return_value = mock_session
            
            with ContainerManager() as manager:
                assert manager.db is mock_session
            
            # Verify session was closed
            mock_session.close.assert_called_once()
    
    def test_context_manager_no_cleanup_if_provided(self, db_session):
        """Test that provided session is not closed by context manager."""
        # Provide our own session
        with ContainerManager(db=db_session) as manager:
            assert manager.db is db_session
        
        # Session should still be open (not closed by context manager)
        # This is verified by the fact that db_session fixture cleanup
        # won't fail trying to close an already-closed session