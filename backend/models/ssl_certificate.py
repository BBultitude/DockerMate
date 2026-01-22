"""
SSL Certificate Database Model

Tracks SSL/TLS certificates used by DockerMate for HTTPS.

Why this exists:
- Home labs need HTTPS for security (even self-signed)
- Let's Encrypt certs need renewal tracking
- Custom certs need validation tracking

Design decisions:
- Supports 3 cert types: self-signed, letsencrypt, custom
- Tracks expiry for auto-renewal alerts
- One active certificate at a time
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from .database import Base


class SSLCertificate(Base):
    """
    SSL Certificate tracking model
    
    Stores metadata about SSL certificates used for HTTPS.
    
    Certificate Types:
    - 'self-signed': Auto-generated, good for home labs
    - 'letsencrypt': Free certs from Let's Encrypt
    - 'custom': User-provided certificates
    
    Only one certificate should be active (is_active=True) at a time.
    """
    __tablename__ = "ssl_certificates"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Certificate type: self-signed, letsencrypt, custom
    cert_type = Column(String(50), nullable=False)
    
    # File paths
    cert_path = Column(String(500), nullable=False)
    key_path = Column(String(500), nullable=False)
    
    # Domain/hostname
    domain = Column(String(255), nullable=True)  # For Let's Encrypt
    
    # Validity period
    issued_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True, index=True)
    
    # Auto-renewal settings
    auto_renew = Column(Boolean, default=False)
    
    # Status
    is_active = Column(Boolean, default=False, index=True)
    
    # Let's Encrypt specific
    letsencrypt_email = Column(String(255), nullable=True)
    
    # Custom certificate metadata
    is_wildcard = Column(Boolean, default=False)
    uploaded_by_user = Column(Boolean, default=False)
    original_filename = Column(String(255), nullable=True)
    
    # Certificate chain (for custom certs with intermediate CAs)
    has_chain = Column(Boolean, default=False)
    chain_path = Column(String(500), nullable=True)
    
    # Custom cert validation
    validation_errors = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<SSLCertificate(type={self.cert_type}, domain={self.domain}, active={self.is_active})>"
    
    def days_until_expiry(self):
        """
        Calculate days until certificate expires
        
        Returns:
            int: Days remaining, or None if no expiry set
        """
        if not self.expires_at:
            return None
        
        from datetime import datetime
        delta = self.expires_at - datetime.utcnow()
        return delta.days
    
    def needs_renewal(self, days_before=30):
        """
        Check if certificate needs renewal
        
        Args:
            days_before: Renew if expiry is within this many days
        
        Returns:
            bool: True if renewal needed
        """
        days_left = self.days_until_expiry()
        if days_left is None:
            return False
        
        return days_left <= days_before
    
    def is_custom(self):
        """
        Check if this is a user-uploaded custom certificate
        
        Returns:
            bool: True if custom/uploaded certificate
        """
        return self.cert_type == 'custom' or self.uploaded_by_user
    
    def get_certificate_type_display(self):
        """
        Get user-friendly certificate type description
        
        Returns:
            str: Human-readable certificate type
        """
        type_map = {
            'self-signed': 'Self-Signed (DockerMate Generated)',
            'letsencrypt': "Let's Encrypt (Auto-Renewed)",
            'custom': 'Custom Certificate (User Uploaded)'
        }
        
        display = type_map.get(self.cert_type, 'Unknown')
        
        if self.is_wildcard:
            display += ' - Wildcard'
        
        return display
