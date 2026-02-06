# DockerMate

**Docker Management for Home Labs**

A lightweight, intelligent Docker management tool designed specifically for home lab environments and self-hosters.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

---

## 🎯 Project Overview

DockerMate is a **home lab focused** Docker management tool designed for:
- Single-user home lab environments (5-50 containers)
- Self-hosters running personal services
- Learning developers who want to understand Docker
- Resource-constrained hardware (Raspberry Pi to home servers)

**Explicitly NOT for:**
- Enterprise deployments with compliance requirements
- Multi-user/multi-tenant scenarios
- Cloud-based services requiring external dependencies
- Large-scale operations (100+ containers, multiple hosts)

---

## ✨ Key Features

- **🔄 Auto Update Detection** - Automatically detect when container images have updates available
- **🚀 One-Click Updates** - Update all containers with a single click (with safety confirmations)
- **🌐 Smart Network IPAM** - Hardware-aware IP address management with reservation system
- **🏷️ Environment Tags** - Organize containers by environment (PRD/UAT/DEV/SANDBOX)
- **📚 Educational CLI Display** - See the Docker CLI equivalent for every action (3 modes)
- **💚 Health Monitoring** - Automatic health checks with on-demand log analysis
- **📦 Export System** - Export container configurations in multiple formats
- **🔧 Hardware-Aware** - Automatically adjusts features based on available resources

---

## 🚀 Quick Start

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+ (optional, for easy deployment)
- Python 3.11+ (for local development)

### Installation

#### Option 1: Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/BBultitude/DockerMate.git
cd DockerMate

# Start DockerMate
docker-compose up -d

# Access at https://localhost:5000
# (Accept self-signed certificate warning)
```

#### Option 2: Docker Run

```bash
docker run -d \
  --name dockermate \
  -p 5000:5000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v ./data:/app/data \
  dockermate/dockermate:latest
```

#### Option 3: Local Development

```bash
# Clone the repository
git clone https://github.com/BBultitude/DockerMate.git
cd DockerMate

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python3 app.py
```

---

## 🔐 Password Requirements

When setting up DockerMate for the first time, you'll create an admin password.

### Requirements

DockerMate enforces modern password security best practices:

- **Minimum 12 characters** (industry standard for 2024+)
- **Required:** Uppercase letter, lowercase letter, and digit
- **Recommended:** Special characters for extra strength
- **Blocked:** Common weak patterns in any position

### What Makes a Good Password?

**✅ Good Examples:**
```
MyDockerLabPass2026
CorrectHorseBattery42
SecureHomeLab!2026
DockerMatePassword2026
HomeServerSecure!
```

**❌ Avoid These (Will Be Rejected):**
```
password123     ← Common pattern (rejected)
123password     ← Reversed pattern (rejected)
admin2024       ← Too predictable (rejected)
docker          ← Too short (rejected)
Welcome123!     ← Common pattern (rejected)
qwerty123       ← Keyboard pattern (rejected)
```

### Why These Requirements?

DockerMate follows modern password security research:

- **SSH.com recommendation**: 12-14 character minimum
- **NIST 2024 guidelines**: Length is the primary security factor
- **Industry consensus**: Complexity requirements create predictable patterns

Our smart validation detects weak passwords in any form:
- Catches `password123`, `123password`, and `!!!password!!!`
- Allows strong passphrases like `CorrectHorseBattery42`
- Encourages length over forced complexity
- Rejects common patterns even with symbol padding

### Password Tips

1. **Use a password manager** to generate and store strong passwords
2. **Passphrases are great**: `correct-horse-battery-staple` is strong and memorable
3. **Length matters most**: A 16-character simple password beats an 8-character complex one
4. **Make it unique**: Don't reuse passwords from other services
5. **Write it down**: If you keep it secure (safe, locked drawer), writing passwords down is safer than reusing weak ones

### Password Reset

If you forget your password, you can reset it using one of these methods:

**Method 1: Docker CLI (Recommended)**
```bash
# Generate a new temporary password
docker exec -it dockermate python reset_password.py

# Output will show:
# Temporary Password: Correct-horse-battery-42
# Force password change on next login: Yes
```

**Method 2: Environment Variable**
```bash
# Edit docker-compose.yml, add to environment section:
environment:
  - DOCKERMATE_RESET_PASSWORD=true

# Restart container
docker-compose restart

# Check logs for temporary password
docker-compose logs

# IMPORTANT: Remove the variable and restart again
# (Edit docker-compose.yml, remove the line, then restart)
```

---

## 📖 Documentation

- **[DESIGN.md](DESIGN.md)** - Complete technical design specification
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - How to contribute to the project
- **[PROJECT_STATUS.md](PROJECT_STATUS.md)** - Current development status

---

## 🏗️ Project Status

**Current Version:** v0.1.0-alpha (Sprint 3 in progress)

- ✅ Sprint 1: Foundation & Auth — complete
- ✅ Sprint 2: Container Management — complete
- 🔄 Sprint 3: Image Management & Updates — Tasks 1-7 complete
  - ✅ Image listing, pulling, tagging, deletion
  - ✅ Show all Docker containers (managed + external)
  - ✅ Real-time dashboard with auto-refresh
  - ✅ Background scheduler for update checks
  - ✅ Database sync / recovery after DB reset
  - ⏳ Update & redeploy, history, rollback (upcoming)
- ⏳ Sprint 4: Network Management
- ⏳ Sprint 5: Volumes, Stacks & Health
- ⏳ Sprint 6: Export & CLI
- ⏳ Sprint 7: Polish & Testing

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for detailed progress.

---

## 🛡️ Security

### Docker Socket Access

DockerMate requires access to `/var/run/docker.sock` to manage containers. This grants root-equivalent privileges. Important security considerations:

- **Network Isolation**: Run DockerMate on an isolated VLAN
- **Firewall Rules**: Restrict access to trusted IPs only
- **Never Public**: Never expose DockerMate to the public internet
- **VPN Access**: Use VPN for remote access
- **Regular Updates**: Keep DockerMate updated

### HTTPS

DockerMate runs with HTTPS by default:
- Self-signed certificates generated automatically
- Certificates include host IP addresses for LAN access
- Let's Encrypt support available (requires public domain)
- HTTP automatically redirects to HTTPS

### API Security Model

**Important: Home Lab Security Design**

DockerMate uses a **perimeter security model** optimized for trusted home lab networks:

- ✅ **UI routes protected**: All HTML pages require authentication (`@require_auth()`)
- ✅ **HTTPS everywhere**: TLS 1.2+ encryption for all traffic
- ✅ **CSRF protection**: All mutation operations protected with CSRF tokens
- ✅ **Rate limiting**: Login attempts and mutation operations rate-limited
- ⚠️ **API routes unprotected**: REST APIs trust same-origin requests (no session validation)

**Why This Architecture?**
- Single-user home lab context (no multi-user threats)
- Browser same-origin policy prevents external API access
- Reduces testing complexity and improves Raspberry Pi performance
- Relies on network-level security (firewall, VLAN isolation)

**Critical Security Requirements:**
- ⚠️ **NEVER expose DockerMate to public internet** (no port forwarding)
- ⚠️ **REQUIRED**: Isolated VLAN with firewall rules blocking external access
- ⚠️ **REQUIRED**: VPN for remote access (WireGuard/OpenVPN recommended)
- ✅ HTTPS prevents network sniffing on local network
- ✅ SameSite=Strict cookies prevent CSRF attacks
- ✅ Flask-WTF CSRF tokens on all mutation operations
- ✅ Rate limiting on authentication and API mutations

**This Design is NOT Suitable For:**
- ❌ Multi-user environments
- ❌ Untrusted network deployments
- ❌ Public-facing access
- ❌ Enterprise production systems

**For enterprise security needs**, use Portainer Business Edition or fork DockerMate to implement API-level authentication.

### Reporting Security Issues

If you discover a security vulnerability, please email: security@dockermate.project

**Do NOT** open public GitHub issues for security problems.

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Good Contributions:**
- Bug fixes
- Performance improvements
- Documentation improvements
- Home lab-specific features
- Test coverage improvements

**Not Accepted:**
- Enterprise features (LDAP, SAML, multi-user, RBAC)
- Complex dependencies that violate KISS principle
- Features that don't work on Raspberry Pi

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**In Summary:**
- ✅ Commercial use allowed
- ✅ Modification allowed
- ✅ Distribution allowed
- ✅ Private use allowed
- ⚠️ No liability or warranty
- ⚠️ License and copyright notice required

---

## 🙏 Acknowledgments

**Inspiration:**
- Portainer - For proving Docker GUIs are valuable
- Dockge - For stack-focused simplicity
- Home Assistant - For hardware-aware design
- Pi-hole - For excellent home lab UX

**Technologies:**
- Docker & Docker SDK
- Flask & SQLAlchemy
- Tailwind CSS & Alpine.js
- The amazing Python ecosystem

---

## 📧 Contact & Support

- **GitHub Issues**: [Report bugs or request features](https://github.com/BBultitude/DockerMate/issues)
- **GitHub Discussions**: [Ask questions or share ideas](https://github.com/BBultitude/DockerMate/discussions)
- **Documentation**: See [DESIGN.md](DESIGN.md) for technical details

---

## 🗺️ Roadmap

### v1.0.0 (Target: Q1 2026)
- ✅ Authentication system
- ✅ Container management (CRUD operations)
- 🔄 Image management & updates (foundation complete, update/redeploy upcoming)
- ⏳ Network management with IPAM
- ⏳ Volume management
- ⏳ Stack deployment (Docker Compose)
- ⏳ Health monitoring
- ⏳ Configuration export

### v1.1.0 (Target: Q2 2026)
- Enhanced health monitoring
- Additional export formats
- Stack templates library
- UI improvements

### v2.0.0 (Future)
- Optional multi-host support (keeping home lab focus)
- Advanced scheduling
- Plugin system (maybe)

---

**Made with ❤️ for home lab enthusiasts**