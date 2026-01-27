"""
Unit Tests - Docker Client Wrapper

Tests for backend/utils/docker_client.py:
- Client connection and singleton behavior
- Health checking
- Error handling and reconnection
- Decorator functionality
- Context manager usage

Educational Notes:
- Tests use mocking to avoid requiring Docker daemon
- unittest.mock provides MagicMock for creating fake objects
- Patching replaces real functions with test doubles
- Tests verify behavior, not implementation
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from docker.errors import DockerException, APIError, NotFound

from backend.utils.docker_client import (
    get_docker_client,
    check_docker_connection,
    close_docker_client,
    docker_operation,
    DockerClientContext,
    _docker_client,
    _connection_healthy
)
from backend.utils.exceptions import DockerConnectionError


class TestGetDockerClient:
    """Test Docker client creation and singleton behavior."""
    
    @patch('backend.utils.docker_client.docker.from_env')
    def test_create_client_success(self, mock_from_env):
        """Test successful client creation."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.info.return_value = {
            'ServerVersion': '24.0.0',
            'Name': 'test-docker',
            'OperatingSystem': 'Ubuntu 22.04'
        }
        mock_from_env.return_value = mock_client
        
        # Reset global state
        import backend.utils.docker_client as dc
        dc._docker_client = None
        dc._connection_healthy = False
        
        # Get client
        client = get_docker_client()
        
        # Verify
        assert client is mock_client
        mock_from_env.assert_called_once()
        mock_client.ping.assert_called_once()
        mock_client.info.assert_called_once()
    
    @patch('backend.utils.docker_client.docker.from_env')
    def test_singleton_behavior(self, mock_from_env):
        """Test that get_docker_client returns same instance."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.info.return_value = {'ServerVersion': '24.0.0', 'Name': 'test', 'OperatingSystem': 'Linux'}
        mock_from_env.return_value = mock_client
        
        # Reset global state
        import backend.utils.docker_client as dc
        dc._docker_client = None
        dc._connection_healthy = False
        
        # Get client twice
        client1 = get_docker_client()
        client2 = get_docker_client()
        
        # Should be same instance
        assert client1 is client2
        
        # from_env should only be called once (singleton)
        assert mock_from_env.call_count == 1
    
    @patch('backend.utils.docker_client.docker.from_env')
    def test_force_reconnect(self, mock_from_env):
        """Test force reconnection creates new client."""
        # Setup mock
        mock_client1 = MagicMock()
        mock_client1.ping.return_value = True
        mock_client1.info.return_value = {'ServerVersion': '24.0.0', 'Name': 'test', 'OperatingSystem': 'Linux'}
        
        mock_client2 = MagicMock()
        mock_client2.ping.return_value = True
        mock_client2.info.return_value = {'ServerVersion': '24.0.0', 'Name': 'test', 'OperatingSystem': 'Linux'}
        
        mock_from_env.side_effect = [mock_client1, mock_client2]
        
        # Reset global state
        import backend.utils.docker_client as dc
        dc._docker_client = None
        dc._connection_healthy = False
        
        # Get client twice with force_reconnect
        client1 = get_docker_client()
        client2 = get_docker_client(force_reconnect=True)
        
        # Should be different instances
        assert client1 is not client2
        assert client1 is mock_client1
        assert client2 is mock_client2
        
        # from_env should be called twice
        assert mock_from_env.call_count == 2
    
    @patch('backend.utils.docker_client.docker.from_env')
    def test_connection_failure(self, mock_from_env):
        """Test handling of connection failure."""
        # Setup mock to raise exception
        mock_from_env.side_effect = DockerException("Cannot connect to Docker daemon")
        
        # Reset global state
        import backend.utils.docker_client as dc
        dc._docker_client = None
        dc._connection_healthy = False
        
        # Should raise DockerConnectionError
        with pytest.raises(DockerConnectionError) as exc_info:
            get_docker_client()
        
        assert "Cannot connect to Docker daemon" in str(exc_info.value)
    
    @patch('backend.utils.docker_client.docker.from_env')
    def test_ping_failure(self, mock_from_env):
        """Test handling of ping failure."""
        # Setup mock where client creates but ping fails
        mock_client = MagicMock()
        mock_client.ping.side_effect = DockerException("Connection refused")
        mock_from_env.return_value = mock_client
        
        # Reset global state
        import backend.utils.docker_client as dc
        dc._docker_client = None
        dc._connection_healthy = False
        
        # Should raise DockerConnectionError
        with pytest.raises(DockerConnectionError):
            get_docker_client()


class TestCheckDockerConnection:
    """Test Docker connection health checking."""
    
    @patch('backend.utils.docker_client.get_docker_client')
    def test_health_check_success(self, mock_get_client):
        """Test successful health check."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_get_client.return_value = mock_client
        
        # Reset global state
        import backend.utils.docker_client as dc
        dc._connection_healthy = False
        
        # Check connection
        result = check_docker_connection()
        
        # Verify
        assert result is True
        mock_client.ping.assert_called_once()
    
    @patch('backend.utils.docker_client.get_docker_client')
    def test_health_check_failure(self, mock_get_client):
        """Test failed health check."""
        # Setup mock to raise exception
        mock_get_client.side_effect = DockerConnectionError("Connection failed")
        
        # Reset global state
        import backend.utils.docker_client as dc
        dc._connection_healthy = True  # Start as healthy
        
        # Check connection
        result = check_docker_connection()
        
        # Should return False and update state
        assert result is False


class TestCloseDockerClient:
    """Test Docker client cleanup."""
    
    @patch('backend.utils.docker_client._docker_client')
    def test_close_client(self, mock_client):
        """Test closing Docker client."""
        # Setup mock
        mock_client.close = MagicMock()
        
        # Reset global state
        import backend.utils.docker_client as dc
        dc._docker_client = mock_client
        dc._connection_healthy = True
        
        # Close client
        close_docker_client()
        
        # Verify
        mock_client.close.assert_called_once()
    
    def test_close_no_client(self):
        """Test closing when no client exists."""
        # Reset global state
        import backend.utils.docker_client as dc
        dc._docker_client = None
        dc._connection_healthy = False
        
        # Should not raise exception
        close_docker_client()


class TestDockerOperationDecorator:
    """Test decorator for Docker operations."""
    
    @patch('backend.utils.docker_client.get_docker_client')
    def test_decorator_success(self, mock_get_client):
        """Test decorator allows successful operation."""
        # Create test function
        @docker_operation
        def test_function():
            return "success"
        
        # Execute
        result = test_function()
        
        # Verify
        assert result == "success"
    
    @patch('backend.utils.docker_client.get_docker_client')
    def test_decorator_notfound_reraises(self, mock_get_client):
        """Test decorator reraises NotFound exceptions."""
        # Create test function that raises NotFound
        @docker_operation
        def test_function():
            raise NotFound("Container not found")
        
        # Should reraise NotFound as-is
        with pytest.raises(NotFound):
            test_function()
    
    @patch('backend.utils.docker_client.get_docker_client')
    def test_decorator_apierror_reraises(self, mock_get_client):
        """Test decorator reraises APIError exceptions."""
        # Create test function that raises APIError
        @docker_operation
        def test_function():
            raise APIError("API error occurred")
        
        # Should reraise APIError as-is
        with pytest.raises(APIError):
            test_function()
    
    @patch('backend.utils.docker_client.get_docker_client')
    def test_decorator_docker_exception_retry(self, mock_get_client):
        """Test decorator retries on DockerException."""
        call_count = 0
        
        # Create test function that fails once then succeeds
        @docker_operation
        def test_function():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise DockerException("Connection lost")
            return "success"
        
        # Mock get_docker_client to succeed on reconnect
        mock_get_client.return_value = MagicMock()
        
        # Execute
        result = test_function()
        
        # Verify retry happened
        assert result == "success"
        assert call_count == 2  # Original call + 1 retry
        assert mock_get_client.call_count == 1  # Reconnection attempted
    
    @patch('backend.utils.docker_client.get_docker_client')
    def test_decorator_docker_exception_retry_fails(self, mock_get_client):
        """Test decorator raises DockerConnectionError if retry fails."""
        # Create test function that always fails
        @docker_operation
        def test_function():
            raise DockerException("Connection lost")
        
        # Mock get_docker_client for reconnect
        mock_get_client.return_value = MagicMock()
        
        # Execute
        with pytest.raises(DockerConnectionError) as exc_info:
            test_function()
        
        # Verify error message
        assert "retry unsuccessful" in str(exc_info.value)


class TestDockerClientContext:
    """Test context manager for Docker operations."""
    
    @patch('backend.utils.docker_client.get_docker_client')
    def test_context_manager_success(self, mock_get_client):
        """Test context manager provides client."""
        # Setup mock
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Use context manager
        with DockerClientContext() as client:
            assert client is mock_client
        
        # Verify get_docker_client was called
        mock_get_client.assert_called_once()
    
    @patch('backend.utils.docker_client.get_docker_client')
    def test_context_manager_exception_handling(self, mock_get_client):
        """Test context manager handles exceptions."""
        # Setup mock
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Use context manager with exception
        with pytest.raises(ValueError):
            with DockerClientContext() as client:
                raise ValueError("Test error")
        
        # Context manager should not suppress exception
        # But should still exit cleanly


class TestGlobalState:
    """Test global state management."""
    
    def test_initial_state(self):
        """Test initial global state."""
        import backend.utils.docker_client as dc
        
        # Global state should be initialized
        # (may not be None if other tests ran first, but should be consistent)
        assert isinstance(dc._connection_healthy, bool)
    
    @patch('backend.utils.docker_client.docker.from_env')
    def test_state_updates_on_connection(self, mock_from_env):
        """Test global state updates on successful connection."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.info.return_value = {'ServerVersion': '24.0.0', 'Name': 'test', 'OperatingSystem': 'Linux'}
        mock_from_env.return_value = mock_client
        
        # Reset global state
        import backend.utils.docker_client as dc
        dc._docker_client = None
        dc._connection_healthy = False
        
        # Get client
        get_docker_client()
        
        # State should be updated
        assert dc._connection_healthy is True
        assert dc._docker_client is mock_client
    
    @patch('backend.utils.docker_client.docker.from_env')
    def test_state_updates_on_failure(self, mock_from_env):
        """Test global state updates on connection failure."""
        # Setup mock to fail
        mock_from_env.side_effect = DockerException("Connection failed")
        
        # Reset global state
        import backend.utils.docker_client as dc
        dc._docker_client = None
        dc._connection_healthy = True  # Start as healthy
        
        # Try to get client
        with pytest.raises(DockerConnectionError):
            get_docker_client()
        
        # State should be updated to unhealthy
        assert dc._connection_healthy is False


# Educational: Pytest fixture example for common test setup
@pytest.fixture
def mock_docker_client():
    """
    Pytest fixture that provides a mocked Docker client.
    
    Fixtures are reusable test components that can be injected into tests.
    Use by adding parameter with same name to test function.
    
    Example:
        def test_something(mock_docker_client):
            # mock_docker_client is automatically provided
            pass
    """
    mock_client = MagicMock()
    mock_client.ping.return_value = True
    mock_client.info.return_value = {
        'ServerVersion': '24.0.0',
        'Name': 'test-docker',
        'OperatingSystem': 'Linux'
    }
    return mock_client


def test_fixture_example(mock_docker_client):
    """Example test using fixture."""
    # Fixture automatically provided
    assert mock_docker_client.ping() is True
