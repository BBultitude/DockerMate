"""
DockerMate Authentication Package

Handles authentication and session management:
- Password hashing (bcrypt)
- Session token generation and validation
- Authentication middleware
- Single-user home lab design (no multi-user complexity)

Security Features:
- Bcrypt password hashing with work factor 12
- SHA-256 session token hashing
- httpOnly, secure, SameSite cookies
- Configurable session expiry (8h default, 7d remember me)
"""
