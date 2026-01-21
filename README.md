# 🐳 DockerMate

**Intelligent Docker Management for Home Labs**

DockerMate is a lightweight, user-friendly web interface for managing Docker containers, designed specifically for home lab enthusiasts and self-hosters. It grows with you from beginner to advanced user while respecting your hardware limitations.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-required-blue.svg)](https://www.docker.com/)

---

## ⚡ Key Features

### 🔄 Automatic Updates
- **Auto-detect updates** for all your containers
- **One-click update all** with automatic rollback on failure
- **Safe redeploy** with health verification
- Environment-based safety (skip production containers in bulk updates)

### 🌐 Intelligent Networking (IPAM)
- **Hardware-aware network sizing** - never create oversized networks
- **Smart IP allocation** with visual IP maps
- **IP reservations** with labels and color coding
- **Multi-IP container support** for VLAN separation
- Auto-generated network documentation

### 📊 Smart Resource Management
- **Hardware detection** - Raspberry Pi to Enterprise servers
- **Container limits** based on your hardware
- **Performance warnings** for oversized networks
- Adaptive monitoring intervals

### 🏥 Health Monitoring
- **Automatic health checks** (lightweight, scheduled)
- **Manual log analysis** (on-demand, detailed)
- Error pattern detection
- Health history tracking

### 📦 Export & Backup
- Export as **Docker run scripts**, **Compose files**, or **JSON**
- **Complete documentation** generated automatically
- Bulk export by environment (PRD/UAT/DEV)
- Volume backup commands included

### 🎓 Educational CLI Display
- See **CLI equivalent** for every action
- Three modes: Simple, Intermediate, Advanced
- Learn Docker while using the GUI
- Copy-paste ready commands

### 🔒 Simple Security
- Password-protected access (single-user)
- **HTTPS by default** (self-signed or Let's Encrypt)
- Session management with remember-me
- No enterprise bloat (LDAP/SAML/etc)

### 🎯 Environment Tags
- Tag containers as **PRD** / **UAT** / **DEV** / **SANDBOX**
- Environment-based safety features
- Host-level or per-container tagging
- Custom environments supported

---

## 🚀 Quick Start

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- x86_64, ARM64, or ARMv7 architecture
- 512MB RAM minimum (2GB+ recommended)

### Installation

#### Option 1: Docker Compose (Recommended)

```bash
# Clone repository
git clone https://github.com/BBultitude/DockerMate.git
cd DockerMate

# Create data directories
mkdir -p data stacks exports

# Start DockerMate
docker compose up -d

# View logs
docker compose logs -f
```

#### Option 2: Docker Run

```bash
# Clone repository
git clone https://github.com/BBultitude/DockerMate.git
cd DockerMate

# Build image
docker build -t dockermate:latest .

# Run container
docker run -d \
  --name dockermate \
  --restart unless-stopped \
  -p 5000:5000 \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v ./data:/app/data \
  -v ./stacks:/app/stacks \
  -v ./exports:/app/exports \
  dockermate:latest
```

### First-Time Setup

1. **Access DockerMate**: Navigate to `https://your-server-ip:5000`
2. **Accept Certificate Warning**: Click "Advanced" → "Proceed" (self-signed cert)
3. **Complete Setup Wizard**:
   - Create strong password
   - Choose HTTPS method (self-signed recommended for home labs)
   - Review hardware detection
   - Finish setup

4. **Login**: Use your password to access DockerMate

---

## 📖 Documentation

- **[Complete Design Document](DESIGN.md)** - Full technical specification
- **[Contributing Guide](CONTRIBUTING.md)** - How to contribute
- **[Issues & Bug Reports](https://github.com/BBultitude/DockerMate/issues)** - Report bugs or request features
- **[Discussions](https://github.com/BBultitude/DockerMate/discussions)** - Ask questions and share ideas

---

## 🎯 Use Cases

### Media Server Management
Perfect for managing Jellyfin, Plex, *arr stacks with organized networking and automatic updates.

### Development Environments
Learn Docker while building - see CLI commands for every action, experiment safely in DEV mode.

### Home Lab Production Services
Separate DEV/UAT/PRD environments, health monitoring, safe updates with rollback.

### Resource-Constrained Deployments
Optimized for Raspberry Pi and low-power devices with intelligent resource limits.

---

## 🔧 Configuration

### Environment Variables

```yaml
# docker-compose.yml
environment:
  # Timezone
  - TZ=UTC
  
  # Initial setup password (optional - wizard prompts if not set)
  # - DOCKERMATE_INITIAL_PASSWORD=YourSecurePassword123
  
  # HTTPS mode
  - DOCKERMATE_SSL_MODE=self-signed  # or 'letsencrypt' or 'custom'
  
  # Let's Encrypt (if using)
  # - DOCKERMATE_DOMAIN=dockermate.home.example.com
  # - DOCKERMATE_EMAIL=admin@example.com
  
  # Session expiry
  - DOCKERMATE_SESSION_EXPIRY=8h
  - DOCKERMATE_REMEMBER_ME_EXPIRY=7d
  
  # Hardware profile (optional - auto-detected)
  # - DOCKERMATE_HARDWARE_PROFILE=MEDIUM_SERVER
  
  # Host environment (optional - wizard asks if not set)
  # - DOCKERMATE_HOST_ENVIRONMENT=DEV
```

### Storage Paths

```
dockermate/
├── data/                   # Database, SSL certs, configs
│   ├── dockermate.db      # SQLite database
│   ├── config.json        # Settings
│   └── ssl/               # SSL certificates
├── stacks/                # Docker Compose files
└── exports/               # Configuration exports
```

---

## 🛡️ Security

### Network Security
✅ **DO**: Run on isolated VLAN  
✅ **DO**: Use firewall rules  
✅ **DO**: Use VPN for remote access  
❌ **DON'T**: Expose to public internet  

### Password Security
✅ **DO**: Use strong, unique password  
✅ **DO**: Store in password manager  
✅ **DO**: Change periodically  
❌ **DON'T**: Reuse passwords  

### HTTPS
✅ **DO**: Use HTTPS (self-signed OK for home)  
✅ **DO**: Add browser exception for your IP  
❌ **DON'T**: Disable HTTPS  

See [DESIGN.md](DESIGN.md) for complete security best practices.

---

## 🔄 Password Reset

If you forget your password:

### Method 1: Docker CLI (Recommended)
```bash
docker exec -it dockermate python reset_password.py
# Follow prompts, receive temporary password
```

### Method 2: Environment Variable
```bash
# Edit docker-compose.yml, add:
# - DOCKERMATE_RESET_PASSWORD=true

docker compose down
docker compose up -d

# Check logs for temporary password
docker compose logs

# Remove environment variable and restart
```

---

## 🆚 Comparison

| Feature | Portainer CE | Dockge | **DockerMate** |
|---------|--------------|---------|----------------|
| Auto Update Detection | ❌ | ❌ | ✅ |
| One-Click Update All | ❌ | ⚠️ | ✅ |
| Hardware-Aware Limits | ❌ | ❌ | ✅ |
| IP Address Management | ⚠️ Basic | ❌ | ✅ Advanced |
| CLI Learning Mode | ❌ | ❌ | ✅ |
| Environment Tagging | ❌ | ❌ | ✅ |
| Home Lab Optimized | ❌ | ⚠️ | ✅ |
| Resource Required | High | Low | Low |
| Learning Curve | Steep | Easy | Easy → Advanced |

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Ways to Contribute
- 🐛 Bug reports and fixes
- 📖 Documentation improvements
- ✨ Feature requests (home lab focused)
- 🌍 Translations
- 🧪 Testing and feedback

### What We Won't Accept
- ❌ Enterprise features (LDAP, SAML, multi-user)
- ❌ Cloud dependencies
- ❌ Features that violate KISS principle

**Want enterprise features?** Fork the project! See [DESIGN.md](DESIGN.md) for fork guidelines.

---

## 🗺️ Roadmap

### v1.0.0 (Current Sprint)
- [x] Design complete
- [ ] Authentication & HTTPS
- [ ] Container management
- [ ] Auto-update system
- [ ] Network IPAM
- [ ] Health monitoring
- [ ] Export system

### v1.1.0 (Q2 2026)
- [ ] Enhanced UI/UX
- [ ] Additional export formats
- [ ] More stack templates
- [ ] Performance improvements

### v1.2.0 (Q3 2026)
- [ ] Webhook notifications
- [ ] Custom health check scripts
- [ ] Advanced scheduling

### v2.0.0 (Q4 2026)
- [ ] Optional multi-host management
- [ ] Plugin system (maybe)
- [ ] Enhanced backup/restore

---

## 📊 System Requirements

### Minimum
- **CPU**: 1 core
- **RAM**: 512MB
- **Disk**: 100MB
- **OS**: Linux with Docker

### Recommended
- **CPU**: 2+ cores
- **RAM**: 2GB+
- **Disk**: 1GB+
- **OS**: Ubuntu 22.04+ or Debian 12+

### Tested Platforms
- ✅ x86_64 (AMD64)
- ✅ ARM64 (Raspberry Pi 4, Apple M1/M2)
- ✅ ARMv7 (Raspberry Pi 3)

### Tested Distributions
- ✅ Ubuntu 22.04, 24.04
- ✅ Debian 11, 12
- ✅ Raspberry Pi OS
- ✅ Proxmox (LXC containers)
- ✅ Unraid (Docker)
- ✅ TrueNAS Scale

---

## 🐛 Troubleshooting

### Container won't start
```bash
# Check logs
docker logs dockermate

# Check permissions
ls -la /var/run/docker.sock

# Verify Docker access
docker exec dockermate docker ps
```

### Can't access web interface
```bash
# Check if running
docker ps | grep dockermate

# Check port binding
docker port dockermate

# Check firewall
sudo ufw status
```

### Certificate errors
```bash
# Regenerate self-signed certificate
docker exec dockermate python -c "from backend.ssl.cert_manager import CertificateManager; CertificateManager.generate_self_signed_cert()"

# Restart
docker restart dockermate
```

For more troubleshooting help, [open an issue](https://github.com/BBultitude/DockerMate/issues) on GitHub.

---

## 📜 License

MIT License - See [LICENSE](LICENSE) file for details.

**TL;DR**: 
- ✅ Use commercially
- ✅ Modify freely
- ✅ Distribute
- ✅ Private use
- ⚠️ No warranty
- ⚠️ License must be included

---

## 🙏 Acknowledgments

**Inspiration**
- Portainer - For proving Docker GUIs are valuable
- Dockge - For stack-focused simplicity
- Home Assistant - For hardware-aware design
- Pi-hole - For excellent home lab UX

**Built With**
- [Docker SDK](https://docker-py.readthedocs.io/) - Docker integration
- [Flask](https://flask.palletsprojects.com/) - Web framework
- [Tailwind CSS](https://tailwindcss.com/) - UI styling
- [Alpine.js](https://alpinejs.dev/) - Reactive components
- [SQLite](https://www.sqlite.org/) - Database

---

## 📞 Support

### Getting Help
- 📖 [Documentation](https://github.com/BBultitude/DockerMate/blob/main/DESIGN.md) - Read the design document
- 💬 [GitHub Discussions](https://github.com/BBultitude/DockerMate/discussions) - Ask questions
- 🐛 [Issue Tracker](https://github.com/BBultitude/DockerMate/issues) - Report bugs

### Security Issues
**Found a vulnerability?**
- 🔒 Open a private security advisory on GitHub
- Or create an issue with `[SECURITY]` prefix
- ⏱️ We'll respond as soon as possible

---

**Made with ❤️ for the home lab community**

[GitHub Repository](https://github.com/BBultitude/DockerMate)