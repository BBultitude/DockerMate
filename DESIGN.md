# DockerMate - Complete Design Documentation

**Version:** 1.0.0  
**Last Updated:** January 21, 2026  
**Status:** Design Complete - Ready for Implementation  
**License:** MIT  
**Focus:** 100% Home Lab Optimized

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Core Philosophy](#2-core-philosophy)
3. [Target Users & Use Cases](#3-target-users--use-cases)
4. [Technical Architecture](#4-technical-architecture)
5. [Hardware Profiling & Resource Management](#5-hardware-profiling--resource-management)
6. [Environment Management](#6-environment-management)
7. [Container Management](#7-container-management)
8. [Network Management & IPAM](#8-network-management--ipam)
9. [Image Management & Updates](#9-image-management--updates)
10. [Volume Management](#10-volume-management)
11. [Stack Management](#11-stack-management)
12. [Health Monitoring System](#12-health-monitoring-system)
13. [Export & Backup System](#13-export--backup-system)
14. [CLI Command Generation](#14-cli-command-generation)
15. [Authentication & Security](#15-authentication--security)
16. [User Interface Design](#16-user-interface-design)
17. [Database Schema](#17-database-schema)
18. [API Endpoints](#18-api-endpoints)
19. [Security Considerations](#19-security-considerations)
20. [Performance Optimization](#20-performance-optimization)
21. [Testing Strategy](#21-testing-strategy)
22. [Development Roadmap](#22-development-roadmap)
23. [Future Enhancements](#23-future-enhancements)
24. [Contributing](#24-contributing)

---

## 1. Project Overview

### 1.1 Mission Statement

DockerMate is a lightweight, intelligent Docker management tool designed specifically for home lab environments and self-hosters. It provides a user-friendly web interface that grows with the user's expertise—from beginner-friendly wizards to advanced power-user features—while respecting hardware limitations and promoting best practices.

### 1.2 Key Differentiators

| Feature | Portainer CE | Dockge | **DockerMate** |
|---------|--------------|---------|----------------|
| Auto Update Detection | ❌ | ❌ | ✅ |
| One-Click Update All | ❌ | ⚠️ Manual | ✅ |
| Auto Redeploy | ❌ | ❌ | ✅ |
| Network IPAM | ✅ Basic | ❌ | ✅ Advanced |
| Hardware-Aware Limits | ❌ | ❌ | ✅ |
| CLI Command Display | ❌ | ❌ | ✅ (3 modes) |
| Beginner → Advanced Path | ❌ | ❌ | ✅ |
| Health Monitoring | ✅ | ❌ | ✅ Intelligent |
| Export Configurations | ⚠️ Limited | ❌ | ✅ Comprehensive |
| Environment Tags | ❌ | ❌ | ✅ Host & Container |
| Resource Management | ❌ | ❌ | ✅ Hardware-Aware |

### 1.3 Design Principles

1. **KISS (Keep It Simple, Stupid)** - Simplicity over complexity
2. **Hardware-Aware** - Respect resource limitations
3. **Educational** - Show CLI equivalents for learning
4. **Progressive Disclosure** - Hide complexity until needed
5. **Safety First** - Prevent destructive actions, especially in production
6. **Offline-First** - No cloud dependencies
7. **Single-User Optimized** - Perfect for home labs
8. **Home Lab Focused** - Never enterprise bloat

---

## 2. Core Philosophy

### 2.1 User Experience Principles

#### **Beginner Mode**
- Form-based container creation
- Visual wizards for complex tasks
- Tooltips and inline help
- Pre-built templates
- Safe defaults
- Warning before destructive actions

#### **Intermediate Mode**
- YAML editors with validation
- Direct network configuration
- Volume management
- Stack deployment
- CLI command preview

#### **Advanced Mode**
- Raw Docker operations
- Custom registries
- Complex networking
- Multi-network containers
- Expert options unlocked

### 2.2 Hardware Respect

DockerMate adapts to available hardware:

- **Raspberry Pi**: Limited features, conservative limits
- **Low-End**: Basic features, on-demand processing
- **Medium Server**: Full features, balanced monitoring
- **High-End**: All features, real-time monitoring
- **Enterprise**: Unlimited, continuous monitoring

### 2.3 Safety & Production Awareness

Environment-based safety features:

- **PRD (Production)**: Maximum safety, confirmations required
- **UAT (Testing)**: Moderate safety, some confirmations
- **DEV (Development)**: Minimal safety, fast iteration
- **SANDBOX**: No safety restrictions, experimental

### 2.4 Home Lab First

**Design Decisions:**
- ✅ Single-user authentication (password-based)
- ✅ Self-signed HTTPS certificates (with Let's Encrypt option)
- ✅ Local-only operation (no cloud dependencies)
- ✅ Simple backup/export (manual, user-controlled)
- ❌ NO multi-user management
- ❌ NO LDAP/SAML/OAuth (enterprise complexity)
- ❌ NO role-based access control
- ❌ NO audit compliance features

---

## 3. Target Users & Use Cases

### 3.1 Primary User Personas

#### **Home Lab Enthusiast**
- **Profile**: Runs 5-20 containers on NAS or mini PC
- **Needs**: Easy management, auto-updates, network organization
- **Pain Points**: Port conflicts, forgetting what containers do
- **Solution**: DockerMate's IPAM, descriptions, auto-updates

#### **Self-Hoster**
- **Profile**: Runs personal services (Jellyfin, *arr stack, etc.)
- **Needs**: Reliable updates, health monitoring, backup configs
- **Pain Points**: Services break after updates, no monitoring
- **Solution**: Safe updates, health checks, export system

#### **Learning Developer**
- **Profile**: Learning Docker, wants to understand commands
- **Needs**: See CLI equivalents, understand what's happening
- **Pain Points**: GUI abstracts too much, hard to learn
- **Solution**: CLI command display in 3 modes

#### **Small Business Admin**
- **Profile**: Managing production services on dedicated hardware
- **Needs**: Environment separation, safety, monitoring
- **Pain Points**: Accidentally breaking production, no isolation
- **Solution**: Environment tags, confirmations, health monitoring

### 3.2 Use Cases

#### **Use Case 1: Media Server Setup**
```
User: Home lab enthusiast
Goal: Deploy Jellyfin + Sonarr + Radarr + Prowlarr
Steps:
1. Create "media-network" with /26 subnet
2. Reserve IPs .10-.19 for media services
3. Deploy stack from wizard
4. Auto-assign IPs in reserved range
5. Enable auto-updates for non-breaking changes
6. Set up health monitoring
Result: Organized media stack with clean networking
```

#### **Use Case 2: Development Environment**
```
User: Learning developer
Goal: Understand Docker while building app stack
Steps:
1. Set host environment to DEV
2. Create containers via form
3. View CLI equivalent after each action
4. Copy commands to notes for learning
5. Experiment with confidence (DEV mode)
Result: Learning Docker through practical experience
```

#### **Use Case 3: Production Migration**
```
User: Small business admin
Goal: Move containers from dev to production
Steps:
1. Export all DEV containers
2. Review exported configs
3. Change environment tags to PRD
4. Deploy on production server
5. Enable confirmations and health checks
6. Disable auto-updates
Result: Safe production deployment with documentation
```

#### **Use Case 4: Resource-Constrained Deployment**
```
User: Raspberry Pi user
Goal: Run maximum containers on limited hardware
Steps:
1. DockerMate detects Pi, sets 15 container limit
2. Suggests /27 network (30 IPs)
3. Warns when approaching limits
4. Disables CPU-intensive features
5. Recommends cleanup when at 90%
Result: Stable operation within hardware limits
```

---

## 4. Technical Architecture

### 4.1 Technology Stack

#### **Backend**
```
Language: Python 3.11+
Framework: Flask 3.0
Docker SDK: docker-py 7.0
Scheduler: APScheduler 3.10
Database: SQLite 3.40
ORM: SQLAlchemy 2.0
Validation: Pydantic 2.0
Logging: Structured logging with JSON
SSL/TLS: cryptography, certbot (optional)
Password Hashing: bcrypt
```

#### **Frontend**
```
Base: HTML5 + Jinja2 templates
CSS: Tailwind CSS 3.4
JavaScript: Alpine.js 3.13 (reactive)
Code Editor: Monaco Editor 0.45 (VS Code)
Charts: Chart.js 4.4
Icons: Lucide Icons 0.263
Live Updates: Server-Sent Events (SSE)
```

#### **Container**
```
Base Image: python:3.11-slim-bookworm
Size Target: <200MB
Ports: 5000 (HTTPS)
Volumes:
  - /var/run/docker.sock (Docker control)
  - ./data (SQLite + configs + SSL certs)
  - ./stacks (Compose files)
  - ./exports (Configuration exports)
```

### 4.2 System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     User Browser                         │
│                 (HTTPS Client)                           │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ HTTPS (TLS 1.2+)
                     │
┌────────────────────▼────────────────────────────────────┐
│                  Flask Application                       │
│  ┌─────────────────────────────────────────────────┐   │
│  │         Authentication Middleware                │   │
│  │  Session validation, password verification       │   │
│  └────────────┬────────────────────────────────────┘   │
│               │                                          │
│  ┌────────────▼────────────────────────────────────┐   │
│  │              API Endpoints                       │   │
│  │  /api/containers | /api/images | /api/networks  │   │
│  │  /api/volumes | /api/stacks | /api/health       │   │
│  │  /api/auth | /api/updates | /api/export         │   │
│  └────────────┬────────────────────────────────────┘   │
│               │                                          │
│  ┌────────────▼────────────────────────────────────┐   │
│  │           Business Logic Layer                   │   │
│  │  ┌──────────────┐  ┌──────────────┐            │   │
│  │  │ Docker Mgr   │  │ Network Mgr  │            │   │
│  │  ├──────────────┤  ├──────────────┤            │   │
│  │  │ Update Mgr   │  │ Health Mgr   │            │   │
│  │  ├──────────────┤  ├──────────────┤            │   │
│  │  │ Backup Mgr   │  │ CLI Gen      │            │   │
│  │  ├──────────────┤  ├──────────────┤            │   │
│  │  │ Auth Mgr     │  │ Cert Mgr     │            │   │
│  │  └──────────────┘  └──────────────┘            │   │
│  └────────────┬────────────────────────────────────┘   │
│               │                                          │
│  ┌────────────▼────────────────────────────────────┐   │
│  │           Data Access Layer                      │   │
│  │  SQLAlchemy ORM + SQLite Database               │   │
│  └─────────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ Docker Socket
                     │
┌────────────────────▼────────────────────────────────────┐
│                   Docker Engine                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Containers | Images | Networks | Volumes       │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 4.3 Directory Structure

```
dockermate/
├── Dockerfile                      # Container build
├── docker-compose.yml             # Self-hosting
├── requirements.txt               # Python deps
├── README.md                      # User guide
├── DESIGN.md                      # This document
├── LICENSE                        # MIT License
│
├── app.py                         # Flask entry point
├── config.py                      # Configuration
├── reset_password.py              # Password reset tool
│
├── backend/
│   ├── __init__.py
│   │
│   ├── auth/                      # Authentication
│   │   ├── __init__.py
│   │   ├── session_manager.py    # Session handling
│   │   ├── password_manager.py   # Password hashing
│   │   └── middleware.py         # Auth middleware
│   │
│   ├── ssl/                       # SSL/TLS
│   │   ├── __init__.py
│   │   ├── cert_manager.py       # Certificate management
│   │   └── letsencrypt.py        # Let's Encrypt integration
│   │
│   ├── api/                       # REST API endpoints
│   │   ├── __init__.py
│   │   ├── auth.py               # Auth endpoints
│   │   ├── containers.py         # Container CRUD
│   │   ├── images.py             # Image operations
│   │   ├── networks.py           # Network + IPAM
│   │   ├── volumes.py            # Volume management
│   │   ├── stacks.py             # Compose stacks
│   │   ├── updates.py            # Update detection
│   │   ├── health.py             # Health checks
│   │   └── export.py             # Config export
│   │
│   ├── managers/                  # Business logic
│   │   ├── __init__.py
│   │   ├── docker_client.py      # Docker SDK wrapper
│   │   ├── network_manager.py    # Network operations
│   │   ├── ip_allocator.py       # IP assignment
│   │   ├── update_manager.py     # Update logic
│   │   ├── health_manager.py     # Health monitoring
│   │   ├── backup_manager.py     # Export orchestration
│   │   ├── cli_generator.py      # CLI commands
│   │   └── resource_manager.py   # Hardware profiling
│   │
│   ├── models/                    # Database models
│   │   ├── __init__.py
│   │   ├── database.py           # SQLAlchemy setup
│   │   ├── user.py               # User model
│   │   ├── session.py            # Session model
│   │   ├── container.py          # Container model
│   │   ├── network.py            # Network model
│   │   ├── environment.py        # Environment model
│   │   ├── reservation.py        # IP reservation
│   │   └── health_check.py       # Health results
│   │
│   ├── utils/                     # Utilities
│   │   ├── __init__.py
│   │   ├── logging.py            # Structured logging
│   │   ├── validators.py         # Input validation
│   │   ├── subnet_calculator.py  # CIDR math
│   │   └── errors.py             # Custom exceptions
│   │
│   └── scheduler/                 # Background jobs
│       ├── __init__.py
│       ├── update_checker.py     # Periodic updates
│       └── cert_renewal.py       # Cert auto-renewal
│
├── frontend/
│   ├── static/
│   │   ├── css/
│   │   │   └── main.css          # Tailwind output
│   │   ├── js/
│   │   │   ├── app.js            # Core logic
│   │   │   ├── auth.js           # Login handling
│   │   │   ├── containers.js     # Container page
│   │   │   ├── networks.js       # Network page
│   │   │   ├── images.js         # Image page
│   │   │   ├── health.js         # Health page
│   │   │   └── cli-display.js    # CLI viewer
│   │   └── img/
│   │       └── logo.svg
│   │
│   └── templates/
│       ├── base.html             # Base layout
│       ├── login.html            # Login page
│       ├── setup.html            # Initial setup wizard
│       ├── dashboard.html        # Main dashboard
│       ├── containers.html       # Container mgmt
│       ├── images.html           # Image + updates
│       ├── networks.html         # Network + IPAM
│       ├── volumes.html          # Volume mgmt
│       ├── stacks.html           # Stack mgmt
│       ├── health.html           # Health monitoring
│       ├── settings.html         # Settings
│       └── components/
│           ├── ip-picker.html    # IP selection
│           ├── network-wizard.html # Network creator
│           └── cli-viewer.html   # CLI display
│
├── data/                         # Mounted volume
│   ├── dockermate.db            # SQLite DB
│   ├── config.json              # Settings
│   ├── ssl/                     # SSL certificates
│   │   ├── cert.pem
│   │   └── key.pem
│   └── backups/                 # Config backups
│
├── stacks/                      # Mounted volume
│   └── [user-stacks]/           # Compose files
│
├── exports/                     # Mounted volume
│   └── [dated-exports]/         # Config exports
│
└── tests/
    ├── unit/
    │   ├── test_auth.py
    │   ├── test_network_manager.py
    │   ├── test_ip_allocator.py
    │   ├── test_update_manager.py
    │   └── test_cli_generator.py
    ├── integration/
    │   ├── test_container_lifecycle.sh
    │   ├── test_network_creation.sh
    │   ├── test_auth_flow.sh
    │   └── test_update_workflow.sh
    └── README.md
```

### 4.4 Data Flow Examples

#### **Authentication Flow**
```
1. User visits https://dockermate:5000
   └─> Check session cookie
       
2. No valid session → Redirect to /login
   └─> User enters password
       
3. POST /api/auth/login
   ├─> Validate password (bcrypt)
   ├─> Create session token
   ├─> Store in database (hashed)
   └─> Set httpOnly secure cookie
       
4. Redirect to /dashboard
   └─> Session validated on each request
```

#### **Container Creation Flow**
```
1. User fills form in UI
   └─> POST /api/containers/create
       
2. API validates input
   ├─> Check session (authenticated?)
   ├─> Check name uniqueness
   ├─> Validate environment tag
   ├─> Check hardware limits
   └─> Validate network/IP
       
3. Docker Manager creates container
   ├─> Pull image if needed
   ├─> Assign IP from IPAM
   ├─> Create container
   └─> Store metadata in DB
       
4. CLI Generator creates commands
   └─> Store for display
       
5. Response to UI
   └─> Show container details + CLI
```

---

## 5. Hardware Profiling & Resource Management

### 5.1 Hardware Detection

```python
# Detection Logic
def detect_hardware_profile():
    cpu_cores = psutil.cpu_count(logical=True)
    ram_gb = psutil.virtual_memory().total / (1024**3)
    is_raspberry_pi = check_raspberry_pi()
    
    if is_raspberry_pi:
        return RASPBERRY_PI_PROFILE
    elif cpu_cores <= 4 and ram_gb <= 16:
        return LOW_END_PROFILE
    elif cpu_cores <= 16 and ram_gb <= 64:
        return MEDIUM_SERVER_PROFILE
    elif cpu_cores <= 32 and ram_gb <= 128:
        return HIGH_END_PROFILE
    else:
        return ENTERPRISE_PROFILE
```

### 5.2 Hardware Profiles

#### **Raspberry Pi Profile**
```yaml
profile_name: RASPBERRY_PI
cpu_cores_max: 4
ram_gb_max: 8
max_containers: 15
update_check_interval: 12h
health_check_interval: 15m
enable_continuous_monitoring: false
enable_log_analysis: false
enable_auto_update: false
network_size_limit: /25  # Max 126 IPs
warning: "Limited resources detected. Some features disabled."
```

#### **Medium Server Profile** (Typical Home Lab)
```yaml
profile_name: MEDIUM_SERVER
cpu_cores_max: 16
ram_gb_max: 64
max_containers: 50
update_check_interval: 6h
health_check_interval: 5m
enable_continuous_monitoring: true
enable_log_analysis: on_demand
enable_auto_update: true
network_size_limit: /24  # Max 254 IPs
```

### 5.3 Container Limit Enforcement

When creating containers, DockerMate checks current count against hardware limits:

```
Raspberry Pi (15 container limit):
├─ 0-11 containers: ✅ Allowed, no warning
├─ 12-14 containers: ⚠️ Approaching limit warning
├─ 15 containers: ⚠️ At limit, still allowed
└─ 16+ containers: ❌ Blocked unless user acknowledges risk

Medium Server (50 container limit):
├─ 0-37 containers: ✅ Allowed, no warning
├─ 38-45 containers: ⚠️ Approaching limit warning
├─ 46-50 containers: ⚠️ At limit, still allowed
└─ 51+ containers: ❌ Blocked unless user acknowledges risk
```

---

## 6. Environment Management

### 6.1 Environment Types

| Code | Name | Color | Priority | Use Case |
|------|------|-------|----------|----------|
| PRD | Production | 🔴 Red | 1 | Critical services |
| UAT | User Acceptance Testing | 🟡 Yellow | 2 | Pre-production testing |
| DEV | Development | 🟢 Green | 3 | Development work |
| SANDBOX | Sandbox/Experimental | 🔵 Blue | 4 | Testing & experiments |

### 6.2 Host Environment Modes

#### **Single Environment Mode**
Host configured as DEV/UAT/PRD/SANDBOX:
- All containers default to host environment
- Can override per container
- Safety features based on host environment

#### **Mixed Environment Mode**
Host configured as MIXED:
- No default environment
- Must choose for each container
- Safety based on individual container tags

### 6.3 Environment-Based Features

| Feature | PRD | UAT | DEV | SANDBOX |
|---------|-----|-----|-----|---------|
| Confirmation for updates | ✅ | ⚠️ | ❌ | ❌ |
| Confirmation for deletion | ✅ | ⚠️ | ❌ | ❌ |
| Auto-update default | ❌ | ⚠️ | ✅ | ✅ |
| Health check frequency | High | Medium | Low | Low |
| Backup on change | ✅ | ⚠️ | ❌ | ❌ |
| Warning visibility | High | Medium | Low | None |

---

## 7. Container Management

### 7.1 Container Identity Requirements

Every container must have:

1. **Unique Name** - Docker-enforced globally unique name
2. **Description** - User-provided explanation (recommended)
3. **Environment Tag** - PRD/UAT/DEV/SANDBOX

### 7.2 Name Validation

```python
def validate_container_name(name, docker_client):
    """
    Validate container name for uniqueness and format
    
    Rules:
    1. Must be unique (all containers, running or stopped)
    2. Format: [a-zA-Z0-9][a-zA-Z0-9_.-]*
    3. Length: 1-255 characters
    
    Returns suggestions if name conflicts
    """
```

**Conflict Resolution:**
If `nginx-web` exists, suggest:
- `nginx-web-dev` (for DEV environment)
- `nginx-web-uat` (for UAT environment)
- `nginx-web-2` (alternative instance)
- `nginx-secondary` (different purpose)

### 7.3 Container Lifecycle

```
CREATE → RUNNING ⇄ STOPPED → DELETE
         ↓           ↓
       UPDATE     RESTART
```

Each transition:
- Generates CLI command for learning
- Logs event with timestamp
- Can be reverted (for updates via backup)

---

## 8. Network Management & IPAM

### 8.1 Intelligent Network Sizing

#### **Hardware-Aware Calculation**
```
Required IPs = (max_containers × ips_per_container) × (1 + buffer/100)

Examples:
Raspberry Pi (15 containers):
- 1 IP per container: 15 × 1 × 1.2 = 18 IPs → /27 (30 IPs) ✅
- 2 IPs per container: 15 × 2 × 1.2 = 36 IPs → /26 (62 IPs) ✅
- 4 IPs per container: 15 × 4 × 1.2 = 72 IPs → /25 (126 IPs) ⚠️

Medium Server (50 containers):
- 1 IP per container: 50 × 1 × 1.2 = 60 IPs → /26 (62 IPs) ✅
- 2 IPs per container: 50 × 2 × 1.2 = 120 IPs → /25 (126 IPs) ✅
```

### 8.2 Network Size Reference

| CIDR | Total IPs | Usable IPs | Containers (1 IP each) | Containers (4 IPs each) |
|------|-----------|------------|------------------------|-------------------------|
| /29 | 8 | 6 | 6 | 1 |
| /28 | 16 | 14 | 14 | 3 |
| /27 | 32 | 30 | 30 | 7 |
| /26 | 64 | 62 | 62 | 15 |
| /25 | 128 | 126 | 126 | 31 |
| /24 | 256 | 254 | 254 | 63 |
| /16 | 65536 | 65534 | 65534 | 16383 |

### 8.3 Conservative Network Sizing (Default)

**Default Behavior:**
- Show only appropriate sizes for hardware
- Hide oversized options by default
- User must opt-in to see larger sizes
- Display performance impact warnings

**User Checkbox:**
```
[ ] Show larger network sizes (not recommended)
    ⚠️ Larger networks may impact performance
    You own the risk if enabled
```

### 8.4 Multi-IP Container Support

**Use Case: VLAN Separation**
```yaml
# Container needs internal + internet IPs

networks:
  internal-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/26
  
  internet-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.21.0.0/26

services:
  web-server:
    networks:
      internal-network:
        ipv4_address: 172.20.0.10  # Internal
      internet-network:
        ipv4_address: 172.21.0.10  # Internet via firewall
```

### 8.5 IP Reservation System

Users can reserve IP ranges with labels:

```
Network: 172.20.0.0/26

Reservations:
├─ .10-.19 "Web Services" (blue)
├─ .20-.29 "Databases" (green)
├─ .30-.39 "Media Services" (yellow)
└─ .40-.49 "Background Workers" (purple)
```

Benefits:
- Organized IP allocation
- Visual IP map with colors
- Auto-assignment respects reservations
- Easy to remember where things are

### 8.6 Oversized Network Handling

#### **Warning at Creation**
```
User selects /24 on Raspberry Pi:

⚠️ WARNING: Oversized Network
Your hardware: 15 container limit
Network capacity: 254 containers
Waste: 94% of IPs unused
Performance impact: MODERATE

Required acknowledgments:
[×] I understand this network is oversized
[×] I accept potential performance issues
[×] I understand sizing cannot be changed later

[Use Recommended /27]  [Create Anyway]
```

#### **Persistent Warning in Network View**
```
⚠️ PERFORMANCE WARNING - OVERSIZED NETWORK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Network: experimental-network
Subnet: 10.10.0.0/24 (254 IPs)
Containers: 2 / 254 (0.8% utilization)

This network is significantly oversized for your hardware.

[Analyze Performance] [Recreate Smaller] [Dismiss]
```

**Dismissal Options:**
- 7 days
- 30 days
- Permanent
- Remind during maintenance window

---

## 9. Image Management & Updates

### 9.1 Update Detection System

**Automatic Detection** (every 6 hours, configurable):
```
1. Get all running containers
2. For each container:
   - Extract image name:tag
   - Get local image digest
   - Query registry for latest digest
   - Compare
   - If different: mark as "update available"
3. Update UI: "3 updates available"
```

### 9.2 Update & Redeploy Process

**Safe Update Workflow:**
```
Pre-Update:
├─ Backup container configuration (JSON)
├─ Store current image digest
├─ Store all settings (env, volumes, network)
└─ User can review before proceeding

Update:
├─ Pull new image
├─ Stop old container (graceful, 10s timeout)
├─ Rename old container (nginx → nginx-backup)
├─ Create new container (same config)
├─ Start new container
└─ Verify health (30s stabilization)

Post-Update:
├─ If healthy:
│   ├─ Remove old container
│   ├─ Remove old image (optional)
│   └─ Mark success
└─ If unhealthy:
    ├─ Stop new container
    ├─ Restore backup container
    ├─ Automatic rollback
    └─ Notify user of failure
```

### 9.3 One-Click "Update All"

**Process:**
- Sequential updates (not parallel for safety)
- Environment-based ordering: DEV → UAT → PRD
- Skip PRD containers (require manual confirmation)
- Stop on critical failure
- Continue on non-critical failures

**Results Display:**
```
Update All Results:
✅ Successful: 8
⚠️ Skipped: 2 (Production containers require manual update)
❌ Failed: 1 (rolled back automatically)
```

---

## 10. Volume Management

### 10.1 Storage Path Configuration

Users configure root storage directory in settings:

```yaml
Options:
- /var/lib/docker (Docker default)
- /mnt/appdata (Custom - recommended for home labs)
- /home/user/docker-data
- /opt/docker-volumes

Directory Structure:
organized_by_container:  # Recommended
  /mnt/appdata/
  ├── nginx-web/
  │   ├── html/
  │   └── conf/
  ├── postgres-db/
  │   └── data/
  └── jellyfin/
      ├── config/
      └── cache/
```

### 10.2 Smart Path Suggestions

When creating containers, DockerMate suggests paths based on user's storage configuration:

```
Container: jellyfin
Suggested paths:
- Config: /mnt/appdata/jellyfin/config → /config
- Cache:  /mnt/appdata/jellyfin/cache → /cache
- Media:  /mnt/media → /media (read-only)

[×] Auto-create directories
[×] Set proper permissions
```

---

## 11. Stack Management

### 11.1 Docker Compose Support

DockerMate stores compose files in `/opt/dockermate/stacks/`:

```yaml
version: '3.8'

# Auto-generated comments
# Stack: media-server
# Created: 2026-01-21
# Environment: DEV
# Network: media-network (172.21.0.0/26)

services:
  jellyfin:
    image: jellyfin/jellyfin:latest
    container_name: jellyfin-dev
    networks:
      media-network:
        ipv4_address: 172.21.0.10
    # ... rest of config

networks:
  media-network:
    external: true
```

### 11.2 Docker Run → Compose Converter

Paste `docker run` commands, get compose files:

```bash
# Input:
docker run -d --name nginx -p 80:80 -v /data:/usr/share/nginx/html nginx:latest

# Output:
version: '3.8'
services:
  nginx:
    image: nginx:latest
    container_name: nginx
    ports:
      - "80:80"
    volumes:
      - /data:/usr/share/nginx/html
```

---

## 12. Health Monitoring System

### 12.1 Two-Tier Health Checks

#### **Automatic (Lightweight)** - Runs every 5 minutes
```
Checks:
✅ Container status (running/stopped/restarting)
✅ Restart count
✅ Resource usage (CPU/RAM)
✅ Exit code if stopped
✅ Docker health checks (if defined in image)

Does NOT analyze logs (too CPU intensive)
```

#### **Manual (Full Analysis)** - User clicks "Analyze Logs"
```
Analysis:
✅ Fetch last 500 lines of logs
✅ Parse log levels (ERROR, WARN, INFO)
✅ Search for error patterns
✅ Count error rate (per minute)
✅ Identify common error messages
✅ Generate actionable recommendations

CPU-intensive - only run on demand
```

### 12.2 Health Status Levels

| Status | Icon | Description | Action |
|--------|------|-------------|--------|
| Healthy | ✅ | All checks pass | None |
| Warning | ⚠️ | Minor issues | Monitor |
| Critical | ❌ | Major issues | Immediate |
| Unknown | ❓ | Cannot determine | Investigate |
| Stopped | ⏸️ | Not running | Start if needed |

### 12.3 Hardware-Appropriate Monitoring

| Hardware | Health Check Interval | Log Analysis |
|----------|----------------------|--------------|
| Raspberry Pi | 15 minutes | On-demand only |
| Low-End | 10 minutes | On-demand only |
| Medium Server | 5 minutes | On-demand only |
| High-End | 2 minutes | On-demand or continuous |
| Enterprise | 1 minute | Continuous available |

---

## 13. Export & Backup System

### 13.1 Export Formats

| Format | File | Purpose |
|--------|------|---------|
| Docker Run | `run.sh` | Bash script to recreate |
| Compose | `compose.yml` | Docker Compose file |
| JSON | `config.json` | Machine-readable config |
| Documentation | `README.md` | Human-readable docs |
| Complete | `backup.tar.gz` | Everything bundled |

### 13.2 File Naming Convention

**Single Container Export:**
```
nginx-web/
├── run.sh
├── compose.yml
├── config.json
└── README.md
```

**Multi-Container Export:**
```
dockermate-backup-2026-01-21/
├── PRD/
│   ├── nginx-web-prd.docker-run.sh
│   ├── nginx-web-prd.compose.yml
│   └── nginx-web-prd.README.md
├── UAT/
├── DEV/
├── MASTER-INVENTORY.md
└── create-networks.sh
```

### 13.3 No Automatic Backups

```
⚠️ IMPORTANT: DockerMate does NOT auto-backup configurations

You must manually export:
- Per container: Container Details → Export
- Bulk: Containers → Export All

Recommended: Export after major changes
```

### 13.4 Volume Backup Commands

Export includes copy-paste backup commands:

```bash
# Backup
docker stop nginx-web
sudo rsync -av /mnt/appdata/nginx-web/ /mnt/backups/nginx-web-$(date +%Y%m%d)/
docker start nginx-web

# Restore
docker stop nginx-web
sudo rsync -av /mnt/backups/nginx-web-20260121/ /mnt/appdata/nginx-web/
docker start nginx-web
```

---

## 14. CLI Command Generation

### 14.1 Three Display Modes

#### **Simple** (Beginner)
```bash
docker run -d --name nginx nginx:latest
```

#### **Intermediate** (Default)
```bash
docker run -d \
  --name nginx-web \
  --network my-apps-network \
  --ip 172.20.0.10 \
  -v /mnt/appdata/nginx:/data \
  -p 80:80 \
  nginx:latest
```

#### **Advanced** (Production-Ready Script)
```bash
#!/bin/bash
set -e

# Check network exists
if ! docker network ls | grep -q my-apps-network; then
    docker network create --subnet 172.20.0.0/26 my-apps-network
fi

# Stop existing
docker stop nginx-web 2>/dev/null || true
docker rm nginx-web 2>/dev/null || true

# Create
docker run -d \
  --name nginx-web \
  --network my-apps-network \
  --ip 172.20.0.10 \
  -v /mnt/appdata/nginx:/data \
  -p 80:80 \
  --restart unless-stopped \
  nginx:latest

# Verify
if [ $? -eq 0 ]; then
    echo "✅ Container started"
else
    echo "❌ Failed"
    exit 1
fi
```

### 14.2 Educational Purpose

Every action in DockerMate shows the equivalent CLI command:
- Users learn Docker by using the GUI
- Can copy commands to notes
- Understand what's happening "under the hood"
- Graduate to CLI when comfortable

---

## 15. Authentication & Security

### 15.1 Design Philosophy

**Home Lab Focused:**
- ✅ Simple password authentication
- ✅ HTTPS with self-signed certificates
- ✅ Single-user access
- ✅ Session management
- ❌ NO enterprise auth (LDAP/SAML/OAuth)
- ❌ NO multi-user management
- ❌ NO role-based access control

### 15.2 Initial Setup Wizard

**First Launch:**
```
Step 1: Create Password
- Minimum 12 characters
- Strength indicator
- Requirements validation

Step 2: HTTPS Configuration
(*) Self-Signed (recommended for home)
( ) Let's Encrypt (requires public domain)
( ) Custom Certificate (advanced)

Step 3: Hardware Detection
- Auto-detect hardware profile
- Set container limits

Step 4: Review & Complete
- Restart with HTTPS enabled
- Add browser security exception (one-time)
```

### 15.3 Authentication System

#### **Password Requirements:**
- Minimum 12 characters
- Uppercase letter
- Lowercase letter
- Number
- Special character (recommended)

#### **Password Hashing:**
```python
# bcrypt with work factor 12
password_hash = bcrypt.hashpw(password, bcrypt.gensalt(12))
```

#### **Session Management:**
- Session tokens: 256-bit cryptographically secure
- Cookie: httpOnly, secure, SameSite=Strict
- Default expiry: 8 hours
- Remember me: 7 days
- Stored hashed in database

### 15.4 Password Reset

#### **Method 1: Docker CLI (Recommended)**
```bash
docker exec -it dockermate python reset_password.py

# Output:
Temporary Password: correct-horse-battery-staple-42
Force password change on next login: Yes
```

#### **Method 2: Environment Variable**
```yaml
# docker-compose.yml
environment:
  - DOCKERMATE_RESET_PASSWORD=true

# Restart container, new password in logs
# Remove variable and restart again
```

### 15.5 HTTPS Configuration

#### **Self-Signed Certificate (Default)**
```
Automatic generation on first setup:
- 2048-bit RSA key
- Valid for 825 days (2+ years)
- Includes hostname and local IP
- SHA-256 signature

Browser warning expected:
1. Click "Advanced"
2. Click "Proceed anyway"
3. Add security exception (one-time)
```

#### **Let's Encrypt (Optional)**
```
Requirements:
- Public domain name
- Ports 80/443 accessible from internet
- DNS pointing to your server

Uses certbot:
- Auto-renewal every 60 days
- No browser warnings
- Free certificates
```

#### **Custom Certificate (Advanced)**
```
Provide your own:
- cert.pem (certificate)
- key.pem (private key)

For corporate/advanced home labs
```

### 15.6 Security Best Practices

**Network Security:**
- Run on isolated VLAN
- Use firewall rules
- VPN for remote access
- Never expose to public internet

**Password Security:**
- Use strong, unique password
- Store in password manager
- Change periodically
- Never reuse from other services

**HTTPS:**
- Always use HTTPS (self-signed OK)
- Add browser exception for your IP
- Regenerate cert annually
- Never disable HTTPS

**Docker Socket:**
- DockerMate requires socket access
- Can control all containers
- Keep DockerMate container isolated
- Monitor logs for suspicious activity

---

## 16. User Interface Design

### 16.1 Layout Structure

```
┌─────────────────────────────────────────────────────────┐
│ 🐳 DockerMate    [Dashboard] [Containers] [Images]      │
│                  [Networks] [Volumes] [Stacks]          │
│ 🟢 DEV Host      [Health]              [⚙️] [Logout]    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│                    Main Content Area                     │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 16.2 Color Scheme

```css
/* Environment Colors */
--env-prd: #ef4444;     /* red-500 */
--env-uat: #eab308;     /* yellow-500 */
--env-dev: #22c55e;     /* green-500 */
--env-sandbox: #3b82f6; /* blue-500 */

/* Status Colors */
--status-healthy: #22c55e;   /* green-500 */
--status-warning: #f59e0b;   /* amber-500 */
--status-critical: #ef4444;  /* red-500 */

/* Dark Mode Theme */
--bg-primary: #0f172a;    /* slate-900 */
--bg-secondary: #1e293b;  /* slate-800 */
--text-primary: #f1f5f9;  /* slate-100 */
```

### 16.3 Responsive Design

```
Mobile (< 768px):
├─ Single column
├─ Hamburger menu
├─ Touch-friendly buttons
└─ Simplified tables

Desktop (> 1024px):
├─ Full sidebar
├─ Multi-column layouts
└─ High information density
```

---

## 17. Database Schema

### 17.1 Complete Schema

```sql
-- ============================================
-- Authentication
-- ============================================

CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username VARCHAR(255) DEFAULT 'admin',
    password_hash VARCHAR(255) NOT NULL,
    force_password_change BOOLEAN DEFAULT FALSE,
    password_reset_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sessions (
    id INTEGER PRIMARY KEY,
    token_hash VARCHAR(64) UNIQUE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    last_accessed DATETIME,
    user_agent TEXT,
    ip_address VARCHAR(45)
);

CREATE TABLE ssl_certificates (
    id INTEGER PRIMARY KEY,
    cert_type VARCHAR(50) NOT NULL,
    cert_path VARCHAR(500),
    key_path VARCHAR(500),
    domain VARCHAR(255),
    issued_at DATETIME,
    expires_at DATETIME,
    auto_renew BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- Configuration
-- ============================================

CREATE TABLE host_config (
    id INTEGER PRIMARY KEY,
    host_environment VARCHAR(50) NOT NULL,
    host_name VARCHAR(255),
    hardware_profile VARCHAR(50),
    max_containers INTEGER,
    enable_auto_update BOOLEAN DEFAULT TRUE,
    require_prd_confirmation BOOLEAN DEFAULT TRUE,
    storage_root VARCHAR(500),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE environments (
    id INTEGER PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    color VARCHAR(20) DEFAULT 'gray',
    icon_emoji VARCHAR(10) DEFAULT '🔵',
    display_order INTEGER DEFAULT 999,
    require_confirmation BOOLEAN DEFAULT FALSE,
    prevent_auto_update BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- Docker Resources
-- ============================================

CREATE TABLE containers (
    id INTEGER PRIMARY KEY,
    docker_id VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    environment VARCHAR(50) NOT NULL,
    image_name VARCHAR(255) NOT NULL,
    image_tag VARCHAR(100) NOT NULL,
    image_digest VARCHAR(100),
    network_id INTEGER,
    ip_address VARCHAR(45),
    dockermate_instance_id VARCHAR(64),
    docker_host VARCHAR(255) DEFAULT 'local',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_started DATETIME,
    labels TEXT,
    FOREIGN KEY (network_id) REFERENCES networks(id),
    FOREIGN KEY (environment) REFERENCES environments(code)
);

CREATE TABLE networks (
    id INTEGER PRIMARY KEY,
    docker_id VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(255) UNIQUE NOT NULL,
    driver VARCHAR(50) DEFAULT 'bridge',
    subnet VARCHAR(50) NOT NULL,
    gateway VARCHAR(45) NOT NULL,
    recommended_cidr VARCHAR(10),
    actual_cidr VARCHAR(10) NOT NULL,
    oversized BOOLEAN DEFAULT FALSE,
    performance_impact VARCHAR(20),
    waste_percent FLOAT,
    user_acknowledged_risk BOOLEAN DEFAULT FALSE,
    risk_acknowledged_at DATETIME,
    warning_dismissed_until DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ip_reservations (
    id INTEGER PRIMARY KEY,
    network_id INTEGER NOT NULL,
    ip_start VARCHAR(45) NOT NULL,
    ip_end VARCHAR(45) NOT NULL,
    label VARCHAR(255),
    description TEXT,
    color VARCHAR(20),
    prevent_auto_assign BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (network_id) REFERENCES networks(id) ON DELETE CASCADE
);

-- ============================================
-- Updates & Health
-- ============================================

CREATE TABLE update_checks (
    id INTEGER PRIMARY KEY,
    container_id VARCHAR(64) NOT NULL,
    checked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    current_digest VARCHAR(100),
    latest_digest VARCHAR(100),
    update_available BOOLEAN,
    FOREIGN KEY (container_id) REFERENCES containers(docker_id) ON DELETE CASCADE
);

CREATE TABLE update_history (
    id INTEGER PRIMARY KEY,
    container_id VARCHAR(64) NOT NULL,
    old_image VARCHAR(255),
    new_image VARCHAR(255),
    old_digest VARCHAR(100),
    new_digest VARCHAR(100),
    update_started DATETIME,
    update_completed DATETIME,
    success BOOLEAN,
    rolled_back BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    FOREIGN KEY (container_id) REFERENCES containers(docker_id) ON DELETE CASCADE
);

CREATE TABLE health_checks (
    id INTEGER PRIMARY KEY,
    container_id VARCHAR(64) NOT NULL,
    checked_at DATETIME NOT NULL,
    overall_status VARCHAR(20),
    issues TEXT,
    cpu_percent FLOAT,
    memory_percent FLOAT,
    restart_count INTEGER,
    FOREIGN KEY (container_id) REFERENCES containers(docker_id) ON DELETE CASCADE
);

CREATE TABLE log_analyses (
    id INTEGER PRIMARY KEY,
    container_id VARCHAR(64) NOT NULL,
    analyzed_at DATETIME NOT NULL,
    lines_analyzed INTEGER,
    error_count INTEGER,
    warning_count INTEGER,
    error_rate FLOAT,
    common_errors TEXT,
    analysis_duration FLOAT,
    FOREIGN KEY (container_id) REFERENCES containers(docker_id) ON DELETE CASCADE
);

-- ============================================
-- Security Events
-- ============================================

CREATE TABLE security_events (
    id INTEGER PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    success BOOLEAN,
    details TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- Indexes
-- ============================================

CREATE INDEX idx_containers_environment ON containers(environment);
CREATE INDEX idx_containers_name ON containers(name);
CREATE INDEX idx_sessions_expires ON sessions(expires_at);
CREATE INDEX idx_sessions_token ON sessions(token_hash);
CREATE INDEX idx_health_checks_container ON health_checks(container_id);
CREATE INDEX idx_security_events_type ON security_events(event_type);
```

---

## 18. API Endpoints

### 18.1 Authentication Endpoints

```
POST   /api/auth/login              # Login with password
POST   /api/auth/logout             # Logout (revoke session)
GET    /api/auth/session            # Check session validity
POST   /api/auth/change-password    # Change password
GET    /api/auth/sessions           # List active sessions
DELETE /api/auth/sessions/{id}      # Revoke specific session
```

### 18.2 Container Endpoints

```
GET    /api/containers              # List all containers
POST   /api/containers              # Create container
GET    /api/containers/{id}         # Get details
PUT    /api/containers/{id}         # Update container
DELETE /api/containers/{id}         # Delete container
POST   /api/containers/{id}/start   # Start
POST   /api/containers/{id}/stop    # Stop
POST   /api/containers/{id}/restart # Restart
GET    /api/containers/{id}/logs    # Get logs (SSE)
POST   /api/containers/{id}/exec    # Execute command
GET    /api/containers/{id}/stats   # Resource stats
POST   /api/containers/{id}/export  # Export config
GET    /api/containers/validate-name # Validate name
```

### 18.3 Network Endpoints

```
GET    /api/networks                # List networks
POST   /api/networks                # Create network
GET    /api/networks/{id}           # Get details
DELETE /api/networks/{id}           # Delete network
GET    /api/networks/{id}/containers # Containers on network
POST   /api/networks/{id}/connect   # Connect container
POST   /api/networks/{id}/disconnect # Disconnect container
GET    /api/networks/{id}/topology  # Topology view
POST   /api/networks/{id}/reservations # Manage IP reservations
GET    /api/networks/calculate-size # Calculate recommended size
POST   /api/networks/{id}/analyze   # Analyze performance
POST   /api/networks/{id}/migrate   # Migrate to smaller
```

### 18.4 Update Endpoints

```
GET    /api/updates/check           # Trigger check
GET    /api/updates/available       # List available
POST   /api/updates/apply           # Apply single
POST   /api/updates/apply-all       # Apply all
GET    /api/updates/history         # Update history
POST   /api/updates/rollback/{id}   # Rollback
```

### 18.5 Health Endpoints

```
GET    /api/health/containers       # Status of all
GET    /api/health/containers/{id}  # Status of one
POST   /api/health/containers/{id}/check # Manual check
POST   /api/health/containers/{id}/analyze # Analyze logs
GET    /api/health/history/{id}     # History
PUT    /api/health/settings         # Update settings
```

---

## 19. Security Considerations

### 19.1 Docker Socket Risk

**Understanding the Risk:**
- DockerMate requires `/var/run/docker.sock` access
- This gives full control over Docker daemon
- Can manage all containers, images, networks, volumes
- Equivalent to root access on host

**Mitigation Strategies:**
1. Network isolation (run on isolated VLAN)
2. Firewall rules (restrict access to trusted IPs)
3. Never expose to public internet
4. Monitor DockerMate logs regularly
5. Keep DockerMate updated
6. Use VPN for remote access

### 19.2 Password Security

**Requirements:**
- Minimum 12 characters enforced
- Bcrypt hashing with work factor 12
- No default password (setup wizard required)
- Password strength validation
- Force password change after reset

**Best Practices:**
- Use password manager
- Use strong, unique password
- Change periodically
- Never reuse from other services
- Enable "remember me" only on trusted devices

### 19.3 Session Security

**Protection Mechanisms:**
- httpOnly cookies (no JavaScript access)
- Secure flag (HTTPS only)
- SameSite=Strict (CSRF protection)
- Session token hashing (SHA-256)
- Configurable expiry (8h default, 7d remember me)
- IP address tracking
- User agent tracking

### 19.4 HTTPS/TLS Security

**Configuration:**
- TLS 1.2+ only (no TLS 1.0/1.1)
- Strong cipher suites
- HSTS header recommended
- Self-signed certificate acceptable for home labs
- HTTP → HTTPS redirect enforced

### 19.5 Input Validation

**All Inputs Validated:**
- Container names (regex, length, uniqueness)
- Network CIDRs (valid subnet notation)
- IP addresses (valid IPv4/IPv6)
- File paths (no path traversal)
- Environment tags (whitelist)
- SQL injection prevention (parameterized queries)
- XSS prevention (template escaping)

---

## 20. Performance Optimization

### 20.1 Hardware-Specific Optimizations

```python
# Raspberry Pi
if hardware_profile == 'RASPBERRY_PI':
    - Disable continuous monitoring
    - Log analysis: on-demand only
    - Health checks: 15-min intervals
    - Update checks: 12-hour intervals
    - Reduced UI animations
    - Smaller database cache

# High-End
if hardware_profile == 'HIGH_END':
    - Enable continuous monitoring
    - Log analysis: real-time option
    - Health checks: 2-min intervals
    - Update checks: 3-hour intervals
    - Full UI animations
    - Larger database cache
```

### 20.2 Database Performance

```sql
-- Periodic maintenance
VACUUM;
ANALYZE;

-- Auto-cleanup old data
DELETE FROM health_checks WHERE checked_at < datetime('now', '-30 days');
DELETE FROM log_analyses WHERE analyzed_at < datetime('now', '-7 days');
DELETE FROM security_events WHERE created_at < datetime('now', '-90 days');
```

### 20.3 Frontend Performance

```javascript
// Lazy loading
- Load charts only when visible
- Defer non-critical JavaScript
- Code splitting per page

// Caching
- API responses: 5 seconds
- Container stats: 2 seconds
- Search input debounce: 300ms

// Virtual scrolling
- Large container lists (>50)
- Large network IP maps (>100 IPs)
```

---

## 21. Testing Strategy

### 21.1 Unit Tests

```python
# tests/unit/test_auth.py
def test_password_hashing():
    """Test bcrypt password hashing"""
    password = "MySecurePassword123"
    hashed = PasswordManager.hash_password(password)
    assert PasswordManager.verify_password(password, hashed)

def test_session_validation():
    """Test session token validation"""
    token = SessionManager.create_session()
    assert SessionManager.validate_session(token)

# tests/unit/test_network_manager.py
def test_hardware_aware_sizing():
    """Test network size calculation for Raspberry Pi"""
    result = NetworkSizeCalculator.calculate_size(
        max_containers=15,
        ips_per_container=1,
        buffer_percent=20
    )
    assert result['recommended_cidr'] == '/27'
```

### 21.2 Integration Tests

```bash
#!/bin/bash
# tests/integration/test_auth_flow.sh

# Test authentication flow

# 1. Initial setup (no password set)
response=$(curl -k https://localhost:5000/)
[[ "$response" == *"setup"* ]] || exit 1

# 2. Complete setup
curl -k -X POST https://localhost:5000/api/setup \
  -d '{"password":"TestPassword123"}'

# 3. Login
response=$(curl -k -X POST https://localhost:5000/api/auth/login \
  -d '{"password":"TestPassword123"}')
token=$(echo $response | jq -r '.session_token')

# 4. Access protected endpoint
curl -k https://localhost:5000/api/containers \
  -H "Cookie: session=$token"

echo "✅ Authentication flow test passed"
```

### 21.3 Security Tests

```bash
# Test HTTPS enforcement
curl -I http://localhost:5000/ | grep "301"  # Should redirect

# Test password requirements
curl -X POST http://localhost:5000/api/setup \
  -d '{"password":"weak"}' | grep "error"

# Test session expiry
# ... wait for expiry, test rejection

# Test CSRF protection
# ... test without proper headers
```

---

## 22. Development Roadmap

### 22.1 Sprint Plan (7 Sprints × 1 Week Each)

#### **Sprint 1: Foundation & Auth**
- [ ] Project structure setup
- [ ] Flask application skeleton
- [ ] Authentication system (login, sessions)
- [ ] HTTPS/SSL certificate generation
- [ ] Database models (users, sessions)
- [ ] Initial setup wizard
- [ ] Password reset tool
- **Goal:** Secure authentication works

#### **Sprint 2: Container Management**
- [ ] Docker SDK integration
- [ ] Container CRUD operations
- [ ] Environment tags
- [ ] Hardware profile detection
- [ ] Container limits enforcement
- [ ] Basic UI (list, create, start/stop)
- **Goal:** Basic container management

#### **Sprint 3: Image & Updates** ⭐
- [ ] Image listing and operations
- [ ] Update detection system
- [ ] Background scheduler (APScheduler)
- [ ] Update & redeploy functionality
- [ ] "Update All" feature
- [ ] Update history tracking
- [ ] Rollback capability
- **Goal:** Auto-update system operational

#### **Sprint 4: Network Management** ⭐
- [ ] Network creation wizard
- [ ] Hardware-aware subnet sizing
- [ ] IP auto-assignment system
- [ ] IP reservation system
- [ ] Oversized network detection & warnings
- [ ] Network topology visualization
- [ ] Auto-generated network docs
- **Goal:** Intelligent networking complete

#### **Sprint 5: Volumes, Stacks & Health**
- [ ] Volume management
- [ ] Storage path configuration
- [ ] Stack deployment (Compose)
- [ ] Docker run → Compose converter
- [ ] Automatic health checks
- [ ] Manual log analysis
- [ ] Health history
- **Goal:** Multi-container stacks & monitoring

#### **Sprint 6: Export & CLI** ⭐
- [ ] Export system (all formats)
- [ ] Bulk export by environment
- [ ] CLI command generation (3 modes)
- [ ] Volume backup command generation
- [ ] Master inventory generation
- [ ] Export history tracking
- **Goal:** Complete export system

#### **Sprint 7: Polish & Testing**
- [ ] Mobile responsive design
- [ ] Error handling refinement
- [ ] Help tooltips & documentation
- [ ] Comprehensive unit tests
- [ ] Integration tests
- [ ] Security audit
- [ ] Performance tuning
- [ ] User documentation
- **Goal:** Production-ready v1.0.0

### 22.2 Version Milestones

```
v0.1.0 - Alpha (Sprint 1-2)
├─ Authentication & basic container management
└─ Internal testing only

v0.5.0 - Beta (Sprint 3-4)
├─ Update system
├─ Network management with IPAM
└─ Public beta testing

v1.0.0 - Release (Sprint 5-7)
├─ All core features complete
├─ Full documentation
├─ Production-ready
└─ Public release

v1.1.0 - First Enhancement
├─ User feedback incorporated
├─ Bug fixes
├─ Performance improvements
└─ UI refinements

v1.2.0 - Extended Features
├─ Additional export formats
├─ More stack templates
├─ Enhanced health monitoring
└─ UI improvements

v2.0.0 - Advanced Features (Future)
├─ Optional 2FA (TOTP)
├─ Webhook notifications
├─ Advanced scheduling
└─ Plugin system (maybe)
```

---

## 23. Future Enhancements

### 23.1 Phase 2 Features (Home Lab Scope)

#### **Enhanced Security (Optional)**
- TOTP-based 2FA for paranoid users
- IP whitelist/blacklist
- Automatic session timeout after inactivity
- Failed login attempt limiting
- Security event notifications

#### **Advanced Monitoring**
- Prometheus metrics export
- Grafana dashboard templates
- Custom health check scripts
- Alert webhooks (Discord, Slack, Gotify)
- Historical resource graphs

#### **Backup & Restore**
- Scheduled automatic exports
- Point-in-time recovery
- Cloud backup integration (S3, Backblaze B2)
- Volume snapshot support
- One-click full restore

#### **Usability Improvements**
- Dark/light theme toggle
- Customizable dashboard
- Keyboard shortcuts
- Bulk operations (select multiple containers)
- Advanced filtering and search
- Container templates library

#### **Documentation Generator**
- Auto-generate system documentation
- Network diagrams
- Architecture documentation
- Deployment guides
- Disaster recovery plans

### 23.2 Features We Will NOT Add (Home Lab Focus)

#### **❌ Enterprise Features (Not Planned)**
- Multi-user management
- LDAP/Active Directory integration
- SAML/OAuth2 enterprise SSO
- Role-based access control (RBAC)
- Audit compliance reporting
- Multi-tenancy
- Billing/quota systems
- Centralized multi-host management

**Why Not?**
These features add massive complexity that 99% of home lab users don't need. DockerMate is intentionally focused on single-user home lab environments. If you need enterprise features, fork the project!

### 23.3 Community Contributions

We welcome contributions that align with our home lab focus:

**✅ Welcome:**
- Bug fixes
- Performance improvements
- New export formats
- Additional stack templates
- UI/UX improvements
- Documentation improvements
- Translation/localization
- Home lab-specific features

**⚠️ Consider Carefully:**
- Features that add significant complexity
- Features requiring external dependencies
- Features that break single-user model
- Features that require cloud services

**❌ Won't Merge:**
- Enterprise authentication systems
- Multi-user management
- Features that violate KISS principle
- Features that break home lab focus

---

## 24. Contributing

### 24.1 How to Contribute

1. **Fork the Repository**
2. **Create Feature Branch** (`git checkout -b feature/amazing-feature`)
3. **Follow Code Style** (Black formatter, type hints)
4. **Write Tests** (unit + integration)
5. **Update Documentation**
6. **Commit Changes** (`git commit -m 'Add amazing feature'`)
7. **Push to Branch** (`git push origin feature/amazing-feature`)
8. **Open Pull Request**

### 24.2 Code Style

```python
# Use Black formatter
black backend/ frontend/ tests/

# Use type hints
def calculate_size(max_containers: int, ips_per_container: int = 1) -> dict:
    """
    Calculate network size
    
    Args:
        max_containers: Maximum containers hardware supports
        ips_per_container: IPs needed per container
    
    Returns:
        Dictionary with recommended CIDR and details
    """
    pass

# Comment liberally (per design principle #3)
# Error handling everywhere (per design principle #4)
```

### 24.3 Testing Requirements

All PRs must include:
- Unit tests for new functions
- Integration tests for new features
- Verification commands in comments
- Updated documentation

### 24.4 Documentation Requirements

Update relevant docs:
- DESIGN.md (this file) for architecture changes
- README.md for user-facing changes
- API docs for endpoint changes
- Inline code comments for all functions

### 24.5 Enterprise Fork Guidelines

Want to add enterprise features? Fork the project!

**Recommended Additions for Enterprise Fork:**
1. LDAP/AD integration (`backend/auth/ldap_auth.py`)
2. SAML/OAuth2 support (`backend/auth/saml_auth.py`)
3. Multi-user management (additional database tables)
4. RBAC system (`backend/auth/rbac.py`)
5. Audit logging (`backend/audit/`)
6. Multi-tenant support (`backend/tenancy/`)

**Please:**
- Maintain attribution to original project
- Keep it open source (MIT license)
- Document your enterprise additions clearly
- Consider contributing non-enterprise improvements back

---

## 25. License

MIT License - See LICENSE file for details.

**In Summary:**
- ✅ Commercial use allowed
- ✅ Modification allowed
- ✅ Distribution allowed
- ✅ Private use allowed
- ⚠️ No liability or warranty
- ⚠️ License and copyright notice required

---

## 26. Acknowledgments

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

**Community:**
- r/selfhosted
- r/homelab
- Docker community
- Open source contributors

---

## 27. Support & Contact

### 27.1 Getting Help

- 📖 **Documentation**: Check README.md and this DESIGN.md
- 💬 **Discussions**: GitHub Discussions for questions
- 🐛 **Bug Reports**: GitHub Issues
- 💡 **Feature Requests**: GitHub Issues (label: enhancement)

### 27.2 Security Issues

**Found a security vulnerability?**

📧 **Email**: security@dockermate.project  
🔒 **GPG Key**: [fingerprint]  
⏱️ **Response Time**: Within 48 hours

**Please DO NOT** open public GitHub issues for security problems.

### 27.3 Project Links

- **GitHub**: https://github.com/dockermate/dockermate
- **Documentation**: https://docs.dockermate.io
- **Docker Hub**: https://hub.docker.com/r/dockermate/dockermate
- **Website**: https://dockermate.io

---

## 28. FAQ

### 28.1 General Questions

**Q: Is DockerMate free?**  
A: Yes, completely free and open source (MIT license).

**Q: Can I use DockerMate in production?**  
A: Yes, but it's designed for home labs. For enterprise production, consider Portainer Business or Rancher.

**Q: Does DockerMate phone home?**  
A: No. Completely offline, no telemetry, no cloud dependencies.

**Q: Can I manage multiple Docker hosts?**  
A: Not in v1.0. This is planned for v2.0 as an optional feature.

### 28.2 Technical Questions

**Q: Why SQLite instead of PostgreSQL/MySQL?**  
A: Simplicity. Home labs don't need a separate database server. SQLite is perfect for single-user workloads.

**Q: Why Python/Flask instead of Go/Node?**  
A: Python has excellent Docker SDK, easy to read/contribute, great for rapid development. Performance is sufficient for home labs.

**Q: Can I run DockerMate itself in Docker?**  
A: Yes! That's the recommended deployment method.

**Q: What about Kubernetes support?**  
A: Not planned. DockerMate focuses on Docker/Compose. For Kubernetes, use K9s, Lens, or Rancher.

### 28.3 Security Questions

**Q: Is it safe to give DockerMate Docker socket access?**  
A: It's necessary for functionality but comes with risk. Mitigate by: network isolation, firewall rules, keeping updated, never exposing publicly.

**Q: Why no multi-user support?**  
A: Home labs are typically single-user. Multi-user adds massive complexity (authentication, authorization, audit logging, user management, quotas). Not worth it for home use.

**Q: Can I use OAuth/SAML instead of passwords?**  
A: Not in core DockerMate (home lab focus). Fork the project if you need enterprise auth.

**Q: Are my passwords secure?**  
A: Yes. Bcrypt hashing with work factor 12, salted, industry-standard.

---

**End of Design Document**

---

**Version**: 1.0.0  
**Date**: January 21, 2026  
**Status**: Ready for Implementation  
**Next Step**: Start coding Sprint 1! 🚀