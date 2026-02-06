# DockerMate 🐋

**Docker Management for Home Labs & Self-Hosters**

A lightweight, intelligent Docker management tool designed specifically for home lab environments, Raspberry Pi deployments, and self-hosters who want full control without complexity.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-20.10+-blue.svg)](https://www.docker.com/)
[![Version](https://img.shields.io/badge/version-1.0.0--rc1-green.svg)](PROJECT_STATUS.md)

---

## 🎯 Project Overview

DockerMate is a **home lab focused** Docker management tool designed for:
- 🏠 Single-user home lab environments (5-100 containers)
- 🔧 Self-hosters running personal services (media servers, home automation, development)
- 📚 Learning developers who want to understand Docker CLI commands
- 🥧 Resource-constrained hardware (Raspberry Pi 3+ to home servers)
- 🌐 **Offline deployments** (all dependencies bundled, no external CDN calls)

**Explicitly NOT for:**
- ❌ Enterprise deployments with compliance requirements
- ❌ Multi-user/multi-tenant scenarios
- ❌ Cloud-based services requiring external dependencies
- ❌ Large-scale operations (multiple hosts, orchestration)

---

## ✨ Key Features

### Core Management
- **🐳 Container Lifecycle**: Create, start, stop, restart, delete, import external containers
- **📦 Image Management**: Pull, tag, delete, with automatic update detection via Docker Hub
- **🌐 Network IPAM**: Hardware-aware IP management, subnet recommendations, topology visualization
- **💾 Volume Management**: CRUD operations, prune unused, adoption of external volumes
- **📚 Stack Deployment**: Full docker-compose support with YAML editor and validation
- **🏥 Health Monitoring**: 6-domain health checks (Docker, Database, Containers, Images, Networks, Volumes)

### Intelligent Features
- **🔄 Auto Update Detection**: Real digest-based checking against Docker Hub registry
- **↩️ Update & Rollback**: One-click updates with complete rollback capability and history
- **🏷️ Retag & Redeploy**: Change container image versions without full reconfiguration
- **🔁 Docker Run → Compose**: Convert docker run commands to docker-compose YAML
- **📋 Import Unmanaged**: Adopt external containers/networks/volumes into management

### User Experience
- **📚 Educational CLI Display**: See Docker CLI equivalent for every action (learning mode)
- **🎨 Real-Time Dashboard**: Live stats with differential updates (no flashing)
- **🧭 Environment Tags**: Organize by DEV/STG/PROD or create custom tags
- **✅ YAML Validation**: Client-side validation with js-yaml (catches structure errors)
- **🔧 Hardware-Aware**: Auto-adjusts features based on Raspberry Pi to Enterprise hardware

### Deployment & Security
- **🌐 Offline Ready**: All JavaScript/CSS libraries vendored locally (~683KB total)
- **🔒 Production Security**: HTTPS, CSRF protection, rate limiting, secure sessions
- **🔐 Password Management**: Smart validation + CLI reset tool
- **🚀 Zero External Dependencies**: Runs completely offline after initial Docker pull

---

## 🚀 Quick Start

### Prerequisites

- **Docker 20.10+** (tested on 24.x)
- **Docker Compose 2.0+** (optional, for deployment)
- **Python 3.11+** (for local development only)
- **Any of:** Raspberry Pi 3/4/5, x86_64/ARM64 Linux, Windows (WSL2), macOS

### Installation

#### Option 1: Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/BBultitude/DockerMate.git
cd DockerMate

# Start DockerMate (development mode with HTTPS)
docker-compose -f docker-compose.dev.yml up -d

# Access at https://localhost:5000
# (Accept self-signed certificate warning on first visit)

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Stop
docker-compose -f docker-compose.dev.yml down
```

#### Option 2: Docker Run (Production)

```bash
docker run -d \
  --name dockermate \
  -p 5000:5000 \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v dockermate_data:/app/data \
  -v dockermate_certs:/app/certs \
  -e DOCKERMATE_SSL_MODE=self-signed \
  dockermate/dockermate:latest

# Access at https://your-server-ip:5000
```

#### Option 3: Local Development

```bash
# Clone and enter directory
git clone https://github.com/BBultitude/DockerMate.git
cd DockerMate

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the application
python3 app.py

# Access at https://localhost:5000
```

### First-Time Setup

1. **Navigate to** `https://localhost:5000` (accept certificate warning)
2. **Create admin account** (see password requirements below)
3. **Start managing** your Docker environment!

---

## 🔐 Security & Passwords

### Password Requirements

DockerMate enforces modern password security (NIST 2024 guidelines):

**Requirements:**
- ✅ Minimum 12 characters (industry standard for 2025+)
- ✅ Must include: uppercase, lowercase, and digit
- ✅ No common weak patterns (`password`, `admin`, `qwerty`, etc.)
- ✅ Patterns detected anywhere (e.g., `!!!password!!!` rejected)

**Good Examples:**
```
MyDockerLabPass2026        ← Readable and strong
CorrectHorseBattery42      ← Passphrase style
SecureHomeLab!2026         ← With special char
DockerMatePassword2026     ← Clear and long
```

**Will Be Rejected:**
```
password123     ← Common pattern
admin2024       ← Predictable
Welcome123!     ← Too common
docker          ← Too short
```

**Pro Tips:**
- 📝 Use a password manager (Bitwarden, 1Password, KeePass)
- 🔤 Passphrases are great: `correct-horse-battery-staple`
- 📏 Length > Complexity: 16 simple chars beats 8 complex
- 🔑 Make it unique for DockerMate

### Password Reset

If you forget your password:

```bash
# Method 1: Using manage.py (Docker)
docker exec -it dockermate-dev python manage.py reset-password --temp

# Method 2: Using manage.py (Local)
python manage.py reset-password --temp

# Output:
# ✅ Password reset successful!
# Temporary password: CorrectHorseBattery42
# User must change password on next login

# Then login with temp password and set a new one
```

### Security Model

**Perimeter Security Design (Home Lab Optimized):**

✅ **What's Protected:**
- HTTPS/TLS 1.2+ encryption on all traffic
- All UI routes require authentication (`@require_auth()`)
- CSRF tokens on all mutation operations (21 endpoints)
- Rate limiting: Login (5/15min), Mutations (30/min)
- Secure session cookies (httpOnly, Secure, SameSite=Strict)
- Bcrypt password hashing (work factor 12)

⚠️ **Design Trade-offs:**
- API endpoints trust same-origin requests (no token auth)
- Single-user assumption (no RBAC or multi-tenancy)
- Network perimeter is primary defense layer

**Critical Requirements:**
- 🚫 **NEVER expose to public internet** (no port forwarding!)
- ✅ **REQUIRED**: Deploy on isolated VLAN with firewall rules
- ✅ **REQUIRED**: Use VPN (WireGuard/OpenVPN) for remote access
- ✅ Keep on trusted home network only

**This Design is NOT Suitable For:**
- ❌ Multi-user environments
- ❌ Untrusted network deployments
- ❌ Public-facing access
- ❌ Enterprise/compliance-driven systems

For enterprise security, use **Portainer Business Edition** or fork DockerMate to add API-level authentication.

---

## 📖 Documentation

- **[PROJECT_STATUS.md](PROJECT_STATUS.md)** - Current development status and sprint completion
- **[DESIGN-v2.md](DESIGN-v2.md)** - Complete technical design specification
- **[INSTRUCTIONS.md](INSTRUCTIONS.md)** - AI agent workflow and development guidelines
- **[DOCKER_COMPOSE_GUIDE.md](DOCKER_COMPOSE_GUIDE.md)** - Docker Compose syntax reference
- **[DOCKER_COMPOSE_QUICKREF.md](DOCKER_COMPOSE_QUICKREF.md)** - Quick reference guide
- **[docs/STORAGE_CONFIGURATION.md](docs/STORAGE_CONFIGURATION.md)** - Customizing data storage paths
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - How to contribute to the project
- **[KNOWN_ISSUES.md](KNOWN_ISSUES.md)** - Issue tracking and known bugs

---

## 🏗️ Project Status

**Current Version:** v1.0.0-rc1 (Release Candidate 1)
**Last Updated:** February 6, 2026
**Overall Completion:** ~85%

### Completed Sprints ✅

- ✅ **Sprint 1**: Foundation & Auth (authentication, SSL, setup wizard)
- ✅ **Sprint 2**: Container Management (full CRUD, hardware profiles)
- ✅ **Sprint 3**: Image Management & Updates (pull, tag, update detection, rollback)
- ✅ **Sprint 4**: Network Management (IPAM, topology, IP reservations)
- ✅ **Sprint 5**: Volumes, Stacks & Health (volume CRUD, docker-compose, health monitoring)
- ✅ **v1.0 Polish Sprint**: UI improvements, YAML validation, offline support

### What Works Right Now ✅

**Container Management:**
- ✅ Create with full configuration (ports, volumes, env vars, networks, restart policies)
- ✅ Start, stop, restart, delete operations
- ✅ Update containers to latest image versions
- ✅ Rollback to previous versions with history tracking
- ✅ Import external containers into management
- ✅ Retag containers (change image version without reconfiguration)
- ✅ Real-time status updates with differential rendering (no flashing)

**Image Management:**
- ✅ Pull images from Docker Hub
- ✅ Tag and retag images
- ✅ Delete unused images
- ✅ Automatic update detection (digest-based via Docker Hub v2 API)
- ✅ Update indicators on dashboard and containers page
- ✅ Background scheduler (checks every 6 hours)

**Network Management:**
- ✅ Create custom bridge networks
- ✅ Hardware-aware subnet recommendations
- ✅ IP address management and reservations
- ✅ Network topology visualization
- ✅ Auto-generated documentation
- ✅ Adopt/release external networks

**Volume Management:**
- ✅ Create and delete volumes
- ✅ Usage tracking (containers using each volume)
- ✅ Prune unused volumes
- ✅ Adopt/release external volumes

**Stack Deployment:**
- ✅ Deploy docker-compose stacks
- ✅ YAML editor with syntax highlighting
- ✅ Real-time YAML validation (js-yaml parser)
- ✅ Deploy, start, stop, delete stacks
- ✅ View stack logs
- ✅ Auto-import stack resources to database
- ✅ Docker run → Compose converter

**Health & Monitoring:**
- ✅ 6-domain health checks (Docker, Database, Containers, Images, Networks, Volumes)
- ✅ Real-time dashboard with auto-refresh
- ✅ Health detail page with actionable warnings
- ✅ Container health polling with exponential backoff

**Security & Production:**
- ✅ HTTPS with self-signed certificates
- ✅ CSRF protection on all mutations
- ✅ Rate limiting (login 5/15min, mutations 30/min)
- ✅ Password reset CLI tool
- ✅ Session management with secure cookies
- ✅ **Offline deployment support** (all dependencies vendored)

### Next Up ⏳

- ⏳ **Sprint 6**: Export & CLI (JSON/Compose/CLI export, bulk operations)
- ⏳ **Sprint 7**: Polish & Testing (mobile responsive, 90%+ test coverage, full documentation)

See **[PROJECT_STATUS.md](PROJECT_STATUS.md)** for detailed sprint breakdown.

---

## 🗺️ Roadmap

### v1.0.0 Release (Pending Sprint 6-7)
- ⏳ Multi-format export system (JSON, docker-compose, docker CLI)
- ⏳ Bulk export by environment
- ⏳ CLI command generation (learning mode)
- ⏳ Mobile-responsive UI
- ⏳ 90%+ test coverage
- ⏳ Complete user documentation

### v1.1.0 - First Enhancement (Q2 2026)
- 📊 Advanced health metrics and trends
- 📦 Additional export formats
- 📋 Stack templates library (common services)
- 🎨 UI refinements and themes

### v2.0.0 - Advanced Features (Future)
- 🔐 Optional 2FA (TOTP)
- 🪝 Webhook notifications
- ⏰ Advanced scheduling
- 🧩 Plugin system (maybe)

---

## 🌟 Why DockerMate?

### vs Portainer
- ✅ Simpler, focused on home lab use case
- ✅ Offline-ready (no CDN dependencies)
- ✅ Educational CLI display for learning
- ✅ Hardware-aware recommendations
- ❌ No enterprise features (by design)
- ❌ No agent-based multi-host (yet)

### vs Dockge
- ✅ More than just stacks (full container management)
- ✅ Network IPAM and topology
- ✅ Update detection and rollback
- ✅ Health monitoring
- ❌ Less stack-focused simplicity

### vs Docker CLI
- ✅ Visual interface for quick operations
- ✅ Shows equivalent CLI commands (educational)
- ✅ Update detection and one-click updates
- ✅ Network topology and IP management
- ❌ Not as powerful for scripting

**DockerMate is for you if:**
- 🏠 You run a home lab with 5-50 containers
- 📚 You want to learn Docker while using a GUI
- 🥧 You deploy on Raspberry Pi or low-power hardware
- 🌐 You need offline support (no internet on deployment network)
- 🔒 You trust your home network security

---

## 🤝 Contributing

We welcome contributions! See **[CONTRIBUTING.md](CONTRIBUTING.md)** for guidelines.

**Good Contributions:**
- 🐛 Bug fixes and error handling improvements
- ⚡ Performance optimizations (especially for Raspberry Pi)
- 📚 Documentation improvements
- 🏠 Home lab-specific features
- ✅ Test coverage improvements
- 🎨 UI/UX enhancements

**Not Accepted:**
- ❌ Enterprise features (LDAP, SAML, RBAC, multi-user)
- ❌ Complex dependencies that break offline support
- ❌ Features that don't work on Raspberry Pi
- ❌ Cloud-specific integrations

---

## 🐛 Reporting Issues

**Found a bug?**
Open an issue at: [GitHub Issues](https://github.com/BBultitude/DockerMate/issues)

**Security vulnerability?**
Email: [GitHub Issues](https://github.com/BBultitude/DockerMate/issues)

**Have a question?**
Check [GitHub Discussions](https://github.com/BBultitude/DockerMate/discussions)

---

## 📝 License

This project is licensed under the **MIT License** - see [LICENSE](LICENSE) file.

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
- [Portainer](https://www.portainer.io/) - For proving Docker GUIs are valuable
- [Dockge](https://github.com/louislam/dockge) - For stack-focused simplicity
- [Home Assistant](https://www.home-assistant.io/) - For hardware-aware design philosophy
- [Pi-hole](https://pi-hole.net/) - For excellent home lab UX patterns

**Technologies:**
- [Docker](https://www.docker.com/) & [Docker SDK for Python](https://docker-py.readthedocs.io/)
- [Flask](https://flask.palletsprojects.com/) & [SQLAlchemy](https://www.sqlalchemy.org/)
- [Alpine.js](https://alpinejs.dev/) & [Tailwind CSS](https://tailwindcss.com/)
- [Chart.js](https://www.chartjs.org/) - Dashboard graphs
- [js-yaml](https://github.com/nodeca/js-yaml) - YAML validation

**Community:**
- The amazing [r/homelab](https://reddit.com/r/homelab) and [r/selfhosted](https://reddit.com/r/selfhosted) communities
- All our contributors and issue reporters

---

## 📧 Contact & Support

- **📬 GitHub Issues**: [Report bugs or request features](https://github.com/BBultitude/DockerMate/issues)
- **💬 GitHub Discussions**: [Ask questions or share ideas](https://github.com/BBultitude/DockerMate/discussions)
- **📖 Documentation**: See [DESIGN-v2.md](DESIGN-v2.md) for technical details
- **📊 Status**: See [PROJECT_STATUS.md](PROJECT_STATUS.md) for current progress

---

## 🏅 Project Stats

- **Lines of Code**: ~15,000 (Python + JavaScript + HTML)
- **Test Coverage**: 78% (targeting 90%+ for v1.0)
- **Supported Platforms**: Raspberry Pi 3+ / x86_64 / ARM64
- **Supported Architectures**: linux/amd64, linux/arm64, linux/arm/v7
- **Docker Image Size**: ~250MB (Python + dependencies)
- **Vendored Assets**: ~683KB (Alpine.js, Chart.js, Tailwind, js-yaml)
- **Database**: SQLite (single-file, easy backups)
- **Offline Support**: ✅ Yes (all CDN dependencies bundled)

---

**Made with ❤️ for home lab enthusiasts by the self-hosting community**

*"Because your home lab deserves better than docker ps | grep"*
