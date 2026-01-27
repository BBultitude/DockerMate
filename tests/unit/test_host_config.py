"""
Unit Tests for HostConfig Model

Tests the HostConfig database model including:
- Model creation and fields
- Singleton behavior (get_or_create)
- Container limit checking
- Limit message generation
- Dictionary serialization
"""

import pytest
from datetime import datetime
from backend.models.host_config import HostConfig
from backend.models.database import Base, SessionLocal, engine


@pytest.fixture(scope='function')
def db_session():
    """Create a fresh database session for each test"""
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    db = SessionLocal()
    
    yield db
    
    # Cleanup
    db.close()
    Base.metadata.drop_all(bind=engine)


class TestHostConfigModel:
    """Test HostConfig model basic functionality"""
    
    def test_create_host_config(self, db_session):
        """Test creating a HostConfig instance"""
        # Clear any existing config first
        db_session.query(HostConfig).delete()
        db_session.commit()
        
        config = HostConfig(
            profile_name='MEDIUM_SERVER',
            cpu_cores=8,
            ram_gb=32.0,
            is_raspberry_pi=False,
            max_containers=50
        )
        
        db_session.add(config)
        db_session.commit()
        
        # Verify it was created
        result = db_session.query(HostConfig).first()
        assert result is not None
        assert result.profile_name == 'MEDIUM_SERVER'
        assert result.cpu_cores == 8
        assert result.ram_gb == 32.0
    
    def test_host_config_default_values(self, db_session):
        """Test that default values are set correctly"""
        config = HostConfig(
            profile_name='TEST',
            cpu_cores=4,
            ram_gb=8.0
        )
        
        db_session.add(config)
        db_session.commit()
        db_session.refresh(config)
        
        # Check defaults
        assert config.max_containers == 50
        assert config.container_limit_warning_threshold == 75
        assert config.container_limit_critical_threshold == 90
        assert config.enable_continuous_monitoring is True
        assert config.enable_log_analysis is True
        assert config.enable_auto_update is True
        assert config.update_check_interval == 21600  # 6 hours
        assert config.health_check_interval == 300    # 5 minutes
        assert config.network_size_limit == '/24'
    
    def test_host_config_timestamps(self, db_session):
        """Test that timestamps are set automatically"""
        config = HostConfig(
            profile_name='TEST',
            cpu_cores=4,
            ram_gb=8.0
        )
        
        db_session.add(config)
        db_session.commit()
        db_session.refresh(config)
        
        assert config.detected_at is not None
        assert isinstance(config.detected_at, datetime)
    
    def test_host_config_repr(self, db_session):
        """Test string representation"""
        config = HostConfig(
            profile_name='MEDIUM_SERVER',
            cpu_cores=8,
            ram_gb=32.0,
            max_containers=50
        )
        
        repr_str = repr(config)
        assert 'MEDIUM_SERVER' in repr_str
        assert '8' in repr_str
        assert '32.0' in repr_str
        assert '50' in repr_str


class TestHostConfigSingleton:
    """Test singleton behavior (get_or_create)"""
    
    def test_get_or_create_creates_new(self, db_session):
        """Test get_or_create creates config if none exists"""
        config = HostConfig.get_or_create(db_session)
        
        assert config is not None
        assert config.id == 1
        assert config.profile_name == 'UNKNOWN'  # Default before detection
    
    def test_get_or_create_returns_existing(self, db_session):
        """Test get_or_create returns existing config"""
        # Create initial config
        config1 = HostConfig(
            id=1,
            profile_name='MEDIUM_SERVER',
            cpu_cores=8,
            ram_gb=32.0,
            max_containers=50
        )
        db_session.add(config1)
        db_session.commit()
        
        # Get config again (should return existing)
        config2 = HostConfig.get_or_create(db_session)
        
        assert config2.id == 1
        assert config2.profile_name == 'MEDIUM_SERVER'
        assert config2.cpu_cores == 8
        assert config2.ram_gb == 32.0
    
    def test_only_one_config_exists(self, db_session):
        """Test that only one HostConfig row exists"""
        HostConfig.get_or_create(db_session)
        HostConfig.get_or_create(db_session)
        
        count = db_session.query(HostConfig).count()
        assert count == 1


class TestContainerLimitChecking:
    """Test container limit checking logic"""
    
    def test_is_at_container_limit_none(self, db_session):
        """Test when container count is well below limit"""
        config = HostConfig(
            profile_name='MEDIUM_SERVER',
            cpu_cores=8,
            ram_gb=32.0,
            max_containers=50,
            container_limit_warning_threshold=75,
            container_limit_critical_threshold=90
        )
        
        at_limit, level = config.is_at_container_limit(current_count=20)
        
        assert at_limit is False
        assert level == 'none'
    
    def test_is_at_container_limit_warning(self, db_session):
        """Test when container count reaches warning threshold"""
        config = HostConfig(
            profile_name='MEDIUM_SERVER',
            cpu_cores=8,
            ram_gb=32.0,
            max_containers=50,
            container_limit_warning_threshold=75,
            container_limit_critical_threshold=90
        )
        
        # 38 containers = 76% of 50
        at_limit, level = config.is_at_container_limit(current_count=38)
        
        assert at_limit is True
        assert level == 'warning'
    
    def test_is_at_container_limit_critical(self, db_session):
        """Test when container count reaches critical threshold"""
        config = HostConfig(
            profile_name='MEDIUM_SERVER',
            cpu_cores=8,
            ram_gb=32.0,
            max_containers=50,
            container_limit_warning_threshold=75,
            container_limit_critical_threshold=90
        )
        
        # 46 containers = 92% of 50
        at_limit, level = config.is_at_container_limit(current_count=46)
        
        assert at_limit is True
        assert level == 'critical'
    
    def test_is_at_container_limit_exceeded(self, db_session):
        """Test when container count exceeds maximum"""
        config = HostConfig(
            profile_name='MEDIUM_SERVER',
            cpu_cores=8,
            ram_gb=32.0,
            max_containers=50
        )
        
        at_limit, level = config.is_at_container_limit(current_count=55)
        
        assert at_limit is True
        assert level == 'exceeded'
    
    def test_is_at_container_limit_strict_mode(self, db_session):
        """Test strict mode only returns True when exactly at/over limit"""
        config = HostConfig(
            profile_name='MEDIUM_SERVER',
            cpu_cores=8,
            ram_gb=32.0,
            max_containers=50,
            container_limit_warning_threshold=75,
            container_limit_critical_threshold=90
        )
        
        # Warning threshold but strict=True
        at_limit, level = config.is_at_container_limit(current_count=38, strict=True)
        assert at_limit is False
        assert level == 'warning'
        
        # Exceeded with strict=True
        at_limit, level = config.is_at_container_limit(current_count=55, strict=True)
        assert at_limit is True
        assert level == 'exceeded'


class TestContainerLimitMessages:
    """Test container limit message generation"""
    
    def test_get_container_limit_message_none(self, db_session):
        """Test message when well below limit"""
        config = HostConfig(
            profile_name='MEDIUM_SERVER',
            cpu_cores=8,
            ram_gb=32.0,
            max_containers=50,
            container_limit_warning_threshold=75,
            container_limit_critical_threshold=90
        )
        
        message = config.get_container_limit_message(current_count=20)
        
        assert '✅' in message
        assert '30 containers remaining' in message
        assert '20/50' in message
    
    def test_get_container_limit_message_warning(self, db_session):
        """Test warning message"""
        config = HostConfig(
            profile_name='MEDIUM_SERVER',
            cpu_cores=8,
            ram_gb=32.0,
            max_containers=50,
            container_limit_warning_threshold=75
        )
        
        message = config.get_container_limit_message(current_count=38)
        
        assert '⚠️' in message
        assert 'Warning' in message
        assert '12 containers remaining' in message
        assert 'MEDIUM_SERVER' in message
    
    def test_get_container_limit_message_critical(self, db_session):
        """Test critical message"""
        config = HostConfig(
            profile_name='MEDIUM_SERVER',
            cpu_cores=8,
            ram_gb=32.0,
            max_containers=50,
            container_limit_warning_threshold=75,
            container_limit_critical_threshold=90
        )
        
        message = config.get_container_limit_message(current_count=46)
        
        assert '⚠️' in message
        assert 'Critical' in message
        assert '4 containers remaining' in message
    
    def test_get_container_limit_message_exceeded(self, db_session):
        """Test exceeded message"""
        config = HostConfig(
            profile_name='RASPBERRY_PI',
            cpu_cores=4,
            ram_gb=4.0,
            max_containers=15
        )
        
        message = config.get_container_limit_message(current_count=18)
        
        assert '⛔' in message
        assert 'limit exceeded' in message.lower()
        assert '18 containers' in message
        assert 'maximum of 15' in message
        assert 'RASPBERRY_PI' in message


class TestHostConfigSerialization:
    """Test dictionary serialization"""
    
    def test_to_dict_includes_all_fields(self, db_session):
        """Test that to_dict includes all important fields"""
        config = HostConfig(
            profile_name='MEDIUM_SERVER',
            cpu_cores=8,
            ram_gb=32.0,
            is_raspberry_pi=False,
            max_containers=50,
            container_limit_warning_threshold=75,
            container_limit_critical_threshold=90,
            enable_continuous_monitoring=True,
            enable_log_analysis=True,
            enable_auto_update=True,
            update_check_interval=21600,
            health_check_interval=300,
            network_size_limit='/24'
        )
        
        db_session.add(config)
        db_session.commit()
        db_session.refresh(config)
        
        data = config.to_dict()
        
        assert data['profile_name'] == 'MEDIUM_SERVER'
        assert data['cpu_cores'] == 8
        assert data['ram_gb'] == 32.0
        assert data['is_raspberry_pi'] is False
        assert data['max_containers'] == 50
        assert data['container_limit_warning_threshold'] == 75
        assert data['container_limit_critical_threshold'] == 90
        assert data['enable_continuous_monitoring'] is True
        assert data['enable_log_analysis'] is True
        assert data['enable_auto_update'] is True
        assert data['update_check_interval'] == 21600
        assert data['health_check_interval'] == 300
        assert data['network_size_limit'] == '/24'
        assert 'detected_at' in data
    
    def test_to_dict_datetime_serialization(self, db_session):
        """Test that datetimes are serialized to ISO format"""
        config = HostConfig(
            profile_name='TEST',
            cpu_cores=4,
            ram_gb=8.0
        )
        
        db_session.add(config)
        db_session.commit()
        db_session.refresh(config)
        
        data = config.to_dict()
        
        # Check datetime is ISO string
        assert isinstance(data['detected_at'], str)
        assert 'T' in data['detected_at']  # ISO format contains 'T'


class TestRaspberryPiLimits:
    """Test Raspberry Pi specific limits"""
    
    def test_raspberry_pi_low_limits(self, db_session):
        """Test that Raspberry Pi has appropriate low limits"""
        config = HostConfig(
            profile_name='RASPBERRY_PI',
            cpu_cores=4,
            ram_gb=4.0,
            is_raspberry_pi=True,
            max_containers=15,
            container_limit_warning_threshold=75,
            container_limit_critical_threshold=90
        )
        
        # 12 containers = 80% of 15
        at_limit, level = config.is_at_container_limit(current_count=12)
        assert level in ['warning', 'critical']  # Should be warning
        
        # 14 containers = 93% of 15
        at_limit, level = config.is_at_container_limit(current_count=14)
        assert level == 'critical'
        
        # 16 containers = over limit
        at_limit, level = config.is_at_container_limit(current_count=16)
        assert level == 'exceeded'
