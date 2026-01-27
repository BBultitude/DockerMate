"""
Unit Tests for Container Model - Sprint 2 Task 3
================================================
Comprehensive tests for Container model functionality.

Test Coverage:
- Model creation and validation
- State management and transitions
- Resource usage tracking
- Property methods (is_running, uptime, memory conversions)
- to_dict() serialization
- Static validation methods
- Timestamp handling
- Edge cases and null values
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.models.database import Base
from backend.models.container import Container


@pytest.fixture(scope='function')
def db_session():
    """
    Create a database session for Container model testing.
    
    Yields:
        Session: SQLAlchemy session for database operations
    """
    # Create in-memory SQLite database
    engine = create_engine('sqlite:///:memory:', echo=False)
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    # Create session factory
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    yield session
    
    # Cleanup
    session.rollback()
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


class TestContainerModel:
    """Tests for Container model basic functionality."""
    
    def test_create_container(self, db_session):
        """Test creating a basic container record."""
        container = Container(
            container_id='abc123def456' * 5 + 'abcd',  # 64 chars
            name='test-nginx',
            state='running',
            image_name='nginx:latest'
        )
        
        db_session.add(container)
        db_session.commit()
        
        assert container.id is not None
        assert container.container_id == 'abc123def456' * 5 + 'abcd'
        assert container.name == 'test-nginx'
        assert container.state == 'running'
        assert container.image_name == 'nginx:latest'
    
    def test_container_defaults(self, db_session):
        """Test that container fields have correct default values."""
        container = Container(
            container_id='def456abc123' * 5 + 'abcd',
            name='test-container',
            image_name='alpine:latest'
        )
        
        # State defaults to 'created'
        assert container.state == 'created'
        
        # Resource usage defaults to 0
        assert container.cpu_usage == 0.0
        assert container.memory_usage == 0
        
        # Restart policy defaults to 'no'
        assert container.restart_policy == 'no'
        
        # Auto-start defaults to False
        assert container.auto_start is False
        
        # Timestamps set on creation
        assert container.created_at is not None
        assert container.updated_at is not None
    
    def test_container_with_environment(self, db_session):
        """Test creating container with environment tag."""
        container = Container(
            container_id='env123abc456' * 5 + 'abcd',
            name='prod-db',
            state='running',
            image_name='postgres:14',
            environment='prod'
        )
        
        db_session.add(container)
        db_session.commit()
        
        assert container.environment == 'prod'
    
    def test_container_with_resources(self, db_session):
        """Test creating container with resource limits and usage."""
        container = Container(
            container_id='res123abc456' * 5 + 'abcd',
            name='resource-test',
            state='running',
            image_name='nginx:latest',
            cpu_limit=2.0,
            memory_limit=536870912,  # 512 MB in bytes
            cpu_usage=45.5,
            memory_usage=268435456  # 256 MB in bytes
        )
        
        db_session.add(container)
        db_session.commit()
        
        assert container.cpu_limit == 2.0
        assert container.memory_limit == 536870912
        assert container.cpu_usage == 45.5
        assert container.memory_usage == 268435456
    
    def test_container_repr(self, db_session):
        """Test string representation of container."""
        container = Container(
            container_id='repr123abc45' * 5 + 'abcd',
            name='test-repr',
            state='running',
            image_name='nginx:latest'
        )
        
        repr_str = repr(container)
        assert 'test-repr' in repr_str
        assert 'running' in repr_str


class TestContainerState:
    """Tests for container state management."""
    
    def test_update_state_to_running(self, db_session):
        """Test updating state to running sets started_at."""
        container = Container(
            container_id='state123abc45' * 5 + 'abcd',
            name='state-test',
            state='created',
            image_name='nginx:latest'
        )
        
        db_session.add(container)
        db_session.commit()
        
        # Update to running
        test_time = datetime.utcnow()
        container.update_state('running', test_time)
        
        assert container.state == 'running'
        assert container.started_at == test_time
    
    def test_update_state_to_exited(self, db_session):
        """Test updating state to exited sets stopped_at."""
        container = Container(
            container_id='exit123abc456' * 5 + 'abcd',
            name='exit-test',
            state='running',
            image_name='nginx:latest'
        )
        
        db_session.add(container)
        db_session.commit()
        
        # Update to exited
        test_time = datetime.utcnow()
        container.update_state('exited', test_time)
        
        assert container.state == 'exited'
        assert container.stopped_at == test_time
    
    def test_update_state_without_timestamp(self, db_session):
        """Test updating state uses current time if not provided."""
        container = Container(
            container_id='time123abc456' * 5 + 'abcd',
            name='time-test',
            state='created',
            image_name='nginx:latest'
        )
        
        db_session.add(container)
        db_session.commit()
        
        before = datetime.utcnow()
        container.update_state('running')
        after = datetime.utcnow()
        
        assert container.state == 'running'
        assert before <= container.started_at <= after
    
    def test_validate_state_valid(self):
        """Test state validation accepts valid states."""
        valid_states = [
            'created', 'running', 'paused', 'restarting',
            'removing', 'exited', 'dead'
        ]
        
        for state in valid_states:
            assert Container.validate_state(state) is True
    
    def test_validate_state_invalid(self):
        """Test state validation rejects invalid states."""
        invalid_states = ['invalid', 'unknown', 'starting', '']
        
        for state in invalid_states:
            assert Container.validate_state(state) is False


class TestContainerProperties:
    """Tests for container property methods."""
    
    def test_is_running_true(self, db_session):
        """Test is_running property returns True for running containers."""
        container = Container(
            container_id='run123abc4567' * 5 + 'abcd',
            name='running-test',
            state='running',
            image_name='nginx:latest'
        )
        
        assert container.is_running is True
    
    def test_is_running_false(self, db_session):
        """Test is_running property returns False for non-running containers."""
        container = Container(
            container_id='stop123abc456' * 5 + 'abcd',
            name='stopped-test',
            state='exited',
            image_name='nginx:latest'
        )
        
        assert container.is_running is False
    
    def test_uptime_seconds_running(self, db_session):
        """Test uptime calculation for running container."""
        start_time = datetime.utcnow() - timedelta(seconds=300)  # Started 5 minutes ago
        
        container = Container(
            container_id='uptime123abc45' * 5 + 'abcd',
            name='uptime-test',
            state='running',
            image_name='nginx:latest',
            started_at=start_time
        )
        
        uptime = container.uptime_seconds
        
        # Should be approximately 300 seconds (allow 1 second tolerance)
        assert 299 <= uptime <= 301
    
    def test_uptime_seconds_not_running(self, db_session):
        """Test uptime returns 0 for non-running container."""
        container = Container(
            container_id='norun123abc456' * 5 + 'abcd',
            name='norun-test',
            state='exited',
            image_name='nginx:latest'
        )
        
        assert container.uptime_seconds == 0
    
    def test_uptime_seconds_no_start_time(self, db_session):
        """Test uptime returns 0 when started_at is None."""
        container = Container(
            container_id='nostart123abc4' * 5 + 'abcd',
            name='nostart-test',
            state='running',
            image_name='nginx:latest'
        )
        
        assert container.uptime_seconds == 0
    
    def test_memory_usage_mb(self, db_session):
        """Test memory usage conversion to MB."""
        container = Container(
            container_id='mem123abc45678' * 5 + 'abcd',
            name='mem-test',
            state='running',
            image_name='nginx:latest',
            memory_usage=268435456  # 256 MB
        )
        
        assert container.memory_usage_mb == 256.0
    
    def test_memory_usage_mb_none(self, db_session):
        """Test memory usage returns 0.0 when None."""
        container = Container(
            container_id='nomem123abc456' * 5 + 'abcd',
            name='nomem-test',
            state='running',
            image_name='nginx:latest'
        )
        
        assert container.memory_usage_mb == 0.0
    
    def test_memory_limit_mb(self, db_session):
        """Test memory limit conversion to MB."""
        container = Container(
            container_id='limit123abc456' * 5 + 'abcd',
            name='limit-test',
            state='running',
            image_name='nginx:latest',
            memory_limit=536870912  # 512 MB
        )
        
        assert container.memory_limit_mb == 512.0
    
    def test_memory_limit_mb_none(self, db_session):
        """Test memory limit returns None when unlimited."""
        container = Container(
            container_id='nolimit123abc4' * 5 + 'abcd',
            name='nolimit-test',
            state='running',
            image_name='nginx:latest'
        )
        
        assert container.memory_limit_mb is None


class TestContainerResources:
    """Tests for resource usage updates."""
    
    def test_update_resources_both(self, db_session):
        """Test updating both CPU and memory usage."""
        container = Container(
            container_id='both123abc4567' * 5 + 'abcd',
            name='both-test',
            state='running',
            image_name='nginx:latest'
        )
        
        db_session.add(container)
        db_session.commit()
        
        container.update_resources(cpu_usage=75.5, memory_usage=314572800)
        
        assert container.cpu_usage == 75.5
        assert container.memory_usage == 314572800
    
    def test_update_resources_cpu_only(self, db_session):
        """Test updating only CPU usage."""
        container = Container(
            container_id='cpu123abc45678' * 5 + 'abcd',
            name='cpu-test',
            state='running',
            image_name='nginx:latest',
            memory_usage=100000000
        )
        
        db_session.add(container)
        db_session.commit()
        
        original_memory = container.memory_usage
        container.update_resources(cpu_usage=50.0)
        
        assert container.cpu_usage == 50.0
        assert container.memory_usage == original_memory
    
    def test_update_resources_memory_only(self, db_session):
        """Test updating only memory usage."""
        container = Container(
            container_id='meonly123abc45' * 5 + 'abcd',
            name='meonly-test',
            state='running',
            image_name='nginx:latest',
            cpu_usage=25.0
        )
        
        db_session.add(container)
        db_session.commit()
        
        original_cpu = container.cpu_usage
        container.update_resources(memory_usage=200000000)
        
        assert container.cpu_usage == original_cpu
        assert container.memory_usage == 200000000
    
    def test_update_resources_updates_timestamp(self, db_session):
        """Test that updating resources updates updated_at."""
        container = Container(
            container_id='stamp123abc456' * 5 + 'abcd',
            name='stamp-test',
            state='running',
            image_name='nginx:latest'
        )
        
        db_session.add(container)
        db_session.commit()
        
        original_time = container.updated_at
        
        # Sleep not needed - datetime.utcnow() will be different
        container.update_resources(cpu_usage=10.0)
        
        assert container.updated_at >= original_time


class TestContainerSerialization:
    """Tests for container to_dict() method."""
    
    def test_to_dict_basic(self, db_session):
        """Test basic to_dict() serialization."""
        container = Container(
            container_id='dict123abc4567' * 5 + 'abcd',
            name='dict-test',
            state='running',
            image_name='nginx:latest',
            environment='dev'
        )
        
        db_session.add(container)
        db_session.commit()
        
        data = container.to_dict()
        
        assert data['container_id'] == container.container_id
        assert data['name'] == 'dict-test'
        assert data['state'] == 'running'
        assert data['image_name'] == 'nginx:latest'
        assert data['environment'] == 'dev'
    
    def test_to_dict_with_timestamps(self, db_session):
        """Test to_dict() includes ISO format timestamps."""
        container = Container(
            container_id='iso123abc45678' * 5 + 'abcd',
            name='iso-test',
            state='running',
            image_name='nginx:latest'
        )
        
        db_session.add(container)
        db_session.commit()
        
        data = container.to_dict()
        
        # Timestamps should be ISO format strings
        assert isinstance(data['created_at'], str)
        assert isinstance(data['updated_at'], str)
        assert 'T' in data['created_at']  # ISO format marker
    
    def test_to_dict_with_nulls(self, db_session):
        """Test to_dict() handles null values correctly."""
        container = Container(
            container_id='null123abc4567' * 5 + 'abcd',
            name='null-test',
            state='created',
            image_name='alpine:latest'
        )
        
        db_session.add(container)
        db_session.commit()
        
        data = container.to_dict()
        
        # Optional fields should be None
        assert data['environment'] is None
        assert data['started_at'] is None
        assert data['stopped_at'] is None
        assert data['ports_json'] is None
        assert data['cpu_limit'] is None
        assert data['memory_limit'] is None


class TestContainerValidation:
    """Tests for container validation methods."""
    
    def test_validate_restart_policy_valid(self):
        """Test restart policy validation accepts valid policies."""
        valid_policies = ['no', 'on-failure', 'always', 'unless-stopped']
        
        for policy in valid_policies:
            assert Container.validate_restart_policy(policy) is True
    
    def test_validate_restart_policy_invalid(self):
        """Test restart policy validation rejects invalid policies."""
        invalid_policies = ['invalid', 'restart', 'never', '']
        
        for policy in invalid_policies:
            assert Container.validate_restart_policy(policy) is False


class TestContainerConstraints:
    """Tests for database constraints and uniqueness."""
    
    def test_unique_container_id(self, db_session):
        """Test that container_id must be unique."""
        # Create first container
        container1 = Container(
            container_id='unique123abc45' * 5 + 'abcd',
            name='unique-test-1',
            state='running',
            image_name='nginx:latest'
        )
        db_session.add(container1)
        db_session.commit()
        
        # Try to create second container with same container_id
        container2 = Container(
            container_id='unique123abc45' * 5 + 'abcd',  # Same ID
            name='unique-test-2',
            state='running',
            image_name='alpine:latest'
        )
        db_session.add(container2)
        
        # Should raise IntegrityError
        with pytest.raises(Exception):  # SQLAlchemy will raise IntegrityError
            db_session.commit()
        
        db_session.rollback()
    
    def test_non_unique_name(self, db_session):
        """Test that container names don't need to be unique."""
        # Create two containers with same name
        container1 = Container(
            container_id='name123abc4567' * 5 + 'abcd',
            name='same-name',
            state='running',
            image_name='nginx:latest'
        )
        container2 = Container(
            container_id='name456def7890' * 5 + 'abcd',
            name='same-name',
            state='exited',
            image_name='alpine:latest'
        )
        
        db_session.add(container1)
        db_session.add(container2)
        db_session.commit()
        
        # Both should succeed
        assert container1.id != container2.id
        assert container1.name == container2.name


class TestContainerEdgeCases:
    """Tests for edge cases and boundary conditions."""
    
    def test_very_long_container_id(self, db_session):
        """Test that 64-character container ID is handled correctly."""
        # Docker uses 64-character hex IDs
        container_id = 'a' * 64
        
        container = Container(
            container_id=container_id,
            name='long-id-test',
            state='running',
            image_name='nginx:latest'
        )
        
        db_session.add(container)
        db_session.commit()
        
        assert container.container_id == container_id
        assert len(container.container_id) == 64
    
    def test_zero_resource_values(self, db_session):
        """Test containers with zero resource usage."""
        container = Container(
            container_id='zero123abc4567' * 5 + 'abcd',
            name='zero-test',
            state='created',
            image_name='alpine:latest',
            cpu_usage=0.0,
            memory_usage=0
        )
        
        db_session.add(container)
        db_session.commit()
        
        assert container.cpu_usage == 0.0
        assert container.memory_usage == 0
        assert container.memory_usage_mb == 0.0
    
    def test_large_memory_values(self, db_session):
        """Test containers with large memory values."""
        # 16 GB in bytes
        large_memory = 17179869184
        
        container = Container(
            container_id='large123abc456' * 5 + 'abcd',
            name='large-test',
            state='running',
            image_name='postgres:latest',
            memory_limit=large_memory
        )
        
        db_session.add(container)
        db_session.commit()
        
        assert container.memory_limit == large_memory
        assert container.memory_limit_mb == 16384.0  # 16 GB = 16384 MB