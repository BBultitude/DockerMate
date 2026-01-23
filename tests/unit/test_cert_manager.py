"""
Unit tests for Certificate Manager

Tests SSL/TLS certificate generation.
Note: Only tests generation - validation functions not implemented in Sprint 1

Run with: pytest tests/unit/test_cert_manager.py -v
"""

import pytest
import os
import tempfile
import shutil
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from backend.ssl.cert_manager import CertificateManager


class TestCertificateGeneration:
    """Test certificate generation"""
    
    @pytest.fixture
    def temp_ssl_dir(self):
        """Create temporary directory for SSL files"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Cleanup
        shutil.rmtree(temp_dir)
    
    def test_generate_creates_certificate_file(self, temp_ssl_dir):
        """Test that certificate file is created"""
        result = CertificateManager.generate_self_signed_cert(output_dir=temp_ssl_dir)
        
        cert_path = result['cert_path']
        assert os.path.exists(cert_path)
        assert os.path.isfile(cert_path)
    
    def test_generate_creates_key_file(self, temp_ssl_dir):
        """Test that private key file is created"""
        result = CertificateManager.generate_self_signed_cert(output_dir=temp_ssl_dir)
        
        key_path = result['key_path']
        assert os.path.exists(key_path)
        assert os.path.isfile(key_path)
    
    def test_key_file_permissions(self, temp_ssl_dir):
        """Test that private key has correct permissions (600)"""
        result = CertificateManager.generate_self_signed_cert(output_dir=temp_ssl_dir)
        
        key_path = result['key_path']
        # Get file permissions
        stat_info = os.stat(key_path)
        permissions = oct(stat_info.st_mode)[-3:]
        
        # Should be 600 (owner read/write only)
        assert permissions == '600'
    
    def test_certificate_validity_period(self, temp_ssl_dir):
        """Test that certificate has correct validity period (~2 years)"""
        result = CertificateManager.generate_self_signed_cert(output_dir=temp_ssl_dir)
        
        # Load certificate
        with open(result['cert_path'], 'rb') as f:
            cert_data = f.read()
        cert = x509.load_pem_x509_certificate(cert_data)
        
        # Check validity period
        now = datetime.utcnow()
        not_before = cert.not_valid_before
        not_after = cert.not_valid_after
        
        # Should be valid now
        assert not_before <= now <= not_after
        
        # Should expire in ~825 days (allow 1 day tolerance)
        days_valid = (not_after - not_before).days
        assert 824 <= days_valid <= 826
    
    def test_certificate_subject_fields(self, temp_ssl_dir):
        """Test that certificate has correct subject fields"""
        result = CertificateManager.generate_self_signed_cert(output_dir=temp_ssl_dir)
        
        # Load certificate
        with open(result['cert_path'], 'rb') as f:
            cert_data = f.read()
        cert = x509.load_pem_x509_certificate(cert_data)
        
        # Check subject
        subject = cert.subject
        
        # Should have organization
        org_attrs = [attr for attr in subject if attr.oid == x509.NameOID.ORGANIZATION_NAME]
        assert len(org_attrs) == 1
        assert org_attrs[0].value == "DockerMate"
    
    def test_certificate_has_san_extension(self, temp_ssl_dir):
        """Test that certificate has Subject Alternative Names"""
        result = CertificateManager.generate_self_signed_cert(output_dir=temp_ssl_dir)
        
        # Load certificate
        with open(result['cert_path'], 'rb') as f:
            cert_data = f.read()
        cert = x509.load_pem_x509_certificate(cert_data)
        
        # Get SAN extension
        try:
            san_ext = cert.extensions.get_extension_for_oid(
                x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME
            )
            san = san_ext.value
            
            # Should have localhost
            dns_names = san.get_values_for_type(x509.DNSName)
            dns_names_list = [str(name) for name in dns_names]
            assert "localhost" in dns_names_list
            
            # Should have 127.0.0.1
            ip_addresses = san.get_values_for_type(x509.IPAddress)
            ip_addresses_list = [str(ip) for ip in ip_addresses]
            assert "127.0.0.1" in ip_addresses_list
        except x509.ExtensionNotFound:
            pytest.fail("SAN extension not found")
    
    def test_private_key_format(self, temp_ssl_dir):
        """Test that private key is valid RSA key"""
        result = CertificateManager.generate_self_signed_cert(output_dir=temp_ssl_dir)
        
        # Load private key
        with open(result['key_path'], 'rb') as f:
            key_data = f.read()
        
        # Should be able to load as RSA key
        try:
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.backends import default_backend
            
            private_key = serialization.load_pem_private_key(
                key_data,
                password=None,
                backend=default_backend()
            )
            
            # Should be RSA key
            assert isinstance(private_key, rsa.RSAPrivateKey)
            
            # Should be 2048 bits
            assert private_key.key_size == 2048
        except Exception as e:
            pytest.fail(f"Failed to load private key: {e}")
    
    def test_certificate_self_signed(self, temp_ssl_dir):
        """Test that certificate is self-signed (issuer == subject)"""
        result = CertificateManager.generate_self_signed_cert(output_dir=temp_ssl_dir)
        
        # Load certificate
        with open(result['cert_path'], 'rb') as f:
            cert_data = f.read()
        cert = x509.load_pem_x509_certificate(cert_data)
        
        # For self-signed cert, issuer should equal subject
        assert cert.issuer == cert.subject
    
    def test_result_dictionary_format(self, temp_ssl_dir):
        """Test that result dictionary has expected format"""
        result = CertificateManager.generate_self_signed_cert(output_dir=temp_ssl_dir)
        
        # Should have required keys
        assert 'cert_path' in result
        assert 'key_path' in result
        assert 'expires_at' in result
        
        # Paths should be strings
        assert isinstance(result['cert_path'], str)
        assert isinstance(result['key_path'], str)
        
        # Expires at should be datetime
        assert isinstance(result['expires_at'], datetime)
    
    def test_expiry_timestamp_accurate(self, temp_ssl_dir):
        """Test that expires_at timestamp matches certificate"""
        result = CertificateManager.generate_self_signed_cert(output_dir=temp_ssl_dir)
        
        # Load certificate
        with open(result['cert_path'], 'rb') as f:
            cert_data = f.read()
        cert = x509.load_pem_x509_certificate(cert_data)
        
        # Compare expiry times (allow 10 second tolerance)
        time_diff = abs((cert.not_valid_after - result['expires_at']).total_seconds())
        assert time_diff < 10


class TestCertificateInfo:
    """Test get_certificate_info function"""
    
    @pytest.fixture
    def temp_ssl_dir(self):
        """Create temporary directory for SSL files"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def generated_cert(self, temp_ssl_dir):
        """Generate a certificate for testing"""
        return CertificateManager.generate_self_signed_cert(output_dir=temp_ssl_dir)
    
    def test_get_certificate_info(self, generated_cert):
        """Test getting certificate information"""
        info = CertificateManager.get_certificate_info(generated_cert['cert_path'])
        
        # Should have required fields (matching actual implementation)
        assert 'subject' in info
        assert 'issuer' in info
        assert 'not_valid_before' in info  # Note: actual key name
        assert 'not_valid_after' in info   # Note: actual key name
        assert 'serial_number' in info


class TestCertificateDirectoryHandling:
    """Test directory creation and handling"""
    
    def test_creates_output_directory_if_missing(self):
        """Test that output directory is created if it doesn't exist"""
        temp_parent = tempfile.mkdtemp()
        try:
            output_dir = os.path.join(temp_parent, 'ssl', 'certs')
            
            # Directory shouldn't exist yet
            assert not os.path.exists(output_dir)
            
            # Generate cert
            result = CertificateManager.generate_self_signed_cert(output_dir=output_dir)
            
            # Directory should now exist
            assert os.path.exists(output_dir)
            assert os.path.isdir(output_dir)
            
            # Files should be in that directory
            assert os.path.dirname(result['cert_path']) == output_dir
            assert os.path.dirname(result['key_path']) == output_dir
        finally:
            shutil.rmtree(temp_parent)
    
    def test_uses_existing_directory(self):
        """Test that existing directory is used without error"""
        temp_dir = tempfile.mkdtemp()
        try:
            # Generate cert (directory exists)
            result = CertificateManager.generate_self_signed_cert(output_dir=temp_dir)
            
            # Should work without error
            assert os.path.exists(result['cert_path'])
            assert os.path.exists(result['key_path'])
        finally:
            shutil.rmtree(temp_dir)


class TestCertificateFileNaming:
    """Test certificate and key file naming"""
    
    @pytest.fixture
    def temp_ssl_dir(self):
        """Create temporary directory for SSL files"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_default_filenames(self, temp_ssl_dir):
        """Test that default filenames are used"""
        result = CertificateManager.generate_self_signed_cert(output_dir=temp_ssl_dir)
        
        assert os.path.basename(result['cert_path']) == 'cert.pem'
        assert os.path.basename(result['key_path']) == 'key.pem'
    
    def test_files_in_output_directory(self, temp_ssl_dir):
        """Test that files are created in specified directory"""
        result = CertificateManager.generate_self_signed_cert(output_dir=temp_ssl_dir)
        
        assert os.path.dirname(result['cert_path']) == temp_ssl_dir
        assert os.path.dirname(result['key_path']) == temp_ssl_dir
