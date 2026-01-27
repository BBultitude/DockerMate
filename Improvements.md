# Improvements.md

## PURPOSE
This document tracks all planned improvements, features, fixes, refactors, security enhancements, and technical debt for DockerMate. Items are categorized and prioritized to align with the current Design document version.

---

## CATEGORIES
- **FEATURE**: New functionality or capabilities
- **FIX**: Bug fixes and corrections
- **REFACTOR**: Code improvements without changing functionality
- **SECURITY**: Security enhancements and vulnerability fixes
- **DEBT**: Technical debt and architectural improvements

---

## FEATURE ENHANCEMENTS

### FEAT-001: Advanced Container Filtering
**Priority:** Medium  
**Effort:** 3-4 hours  
**Sprint:** 3 (Container UI)  
**Description:**
- Filter containers by status (running, stopped, paused)
- Filter by environment tags
- Filter by image name
- Search by container name
- Multi-select filters with URL state persistence

---

### FEAT-002: Container Health Monitoring
**Priority:** High  
**Effort:** 4-6 hours  
**Sprint:** 4 (Networks & Volumes)  
**Description:**
- Display container health check status
- Show resource usage (CPU, memory, network I/O)
- Historical resource graphs
- Alert thresholds based on hardware profile
**Dependencies:** Sprint 2 Task 1 (HostConfig profiles)

---

### FEAT-003: Bulk Container Operations
**Priority:** Medium  
**Effort:** 2-3 hours  
**Sprint:** 3 (Container UI)  
**Description:**
- Select multiple containers via checkboxes
- Bulk start/stop/restart/delete
- Bulk tag assignment
- Confirmation modal with operation summary

---

### FEAT-004: Container Logs Viewer
**Priority:** High  
**Effort:** 3-4 hours  
**Sprint:** 3 (Container UI)  
**Description:**
- Real-time log streaming via WebSocket
- Log search and filtering
- Download logs to file
- Configurable log retention (last N lines)
- Show Docker CLI equivalent: `docker logs -f <container>`

---

### FEAT-005: Docker Compose Support
**Priority:** Low  
**Effort:** 8-12 hours  
**Sprint:** 6+ (Future Enhancement)  
**Description:**
- Import docker-compose.yml files
- Create multi-container stacks
- Stack-level operations (start/stop all)
- Environment tag inheritance for stack containers
**Note:** Significant scope increase, requires compose file parser

---

### FEAT-006: Container Templates
**Priority:** Medium  
**Effort:** 4-5 hours  
**Sprint:** 5 (System Administration)  
**Description:**
- Save container configuration as reusable template
- Template library (common apps: nginx, postgres, redis)
- One-click deploy from template
- Template import/export (JSON)
**Educational Value:** Shows best practice configurations

---

### FEAT-007: Backup and Restore
**Priority:** Medium  
**Effort:** 6-8 hours  
**Sprint:** 5 (System Administration)  
**Description:**
- Export all container configurations to JSON
- Restore containers from backup file
- Exclude volumes (config only) or include volume data
- Scheduled backup option
**Dependencies:** Export function from FEAT-009

---

### FEAT-008: Auto-Prune Deleted Containers (Scheduled)
**Priority:** Medium  
**Effort:** 1 hour  
**Dependencies:** Sprint 2 Task 3 complete  
**Sprint:** 5 (System Administration)  
**Description:**
- Integrate auto-prune with app startup (daily check)
- Add `last_prune_timestamp` to HostConfig
- Log prune operations with count deleted
**Implementation Note:** Prune function exists in `prune_service.py`, needs startup hook

---

### FEAT-009: Export Deleted Containers
**Priority:** Low  
**Effort:** 2 hours  
**Dependencies:** Sprint 2 Task 3 complete  
**Sprint:** 3 (Container UI)  
**Description:**
- Export deleted containers to JSON/CSV before pruning
- Enable long-term cold storage audit trail
- UI button in Settings page: "Export Deleted Containers"
- Include all container metadata (ports, volumes, env_vars, tags, deleted_at timestamp)
**Use Case:** Compliance, audit requirements, forensic analysis

---

### FEAT-010: WebSocket Live Updates
**Priority:** Low  
**Effort:** 6-8 hours  
**Sprint:** 6+ (Future Enhancement)  
**Description:**
- Replace sync-on-demand with WebSocket push updates
- Real-time container status changes
- Live resource usage graphs
- Broadcast updates to all connected clients
**Dependencies:** Flask-SocketIO integration
**Note:** Adds complexity, may impact Raspberry Pi performance

---

### FEAT-011: Post-Creation Container Health Validation
**Priority:** High  
**Effort:** 2-3 hours  
**Sprint:** 2 Task 4 (Container CRUD)  
**Status:** ✅ Approved for Implementation  
**Description:**
- After auto-starting container, wait 10-20 seconds (randomized)
- Check container.status, health check status, exit code, error message
- Update database with health validation results
- Return structured health status to user
- Provide actionable feedback if startup failed
**Rationale:**
- Catches immediate startup failures
- Educational (teaches health check concepts)
- Aligns with Docker best practices
- Improves user experience with clear error messages
**Implementation Details:**
```python
# After container.start()
time.sleep(random.uniform(10, 20))
container.reload()
health_status = {
    "running": container.status == "running",
    "health": container.attrs.get("State", {}).get("Health", {}).get("Status"),
    "exit_code": container.attrs.get("State", {}).get("ExitCode"),
    "error": container.attrs.get("State", {}).get("Error")
}
```

---

## FIX ITEMS

### FIX-001: Database Initialization Test Failures
**Priority:** Low  
**Effort:** 1 hour  
**Sprint:** 2 (Container Management)  
**Status:** Known Issue  
**Description:**
- Two tests fail in Sprint 1: `test_init_db_creates_tables` and `test_init_db_idempotent`
- Root cause: Tests check for User table, but Container model not yet created
- Resolution: Will auto-resolve when Sprint 2 Task 3 (Container model) is completed
**Tests Affected:**
- `tests/test_database.py::test_init_db_creates_tables`
- `tests/test_database.py::test_init_db_idempotent`

---

### FIX-002: Password Reset Functionality
**Priority:** High  
**Effort:** 3-4 hours  
**Sprint:** 5 (System Administration)  
**Description:**
- Single-user system has no password recovery mechanism
- Add CLI tool: `python manage.py reset-password`
- Prompt for new password with confirmation
- Log password reset event
**Security Note:** CLI-only (no web endpoint) to prevent brute force

---

## REFACTOR ITEMS

### REF-001: Consolidate Docker Client Initialization
**Priority:** Low  
**Effort:** 1-2 hours  
**Sprint:** 4 (Networks & Volumes)  
**Description:**
- Centralize `docker.from_env()` calls into singleton pattern
- Create `backend/services/docker_client.py`
- Improve error handling for Docker daemon unavailable
- Add connection retry logic with exponential backoff

---

### REF-002: Extract Validation Logic
**Priority:** Low  
**Effort:** 2-3 hours  
**Sprint:** 5 (System Administration)  
**Description:**
- Move regex password validation from `auth_service.py` to `backend/utils/validators.py`
- Create reusable validators for:
  - Container names (Docker naming rules)
  - Port numbers (1-65535)
  - Volume paths (absolute paths)
  - Environment variable syntax
**Benefit:** Reusability, testability, separation of concerns

---

### REF-003: Normalize Environment Tags
**Priority:** Low  
**Effort:** 2-3 hours  
**Trigger:** User reports tag management issues OR >20 unique tags exist  
**Sprint:** 6+ (Future Enhancement)  
**Description:**
- Migrate from JSON column to normalized `env_tags` + `container_tags` tables
- Enable efficient tag-based queries without full table scan
- Add tag management UI (rename, delete, merge tags)
- Prevent tag typos with autocomplete
**Migration Path:** Full SQL migration documented in Sprint 2 Task 3 summary
**Trade-off:** Adds complexity (joins), but improves query performance at scale

---

## SECURITY ENHANCEMENTS

### SEC-001: Rate Limiting
**Priority:** High  
**Effort:** 2-3 hours  
**Sprint:** 5 (System Administration)  
**Description:**
- Add Flask-Limiter for API rate limiting
- Limit login attempts: 5 per 15 minutes per IP
- Limit container operations: 30 per minute per session
- Return 429 Too Many Requests with Retry-After header
**Benefit:** Prevent brute force and resource exhaustion

---

### SEC-002: Content Security Policy (CSP)
**Priority:** Medium  
**Effort:** 2 hours  
**Sprint:** 5 (System Administration)  
**Description:**
- Add CSP headers to all responses
- Restrict script sources to self + CDN (Tailwind/Alpine)
- Block inline scripts (refactor if needed)
- Report CSP violations to log
**Compliance:** Modern browser security best practice

---

### SEC-003: Audit Logging
**Priority:** Medium  
**Effort:** 3-4 hours  
**Sprint:** 5 (System Administration)  
**Description:**
- Log all sensitive operations:
  - Login/logout events
  - Container create/delete
  - Container limit override toggle
  - Password changes
- Include timestamp, IP address, user agent
- Searchable audit log UI (admin only)
**Compliance:** Enables forensic analysis

---

### SEC-004: Docker Socket Security
**Priority:** High  
**Effort:** 1-2 hours  
**Sprint:** 5 (System Administration)  
**Description:**
- Document risks of mounting `/var/run/docker.sock`
- Add warning in installation docs
- Recommend Docker socket proxy (tecnativa/docker-socket-proxy) for production
- Add security checklist to README
**Educational Goal:** Teach home lab security best practices

---

## TECHNICAL DEBT

### DEBT-001: Test Coverage Gaps
**Priority:** Medium  
**Effort:** 4-6 hours  
**Sprint:** 5 (System Administration)  
**Description:**
- Increase Sprint 1 coverage from 78% to >90%
- Add integration tests with real Docker daemon
- Add end-to-end tests with Selenium/Playwright
- Set up CI/CD coverage reporting (Codecov)
**Current Coverage:**
- `auth_service.py`: 78%
- `models/user.py`: 79%
- Target: 90%+ across all modules

---

### DEBT-002: Error Handling Consistency
**Priority:** Medium  
**Effort:** 2-3 hours  
**Sprint:** 4 (Networks & Volumes)  
**Description:**
- Standardize error response format:
  ```json
  {
    "error": "ContainerNotFound",
    "message": "Container 'nginx' not found",
    "code": 404,
    "timestamp": "2025-01-27T10:30:00Z"
  }
  ```
- Create custom exception classes
- Add global error handler in Flask app
- Document error codes in API docs

---

### DEBT-003: Database Migration Strategy
**Priority:** High  
**Effort:** 3-4 hours  
**Sprint:** 3 (Container UI)  
**Description:**
- Implement Flask-Migrate (Alembic) for schema versioning
- Generate initial migration from current models
- Add upgrade/downgrade scripts
- Document migration workflow in CONTRIBUTING.md
**Current State:** SQLAlchemy models exist, but no migration history
**Risk:** Schema changes will break existing installations without migrations

---

### DEBT-004: Frontend State Management
**Priority:** Low  
**Effort:** 6-8 hours  
**Sprint:** 6+ (Future Enhancement)  
**Description:**
- Current: Alpine.js with inline `x-data`
- Future: Centralized store pattern (Alpine Stores or Pinia)
- Benefits:
  - Shared state across components
  - Easier debugging
  - Better testability
**Trigger:** Frontend complexity exceeds 10 components

---

### DEBT-005: Configuration Management
**Priority:** Medium  
**Effort:** 2-3 hours  
**Sprint:** 5 (System Administration)  
**Description:**
- Externalize hardcoded values to `config.py`:
  - Session timeout (currently 24 hours)
  - Sync cache TTL (currently 10 seconds)
  - Default retention period (currently 30 days)
  - Container limit thresholds (currently in HostConfig)
- Support environment variable overrides
- Document configuration options in README

---

## SPRINT 2 TASK 4: CONTAINER CRUD OPERATIONS

### Implementation Scope (Approved 2025-01-27)

#### Lifecycle Management
- ✅ **Auto-start:** Default True, configurable parameter
- ✅ **Pull-if-missing:** Default True, configurable parameter  
- ✅ **Hardware validation:** Always enforced (non-negotiable)
- ✅ **Health check:** 10-20 second post-creation validation (FEAT-011)

#### Update Operations (Phased Approach)
- **Phase 1 (Task 4):** Labels-only updates (non-destructive)
- **Phase 2 (Task 6):** Full updates via recreate workflow in UI

#### Validation Requirements
| Validation | Priority | Task 4 Implementation |
|------------|----------|----------------------|
| Hardware limits | Critical | ✅ Always enforced |
| Image existence | High | ✅ Conditional (if pull_if_missing=False) |
| Port conflicts | Medium | ⏸️ Deferred to Task 5 (API layer) |
| Volume paths | Low | ✅ Basic syntax check only |

#### Error Handling Strategy
- **Daemon connection:** Retry 3x with exponential backoff
- **State conflicts:** Check current state, descriptive error
- **Resource exhaustion:** Pre-validate against hardware profile
- **Missing dependencies:** Auto-pull if enabled, else instructional error

#### Service Layer Structure
```
src/services/container_manager.py
├── ContainerManager class
│   ├── create_container()      # Create + auto-start + health check
│   ├── get_container()         # Retrieve single
│   ├── list_containers()       # Query with filters
│   ├── update_container()      # Labels only (Phase 1)
│   ├── delete_container()      # Stop + remove
│   ├── start_container()       # Lifecycle controls
│   ├── stop_container()
│   └── restart_container()
└── Validation helpers
    ├── _validate_create_request()
    ├── _check_hardware_limits()
    ├── _validate_health_status()  # NEW: Post-creation check
    └── _sync_database_state()
```

#### Dependencies
- `SystemConfig` (hardware limits) ✅ Task 1
- `DockerClient` (SDK integration) ✅ Task 2
- `Container` model (database) ✅ Task 3
- `Database` session management ✅ Task 3

#### Deliverables
1. `backend/services/container_manager.py` - Full CRUD + lifecycle
2. Comprehensive unit tests (mock-based)
3. Health validation helper function
4. Error handling with structured responses
5. Verification script: `scripts/verify_sprint2_task4.sh`

#### What's Deferred
- Full update operations (recreate workflow) → Task 6
- Port conflict detection → Task 5 (API layer)
- Advanced volume validation → Future sprint
- Network validation → Sprint 4

---

## NOTES

### Sprint Alignment
- Sprint 2: Focus on container management backend (FEAT-008, FEAT-009, FEAT-011, FIX-001)
- Sprint 3: Focus on container UI (FEAT-001, FEAT-003, FEAT-004, FEAT-009, DEBT-003)
- Sprint 4: Networks and volumes (REF-001, DEBT-002)
- Sprint 5: System administration and polish (FEAT-002, FEAT-006, FEAT-008, FIX-002, SEC-001, SEC-002, SEC-003, SEC-004, DEBT-001, DEBT-005)
- Sprint 6+: Future enhancements (FEAT-005, FEAT-010, REF-003, DEBT-004)

### Prioritization Criteria
1. **Security** issues take precedence (SEC-*)
2. **Fixes** for broken functionality (FIX-*)
3. **Features** that enhance core user experience (FEAT-001 to FEAT-004, FEAT-011)
4. **Refactors** that reduce future maintenance burden (REF-*)
5. **Debt** items to improve code quality (DEBT-*)
6. **Nice-to-have** features for advanced users (FEAT-005, FEAT-010)

---

## DECISION LOG

### Sprint 2 Task 4 Strategic Decisions (2025-01-27)
✅ **Approved by Product Owner**

| Decision | Recommendation | Rationale |
|----------|---------------|-----------|
| Auto-start containers | Default True (configurable) | Matches Docker CLI behavior, reduces user steps |
| Pull-if-missing images | Default True (configurable) | Seamless UX, aligns with Docker defaults |
| Hardware limit enforcement | Always on (non-negotiable) | System stability, prevents overload |
| **Post-creation health check** | **10-20 second validation** | **Catches startup failures, educational value** |
| Update scope Phase 1 | Labels only | Non-destructive, immediate value |
| Update scope Phase 2 | Full recreate workflow | Deferred to Task 6 (UI complexity) |
| Validation tier | Critical + High priority | Fail fast, clear errors |
| Port conflict detection | Deferred to Task 5 | Better handled at API layer |
| Volume validation | Basic syntax only | Full validation deferred |
| Error handling | Retry + graceful degradation | Handles transient failures |

### Sprint 2 Task 3 Strategic Decisions (2025-01-27)
- Added FEAT-008 (auto-prune scheduling)
- Added FEAT-009 (soft delete with retention)
- Added REF-003 (normalize tags when needed)
- Retention period default: 30 days (changed from 90)
- Container limit override: Persistent setting with stability warnings

---

## VERSION HISTORY
- **v1.2** (2025-01-27): Sprint 2 Task 4 strategic decisions + FEAT-011 health validation
- **v1.1** (2025-01-27): Sprint 2 Task 3 strategic decision items (FEAT-008, FEAT-009, REF-003)
- **v1.0** (2025-01-27): Initial creation after Sprint 1 completion