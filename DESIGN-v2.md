# DockerMate - Complete Design Documentation

**Version:** 2.0.0  
**Last Updated:** January 29, 2026  
**Status:** Active Design (Sprint 2+)  
**License:** MIT  
**Focus:** 100% Home Lab Optimized  
**Supersedes:** DESIGN-v1.md (January 21, 2026)

---

## Version History

- **v1.0.0** (2025-01-21): Initial design
- **v2.0.0** (2026-01-29): Authentication architecture update + Frontend standardization

---

## Changes in Version 2.0.0

### Authentication Architecture (Section 15.3)
**Changed:** API security model from defense-in-depth to perimeter security
- **Previous:** API endpoints protected with `@require_auth(api=True)`
- **New:** UI routes protected, API routes unprotected (same-origin trust)
- **Rationale:** Home lab optimization, testing simplicity, performance on Raspberry Pi

### Frontend Technology Stack (Section 4.1)
**Changed:** Standardized JavaScript pattern
- **Previous:** Alpine.js loaded but inconsistently used
- **New:** Alpine.js used exclusively for all interactivity
- **Rationale:** KISS principle, eliminate pattern mixing

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

**⚠️ CHANGED IN v2.0.0**

#### **Backend**
```
Language: Python 3.11+
Framework: Flask 3.0
Docker SDK: docker-py 7.0
Scheduler: APScheduler 3.10
Database: SQLite 3.40
ORM: SQLAlchemy 2.0 (raw, not Flask-SQLAlchemy)
Validation: Pydantic 2.0
Logging: Structured logging with JSON
SSL/TLS: cryptography, certbot (optional)
Password Hashing: bcrypt
```

#### **Frontend**
```
Base: HTML5 + Jinja2 templates
CSS: Tailwind CSS 3.4 (utility-first)
JavaScript: Alpine.js 3.13 (declarative, reactive)
Code Editor: Monaco Editor 0.45 (VS Code) [Future]
Charts: Chart.js 4.4 [Future]
Icons: Unicode/Emoji (lightweight, no icon library)
Live Updates: Polling (10s interval, WebSocket deferred to Sprint 5)
```

**JavaScript Pattern (v2.0.0 Standardization):**
- ✅ Alpine.js used exclusively for all interactivity
- ✅ Declarative syntax (`x-data`, `@click`, `x-model`)
- ✅ No inline `onclick` handlers
- ✅ Reactive state management
- ❌ No vanilla JavaScript event handlers
- ❌ No separate `.js` files (inline in templates)

**Removed/Not Used:**
- ❌ jQuery or other libraries
- ❌ Vanilla JavaScript `onclick` patterns

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
│  │  ✅ v2.0: UI routes only (@require_auth)         │   │
│  └────────────┬────────────────────────────────────┘   │
│               │                                          │
│  ┌────────────▼────────────────────────────────────┐   │
│  │              API Endpoints                       │   │
│  │  ⚠️ v2.0: NO authentication decorators           │   │
│  │  /api/containers | /api/images | /api/networks  │   │
│  │  /api/volumes | /api/stacks | /api/health       │   │
│  │  /api/auth | /api/updates | /api/export         │   │
│  └────────────┬────────────────────────────────────┘   │
│               │                                          │
│  ┌────────────▼────────────────────────────────────┐   │
│  │           Business Logic Layer                   │   │
│  │  ┌───────────────────────────────────────────┐  │   │
│  │  │ Container Manager | Image Manager         │  │   │
│  │  │ Network Manager (IPAM) | Volume Manager   │  │   │
│  │  │ Stack Manager | Update Manager            │  │   │
│  │  │ Health Monitor | Export Engine            │  │   │
│  │  └───────────────────────────────────────────┘  │   │
│  └────────────┬────────────────────────────────────┘   │
│               │                                          │
│  ┌────────────▼────────────────────────────────────┐   │
│  │           Data Access Layer                      │   │
│  │  SQLAlchemy ORM | SQLite Database               │   │
│  └────────────┬────────────────────────────────────┘   │
└───────────────┼──────────────────────────────────────┘
                │
                │ Unix Socket
                │
┌───────────────▼──────────────────────────────────────┐
│              Docker Daemon                            │
│  Containers | Images | Networks | Volumes            │
└───────────────────────────────────────────────────────┘
```

### 4.3 Directory Structure

```
dockermate/
│
├── app.py                        # Flask app entry point
├── config.py                     # Configuration
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Container build
├── docker-compose.yml            # Deployment config
├── README.md                     # User documentation
├── DESIGN-v2.md                  # This file (ACTIVE)
├── DESIGN-v1.md                  # Historical reference
├── Improvements.md               # Enhancement backlog
├── LICENSE                       # MIT license
│
├── backend/
│   ├── __init__.py
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── password_manager.py   # Bcrypt hashing
│   │   ├── session_manager.py    # Session CRUD
│   │   └── middleware.py         # @require_auth decorator
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py               # Login/logout/sessions
│   │   ├── containers.py         # ⚠️ v2.0: NO @require_auth
│   │   ├── images.py             # ⚠️ v2.0: NO @require_auth
│   │   ├── networks.py           # ⚠️ v2.0: NO @require_auth
│   │   ├── volumes.py            # ⚠️ v2.0: NO @require_auth
│   │   ├── stacks.py             # ⚠️ v2.0: NO @require_auth
│   │   ├── health.py             # ⚠️ v2.0: NO @require_auth
│   │   └── export.py             # ⚠️ v2.0: NO @require_auth
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── database.py           # SQLAlchemy setup
│   │   ├── user.py               # User model
│   │   ├── session.py            # Session model
│   │   ├── host_config.py        # Hardware profile
│   │   ├── container.py          # Container model
│   │   ├── image.py              # Image model
│   │   ├── network.py            # Network model
│   │   ├── volume.py             # Volume model
│   │   └── environment.py        # Environment tags
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── docker_client.py      # Docker SDK wrapper
│   │   ├── container_manager.py  # Container CRUD
│   │   ├── image_manager.py      # Image operations
│   │   ├── network_manager.py    # Network + IPAM
│   │   ├── volume_manager.py     # Volume operations
│   │   ├── stack_manager.py      # Compose handling
│   │   ├── update_manager.py     # Update detection
│   │   ├── health_monitor.py     # Health checks
│   │   └── export_engine.py      # Config export
│   │
│   └── utils/
│       ├── __init__.py
│       ├── hardware_detector.py  # Hardware profiling
│       ├── ip_allocator.py       # IPAM logic
│       ├── cli_generator.py      # CLI command gen
│       └── cert_manager.py       # SSL cert handling
│
├── frontend/
│   ├── static/
│   │   ├── css/
│   │   │   └── main.css          # Tailwind output [Future]
│   │   └── js/
│   │       └── (no separate JS files - inline Alpine.js)
│   │
│   └── templates/
│       ├── base.html             # Base layout (Alpine.js loaded)
│       ├── components/
│       │   └── navbar.html       # ✅ v2.0: Shared navigation
│       ├── login.html            # Login page
│       ├── setup.html            # Initial setup wizard
│       ├── dashboard.html        # ✅ v2.0: Alpine.js pattern
│       ├── containers.html       # ✅ v2.0: Alpine.js pattern
│       ├── images.html           # ✅ v2.0: Alpine.js pattern
│       ├── networks.html         # ✅ v2.0: Alpine.js pattern
│       ├── volumes.html          # Future
│       ├── stacks.html           # Future
│       ├── health.html           # Future
│       └── settings.html         # ✅ v2.0: Alpine.js pattern
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

#### **Authentication Flow (v2.0.0)**
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
   └─> Session validated on UI routes only (v2.0)
```

#### **Container Creation Flow**
```
1. User fills form in UI
   └─> POST /api/containers/create (⚠️ v2.0: NO auth check)
       
2. API validates input
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

### 6.1 Environment Tags

DockerMate supports environment tags for both **host** and **containers**:

- **PRD** (Production) - Red 🔴 - Maximum safety
- **UAT** (User Acceptance Testing) - Yellow 🟡 - Moderate safety
- **DEV** (Development) - Green 🟢 - Minimal safety
- **SANDBOX** - Blue 🔵 - No restrictions

### 6.2 Host Environment Configuration

```python
# Host environment affects global behavior
host_config = {
    "environment": "DEV",
    "require_confirmation": False,  # DEV: No confirmations
    "enable_auto_update": True,     # DEV: Auto updates OK
    "enable_health_checks": True,   # All: Health checks on
}
```

### 6.3 Container Environment Tags

Containers can be tagged independently:

```python
container = {
    "name": "nginx-web",
    "environment": "PRD",  # Even on DEV host
    "safety_level": "high"  # Requires confirmations
}
```

### 6.4 Safety Matrix

| Host Env | Container Env | Delete Confirmation | Auto-Update | CLI Preview |
|----------|---------------|---------------------|-------------|-------------|
| PRD      | PRD           | ✅ Required          | ❌ Disabled  | ✅ Always    |
| PRD      | DEV           | ⚠️ Recommended       | ⚠️ Optional  | ✅ Always    |
| DEV      | PRD           | ✅ Required          | ❌ Disabled  | ✅ Always    |
| DEV      | DEV           | ❌ Not required      | ✅ Enabled   | ⚠️ Optional  |
| SANDBOX  | Any           | ❌ Not required      | ❌ Disabled  | ✅ Always    |

---

## 7. Container Management

### 7.1 Container Lifecycle

```
┌─────────────┐
│   CREATED   │ ─── docker create
└──────┬──────┘
       │ start
       ▼
┌─────────────┐
│   RUNNING   │ ◄─── restart
└──────┬──────┘
       │ stop/pause
       ▼
┌─────────────┐
│   STOPPED   │
└──────┬──────┘
       │ remove
       ▼
┌─────────────┐
│   DELETED   │
└─────────────┘
```

### 7.2 Container Metadata

DockerMate tracks:

```python
container = {
    # Core Info
    "id": "abc123",
    "name": "nginx-web",
    "image": "nginx:latest",
    "status": "running",
    
    # Environment
    "environment": "PRD",
    
    # Network
    "network": "web-network",
    "ip_address": "172.20.0.10",
    "ports": {"80": 8080, "443": 8443},
    
    # Storage
    "volumes": {"/data": "/mnt/appdata/nginx"},
    
    # Resources
    "cpu_limit": 1.0,
    "memory_limit": "512m",
    
    # Metadata
    "description": "Main web server",
    "created_at": "2025-01-15T10:30:00Z",
    "cli_command": "docker run -d --name nginx-web..."
}
```

### 7.3 Container CRUD Operations

#### **Create**
```python
# High-level operation
container_manager.create_container(
    name="nginx-web",
    image="nginx:latest",
    environment="PRD",
    network="web-network",
    ip="172.20.0.10",
    ports={"80": 8080},
    volumes={"/data": "/mnt/appdata/nginx"},
    auto_start=True
)

# Equivalent CLI
docker network create --subnet 172.20.0.0/26 web-network
docker run -d \
  --name nginx-web \
  --network web-network \
  --ip 172.20.0.10 \
  -p 8080:80 \
  -v /mnt/appdata/nginx:/data \
  --restart unless-stopped \
  nginx:latest
```

#### **Read**
```python
# Get single container
container = container_manager.get_container("nginx-web")

# List all containers
containers = container_manager.list_containers(
    environment="PRD",  # Filter
    status="running"
)
```

#### **Update**
```python
# Update container (requires recreate)
container_manager.update_container(
    "nginx-web",
    image="nginx:1.25",  # New image
    ports={"80": 8080, "443": 8443}  # New ports
)
```

#### **Delete**
```python
# Delete container
container_manager.delete_container(
    "nginx-web",
    force=False,  # Requires confirmation if running
    remove_volumes=False  # Keep volumes
)
```

---

## 8. Network Management & IPAM

### 8.1 Network Architecture

DockerMate provides intelligent network management with IPAM (IP Address Management):

```
┌─────────────────────────────────────────────────┐
│         Docker Network: web-network             │
│         Subnet: 172.20.0.0/26 (62 usable IPs)   │
├─────────────────────────────────────────────────┤
│ 172.20.0.1      Gateway (Docker)                │
│ 172.20.0.2-9    DHCP Pool (8 IPs)               │
│ 172.20.0.10-19  Reserved: Web services          │
│ 172.20.0.20-29  Reserved: Databases             │
│ 172.20.0.30-39  Reserved: Media services        │
│ 172.20.0.40-62  Available (23 IPs)              │
└─────────────────────────────────────────────────┘
```

### 8.2 IP Allocation Strategies

#### **Auto-Assignment**
- DockerMate picks next available IP from pool
- Avoids reserved ranges
- Records assignment in database

#### **Manual Assignment**
- User specifies exact IP
- DockerMate validates availability
- Warns if IP is in use

#### **Reserved Ranges**
- User defines ranges for specific purposes
- Prevents accidental allocation
- Example: .10-.19 for web servers

### 8.3 Network Wizard

```
Step 1: Network Name
└─> Enter: "web-network"

Step 2: Subnet Size
└─> Choose: /26 (62 hosts) - Recommended for Medium Server

Step 3: Reserved Ranges (Optional)
└─> Add:
    - .10-.19: Web services
    - .20-.29: Databases

Step 4: Review & Create
└─> Show CLI equivalent
└─> Create network

Result: Network created with IPAM configured
```

---

## 9. Image Management & Updates

### 9.1 Update Detection

DockerMate automatically checks for image updates:

```python
# Scheduled job (every 6 hours for Medium Server)
def check_updates():
    for container in containers:
        current_image = container.image
        latest_image = docker.images.pull(current_image)
        
        if current_image.id != latest_image.id:
            update_available = True
            # Record in database
            update_db.add({
                "container": container.name,
                "current": current_image.tag,
                "latest": latest_image.tag,
                "severity": detect_breaking_changes()
            })
```

### 9.2 Update Strategies

#### **Safe Update** (Default)
- Pull new image
- Create new container with same config
- Start new container
- Stop old container (keep for rollback)
- Remove old container after 24h

#### **In-Place Update**
- Stop container
- Remove container
- Pull new image
- Create container with same config
- Start container

#### **Scheduled Update**
- Queue updates for maintenance window
- Example: All DEV containers at 2 AM daily

### 9.3 Rollback Capability

```python
# Rollback to previous image
rollback_manager.rollback_container(
    container="nginx-web",
    version="previous"  # or specific tag
)

# Keeps 3 previous versions by default
```

---

## 10. Volume Management

### 10.1 Volume Types

DockerMate supports:

- **Named Volumes**: Docker-managed, portable
- **Bind Mounts**: Host path to container path
- **Tmpfs Mounts**: Temporary memory-backed

### 10.2 Volume Metadata

```python
volume = {
    "name": "nginx-data",
    "type": "named",
    "driver": "local",
    "mount_point": "/var/lib/docker/volumes/nginx-data/_data",
    "containers": ["nginx-web"],
    "size": "2.3 GB",
    "created_at": "2025-01-15T10:30:00Z"
}
```

### 10.3 Volume Operations

```python
# Create volume
volume_manager.create_volume(
    name="nginx-data",
    driver="local"
)

# Backup volume
volume_manager.backup_volume(
    name="nginx-data",
    destination="/exports/nginx-backup.tar.gz"
)

# Restore volume
volume_manager.restore_volume(
    name="nginx-data",
    source="/exports/nginx-backup.tar.gz"
)
```

---

## 11. Stack Management

### 11.1 Stack Definition

Stacks are groups of related containers defined via Docker Compose:

```yaml
# docker-compose.yml
version: '3.8'

services:
  nginx:
    image: nginx:latest
    networks:
      - web-network
    ports:
      - "80:80"
    volumes:
      - nginx-data:/data
    environment:
      - NGINX_HOST=example.com

  postgres:
    image: postgres:15
    networks:
      - web-network
    volumes:
      - postgres-data:/var/lib/postgresql/data
    environment:
      - POSTGRES_PASSWORD=secret

networks:
  web-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/26

volumes:
  nginx-data:
  postgres-data:
```

### 11.2 Stack Operations

```python
# Deploy stack
stack_manager.deploy_stack(
    name="web-stack",
    compose_file="docker-compose.yml",
    environment="PRD"
)

# Update stack
stack_manager.update_stack(
    name="web-stack",
    services=["nginx"]  # Update specific service
)

# Stop stack
stack_manager.stop_stack("web-stack")

# Remove stack
stack_manager.remove_stack(
    name="web-stack",
    remove_volumes=False
)
```

### 11.3 Stack Templates

DockerMate includes templates for common stacks:

- **Media Stack**: Jellyfin + Sonarr + Radarr + Prowlarr
- **Development Stack**: Nginx + PostgreSQL + Redis
- **Monitoring Stack**: Prometheus + Grafana + cAdvisor
- **Home Automation**: Home Assistant + MQTT + Node-RED

---

## 12. Health Monitoring System

### 12.1 Health Check Types

#### **Container Health**
- Built-in health checks (Docker HEALTHCHECK)
- Custom health endpoints
- Process monitoring

#### **Resource Monitoring**
- CPU usage
- Memory usage
- Network I/O
- Disk I/O

#### **Application Health**
- HTTP endpoint checks
- TCP port checks
- Custom scripts

### 12.2 Health Check Configuration

```python
health_check = {
    "container": "nginx-web",
    "type": "http",
    "endpoint": "http://172.20.0.10/health",
    "interval": 30,  # seconds
    "timeout": 5,
    "retries": 3,
    "expected_status": 200
}
```

### 12.3 Health Monitoring Dashboard

```
Container Health Overview:
┌────────────────────────────────────────────┐
│ ✅ nginx-web       UP      CPU: 5%   MEM: 2%│
│ ✅ postgres-db     UP      CPU: 3%   MEM: 15%│
│ ⚠️ redis-cache     WARN    CPU: 85%  MEM: 8%│
│ ❌ app-worker      DOWN    CPU: 0%   MEM: 0%│
└────────────────────────────────────────────┘

Alerts:
- redis-cache: High CPU usage (85%)
- app-worker: Container stopped unexpectedly
```

---

## 13. Export & Backup System

### 13.1 Export Formats

DockerMate can export configurations in multiple formats:

#### **JSON Export**
```json
{
  "version": "1.0",
  "exported_at": "2025-01-27T10:30:00Z",
  "containers": [
    {
      "name": "nginx-web",
      "image": "nginx:latest",
      "environment": "PRD",
      "network": "web-network",
      "ip": "172.20.0.10",
      "ports": {"80": 8080},
      "volumes": {"/data": "/mnt/appdata/nginx"}
    }
  ]
}
```

#### **Docker Compose Export**
```yaml
version: '3.8'
services:
  nginx-web:
    image: nginx:latest
    networks:
      web-network:
        ipv4_address: 172.20.0.10
    ports:
      - "8080:80"
    volumes:
      - /mnt/appdata/nginx:/data
```

#### **CLI Script Export**
```bash
#!/bin/bash
# Generated by DockerMate on 2025-01-27

docker network create --subnet 172.20.0.0/26 web-network

docker run -d \
  --name nginx-web \
  --network web-network \
  --ip 172.20.0.10 \
  -p 8080:80 \
  -v /mnt/appdata/nginx:/data \
  nginx:latest
```

### 13.2 Backup Strategy

```python
# Full system backup
backup_manager.create_backup(
    include_volumes=False,  # Config only
    include_images=False,   # Don't backup images
    destination="/exports/backup-2025-01-27.tar.gz"
)

# Selective backup
backup_manager.create_backup(
    containers=["nginx-web", "postgres-db"],
    include_volumes=True,
    destination="/exports/web-stack-backup.tar.gz"
)
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

**⚠️ CHANGED IN v2.0.0**

#### **Authentication Architecture - Perimeter Security Model**

DockerMate implements a **perimeter security model** optimized for single-user home lab environments:

| Security Layer | Protection | Enforcement Point |
|---------------|-----------|-------------------|
| **UI Routes** | ✅ `@require_auth()` decorator | Flask route handlers |
| **API Routes** | ❌ No authentication | Trusted same-origin only |
| **Network** | ✅ Same-origin policy | Browser security model |
| **Transport** | ✅ HTTPS/TLS 1.2+ | Application layer |
| **Session** | ✅ httpOnly, Secure, SameSite=Strict | Cookie headers |

**Design Rationale:**

1. **Single-user context**: No insider threat model to defend against
2. **Same-origin enforcement**: Browser prevents external API access
3. **Testing simplicity**: No session mocking required for business logic tests
4. **Performance**: No session database lookups on every API call (benefits Raspberry Pi)
5. **Network trust assumption**: Home lab networks are firewall-protected

**Security Layers:**

```
┌─────────────────────────────────────────────────┐
│ LAYER 1: Infrastructure (User Responsibility)  │
│ - Firewall rules (block external access)       │
│ - VLAN isolation (separate management network) │
│ - VPN for remote access (never port forward)   │
└─────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────┐
│ LAYER 2: Transport Security                    │
│ - HTTPS enforcement (TLS 1.2+)                  │
│ - Self-signed certificates acceptable           │
│ - HTTP → HTTPS redirect                         │
└─────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────┐
│ LAYER 3: Application Perimeter                 │
│ - UI routes: @require_auth() decorator          │
│ - Login page: Password validation (bcrypt)      │
│ - Session cookies: httpOnly, Secure, SameSite   │
└─────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────┐
│ LAYER 4: Browser Security                      │
│ - Same-origin policy (prevents external API)   │
│ - CSRF protection (SameSite=Strict cookies)     │
│ - XSS protection (template escaping)            │
└─────────────────────────────────────────────────┘
```

**Attack Surface Analysis:**

| Attack Vector | Mitigation | Status |
|--------------|-----------|--------|
| **External API access** | Same-origin policy + firewall | ✅ Protected |
| **CSRF attacks** | SameSite=Strict cookies | ✅ Protected |
| **Session hijacking** | HTTPS + httpOnly cookies | ✅ Protected |
| **Brute force login** | Bcrypt work factor 12 | ✅ Protected |
| **Network sniffing** | HTTPS/TLS encryption | ✅ Protected |
| **Docker socket escape** | ⚠️ Inherent risk - requires network isolation | ⚠️ User responsibility |

**Implementation Example:**

```python
# app.py - UI routes protected
@app.route('/containers')
@require_auth()  # ✅ v2.0: Session validation required
def containers_page():
    return render_template('containers.html')

# backend/api/containers.py - API routes unprotected
@containers_bp.route('/', methods=['GET'])
# ❌ v2.0: NO @require_auth decorator - trusted same-origin only
def list_containers():
    containers = ContainerManager(db).list_containers()
    return jsonify({"containers": containers})
```

**Testing Strategy:**

```python
# UI route tests - verify auth enforcement
def test_containers_page_requires_auth(client):
    response = client.get('/containers')
    assert response.status_code == 302  # Redirect to login

# API tests - no auth mocking needed
def test_list_containers_returns_json(client, mock_docker):
    response = client.get('/api/containers')
    assert response.status_code == 200
    assert 'containers' in response.json
```

**Deployment Security Checklist:**

```bash
# ✅ Required for secure deployment
□ DockerMate on isolated VLAN (e.g., 192.168.100.0/24)
□ Firewall rules blocking external access to port 5000
□ VPN configured for remote access (WireGuard/OpenVPN)
□ Strong password set (12+ characters)
□ HTTPS enabled with valid certificate
□ Regular updates applied

# ⚠️ Never do this
□ Port forward DockerMate to public internet
□ Run on same network as untrusted devices
□ Disable HTTPS
□ Use weak passwords
□ Share credentials
```

**Not Suitable For:**
- ❌ Multi-user environments
- ❌ Untrusted network deployments
- ❌ Public-facing access
- ❌ Enterprise production systems

**For enterprise security needs**, use Portainer Business Edition or fork DockerMate to implement API-level authentication.

---

#### **Password Requirements:**

DockerMate enforces modern password best practices aligned with SSH.com and NIST 2024 guidelines:

**Core Requirements:**
- **Minimum 12 characters** (industry standard for 2024+)
- **Required:** Uppercase letter (A-Z), lowercase letter (a-z), and digit (0-9)
- **Recommended:** Special characters for additional strength (but not required)

**Smart Weak Password Detection:**
DockerMate uses regex pattern matching to reject common weak passwords in any position:

**Rejected Patterns:**
- Base weak words with only numbers/symbols: `password123`, `123password`, `admin!@#`, `!!!admin2024!!!`
- Common keyboard patterns: `qwerty`, `asdf`, `12345`
- Common words: `password`, `admin`, `user`, `docker`, `root`, `welcome`

**Why This Approach:**
- Length is the primary defense against brute force (NIST 2024)
- Pattern detection catches creative padding (`!!!password!!!`)
- No artificial complexity requirements (reduces user frustration)
- Focus on entropy over arbitrary character requirements

**Password Strength Indicator:**
- Weak: < 12 characters or contains common patterns
- Medium: 12-15 characters, mixed case + digits
- Strong: 16+ characters, mixed case + digits + special chars
- Very Strong: 20+ characters with high entropy

**Examples:**
- ✅ Good: `MyDockerLabPassword2026`, `CorrectHorseBattery42`, `HomeServerSecure!`
- ❌ Bad: `password123`, `admin`, `docker`, `Welcome2026`

**Remember:**
Strong passwords are important, but they're just one layer of security.
Network isolation, firewall rules, and not exposing DockerMate to the public internet are equally critical.

#### **Session Management:**
- Session tokens: 256-bit cryptographically secure
- Cookie: httpOnly, secure, SameSite=Strict
- Default expiry: 8 hours
- Remember me: 7 days
- Stored hashed in database (SHA-256)

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
- Use password manager
- Change periodically
- Never reuse from other services
- Enable "remember me" only on trusted devices

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

**⚠️ UPDATED IN v2.0.0**

### 16.1 Layout Structure

```
┌─────────────────────────────────────────────────────────┐
│ 🐳 DockerMate    [Dashboard] [Containers] [Images]      │
│                  [Networks] [Volumes] [Stacks]          │
│ 🟢 DEV Host      [Health]              [⚙️] [Logout]    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│                    Main Content Area                     │
│                    (Alpine.js components)                │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 16.2 Frontend Architecture (v2.0.0)

**Template Structure:**
```html
<!-- All templates follow this pattern -->
{% extends "base.html" %}

{% block content %}
<div class="min-h-screen bg-slate-900" x-data="pageComponent()">
    {% include 'components/navbar.html' %}
    
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <!-- Page content with Alpine.js directives -->
    </main>
</div>

<script>
function pageComponent() {
    return {
        // Reactive state
        data: [],
        loading: false,
        
        // Methods
        async loadData() {
            this.loading = true;
            const response = await fetch('/api/endpoint');
            this.data = await response.json();
            this.loading = false;
        }
    }
}
</script>
{% endblock %}
```

**Alpine.js Patterns:**
```html
<!-- Declarative interactivity -->
<button @click="handleAction()" 
        x-bind:disabled="loading"
        class="px-4 py-2 bg-blue-600">
    <span x-show="!loading">Click Me</span>
    <span x-show="loading">Loading...</span>
</button>

<!-- Reactive filtering -->
<select x-model="filters.environment" @change="applyFilters()">
    <option value="all">All Environments</option>
    <option value="dev">Development</option>
</select>

<!-- Template loops -->
<template x-for="item in filteredData" :key="item.id">
    <div x-text="item.name"></div>
</template>
```

### 16.3 Color Scheme

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

### 16.4 Responsive Design

```
Mobile (< 768px):
├─ Single column
├─ Hamburger menu
├─ Touch-friendly buttons
└─ Simplified tables

Tablet (768px - 1024px):
├─ Two-column layouts
├─ Collapsible sidebar
└─ Medium information density

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
    color VARCHAR(50),
    safety_level VARCHAR(50),
    require_confirmation BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- Container Management
-- ============================================

CREATE TABLE containers (
    id INTEGER PRIMARY KEY,
    docker_id VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(255) UNIQUE NOT NULL,
    image VARCHAR(500) NOT NULL,
    status VARCHAR(50),
    environment_id INTEGER,
    network_id INTEGER,
    ip_address VARCHAR(45),
    ports TEXT,
    volumes TEXT,
    env_vars TEXT,
    labels TEXT,
    description TEXT,
    cli_command TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (environment_id) REFERENCES environments(id),
    FOREIGN KEY (network_id) REFERENCES networks(id)
);

-- ============================================
-- Image Management
-- ============================================

CREATE TABLE images (
    id INTEGER PRIMARY KEY,
    docker_id VARCHAR(64) UNIQUE NOT NULL,
    repository VARCHAR(500) NOT NULL,
    tag VARCHAR(255) NOT NULL,
    digest VARCHAR(255),
    size BIGINT,
    created_at DATETIME,
    pulled_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE update_checks (
    id INTEGER PRIMARY KEY,
    container_id INTEGER NOT NULL,
    current_image_id INTEGER NOT NULL,
    latest_image_id INTEGER,
    update_available BOOLEAN DEFAULT FALSE,
    breaking_changes BOOLEAN DEFAULT FALSE,
    checked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (container_id) REFERENCES containers(id),
    FOREIGN KEY (current_image_id) REFERENCES images(id),
    FOREIGN KEY (latest_image_id) REFERENCES images(id)
);

CREATE TABLE update_history (
    id INTEGER PRIMARY KEY,
    container_id INTEGER NOT NULL,
    old_image_id INTEGER NOT NULL,
    new_image_id INTEGER NOT NULL,
    success BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    rollback_available BOOLEAN DEFAULT TRUE,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (container_id) REFERENCES containers(id),
    FOREIGN KEY (old_image_id) REFERENCES images(id),
    FOREIGN KEY (new_image_id) REFERENCES images(id)
);

-- ============================================
-- Network Management & IPAM
-- ============================================

CREATE TABLE networks (
    id INTEGER PRIMARY KEY,
    docker_id VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(255) UNIQUE NOT NULL,
    driver VARCHAR(50) DEFAULT 'bridge',
    subnet VARCHAR(50),
    gateway VARCHAR(45),
    dhcp_range_start VARCHAR(45),
    dhcp_range_end VARCHAR(45),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ip_reservations (
    id INTEGER PRIMARY KEY,
    network_id INTEGER NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    container_id INTEGER,
    range_name VARCHAR(255),
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (network_id) REFERENCES networks(id),
    FOREIGN KEY (container_id) REFERENCES containers(id),
    UNIQUE(network_id, ip_address)
);

-- ============================================
-- Volume Management
-- ============================================

CREATE TABLE volumes (
    id INTEGER PRIMARY KEY,
    docker_id VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(255) UNIQUE NOT NULL,
    driver VARCHAR(50) DEFAULT 'local',
    mount_point VARCHAR(500),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE volume_mounts (
    id INTEGER PRIMARY KEY,
    container_id INTEGER NOT NULL,
    volume_id INTEGER,
    source VARCHAR(500),
    target VARCHAR(500) NOT NULL,
    read_only BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (container_id) REFERENCES containers(id),
    FOREIGN KEY (volume_id) REFERENCES volumes(id)
);

-- ============================================
-- Health Monitoring
-- ============================================

CREATE TABLE health_checks (
    id INTEGER PRIMARY KEY,
    container_id INTEGER NOT NULL,
    check_type VARCHAR(50),
    endpoint VARCHAR(500),
    interval INTEGER DEFAULT 30,
    timeout INTEGER DEFAULT 5,
    retries INTEGER DEFAULT 3,
    last_check DATETIME,
    last_status VARCHAR(50),
    consecutive_failures INTEGER DEFAULT 0,
    FOREIGN KEY (container_id) REFERENCES containers(id)
);

CREATE TABLE health_history (
    id INTEGER PRIMARY KEY,
    container_id INTEGER NOT NULL,
    status VARCHAR(50),
    cpu_percent REAL,
    memory_percent REAL,
    network_rx BIGINT,
    network_tx BIGINT,
    checked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (container_id) REFERENCES containers(id)
);

CREATE TABLE log_analysis (
    id INTEGER PRIMARY KEY,
    container_id INTEGER NOT NULL,
    log_level VARCHAR(50),
    pattern VARCHAR(500),
    count INTEGER DEFAULT 1,
    first_seen DATETIME,
    last_seen DATETIME,
    FOREIGN KEY (container_id) REFERENCES containers(id)
);

-- ============================================
-- Indexes for Performance
-- ============================================

CREATE INDEX idx_containers_status ON containers(status);
CREATE INDEX idx_containers_environment ON containers(environment_id);
CREATE INDEX idx_update_checks_container ON update_checks(container_id);
CREATE INDEX idx_health_history_container ON health_history(container_id);
CREATE INDEX idx_health_history_checked_at ON health_history(checked_at);
CREATE INDEX idx_ip_reservations_network ON ip_reservations(network_id);
```

---

## 18. API Endpoints

**⚠️ CHANGED IN v2.0.0: All API endpoints are unprotected (same-origin trust)**

### 18.1 Authentication API

```
POST   /api/auth/login           - Login with password
POST   /api/auth/logout          - Logout and revoke session
GET    /api/auth/session         - Check if session is valid
POST   /api/auth/change-password - Change password
GET    /api/auth/sessions        - List all active sessions
DELETE /api/auth/sessions/{id}   - Revoke specific session
```

### 18.2 Container API

```
GET    /api/containers              - List all containers
POST   /api/containers              - Create new container
GET    /api/containers/{id}         - Get container details
PATCH  /api/containers/{id}         - Update container
DELETE /api/containers/{id}         - Delete container
POST   /api/containers/{id}/start   - Start container
POST   /api/containers/{id}/stop    - Stop container
POST   /api/containers/{id}/restart - Restart container
GET    /api/containers/{id}/logs    - Get container logs
GET    /api/containers/{id}/stats   - Get resource usage
```

### 18.3 Image API

```
GET    /api/images                  - List all images
POST   /api/images/pull             - Pull new image
DELETE /api/images/{id}             - Delete image
GET    /api/images/updates          - Check for updates
POST   /api/images/updates/apply    - Apply updates
```

### 18.4 Network API

```
GET    /api/networks                - List all networks
POST   /api/networks                - Create new network
GET    /api/networks/{id}           - Get network details
DELETE /api/networks/{id}           - Delete network
GET    /api/networks/{id}/ips       - List IP allocations
POST   /api/networks/{id}/reserve   - Reserve IP range
```

### 18.5 Volume API

```
GET    /api/volumes                 - List all volumes
POST   /api/volumes                 - Create new volume
GET    /api/volumes/{id}            - Get volume details
DELETE /api/volumes/{id}            - Delete volume
POST   /api/volumes/{id}/backup     - Backup volume
POST   /api/volumes/{id}/restore    - Restore volume
```

### 18.6 Stack API

```
GET    /api/stacks                  - List all stacks
POST   /api/stacks                  - Deploy stack
GET    /api/stacks/{id}             - Get stack details
PATCH  /api/stacks/{id}             - Update stack
DELETE /api/stacks/{id}             - Remove stack
POST   /api/stacks/{id}/start       - Start all services
POST   /api/stacks/{id}/stop        - Stop all services
```

### 18.7 Health API

```
GET    /api/health/containers       - Get health status for all
GET    /api/health/containers/{id}  - Get health for specific container
GET    /api/health/history/{id}     - Get health history
POST   /api/health/check/{id}       - Trigger manual health check
```

### 18.8 Export API

```
GET    /api/export/json             - Export as JSON
GET    /api/export/compose          - Export as Docker Compose
GET    /api/export/cli              - Export as CLI script
POST   /api/export/backup           - Create full backup
```

---

## 19. Security Considerations

**⚠️ UPDATED IN v2.0.0**

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

### 19.5 API Security Model (v2.0.0)

**Perimeter Security Approach:**
- UI routes protected with authentication
- API routes unprotected (same-origin trust)
- Browser same-origin policy prevents external access
- Network-level security required (firewall + VLAN)

**Critical Requirements:**
- ⚠️ NEVER expose to public internet
- ⚠️ REQUIRED: Isolated VLAN
- ⚠️ REQUIRED: Firewall rules
- ⚠️ REQUIRED: VPN for remote access

### 19.6 Input Validation

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

### 20.1 Hardware-Aware Tuning

DockerMate adapts performance settings based on hardware profile:

#### **Raspberry Pi**
- Database: WAL mode, 10MB cache
- Update checks: 12 hours
- Health checks: 15 minutes
- Sync cache: 30 seconds
- Log retention: 7 days

#### **Medium Server**
- Database: WAL mode, 100MB cache
- Update checks: 6 hours
- Health checks: 5 minutes
- Sync cache: 10 seconds
- Log retention: 30 days

### 20.2 Database Optimization

```python
# SQLite optimizations
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = -100000;  # 100MB
PRAGMA temp_store = MEMORY;
PRAGMA mmap_size = 30000000000;  # 30GB
```

### 20.3 Caching Strategy

```python
# In-memory caching for frequent queries
cache = {
    "containers": {
        "data": [],
        "expires_at": datetime,
        "ttl": 10  # seconds
    },
    "networks": {
        "data": [],
        "expires_at": datetime,
        "ttl": 60  # seconds
    }
}
```

### 20.4 Background Jobs

```python
# APScheduler configuration
scheduler.add_job(
    check_updates,
    trigger="interval",
    hours=6,  # Based on hardware profile
    id="update_check"
)

scheduler.add_job(
    health_monitor,
    trigger="interval",
    minutes=5,  # Based on hardware profile
    id="health_check"
)
```

---

## 21. Testing Strategy

**⚠️ UPDATED IN v2.0.0**

### 21.1 Unit Tests

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run with coverage
pytest tests/unit/ --cov=backend --cov-report=html

# Target: 90%+ coverage
```

**Test Categories:**
- Authentication (passwords, sessions)
- Container management
- Network IPAM
- Image operations
- Health monitoring
- CLI generation

**v2.0.0 Testing Changes:**
- ✅ UI routes: Test authentication enforcement
- ✅ API routes: Test business logic without auth mocking
- ✅ Simplified test fixtures (no session mocking for APIs)

### 21.2 Integration Tests

```bash
# End-to-end tests (requires Docker)
./tests/integration/test_container_lifecycle.sh
./tests/integration/test_network_creation.sh
./tests/integration/test_update_workflow.sh
```

### 21.3 Example Tests

#### **Authentication Test (v2.0.0)**
```python
def test_containers_page_requires_auth(client):
    """UI route should require authentication"""
    response = client.get('/containers')
    assert response.status_code == 302  # Redirect to login
    assert '/login' in response.location

def test_list_containers_api(client, mock_docker):
    """API route does not require authentication"""
    response = client.get('/api/containers')
    assert response.status_code == 200
    assert 'containers' in response.json
```

#### **Container Test**
```python
def test_create_container(mock_docker):
    manager = ContainerManager()
    container = manager.create_container(
        name="test-nginx",
        image="nginx:latest",
        environment="DEV"
    )
    assert container.name == "test-nginx"
    assert container.status == "created"
```

#### **Network IPAM Test**
```python
def test_ip_allocation(mock_docker):
    allocator = IPAllocator("172.20.0.0/26")
    ip = allocator.allocate_next()
    assert ip == "172.20.0.2"  # First available
    
    allocator.reserve_range("172.20.0.10", "172.20.0.19")
    ip = allocator.allocate_next()
    assert ip == "172.20.0.3"  # Skips reserved range
```

### 21.4 Test Data

```python
# Fixtures for consistent test data
@pytest.fixture
def sample_container():
    return {
        "name": "test-nginx",
        "image": "nginx:latest",
        "environment": "DEV",
        "network": "test-network",
        "ports": {"80": 8080}
    }

@pytest.fixture
def sample_network():
    return {
        "name": "test-network",
        "subnet": "172.20.0.0/26",
        "gateway": "172.20.0.1"
    }
```

### 21.5 Manual Testing Checklist

```
Authentication:
□ Login with valid password
□ Login with invalid password
□ Session expires after timeout
□ Remember me extends session
□ Logout revokes session

Container Management:
□ Create container
□ Start/stop/restart container
□ Delete container
□ View logs
□ Update container

Network Management:
□ Create network with IPAM
□ Reserve IP range
□ Auto-assign IPs
□ Manual IP assignment

Health Monitoring:
□ Health checks run on schedule
□ Resource usage displays correctly
□ Alerts trigger properly
□ History tracking works

Export:
□ JSON export complete
□ Docker Compose export works
□ CLI script executes correctly
□ Backup/restore functions
```

---

## 22. Development Roadmap

### 22.1 Sprint Plan (7 Sprints × 1 Week Each)

#### **Sprint 1: Foundation & Auth** ✅ COMPLETE
- [x] Project structure setup
- [x] Flask application skeleton
- [x] Authentication system (login, sessions)
- [x] HTTPS/SSL certificate generation
- [x] Database models (users, sessions)
- [x] Initial setup wizard
- [x] Password reset tool
- **Goal:** Secure authentication works

#### **Sprint 2: Container Management** ⏳ IN PROGRESS (Task 6)
- [x] Hardware profile detection
- [x] Docker SDK integration
- [x] Container database model
- [x] Container CRUD operations
- [x] Container API endpoints
- [ ] Basic UI (list, create, start/stop) ← **Current Task**
- [ ] Container form
- [ ] Integration testing
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

### 23.1 Potential Features (Post-v1.0)

#### **Multi-Host Support** (v2.0)
- Manage Docker on multiple servers
- Centralized monitoring dashboard
- Cross-host networking
- Distributed stack deployment

#### **Advanced Monitoring**
- Prometheus integration
- Grafana dashboards
- Custom alert rules
- Slack/Discord notifications

#### **Backup Automation**
- Scheduled backups
- Incremental backups
- Cloud storage integration (S3, Backblaze)
- Disaster recovery workflows

#### **Template Marketplace**
- Community-contributed stack templates
- One-click deployments
- Version management
- Rating system

#### **API Extensions**
- Webhook endpoints
- Custom integrations
- Third-party plugin support
- GraphQL API (optional)

### 23.2 Deferred Features

These are explicitly **NOT** planned for v1.0:

- ❌ Multi-user management
- ❌ LDAP/SAML authentication
- ❌ Role-based access control
- ❌ Kubernetes support
- ❌ Cloud provider integrations
- ❌ License management
- ❌ Audit compliance reporting

**Reason:** Home lab focus, KISS principle

---

## 24. Contributing

### 24.1 How to Contribute

**Good Contributions:**
- Bug fixes
- Performance improvements
- Documentation improvements
- Home lab-specific features
- Test coverage improvements
- Hardware profile additions
- Stack templates

**Not Accepted:**
- Enterprise features (LDAP, SAML, multi-user, RBAC)
- Complex dependencies that violate KISS principle
- Features that don't work on Raspberry Pi
- Cloud-dependent features
- Features requiring external services

### 24.2 Development Setup

```bash
# Clone repository
git clone https://github.com/dockermate/dockermate.git
cd dockermate

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/unit/ -v

# Run application
python app.py
```

### 24.3 Code Standards

- PEP 8 for Python
- Docstrings for all functions
- Educational comments for complex logic
- CLI command equivalents documented
- Hardware-aware design
- Test coverage >80%

### 24.4 Pull Request Process

1. Fork the repository
2. Create feature branch (`feature/your-feature`)
3. Write tests for new functionality
4. Ensure all tests pass
5. Update documentation
6. Submit pull request with clear description

### 24.5 Support & Contact

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Questions and ideas
- **Documentation**: See README.md and this DESIGN-v2.md

---

## 25. Appendix

### 25.1 Glossary

- **IPAM**: IP Address Management
- **CRUD**: Create, Read, Update, Delete
- **YAML**: YAML Ain't Markup Language
- **TLS**: Transport Layer Security
- **VLAN**: Virtual Local Area Network
- **NAS**: Network Attached Storage
- **TTL**: Time To Live
- **WAL**: Write-Ahead Logging

### 25.2 References

- Docker SDK for Python: https://docker-py.readthedocs.io/
- Flask Documentation: https://flask.palletsprojects.com/
- SQLAlchemy Documentation: https://docs.sqlalchemy.org/
- Tailwind CSS: https://tailwindcss.com/
- Alpine.js: https://alpinejs.dev/

### 25.3 License

MIT License - See LICENSE file for details

---

**End of Design Document v2.0.0**

---

**Version**: 2.0.0  
**Date**: January 29, 2026  
**Status**: Active Design (Sprint 2+)  
**Supersedes**: DESIGN-v1.md  
**Next Review**: Sprint 3 completion or next architectural change request

---

## Approval & Locking Rules

Once approved by Bryan, this document (DESIGN-v2.md) becomes **locked** and must not be modified. All future changes require:
- A new design version (DESIGN-v3.md)
- Architectural deltas documented
- User approval before activation

**Active Design**: v2.0.0 (this document)  
**Historical Designs**: DESIGN-v1.md (locked, reference only)