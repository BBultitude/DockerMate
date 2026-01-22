"""
Let's Encrypt Certificate Integration (Optional)

Provides automated certificate generation using Let's Encrypt for users
who want publicly-trusted certificates.

Why this exists:
- Some users have public domain names pointing to home labs
- Let's Encrypt provides free, auto-renewing certificates
- No browser warnings with properly configured Let's Encrypt certs

Requirements:
- Public domain name
- Ports 80/443 accessible from internet
- DNS correctly configured

Design decisions:
- Uses certbot (industry standard)
- Standalone mode (no web server needed during renewal)
- Auto-renewal with cron/scheduler
- Falls back to self-signed if Let's Encrypt fails

Note: This is OPTIONAL. Self-signed certificates are perfectly fine
for home labs and are the recommended default.
"""

import subprocess
import os
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class LetsEncryptManager:
    """
    Manage Let's Encrypt certificates using certbot
    
    This is optional and only for users who:
    - Have a public domain name
    - Want to avoid browser certificate warnings
    - Can expose ports 80/443 to the internet
    
    Most home lab users should use self-signed certificates instead.
    """
    
    # Default certbot paths
    CERTBOT_PATH = '/usr/bin/certbot'
    LETSENCRYPT_DIR = '/etc/letsencrypt'
    
    @staticmethod
    def is_certbot_installed() -> bool:
        """
        Check if certbot is installed
        
        Returns:
            bool: True if certbot is available
        
        Example:
            >>> if LetsEncryptManager.is_certbot_installed():
            ...     print("Can use Let's Encrypt")
        """
        return os.path.exists(LetsEncryptManager.CERTBOT_PATH)
    
    @staticmethod
    def obtain_certificate(
        domain: str,
        email: str,
        agree_tos: bool = False,
        test: bool = False
    ) -> Dict[str, any]:
        """
        Obtain a certificate from Let's Encrypt
        
        This uses certbot in standalone mode, which means:
        - DockerMate must be stopped first (port 80 conflict)
        - Certbot temporarily runs its own web server
        - Certificate is obtained and then DockerMate restarts
        
        Args:
            domain: Domain name (must point to this server)
            email: Email for renewal notifications
            agree_tos: Must be True to accept Let's Encrypt ToS
            test: Use staging server (doesn't count against rate limits)
        
        Returns:
            dict: {
                'success': bool,
                'cert_path': str or None,
                'key_path': str or None,
                'error': str or None
            }
        
        Example:
            >>> result = LetsEncryptManager.obtain_certificate(
            ...     domain='dockermate.example.com',
            ...     email='admin@example.com',
            ...     agree_tos=True
            ... )
            >>> if result['success']:
            ...     print(f"Certificate: {result['cert_path']}")
        
        Raises:
            ValueError: If agree_tos is False or email/domain invalid
        """
        # Validation
        if not agree_tos:
            raise ValueError("Must agree to Let's Encrypt Terms of Service")
        
        if not email or '@' not in email:
            raise ValueError("Valid email address required")
        
        if not domain or '.' not in domain:
            raise ValueError("Valid domain name required")
        
        if not LetsEncryptManager.is_certbot_installed():
            return {
                'success': False,
                'cert_path': None,
                'key_path': None,
                'error': 'certbot not installed'
            }
        
        try:
            # Build certbot command
            cmd = [
                LetsEncryptManager.CERTBOT_PATH,
                'certonly',
                '--standalone',  # Standalone mode (no web server)
                '--non-interactive',  # No prompts
                '--agree-tos',  # Accept ToS
                '--email', email,
                '-d', domain,
            ]
            
            # Use staging server for testing (avoids rate limits)
            if test:
                cmd.append('--staging')
                logger.info("Using Let's Encrypt STAGING server (test mode)")
            
            logger.info(f"Requesting certificate for {domain}...")
            logger.warning("Port 80 must be accessible from internet!")
            
            # Run certbot
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                logger.error(f"Certbot failed: {error_msg}")
                return {
                    'success': False,
                    'cert_path': None,
                    'key_path': None,
                    'error': error_msg
                }
            
            # Certificate files are stored by certbot
            cert_path = f"/etc/letsencrypt/live/{domain}/fullchain.pem"
            key_path = f"/etc/letsencrypt/live/{domain}/privkey.pem"
            
            # Verify files exist
            if not os.path.exists(cert_path) or not os.path.exists(key_path):
                return {
                    'success': False,
                    'cert_path': None,
                    'key_path': None,
                    'error': 'Certificate files not found after certbot run'
                }
            
            logger.info(f"Certificate obtained successfully for {domain}")
            
            return {
                'success': True,
                'cert_path': cert_path,
                'key_path': key_path,
                'error': None
            }
            
        except subprocess.TimeoutExpired:
            logger.error("Certbot timed out after 5 minutes")
            return {
                'success': False,
                'cert_path': None,
                'key_path': None,
                'error': 'Certbot timed out'
            }
        except Exception as e:
            logger.error(f"Unexpected error during certificate request: {e}")
            return {
                'success': False,
                'cert_path': None,
                'key_path': None,
                'error': str(e)
            }
    
    @staticmethod
    def renew_certificates() -> Dict[str, any]:
        """
        Renew all Let's Encrypt certificates
        
        This should be run periodically (daily is recommended).
        Certbot will only renew certificates that are close to expiry.
        
        Returns:
            dict: {
                'success': bool,
                'output': str,
                'error': str or None
            }
        
        Example:
            >>> # In a cron job or scheduler
            >>> result = LetsEncryptManager.renew_certificates()
            >>> if not result['success']:
            ...     send_alert(result['error'])
        """
        if not LetsEncryptManager.is_certbot_installed():
            return {
                'success': False,
                'output': '',
                'error': 'certbot not installed'
            }
        
        try:
            logger.info("Running certificate renewal...")
            
            result = subprocess.run(
                [LetsEncryptManager.CERTBOT_PATH, 'renew', '--quiet'],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                logger.error(f"Renewal failed: {result.stderr}")
                return {
                    'success': False,
                    'output': result.stdout,
                    'error': result.stderr
                }
            
            logger.info("Certificate renewal check complete")
            
            return {
                'success': True,
                'output': result.stdout,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"Renewal error: {e}")
            return {
                'success': False,
                'output': '',
                'error': str(e)
            }
