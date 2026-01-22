"""
SSL/TLS Package

Manages SSL certificates for HTTPS in DockerMate.

Modules:
- cert_manager: Self-signed certificate generation, custom import, and validation
- letsencrypt: Let's Encrypt integration (optional)

Default behavior:
- Generate self-signed certificate on first run
- Store in /app/data/ssl/
- Valid for 825 days (~2 years)
- Auto-renewal reminder at 30 days before expiry

Certificate Types:
1. Self-Signed (Default - Recommended for Home Labs):
   - Auto-generated, no external dependencies
   - One-time browser security exception needed
   - Manual renewal every ~2 years (simple button click)
   - No internet required

2. Let's Encrypt (Optional - For Public Domains):
   - Requires public domain name pointing to server
   - Requires ports 80/443 accessible from internet
   - Auto-renewal every 60 days
   - No browser warnings

3. Custom Upload (Advanced Users):
   - User provides their own certificate files
   - Supports wildcard certificates (*.example.com)
   - Supports corporate/purchased certificates
   - User manages renewal

For home labs:
- Self-signed certificates are RECOMMENDED
- One-time browser security exception needed
- No external dependencies or internet required
- Simplest setup and maintenance

For public-facing deployments:
- Let's Encrypt available if domain name configured
- Requires ports 80/443 accessible from internet
- Auto-renewal every 60 days
"""

from .cert_manager import CertificateManager
from .letsencrypt import LetsEncryptManager

__all__ = ['CertificateManager', 'LetsEncryptManager']
