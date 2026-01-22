#!/usr/bin/env python3
"""
Task 4 Verification Script - SSL/TLS Certificate Management

Tests all SSL certificate functionality:
1. Self-signed certificate generation
2. Certificate validation
3. Certificate info extraction
4. Let's Encrypt manager (basic checks)
5. Database model
6. Custom certificate import

Run with: python3 verify_task4.py
"""

import os
import sys
import tempfile
import shutil
from datetime import datetime

# Test output formatting
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def print_test(name, passed, details=""):
    """Print test result"""
    status = f"{GREEN}✅ PASS{RESET}" if passed else f"{RED}❌ FAIL{RESET}"
    print(f"{status} - {name}")
    if details:
        print(f"       {details}")

def test_imports():
    """Test 1: Can import SSL modules"""
    try:
        from backend.ssl.cert_manager import CertificateManager
        from backend.ssl.letsencrypt import LetsEncryptManager
        from backend.models.ssl_certificate import SSLCertificate
        print_test("Import SSL modules", True, 
                  "CertificateManager, LetsEncryptManager, SSLCertificate")
        return True
    except Exception as e:
        print_test("Import SSL modules", False, str(e))
        return False

def test_self_signed_generation():
    """Test 2: Self-signed certificate generation"""
    try:
        from backend.ssl.cert_manager import CertificateManager
        
        # Create temp directory for test
        test_dir = tempfile.mkdtemp(prefix='dockermate_ssl_test_')
        
        try:
            # Generate certificate
            result = CertificateManager.generate_self_signed_cert(
                output_dir=test_dir,
                hostname='test-dockermate',
                organization='Test Org'
            )
            
            # Check result structure
            assert 'cert_path' in result
            assert 'key_path' in result
            assert 'expires_at' in result
            assert 'issued_at' in result
            assert 'hostname' in result
            assert 'ip_address' in result
            
            # Check files exist
            assert os.path.exists(result['cert_path'])
            assert os.path.exists(result['key_path'])
            
            # Check file permissions on key (should be 600)
            key_stat = os.stat(result['key_path'])
            key_perms = oct(key_stat.st_mode)[-3:]
            assert key_perms == '600', f"Key permissions should be 600, got {key_perms}"
            
            # Check certificate validity period
            assert isinstance(result['expires_at'], datetime)
            assert isinstance(result['issued_at'], datetime)
            
            # Check hostname
            assert result['hostname'] == 'test-dockermate'
            
            print_test("Self-signed certificate generation", True,
                      f"Cert: {os.path.basename(result['cert_path'])}, "
                      f"Key: {os.path.basename(result['key_path'])}, "
                      f"Expires: {result['expires_at'].strftime('%Y-%m-%d')}")
            return True
            
        finally:
            # Cleanup
            shutil.rmtree(test_dir, ignore_errors=True)
            
    except Exception as e:
        print_test("Self-signed certificate generation", False, str(e))
        return False

def test_certificate_validation():
    """Test 3: Certificate validation"""
    try:
        from backend.ssl.cert_manager import CertificateManager
        
        # Create temp directory
        test_dir = tempfile.mkdtemp(prefix='dockermate_ssl_test_')
        
        try:
            # Generate valid certificate
            result = CertificateManager.generate_self_signed_cert(
                output_dir=test_dir
            )
            
            # Validate it
            validation = CertificateManager.validate_certificate_files(
                result['cert_path'],
                result['key_path']
            )
            
            # Check validation result
            assert validation['valid'] == True
            assert len(validation['errors']) == 0
            assert validation['expires_at'] is not None
            assert validation['days_remaining'] > 0
            assert validation['subject'] is not None
            
            # Test with non-existent files
            invalid = CertificateManager.validate_certificate_files(
                '/tmp/nonexistent.pem',
                '/tmp/nonexistent.key'
            )
            
            assert invalid['valid'] == False
            assert len(invalid['errors']) > 0
            
            print_test("Certificate validation", True,
                      f"Valid cert detected, {validation['days_remaining']} days remaining")
            return True
            
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)
            
    except Exception as e:
        print_test("Certificate validation", False, str(e))
        return False

def test_certificate_info():
    """Test 4: Certificate info extraction"""
    try:
        from backend.ssl.cert_manager import CertificateManager
        
        # Create temp directory
        test_dir = tempfile.mkdtemp(prefix='dockermate_ssl_test_')
        
        try:
            # Generate certificate
            result = CertificateManager.generate_self_signed_cert(
                output_dir=test_dir,
                hostname='info-test'
            )
            
            # Get info
            info = CertificateManager.get_certificate_info(result['cert_path'])
            
            # Check info structure
            assert info is not None
            assert 'subject' in info
            assert 'issuer' in info
            assert 'serial_number' in info
            assert 'not_valid_before' in info
            assert 'not_valid_after' in info
            
            # Check subject contains hostname
            assert 'info-test' in info['subject']
            
            print_test("Certificate info extraction", True,
                      f"Subject: {info['subject'][:50]}...")
            return True
            
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)
            
    except Exception as e:
        print_test("Certificate info extraction", False, str(e))
        return False

def test_letsencrypt_manager():
    """Test 5: Let's Encrypt manager basics"""
    try:
        from backend.ssl.letsencrypt import LetsEncryptManager
        
        # Just test that methods exist and handle errors properly
        is_installed = LetsEncryptManager.is_certbot_installed()
        assert isinstance(is_installed, bool)
        
        # Test that obtain_certificate rejects invalid input
        try:
            LetsEncryptManager.obtain_certificate(
                domain='',
                email='invalid',
                agree_tos=False
            )
            # Should have raised ValueError
            assert False, "Should have raised ValueError"
        except ValueError:
            pass  # Expected
        
        print_test("Let's Encrypt manager", True,
                  f"Certbot installed: {is_installed}")
        return True
        
    except Exception as e:
        print_test("Let's Encrypt manager", False, str(e))
        return False

def test_database_model():
    """Test 6: SSLCertificate database model"""
    try:
        from backend.models.ssl_certificate import SSLCertificate
        from datetime import datetime, timedelta
        
        # Create instance
        cert = SSLCertificate(
            cert_type='self-signed',
            cert_path='/test/cert.pem',
            key_path='/test/key.pem',
            domain='test.local',
            issued_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=825),
            is_active=True
        )
        
        # Test days_until_expiry
        days = cert.days_until_expiry()
        assert days is not None
        assert 820 <= days <= 825  # Should be close to 825
        
        # Test needs_renewal (shouldn't need renewal with 825 days)
        assert cert.needs_renewal(days_before=30) == False
        
        # Test needs renewal with short expiry
        cert.expires_at = datetime.utcnow() + timedelta(days=20)
        assert cert.needs_renewal(days_before=30) == True
        
        # Test get_certificate_type_display
        display = cert.get_certificate_type_display()
        assert 'Self-Signed' in display
        
        print_test("SSLCertificate database model", True,
                  f"Renewal detection working")
        return True
        
    except Exception as e:
        print_test("SSLCertificate database model", False, str(e))
        return False

def test_custom_certificate_import():
    """Test 7: Custom certificate import"""
    try:
        from backend.ssl.cert_manager import CertificateManager
        
        # Create temp directories
        source_dir = tempfile.mkdtemp(prefix='dockermate_ssl_source_')
        dest_dir = tempfile.mkdtemp(prefix='dockermate_ssl_dest_')
        
        try:
            # Generate a certificate to use as "uploaded" cert
            uploaded = CertificateManager.generate_self_signed_cert(
                output_dir=source_dir,
                hostname='*.example.com'  # Wildcard cert
            )
            
            # Import it as custom certificate
            result = CertificateManager.import_custom_certificate(
                cert_file_path=uploaded['cert_path'],
                key_file_path=uploaded['key_path'],
                output_dir=dest_dir
            )
            
            # Check result
            assert result['success'] == True
            assert len(result['errors']) == 0
            assert result['cert_path'] is not None
            assert result['key_path'] is not None
            assert result['is_wildcard'] == True  # Should detect wildcard
            
            # Verify files were copied
            assert os.path.exists(result['cert_path'])
            assert os.path.exists(result['key_path'])
            
            # Verify permissions on key
            key_stat = os.stat(result['key_path'])
            key_perms = oct(key_stat.st_mode)[-3:]
            assert key_perms == '600', f"Key permissions should be 600, got {key_perms}"
            
            # Test with invalid files
            invalid = CertificateManager.import_custom_certificate(
                cert_file_path='/tmp/nonexistent.pem',
                key_file_path='/tmp/nonexistent.key',
                output_dir=dest_dir
            )
            assert invalid['success'] == False
            assert len(invalid['errors']) > 0
            
            print_test("Custom certificate import", True,
                      f"Wildcard detected: {result['is_wildcard']}, "
                      f"Days remaining: {result['days_remaining']}")
            return True
            
        finally:
            shutil.rmtree(source_dir, ignore_errors=True)
            shutil.rmtree(dest_dir, ignore_errors=True)
            
    except Exception as e:
        print_test("Custom certificate import", False, str(e))
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("Task 4 Verification - SSL/TLS Certificate Management")
    print("=" * 60)
    print()
    
    tests = [
        test_imports,
        test_self_signed_generation,
        test_certificate_validation,
        test_certificate_info,
        test_letsencrypt_manager,
        test_database_model,
        test_custom_certificate_import,
    ]
    
    results = []
    for test in tests:
        results.append(test())
        print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print(f"{GREEN}✅ All tests passed! Task 4 complete.{RESET}")
        return 0
    else:
        print(f"{RED}❌ Some tests failed. Review errors above.{RESET}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
