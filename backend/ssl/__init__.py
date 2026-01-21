"""
DockerMate SSL/TLS Package

Handles SSL certificate management:
- Self-signed certificate generation (default for home labs)
- Let's Encrypt integration (optional)
- Custom certificate support
- Automatic certificate renewal

Default Mode: Self-signed certificates
- 2048-bit RSA key
- Valid for 825 days (~2 years)
- Includes hostname and local IP in Subject Alternative Names
- SHA-256 signature
"""
