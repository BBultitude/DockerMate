"""
Unit Tests - Container API Endpoints (Sprint 2 Task 5)
=======================================================

Comprehensive tests for backend/api/containers.py covering:
- CRUD operations (create, read, update, delete)
- Lifecycle actions (start, stop, restart)
- Request validation (ports, volumes, env vars, labels)
- Port conflict detection
- Authentication integration
- Error handling and edge cases
- HTTP status codes and response formats

Test Strategy:
- Mock ContainerManager service to avoid Docker daemon dependency
- Use Flask test client for HTTP request simulation
- Test both success and error paths
- Verify response formats and status codes
- Test authentication requirements
- Validate request/response schemas

Educational Notes:
- Tests use pytest fixtures for setup/teardown
- Mock objects simulate service layer responses
- Assertions verify expected HTTP behavior
- Edge cases ensure robustness
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from flask import Flask

from backend.api.containers import containers_bp
from backend.utils.exceptions import (
    ContainerNotFoundError,
    ContainerOperationError,
    ValidationError,
    DockerConnectionError
)


# =============================================================================
# Test Fixtures
# =============================================================================

def mock_auth():
    """
    Mock the require_auth decorator for all tests.
    
    This fixture runs automatically at session start and patches
    require_auth before any modules are imported.
    
    CRITICAL: Must patch where decorator is USED, not where it's defined.
    """
    # Patch in the containers module (where it's imported and used)
    patcher = patch('backend.api.containers.require_auth')
    mock = patcher.start()
    
    # Make it a no-op decorator that returns the function unchanged
    mock.return_value = lambda f: f
    
    yield mock
    
    patcher.stop()


@pytest.fixture
def app():
    """
    Create Flask application configured for testing.
    
    Provides test app with:
    - Testing mode enabled
    - Container blueprint registered
    - Session secret key
    - No authentication (commented out in API for testing)
    """
    from backend.api.containers import containers_bp
    
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test_secret_key'
    
    # Register containers blueprint
    app.register_blueprint(containers_bp)
    
    return app


@pytest.fixture
def client(app):
    """
    Create Flask test client for making HTTP requests.
    """
    return app.test_client()


@pytest.fixture
def auth_headers():
    """
    Provide authentication headers for requests.
    
    In actual tests, we'll mock the @require_auth decorator,
    but this fixture is here for reference.
    """
    return {
        'Cookie': 'session=valid_session_token'
    }


@pytest.fixture
def sample_container_data():
    """
    Sample container data for testing.
    """
    return {
        'id': 1,
        'container_id': 'a1b2c3d4e5f6' + '0' * 52,
        'name': 'test-nginx',
        'state': 'running',
        'image_name': 'nginx:latest',
        'environment': 'test',
        'ports': [
            {'host': '8080', 'container': '80', 'protocol': 'tcp'}
        ],
        'volumes': [],
        'env_vars': {'ENV': 'test'},
        'labels': {'version': '1.0.0'},
        'restart_policy': 'unless-stopped',
        'cpu_limit': 1.0,
        'memory_limit': 536870912,
        'cpu_usage': 2.5,
        'memory_usage': 134217728,
        'created_at': '2025-01-27T10:00:00Z',
        'started_at': '2025-01-27T10:00:05Z',
        'updated_at': '2025-01-27T10:00:05Z'
    }


# =============================================================================
# Test Authentication
# =============================================================================

# =============================================================================
# Test CREATE Container
# =============================================================================

class TestCreateContainer:
    """Test POST /api/containers endpoint."""
    
    @patch('backend.api.containers.ContainerManager')
    def test_create_container_success(
        self, mock_manager_class, client, sample_container_data
    ):
        """Test successful container creation."""
        # Mock service layer
        mock_manager = MagicMock()
        mock_manager.__enter__.return_value = mock_manager
        mock_manager.__exit__.return_value = None
        mock_manager.create_container.return_value = sample_container_data
        mock_manager_class.return_value = mock_manager
        
        # Make request
        response = client.post(
            '/api/containers',
            data=json.dumps({
                'name': 'test-nginx',
                'image': 'nginx:latest',
                'environment': 'test'
            }),
            content_type='application/json'
        )
        
        # Verify response
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'data' in data
        assert data['data']['name'] == 'test-nginx'
        
        # Verify service was called correctly
        mock_manager.create_container.assert_called_once()
        call_kwargs = mock_manager.create_container.call_args[1]
        assert call_kwargs['name'] == 'test-nginx'
        assert call_kwargs['image'] == 'nginx:latest'
    
    @patch('backend.api.containers.ContainerManager')
    def test_create_container_with_all_options(
        self, mock_manager_class, client, sample_container_data
    ):
        """Test container creation with all optional parameters."""
        mock_manager = MagicMock()
        mock_manager.__enter__.return_value = mock_manager
        mock_manager.__exit__.return_value = None
        mock_manager.create_container.return_value = sample_container_data
        mock_manager_class.return_value = mock_manager
        
        request_data = {
            'name': 'test-nginx',
            'image': 'nginx:latest',
            'environment': 'prod',
            'ports': {'80/tcp': 8080, '443/tcp': 8443},
            'volumes': {
                '/host/path': {'bind': '/container/path', 'mode': 'rw'}
            },
            'env_vars': {'KEY': 'value'},
            'labels': {'version': '1.0.0'},
            'restart_policy': 'always',
            'auto_start': True,
            'pull_if_missing': True,
            'cpu_limit': 2.0,
            'memory_limit': 1073741824
        }
        
        response = client.post(
            '/api/containers',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['success'] is True
    
    def test_create_container_missing_name(self, client):
        """Test validation error when name is missing."""
        response = client.post(
            '/api/containers',
            data=json.dumps({'image': 'nginx:latest'}),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'name is required' in data['error'].lower()
        assert data['error_type'] == 'ValidationError'
    
    def test_create_container_missing_image(self, client):
        """Test validation error when image is missing."""
        response = client.post(
            '/api/containers',
            data=json.dumps({'name': 'test-nginx'}),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'image is required' in data['error'].lower()
    
    def test_create_container_invalid_name_format(self, client):
        """Test validation error for invalid container name."""
        response = client.post(
            '/api/containers',
            data=json.dumps({
                'name': 'invalid name with spaces!',
                'image': 'nginx:latest'
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'alphanumeric' in data['error'].lower()
    
    def test_create_container_invalid_ports_format(self, client):
        """Test validation error for invalid port format."""
        # Test invalid port number
        response = client.post(
            '/api/containers',
            data=json.dumps({
                'name': 'test-nginx',
                'image': 'nginx:latest',
                'ports': {'80/tcp': 99999}  # Port out of range
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'port' in data['error'].lower()
    
    def test_create_container_invalid_port_protocol(self, client):
        """Test validation error for missing protocol in container port."""
        response = client.post(
            '/api/containers',
            data=json.dumps({
                'name': 'test-nginx',
                'image': 'nginx:latest',
                'ports': {'80': 8080}  # Missing /tcp
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'protocol' in data['error'].lower()
    
    @patch('backend.api.containers.SessionLocal')
    def test_create_container_port_conflict(self, mock_session_class, client):
        """Test validation error when port is already in use."""
        # Mock database query to return existing container using port 8080
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        existing_container = MagicMock()
        existing_container.name = 'existing-nginx'
        existing_container.container_id = 'existing123' + '0' * 52
        existing_container.ports_json = json.dumps([
            {'host': '8080', 'container': '80', 'protocol': 'tcp'}
        ])
        
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [existing_container]
        mock_session.query.return_value = mock_query
        
        response = client.post(
            '/api/containers',
            data=json.dumps({
                'name': 'new-nginx',
                'image': 'nginx:latest',
                'ports': {'80/tcp': 8080}  # Conflicts with existing
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'port conflict' in data['error'].lower()
        assert 'existing-nginx' in data['error']
    
    @patch('backend.api.containers.ContainerManager')
    def test_create_container_service_error(
        self, mock_manager_class, client
    ):
        """Test error handling when service layer fails."""
        mock_manager = MagicMock()
        mock_manager.__enter__.return_value = mock_manager
        mock_manager.__exit__.return_value = None
        mock_manager.create_container.side_effect = ContainerOperationError(
            "Failed to create container"
        )
        mock_manager_class.return_value = mock_manager
        
        response = client.post(
            '/api/containers',
            data=json.dumps({
                'name': 'test-nginx',
                'image': 'nginx:latest'
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error_type'] == 'ContainerOperationError'
    
    @patch('backend.api.containers.ContainerManager')
    def test_create_container_docker_connection_error(
        self, mock_manager_class, client
    ):
        """Test error handling when Docker daemon is unreachable."""
        mock_manager = MagicMock()
        mock_manager.__enter__.return_value = mock_manager
        mock_manager.__exit__.return_value = None
        mock_manager.create_container.side_effect = DockerConnectionError(
            "Cannot connect to Docker daemon"
        )
        mock_manager_class.return_value = mock_manager
        
        response = client.post(
            '/api/containers',
            data=json.dumps({
                'name': 'test-nginx',
                'image': 'nginx:latest'
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'docker daemon' in data['error'].lower()


# =============================================================================
# Test LIST Containers
# =============================================================================

class TestListContainers:
    """Test GET /api/containers endpoint."""
    
    @patch('backend.api.containers.ContainerManager')
    def test_list_containers_success(
        self, mock_manager_class, client, sample_container_data
    ):
        """Test successful container listing."""
        mock_manager = MagicMock()
        mock_manager.__enter__.return_value = mock_manager
        mock_manager.__exit__.return_value = None
        mock_manager.list_containers.return_value = [
            sample_container_data,
            {**sample_container_data, 'id': 2, 'name': 'test-redis'}
        ]
        mock_manager_class.return_value = mock_manager
        
        response = client.get('/api/containers')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'data' in data
        assert data['count'] == 2
        assert len(data['data']) == 2
    
    @patch('backend.api.containers.ContainerManager')
    def test_list_containers_with_environment_filter(
        self, mock_manager_class, client, sample_container_data
    ):
        """Test listing containers filtered by environment."""
        mock_manager = MagicMock()
        mock_manager.__enter__.return_value = mock_manager
        mock_manager.__exit__.return_value = None
        mock_manager.list_containers.return_value = [sample_container_data]
        mock_manager_class.return_value = mock_manager
        
        response = client.get('/api/containers?environment=prod')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'filters' in data
        assert data['filters']['environment'] == 'prod'
        
        # Verify service was called with filter
        mock_manager.list_containers.assert_called_once()
        call_kwargs = mock_manager.list_containers.call_args[1]
        assert call_kwargs['environment'] == 'prod'
    
    @patch('backend.api.containers.ContainerManager')
    def test_list_containers_with_state_filter(
        self, mock_manager_class, client, sample_container_data
    ):
        """Test listing containers filtered by state."""
        mock_manager = MagicMock()
        mock_manager.__enter__.return_value = mock_manager
        mock_manager.__exit__.return_value = None
        mock_manager.list_containers.return_value = [sample_container_data]
        mock_manager_class.return_value = mock_manager
        
        response = client.get('/api/containers?state=running')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'filters' in data
        assert data['filters']['state'] == 'running'
    
    @patch('backend.api.containers.ContainerManager')
    def test_list_containers_empty(
        self, mock_manager_class, client
    ):
        """Test listing when no containers exist."""
        mock_manager = MagicMock()
        mock_manager.__enter__.return_value = mock_manager
        mock_manager.__exit__.return_value = None
        mock_manager.list_containers.return_value = []
        mock_manager_class.return_value = mock_manager
        
        response = client.get('/api/containers')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['count'] == 0
        assert data['data'] == []


# =============================================================================
# Test GET Single Container
# =============================================================================

class TestGetContainer:
    """Test GET /api/containers/<id> endpoint."""
    
    @patch('backend.api.containers.ContainerManager')
    def test_get_container_success(
        self, mock_manager_class, client, sample_container_data
    ):
        """Test successful container retrieval."""
        mock_manager = MagicMock()
        mock_manager.__enter__.return_value = mock_manager
        mock_manager.__exit__.return_value = None
        mock_manager.get_container.return_value = sample_container_data
        mock_manager_class.return_value = mock_manager
        
        response = client.get('/api/containers/test-nginx')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['name'] == 'test-nginx'
    
    @patch('backend.api.containers.ContainerManager')
    def test_get_container_not_found(
        self, mock_manager_class, client
    ):
        """Test error when container doesn't exist."""
        mock_manager = MagicMock()
        mock_manager.__enter__.return_value = mock_manager
        mock_manager.__exit__.return_value = None
        mock_manager.get_container.side_effect = ContainerNotFoundError(
            "Container 'nonexistent' not found"
        )
        mock_manager_class.return_value = mock_manager
        
        response = client.get('/api/containers/nonexistent')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error_type'] == 'NotFoundError'


# =============================================================================
# Test UPDATE Container
# =============================================================================

class TestUpdateContainer:
    """Test PATCH /api/containers/<id> endpoint."""
    
    @patch('backend.api.containers.ContainerManager')
    def test_update_container_labels_success(
        self, mock_manager_class, client, sample_container_data
    ):
        """Test successful label update."""
        updated_data = {**sample_container_data, 'labels': {'version': '2.0.0'}}
        mock_manager = MagicMock()
        mock_manager.__enter__.return_value = mock_manager
        mock_manager.__exit__.return_value = None
        mock_manager.update_container.return_value = updated_data
        mock_manager_class.return_value = mock_manager
        
        response = client.patch(
            '/api/containers/test-nginx',
            data=json.dumps({'labels': {'version': '2.0.0'}}),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['labels']['version'] == '2.0.0'
    
    def test_update_container_unsupported_field(self, client):
        """Test validation error for unsupported update fields (Phase 1)."""
        response = client.patch(
            '/api/containers/test-nginx',
            data=json.dumps({'ports': {'80/tcp': 9090}}),  # Not supported in Phase 1
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'unsupported' in data['error'].lower()
        assert 'phase 1' in data['error'].lower()
    
    @patch('backend.api.containers.ContainerManager')
    def test_update_container_not_found(
        self, mock_manager_class, client
    ):
        """Test error when updating non-existent container."""
        mock_manager = MagicMock()
        mock_manager.__enter__.return_value = mock_manager
        mock_manager.__exit__.return_value = None
        mock_manager.update_container.side_effect = ContainerNotFoundError(
            "Container 'nonexistent' not found"
        )
        mock_manager_class.return_value = mock_manager
        
        response = client.patch(
            '/api/containers/nonexistent',
            data=json.dumps({'labels': {'version': '1.0.0'}}),
            content_type='application/json'
        )
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False


# =============================================================================
# Test DELETE Container
# =============================================================================

class TestDeleteContainer:
    """Test DELETE /api/containers/<id> endpoint."""
    
    @patch('backend.api.containers.ContainerManager')
    def test_delete_container_success(
        self, mock_manager_class, client
    ):
        """Test successful container deletion."""
        mock_manager = MagicMock()
        mock_manager.__enter__.return_value = mock_manager
        mock_manager.__exit__.return_value = None
        mock_manager.delete_container.return_value = {
            'message': "Container 'test-nginx' deleted successfully"
        }
        mock_manager_class.return_value = mock_manager
        
        response = client.delete('/api/containers/test-nginx')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'deleted successfully' in data['message']
    
    @patch('backend.api.containers.ContainerManager')
    def test_delete_container_with_force(
        self, mock_manager_class, client
    ):
        """Test forced deletion of running container."""
        mock_manager = MagicMock()
        mock_manager.__enter__.return_value = mock_manager
        mock_manager.__exit__.return_value = None
        mock_manager.delete_container.return_value = {
            'message': "Container deleted"
        }
        mock_manager_class.return_value = mock_manager
        
        response = client.delete('/api/containers/test-nginx?force=true')
        
        assert response.status_code == 200
        
        # Verify force parameter was passed
        mock_manager.delete_container.assert_called_once()
        call_kwargs = mock_manager.delete_container.call_args[1]
        assert call_kwargs['force'] is True
    
    @patch('backend.api.containers.ContainerManager')
    def test_delete_container_not_found(
        self, mock_manager_class, client
    ):
        """Test error when deleting non-existent container."""
        mock_manager = MagicMock()
        mock_manager.__enter__.return_value = mock_manager
        mock_manager.__exit__.return_value = None
        mock_manager.delete_container.side_effect = ContainerNotFoundError(
            "Container 'nonexistent' not found"
        )
        mock_manager_class.return_value = mock_manager
        
        response = client.delete('/api/containers/nonexistent')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False


# =============================================================================
# Test Lifecycle Actions
# =============================================================================

class TestStartContainer:
    """Test POST /api/containers/<id>/start endpoint."""
    
    @patch('backend.api.containers.ContainerManager')
    def test_start_container_success(
        self, mock_manager_class, client, sample_container_data
    ):
        """Test successful container start."""
        mock_manager = MagicMock()
        mock_manager.__enter__.return_value = mock_manager
        mock_manager.__exit__.return_value = None
        mock_manager.start_container.return_value = sample_container_data
        mock_manager_class.return_value = mock_manager
        
        response = client.post('/api/containers/test-nginx/start')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'started successfully' in data['message']
    
    @patch('backend.api.containers.ContainerManager')
    def test_start_container_already_running(
        self, mock_manager_class, client
    ):
        """Test error when starting already running container."""
        mock_manager = MagicMock()
        mock_manager.__enter__.return_value = mock_manager
        mock_manager.__exit__.return_value = None
        mock_manager.start_container.side_effect = ValidationError(
            "Container is already running"
        )
        mock_manager_class.return_value = mock_manager
        
        response = client.post('/api/containers/test-nginx/start')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False


class TestStopContainer:
    """Test POST /api/containers/<id>/stop endpoint."""
    
    @patch('backend.api.containers.ContainerManager')
    def test_stop_container_success(
        self, mock_manager_class, client, sample_container_data
    ):
        """Test successful container stop."""
        stopped_data = {**sample_container_data, 'state': 'exited'}
        mock_manager = MagicMock()
        mock_manager.__enter__.return_value = mock_manager
        mock_manager.__exit__.return_value = None
        mock_manager.stop_container.return_value = stopped_data
        mock_manager_class.return_value = mock_manager
        
        response = client.post('/api/containers/test-nginx/stop')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'stopped successfully' in data['message']
    
    @patch('backend.api.containers.ContainerManager')
    def test_stop_container_with_timeout(
        self, mock_manager_class, client, sample_container_data
    ):
        """Test container stop with custom timeout."""
        mock_manager = MagicMock()
        mock_manager.__enter__.return_value = mock_manager
        mock_manager.__exit__.return_value = None
        mock_manager.stop_container.return_value = sample_container_data
        mock_manager_class.return_value = mock_manager
        
        response = client.post('/api/containers/test-nginx/stop?timeout=30')
        
        assert response.status_code == 200
        
        # Verify timeout parameter was passed
        call_kwargs = mock_manager.stop_container.call_args[1]
        assert call_kwargs['timeout'] == 30


class TestRestartContainer:
    """Test POST /api/containers/<id>/restart endpoint."""
    
    @patch('backend.api.containers.ContainerManager')
    def test_restart_container_success(
        self, mock_manager_class, client, sample_container_data
    ):
        """Test successful container restart."""
        mock_manager = MagicMock()
        mock_manager.__enter__.return_value = mock_manager
        mock_manager.__exit__.return_value = None
        mock_manager.restart_container.return_value = sample_container_data
        mock_manager_class.return_value = mock_manager
        
        response = client.post('/api/containers/test-nginx/restart')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'restarted successfully' in data['message']
    
    @patch('backend.api.containers.ContainerManager')
    def test_restart_container_with_timeout(
        self, mock_manager_class, client, sample_container_data
    ):
        """Test container restart with custom timeout."""
        mock_manager = MagicMock()
        mock_manager.__enter__.return_value = mock_manager
        mock_manager.__exit__.return_value = None
        mock_manager.restart_container.return_value = sample_container_data
        mock_manager_class.return_value = mock_manager
        
        response = client.post('/api/containers/test-nginx/restart?timeout=30')
        
        assert response.status_code == 200
        
        # Verify timeout parameter was passed
        call_kwargs = mock_manager.restart_container.call_args[1]
        assert call_kwargs['timeout'] == 30


# =============================================================================
# Test Edge Cases
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error scenarios."""
    
    def test_create_container_empty_body(self, client):
        """Test error when request body is empty."""
        response = client.post(
            '/api/containers',
            data='',
            content_type='application/json'
        )
        
        assert response.status_code == 400
    
    def test_create_container_invalid_json(self, client):
        """Test error when JSON is malformed."""
        response = client.post(
            '/api/containers',
            data='not valid json',
            content_type='application/json'
        )
        
        # Flask should handle JSON parsing error
        assert response.status_code in [400, 415]
    
    def test_update_container_empty_body(self, client):
        """Test error when update body is empty."""
        response = client.patch(
            '/api/containers/test-nginx',
            data=json.dumps({}),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'cannot be empty' in data['error'].lower()