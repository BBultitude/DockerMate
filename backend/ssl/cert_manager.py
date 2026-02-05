"""
SSL/TLS Certificate Manager

Handles generation, validation, and management of SSL certificates for HTTPS.

Why this exists:
- DockerMate requires HTTPS for security
- Home labs need easy setup (self-signed by default)
- Advanced users can use Let's Encrypt or custom certs

Design decisions:
- Default to self-signed (home lab friendly)
- 2048-bit RSA keys (good security/performance balance)
- 825 day validity (Chrome's maximum allowed)
- Includes hostname and local IP in Subject Alternative Names

Certificate Types Supported:
1. Self-Signed (Default):
   - Auto-generated on first run
   - Valid for 825 days (~2.25 years)
   - Manual renewal (simple button click)
   - One-time browser security exception

2. Let's Encrypt (Optional):
   - For users with public domain names
   - Valid for 90 days
   - Auto-renewal via APScheduler
   - No browser warnings

3. Custom Uploaded (Advanced):
   - User provides their own certificate
   - Wildcard certificates supported (*.example.com)
   - Corporate/purchased certificates
   - User manages renewal

CERTIFICATE RENEWAL STRATEGY:

Self-Signed Certificates:
- Valid for 825 days (~2.25 years)
- Manual renewal recommended (KISS principle)
- User clicks "Renew" button when reminded
- Reminder shown 30 days before expiry
- Simple: generate_self_signed_cert() overwrites old cert

Let's Encrypt Certificates:
- Valid for 90 days (Let's Encrypt policy)
- Automatic renewal via APScheduler (Sprint 3+)
- Runs daily, renews at 60 days before expiry
- Zero user interaction needed
- Uses certbot's built-in renewal logic

Custom Certificates:
- User responsible for renewal
- DockerMate shows expiry warnings only
- User re-uploads updated certificate when needed
- Validation performed on each upload

References:
- cryptography library docs: https://cryptography.io/
- Chrome cert requirements: https://support.google.com/chrome/a/answer/7391219
"""

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from datetime import datetime, timedelta
import socket
import struct
import os
import ipaddress
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def _detect_host_ips() -> List[str]:
    """
    Detect the host machine's routable IP addresses from inside a container.

    Order of priority:
        1. DOCKERMATE_HOST_IP env var  (explicit, most reliable)
        2. Default gateway from /proc/1/net/route  (Docker bridge host-side IP)
        3. host.docker.internal  (Docker Desktop / BuildKit)

    Returns a de-duplicated list; may be empty if none are reachable.
    """
    seen: set = set()
    ips: List[str] = []

    def _add(ip_str: str) -> None:
        try:
            normalized = str(ipaddress.IPv4Address(ip_str))
            if normalized not in seen:
                seen.add(normalized)
                ips.append(normalized)
        except (ValueError, TypeError):
            pass

    # 1. Explicit override
    env_ip = os.environ.get('DOCKERMATE_HOST_IP', '').strip()
    if env_ip:
        _add(env_ip)

    # 2. Default gateway from routing table (Linux only)
    try:
        with open('/proc/1/net/route') as fh:
            for line in fh.readlines()[1:]:
                fields = line.strip().split()
                if len(fields) >= 3 and fields[1] == '00000000':  # default route
                    gw_int = int(fields[2], 16)
                    _add(socket.inet_ntoa(struct.pack('<I', gw_int)))
                    break
    except Exception:
        pass

    # 3. host.docker.internal (Docker Desktop / BuildKit)
    try:
        _add(socket.gethostbyname('host.docker.internal'))
    except Exception:
        pass

    return ips


class CertificateManager:
    """
    Manage SSL/TLS certificates for DockerMate
    
    Supports:
    - Self-signed certificate generation (default)
    - Custom certificate import (wildcard, named domain, corporate)
    - Certificate validation
    - Certificate renewal detection
    """
    
    # Certificate validity period (825 days = Chrome's maximum)
    # Why 825? Chrome enforces max 398 days for public CAs, but allows
    # 825 days for self-signed/private CAs
    DEFAULT_VALIDITY_DAYS = 825
    
    # Key size (2048-bit RSA)
    # Why 2048? Good balance of security and performance for home labs
    # 4096-bit would be overkill for home use and slower
    KEY_SIZE = 2048
    
    @staticmethod
    def generate_self_signed_cert(
        output_dir: str = '/app/data/ssl',
        hostname: Optional[str] = None,
        organization: str = 'DockerMate',
        country: str = 'US'
    ) -> Dict[str, str]:
        """
        Generate self-signed SSL certificate for home lab use
        
        This creates a certificate that browsers will show a warning for,
        but that's expected and acceptable for home labs. Users add a
        one-time security exception.
        
        Args:
            output_dir: Where to save cert.pem and key.pem
            hostname: Server hostname (auto-detected if None)
            organization: Organization name for cert
            country: Two-letter country code
        
        Returns:
            dict: {
                'cert_path': '/path/to/cert.pem',
                'key_path': '/path/to/key.pem',
                'expires_at': datetime object,
                'hostname': 'server-hostname',
                'ip_address': '192.168.1.100'
            }
        
        Raises:
            OSError: If cannot create output directory
            RuntimeError: If certificate generation fails
        
        Example:
            >>> result = CertificateManager.generate_self_signed_cert()
            >>> print(f"Certificate: {result['cert_path']}")
            >>> print(f"Expires: {result['expires_at']}")
        """
        try:
            # Create output directory if needed
            os.makedirs(output_dir, exist_ok=True)
            logger.info(f"Generating self-signed certificate in {output_dir}")
            
            # Get hostname if not provided
            if hostname is None:
                hostname = socket.gethostname()
            
            # Get local IP address
            try:
                # Connect to Google DNS to get local IP (doesn't actually send data)
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(('8.8.8.8', 80))
                local_ip = s.getsockname()[0]
                s.close()
            except Exception as e:
                logger.warning(f"Could not detect local IP: {e}, using 127.0.0.1")
                local_ip = '127.0.0.1'
            
            # Generate private key
            logger.info("Generating RSA private key (2048-bit)...")
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=CertificateManager.KEY_SIZE,
                backend=default_backend()
            )
            
            # Certificate subject (who the cert is for)
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, country),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization),
                x509.NameAttribute(NameOID.COMMON_NAME, hostname),
            ])
            
            # Calculate validity period
            not_valid_before = datetime.utcnow()
            not_valid_after = not_valid_before + timedelta(
                days=CertificateManager.DEFAULT_VALIDITY_DAYS
            )
            
            # Build Subject Alternative Names (SAN)
            # This allows the cert to work for multiple hostnames/IPs
            san_list = [
                x509.DNSName(hostname),
                x509.DNSName('localhost'),
                x509.DNSName('dockermate'),  # Common Docker hostname
            ]

            # Collect all IPs, deduplicated
            added_ips: set = set()

            def _add_ip(ip_str: str) -> None:
                try:
                    addr = ipaddress.IPv4Address(ip_str)
                    if str(addr) not in added_ips:
                        added_ips.add(str(addr))
                        san_list.append(x509.IPAddress(addr))
                except (ValueError, TypeError) as e:
                    logger.warning(f"Skipping invalid IP {ip_str!r}: {e}")

            _add_ip('127.0.0.1')
            _add_ip(local_ip)           # container's own bridge IP

            # Host machine IPs (gateway / env var / host.docker.internal)
            host_ips = _detect_host_ips()
            for hip in host_ips:
                _add_ip(hip)
            if host_ips:
                logger.info(f"  Host IPs added to SANs: {host_ips}")
            
            # Create certificate
            logger.info("Creating certificate...")
            cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                issuer
            ).public_key(
                private_key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                not_valid_before
            ).not_valid_after(
                not_valid_after
            ).add_extension(
                x509.SubjectAlternativeName(san_list),
                critical=False,  # Not critical for self-signed
            ).sign(
                private_key,
                hashes.SHA256(),
                backend=default_backend()
            )
            
            # Write certificate to file
            cert_path = os.path.join(output_dir, 'cert.pem')
            with open(cert_path, 'wb') as f:
                f.write(cert.public_bytes(serialization.Encoding.PEM))
            logger.info(f"Certificate written to: {cert_path}")
            
            # Write private key to file
            key_path = os.path.join(output_dir, 'key.pem')
            with open(key_path, 'wb') as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            logger.info(f"Private key written to: {key_path}")
            
            # Set secure permissions on private key (owner read/write only)
            os.chmod(key_path, 0o600)
            logger.info("Set private key permissions to 600 (owner only)")
            
            result = {
                'cert_path': cert_path,
                'key_path': key_path,
                'expires_at': not_valid_after,
                'issued_at': not_valid_before,
                'hostname': hostname,
                'ip_address': local_ip,
                'san_ips': list(added_ips),
            }

            logger.info(f"Certificate generated successfully")
            logger.info(f"  Hostname: {hostname}")
            logger.info(f"  SANs (IPs): {list(added_ips)}")
            logger.info(f"  Expires: {not_valid_after.strftime('%Y-%m-%d')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate certificate: {e}")
            raise RuntimeError(f"Certificate generation failed: {e}")
    
    @staticmethod
    def import_custom_certificate(
        cert_file_path: str,
        key_file_path: str,
        output_dir: str = '/app/data/ssl',
        cert_filename: str = 'custom_cert.pem',
        key_filename: str = 'custom_key.pem'
    ) -> Dict[str, any]:
        """
        Import user-provided custom certificate (e.g., wildcard, named domain)
        
        This allows advanced users to provide their own certificates:
        - Wildcard certificates (*.example.com)
        - Named domain certificates (dockermate.example.com)
        - Corporate/internal CA certificates
        - Purchased SSL certificates
        
        The files are validated and copied to DockerMate's SSL directory.
        
        Args:
            cert_file_path: Path to uploaded certificate file
            key_file_path: Path to uploaded private key file
            output_dir: Where to store the certificate (default: /app/data/ssl)
            cert_filename: Filename for certificate (default: custom_cert.pem)
            key_filename: Filename for private key (default: custom_key.pem)
        
        Returns:
            dict: {
                'success': bool,
                'cert_path': str or None,
                'key_path': str or None,
                'expires_at': datetime or None,
                'subject': str or None,
                'is_wildcard': bool,
                'days_remaining': int or None,
                'errors': list of error messages,
                'warnings': list of warnings
            }
        
        Example:
            >>> # User uploads cert.pem and key.pem via web interface
            >>> result = CertificateManager.import_custom_certificate(
            ...     cert_file_path='/tmp/uploaded_cert.pem',
            ...     key_file_path='/tmp/uploaded_key.pem'
            ... )
            >>> if result['success']:
            ...     print(f"Certificate imported: {result['cert_path']}")
            ...     print(f"Expires: {result['expires_at']}")
            ... else:
            ...     print(f"Errors: {result['errors']}")
        
        Validation performed:
        - Files exist and are readable
        - Certificate is valid PEM format
        - Private key is valid PEM format
        - Certificate and key match (public key comparison)
        - Certificate is not expired
        
        Common use cases:
        - Wildcard cert: *.home.example.com
        - Specific domain: dockermate.home.example.com
        - Corporate CA: Internal company certificate authority
        - Purchased cert: From commercial CA like DigiCert, Sectigo
        
        Security notes:
        - Private key is copied with 600 permissions (owner only)
        - Original uploaded files should be deleted after import
        - Certificate is validated before copying
        """
        errors = []
        warnings = []
        
        try:
            # Step 1: Validate input files exist
            if not os.path.exists(cert_file_path):
                errors.append(f"Certificate file not found: {cert_file_path}")
            if not os.path.exists(key_file_path):
                errors.append(f"Private key file not found: {key_file_path}")
            
            if errors:
                return {
                    'success': False,
                    'cert_path': None,
                    'key_path': None,
                    'expires_at': None,
                    'subject': None,
                    'is_wildcard': False,
                    'days_remaining': None,
                    'errors': errors,
                    'warnings': warnings
                }
            
            # Step 2: Validate certificate and key match
            logger.info("Validating uploaded certificate and key...")
            validation = CertificateManager.validate_certificate_files(
                cert_file_path,
                key_file_path
            )
            
            if not validation['valid']:
                errors.extend(validation['errors'])
                return {
                    'success': False,
                    'cert_path': None,
                    'key_path': None,
                    'expires_at': None,
                    'subject': None,
                    'is_wildcard': False,
                    'days_remaining': None,
                    'errors': errors,
                    'warnings': warnings
                }
            
            # Add any warnings from validation
            warnings.extend(validation['warnings'])
            
            # Step 3: Create output directory
            os.makedirs(output_dir, exist_ok=True)
            
            # Step 4: Copy certificate file
            dest_cert_path = os.path.join(output_dir, cert_filename)
            logger.info(f"Copying certificate to {dest_cert_path}")
            
            # Read and write to ensure proper permissions
            with open(cert_file_path, 'rb') as src:
                cert_data = src.read()
            with open(dest_cert_path, 'wb') as dst:
                dst.write(cert_data)
            
            # Set certificate permissions (644 - readable by all)
            os.chmod(dest_cert_path, 0o644)
            
            # Step 5: Copy private key file
            dest_key_path = os.path.join(output_dir, key_filename)
            logger.info(f"Copying private key to {dest_key_path}")
            
            with open(key_file_path, 'rb') as src:
                key_data = src.read()
            with open(dest_key_path, 'wb') as dst:
                dst.write(key_data)
            
            # Set private key permissions (600 - owner only, CRITICAL)
            os.chmod(dest_key_path, 0o600)
            logger.info("Set private key permissions to 600 (owner only)")
            
            # Step 6: Get certificate info for metadata
            cert_info = CertificateManager.get_certificate_info(dest_cert_path)
            
            # Step 7: Check if it's a wildcard certificate
            is_wildcard = False
            if cert_info and 'subject' in cert_info:
                if '*' in cert_info['subject']:
                    is_wildcard = True
                    logger.info("Detected wildcard certificate")
            
            logger.info("Custom certificate imported successfully")
            logger.info(f"  Subject: {cert_info['subject'] if cert_info else 'Unknown'}")
            logger.info(f"  Expires: {validation['expires_at'].strftime('%Y-%m-%d')}")
            logger.info(f"  Days remaining: {validation['days_remaining']}")
            
            return {
                'success': True,
                'cert_path': dest_cert_path,
                'key_path': dest_key_path,
                'expires_at': validation['expires_at'],
                'subject': cert_info['subject'] if cert_info else None,
                'is_wildcard': is_wildcard,
                'days_remaining': validation['days_remaining'],
                'errors': [],
                'warnings': warnings
            }
            
        except Exception as e:
            logger.error(f"Failed to import custom certificate: {e}")
            errors.append(f"Import failed: {str(e)}")
            return {
                'success': False,
                'cert_path': None,
                'key_path': None,
                'expires_at': None,
                'subject': None,
                'is_wildcard': False,
                'days_remaining': None,
                'errors': errors,
                'warnings': warnings
            }
    
    @staticmethod
    def validate_certificate_files(cert_path: str, key_path: str) -> Dict[str, any]:
        """
        Validate existing certificate and key files
        
        Checks:
        - Files exist and are readable
        - Certificate is valid PEM format
        - Private key is valid PEM format
        - Certificate and key match (public key comparison)
        - Certificate expiry date
        
        Args:
            cert_path: Path to certificate file
            key_path: Path to private key file
        
        Returns:
            dict: {
                'valid': bool,
                'errors': list of error messages,
                'warnings': list of warnings,
                'expires_at': datetime or None,
                'days_remaining': int or None,
                'subject': str or None
            }
        
        Example:
            >>> result = CertificateManager.validate_certificate_files(
            ...     '/app/data/ssl/cert.pem',
            ...     '/app/data/ssl/key.pem'
            ... )
            >>> if result['valid']:
            ...     print(f"Valid! Expires in {result['days_remaining']} days")
        """
        errors = []
        warnings = []
        
        # Check files exist
        if not os.path.exists(cert_path):
            errors.append(f"Certificate file not found: {cert_path}")
        if not os.path.exists(key_path):
            errors.append(f"Private key file not found: {key_path}")
        
        if errors:
            return {
                'valid': False,
                'errors': errors,
                'warnings': warnings,
                'expires_at': None,
                'days_remaining': None,
                'subject': None
            }
        
        try:
            # Load certificate
            with open(cert_path, 'rb') as f:
                cert_data = f.read()
                cert = x509.load_pem_x509_certificate(cert_data, default_backend())
            
            # Load private key
            with open(key_path, 'rb') as f:
                key_data = f.read()
                private_key = serialization.load_pem_private_key(
                    key_data,
                    password=None,
                    backend=default_backend()
                )
            
            # Verify certificate and key match
            cert_public_key = cert.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            key_public_key = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            if cert_public_key != key_public_key:
                errors.append("Certificate and private key do not match")
            
            # Check expiry
            expires_at = cert.not_valid_after
            now = datetime.utcnow()
            
            if expires_at < now:
                errors.append(f"Certificate expired on {expires_at.strftime('%Y-%m-%d')}")
            
            days_remaining = (expires_at - now).days
            
            if days_remaining <= 30:
                warnings.append(f"Certificate expires in {days_remaining} days")
            
            # Get subject
            subject = cert.subject.rfc4514_string()
            
            return {
                'valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings,
                'expires_at': expires_at,
                'days_remaining': days_remaining,
                'subject': subject
            }
            
        except Exception as e:
            errors.append(f"Certificate validation error: {str(e)}")
            return {
                'valid': False,
                'errors': errors,
                'warnings': warnings,
                'expires_at': None,
                'days_remaining': None,
                'subject': None
            }
    
    @staticmethod
    def get_certificate_info(cert_path: str) -> Optional[Dict[str, any]]:
        """
        Extract information from a certificate file
        
        Args:
            cert_path: Path to certificate file
        
        Returns:
            dict with certificate details, or None if invalid
        
        Example:
            >>> info = CertificateManager.get_certificate_info('/app/data/ssl/cert.pem')
            >>> print(f"Subject: {info['subject']}")
            >>> print(f"Issuer: {info['issuer']}")
        """
        try:
            with open(cert_path, 'rb') as f:
                cert = x509.load_pem_x509_certificate(f.read(), default_backend())
            
            return {
                'subject': cert.subject.rfc4514_string(),
                'issuer': cert.issuer.rfc4514_string(),
                'serial_number': cert.serial_number,
                'not_valid_before': cert.not_valid_before,
                'not_valid_after': cert.not_valid_after,
                'signature_algorithm': cert.signature_algorithm_oid._name,
            }
        except Exception as e:
            logger.error(f"Failed to read certificate: {e}")
            return None
