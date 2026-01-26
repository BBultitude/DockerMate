"""
Unit Tests for Hardware Detector

Tests hardware detection logic, profile classification,
and system resource detection.
"""

import pytest
from unittest.mock import patch, MagicMock
from backend.utils.hardware_detector import (
    check_raspberry_pi,
    get_cpu_cores,
    get_ram_gb,
    classify_hardware_profile,
    detect_hardware_profile,
    update_host_config,
    get_profile_description,
    RASPBERRY_PI_PROFILE,
    LOW_END_PROFILE,
    MEDIUM_SERVER_PROFILE,
    HIGH_END_PROFILE,
    ENTERPRISE_PROFILE,
)


class TestRaspberryPiDetection:
    """Test Raspberry Pi detection logic"""
    
    @patch('os.path.exists')
    @patch('builtins.open')
    def test_detects_raspberry_pi_from_device_tree(self, mock_open, mock_exists):
        """Test Raspberry Pi detection from /proc/device-tree/model"""
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = 'Raspberry Pi 4 Model B'
        
        result = check_raspberry_pi()
        assert result is True
    
    @patch('os.path.exists')
    @patch('platform.machine')
    @patch('builtins.open')
    def test_detects_raspberry_pi_from_arm_architecture(self, mock_open, mock_machine, mock_exists):
        """Test Raspberry Pi detection from ARM architecture"""
        def exists_side_effect(path):
            if path == '/proc/device-tree/model':
                return False
            elif path == '/sys/firmware/devicetree/base/model':
                return True
            return False
        
        mock_exists.side_effect = exists_side_effect
        mock_machine.return_value = 'armv7l'
        mock_open.return_value.__enter__.return_value.read.return_value = 'Raspberry Pi 3 Model B'
        
        result = check_raspberry_pi()
        assert result is True
    
    @patch('os.path.exists')
    def test_does_not_detect_raspberry_pi_on_x86(self, mock_exists):
        """Test that x86 systems are not detected as Raspberry Pi"""
        mock_exists.return_value = False
        
        result = check_raspberry_pi()
        assert result is False


class TestSystemResourceDetection:
    """Test CPU and RAM detection"""
    
    @patch('psutil.cpu_count')
    def test_get_cpu_cores_success(self, mock_cpu_count):
        """Test successful CPU core detection"""
        mock_cpu_count.return_value = 8
        
        result = get_cpu_cores()
        assert result == 8
        mock_cpu_count.assert_called_once_with(logical=True)
    
    @patch('psutil.cpu_count')
    def test_get_cpu_cores_fallback(self, mock_cpu_count):
        """Test CPU core detection fallback on error"""
        mock_cpu_count.side_effect = Exception("Detection failed")
        
        result = get_cpu_cores()
        assert result == 4  # Default fallback
    
    @patch('psutil.virtual_memory')
    def test_get_ram_gb_success(self, mock_vm):
        """Test successful RAM detection"""
        mock_vm.return_value.total = 16 * 1024 ** 3  # 16 GB in bytes
        
        result = get_ram_gb()
        assert result == 16.0
    
    @patch('psutil.virtual_memory')
    def test_get_ram_gb_rounds_to_2_decimals(self, mock_vm):
        """Test that RAM is rounded to 2 decimal places"""
        mock_vm.return_value.total = 15.7654321 * 1024 ** 3
        
        result = get_ram_gb()
        assert isinstance(result, float)
        assert len(str(result).split('.')[-1]) <= 2
    
    @patch('psutil.virtual_memory')
    def test_get_ram_gb_fallback(self, mock_vm):
        """Test RAM detection fallback on error"""
        mock_vm.side_effect = Exception("Detection failed")
        
        result = get_ram_gb()
        assert result == 8.0  # Default fallback


class TestHardwareProfileClassification:
    """Test hardware profile classification logic"""
    
    def test_raspberry_pi_profile_priority(self):
        """Test Raspberry Pi gets special profile regardless of specs"""
        profile = classify_hardware_profile(cpu_cores=16, ram_gb=32, is_pi=True)
        assert profile['profile_name'] == 'RASPBERRY_PI'
        assert profile['max_containers'] == 15
    
    def test_low_end_profile(self):
        """Test low-end system classification"""
        profile = classify_hardware_profile(cpu_cores=2, ram_gb=8, is_pi=False)
        assert profile['profile_name'] == 'LOW_END'
        assert profile['max_containers'] == 20
    
    def test_low_end_profile_boundary(self):
        """Test low-end boundary (4 cores, 16GB)"""
        profile = classify_hardware_profile(cpu_cores=4, ram_gb=16, is_pi=False)
        assert profile['profile_name'] == 'LOW_END'
    
    def test_medium_server_profile(self):
        """Test medium server classification"""
        profile = classify_hardware_profile(cpu_cores=8, ram_gb=32, is_pi=False)
        assert profile['profile_name'] == 'MEDIUM_SERVER'
        assert profile['max_containers'] == 50
    
    def test_medium_server_profile_boundary(self):
        """Test medium server boundary (16 cores, 64GB)"""
        profile = classify_hardware_profile(cpu_cores=16, ram_gb=64, is_pi=False)
        assert profile['profile_name'] == 'MEDIUM_SERVER'
    
    def test_high_end_profile(self):
        """Test high-end server classification"""
        profile = classify_hardware_profile(cpu_cores=24, ram_gb=96, is_pi=False)
        assert profile['profile_name'] == 'HIGH_END'
        assert profile['max_containers'] == 100
    
    def test_high_end_profile_boundary(self):
        """Test high-end boundary (32 cores, 128GB)"""
        profile = classify_hardware_profile(cpu_cores=32, ram_gb=128, is_pi=False)
        assert profile['profile_name'] == 'HIGH_END'
    
    def test_enterprise_profile(self):
        """Test enterprise classification"""
        profile = classify_hardware_profile(cpu_cores=64, ram_gb=256, is_pi=False)
        assert profile['profile_name'] == 'ENTERPRISE'
        assert profile['max_containers'] == 200


class TestProfileProperties:
    """Test profile configuration properties"""
    
    def test_raspberry_pi_profile_properties(self):
        """Test Raspberry Pi profile has correct properties"""
        assert RASPBERRY_PI_PROFILE['max_containers'] == 15
        assert RASPBERRY_PI_PROFILE['update_check_interval'] == 43200  # 12h
        assert RASPBERRY_PI_PROFILE['health_check_interval'] == 900    # 15m
        assert RASPBERRY_PI_PROFILE['enable_continuous_monitoring'] is False
        assert RASPBERRY_PI_PROFILE['enable_log_analysis'] is False
        assert RASPBERRY_PI_PROFILE['enable_auto_update'] is False
        assert RASPBERRY_PI_PROFILE['network_size_limit'] == '/25'
    
    def test_medium_server_profile_properties(self):
        """Test Medium Server profile has correct properties"""
        assert MEDIUM_SERVER_PROFILE['max_containers'] == 50
        assert MEDIUM_SERVER_PROFILE['update_check_interval'] == 21600  # 6h
        assert MEDIUM_SERVER_PROFILE['health_check_interval'] == 300    # 5m
        assert MEDIUM_SERVER_PROFILE['enable_continuous_monitoring'] is True
        assert MEDIUM_SERVER_PROFILE['enable_log_analysis'] is True
        assert MEDIUM_SERVER_PROFILE['enable_auto_update'] is True
    
    def test_enterprise_profile_properties(self):
        """Test Enterprise profile has correct properties"""
        assert ENTERPRISE_PROFILE['max_containers'] == 200
        assert ENTERPRISE_PROFILE['update_check_interval'] == 7200   # 2h
        assert ENTERPRISE_PROFILE['health_check_interval'] == 120    # 2m
        assert ENTERPRISE_PROFILE['network_size_limit'] == '/22'


class TestDetectHardwareProfile:
    """Test complete hardware detection"""
    
    @patch('backend.utils.hardware_detector.get_cpu_cores')
    @patch('backend.utils.hardware_detector.get_ram_gb')
    @patch('backend.utils.hardware_detector.check_raspberry_pi')
    def test_detect_hardware_profile_complete(self, mock_pi, mock_ram, mock_cpu):
        """Test complete hardware detection returns all fields"""
        mock_cpu.return_value = 8
        mock_ram.return_value = 32.0
        mock_pi.return_value = False
        
        profile = detect_hardware_profile()
        
        # Check detected specs are included
        assert profile['cpu_cores'] == 8
        assert profile['ram_gb'] == 32.0
        assert profile['is_raspberry_pi'] is False
        
        # Check profile classification
        assert profile['profile_name'] == 'MEDIUM_SERVER'
        
        # Check profile properties are included
        assert 'max_containers' in profile
        assert 'update_check_interval' in profile
        assert 'health_check_interval' in profile
    
    @patch('backend.utils.hardware_detector.get_cpu_cores')
    @patch('backend.utils.hardware_detector.get_ram_gb')
    @patch('backend.utils.hardware_detector.check_raspberry_pi')
    def test_detect_raspberry_pi_hardware(self, mock_pi, mock_ram, mock_cpu):
        """Test Raspberry Pi detection in full profile"""
        mock_cpu.return_value = 4
        mock_ram.return_value = 4.0
        mock_pi.return_value = True
        
        profile = detect_hardware_profile()
        
        assert profile['is_raspberry_pi'] is True
        assert profile['profile_name'] == 'RASPBERRY_PI'
        assert profile['max_containers'] == 15


class TestUpdateHostConfig:
    """Test updating HostConfig model with detected profile"""
    
    @patch('backend.utils.hardware_detector.detect_hardware_profile')
    def test_update_host_config_all_fields(self, mock_detect):
        """Test that all fields are updated correctly"""
        mock_detect.return_value = {
            'profile_name': 'MEDIUM_SERVER',
            'cpu_cores': 8,
            'ram_gb': 32.0,
            'is_raspberry_pi': False,
            'max_containers': 50,
            'container_limit_warning_threshold': 75,
            'container_limit_critical_threshold': 90,
            'enable_continuous_monitoring': True,
            'enable_log_analysis': True,
            'enable_auto_update': True,
            'update_check_interval': 21600,
            'health_check_interval': 300,
            'network_size_limit': '/24',
        }
        
        # Mock database and config
        mock_db = MagicMock()
        mock_config = MagicMock()
        
        result = update_host_config(mock_db, mock_config)
        
        # Verify all fields were set
        assert mock_config.profile_name == 'MEDIUM_SERVER'
        assert mock_config.cpu_cores == 8
        assert mock_config.ram_gb == 32.0
        assert mock_config.is_raspberry_pi is False
        assert mock_config.max_containers == 50
        
        # Verify database operations
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_config)


class TestProfileDescriptions:
    """Test profile description text"""
    
    def test_raspberry_pi_description(self):
        """Test Raspberry Pi profile description"""
        desc = get_profile_description('RASPBERRY_PI')
        assert 'Raspberry Pi' in desc
        assert 'Limited resources' in desc
    
    def test_medium_server_description(self):
        """Test Medium Server profile description"""
        desc = get_profile_description('MEDIUM_SERVER')
        assert 'Medium Server' in desc
        assert 'home lab' in desc
    
    def test_enterprise_description(self):
        """Test Enterprise profile description"""
        desc = get_profile_description('ENTERPRISE')
        assert 'Enterprise' in desc
        assert 'production' in desc.lower()
    
    def test_unknown_profile_description(self):
        """Test unknown profile returns default message"""
        desc = get_profile_description('UNKNOWN_PROFILE')
        assert desc == 'Unknown profile'
