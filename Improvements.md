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

### FEAT-012: Import / Adopt Unmanaged Containers
**Priority:** Medium
**Effort:** 4-6 hours
**Sprint:** 4 or 5 (after network management foundation)
**Status:** 🔴 OPEN — backlog
**Description:**
External (unmanaged) containers are visible on the Containers page when "Show all Docker containers" is toggled, but cannot be managed through DockerMate. This feature adds two paths to get them under DockerMate control:

1. **Import (one-click adopt):** Button on each external container card that reads its current Docker config (image, ports, volumes, env vars, restart policy) and writes a matching record into the database. The container gains the `com.dockermate.managed=true` label via `docker rename` + label update (or container recreate if labels cannot be applied live). After import it behaves identically to a DockerMate-created container.

2. **Rebuild instructions:** For cases where import is not desired (e.g. the container was created by another tool and should stay independent), a "How to recreate" info panel shows the equivalent `docker run` command that would recreate the container inside DockerMate. This lets the user manually create a managed copy and stop the external one at their own pace.

**UI placement:**
- "Import" button on external container cards (only shown when "Show all" is toggled)
- "Show recreate command" expandable section on external container detail/info

**Out of scope for this item:**
- Volume data migration (import copies config only, not volume contents)
- Containers created by docker-compose (recommend stack import instead — see FEAT-005)

---

### FEAT-013: Retag Container Image (change version without full redeploy config)
**Priority:** Medium
**Effort:** 3-4 hours
**Sprint:** 4 or 5
**Status:** 🔴 OPEN — backlog
**Description:**
The current update flow (`POST /api/containers/<id>/update`) pulls the same `repository:tag` the container was created with. If a container was deliberately pinned to `nginx:1.28`, update will only ever pull `nginx:1.28` — it will never jump to `1.29` or `latest`. This is correct default behaviour, but there is no way to *change* the tag without deleting and manually recreating the container.

This feature adds a "Retag & Redeploy" action that lets the user pick a new tag for an existing container's image and recreate it with the same config but the new tag:

1. **UI:** "Change Image Version" button on managed container cards (or in the details modal). Opens a modal showing the current `repository:tag` with a text input for the new tag. Optionally show a dropdown of tags recently seen for that repository (populated from Docker Hub tag list API).
2. **Backend:** New endpoint `POST /api/containers/<id>/retag` with body `{"tag": "1.29"}`. Internally: pull `repository:newtag`, stop+remove old container, recreate with identical config but new image, start, write UpdateHistory record (so rollback back to the old tag is available).
3. **Rollback compatibility:** The UpdateHistory record written by retag stores `old_image` as `nginx:1.28` and `new_image` as `nginx:1.29`. The existing rollback flow already uses `old_image` to recreate, so rollback works with zero changes.

**Out of scope:**
- Changing the repository (e.g. `nginx` → `alpine`). That is a different container.
- Tag auto-discovery / registry tag listing (nice-to-have, tracked separately if wanted).

---

### FEAT-014: Unused Image Detection & Auto-Prune
**Priority:** Medium
**Effort:** 4-6 hours
**Sprint:** 5
**Status:** 🔴 OPEN — backlog
**Description:**
Images accumulate over time — old versions left behind after updates, test pulls never used, dangling images created when a tag moves to a new digest. This feature surfaces that waste and optionally cleans it up.

**Three sub-features:**

1. **Usage status on the Images page:** For each image in the list, show which containers (if any) are currently using it. Query the live Docker daemon for all containers, build a map of `image → [container names]`, and render it as a badge or expandable list on each image card. Images with zero containers get an "Unused" badge. Dangling images (tag = `<none>`) get a "Dangling" badge.

2. **Auto-prune policy (configurable):** A setting (Settings page or env var) that defines a retention window, e.g. "prune unused images older than 30 days". A scheduled job (piggyback on the existing 6 h scheduler in `scheduler.py`) scans the `images` table: if `pulled_at` is older than the threshold AND no container references that image_id, delete it from both Docker and the database. Dangling images can have a shorter threshold (e.g. 7 days). All prune actions are logged with image name, size reclaimed, and reason.

3. **Manual "Prune Unused" button:** A one-click button on the Images page that runs the same logic as auto-prune but immediately, with a confirmation modal showing what will be removed and total size to be reclaimed before committing.

**Implementation notes:**
- Container → image mapping: `docker inspect` each container gives `Config.Image`. Cross-reference against local image tags.
- Dangling detection: images where `RepoTags` is empty or `['<none>:<none>']`.
- The existing `Image.pulled_at` column already tracks when we first saw the image — use that as the age baseline.
- Auto-prune should be opt-in (off by default) and configurable via the Settings page.

---

### FEAT-015: Tag Drift Detection (dangling image tracking after pull)
**Priority:** Medium
**Effort:** 3-4 hours
**Sprint:** 5
**Status:** 🔴 OPEN — backlog
**Description:**
When a mutable tag like `nginx:latest` is pulled again after a remote update, Docker locally untags the previous image — it becomes dangling (`<none>:<none>`). The new image gets the `latest` tag. DockerMate's `_sync_database_state()` already handles this correctly at the record level: it keys on `image_id` and updates `repository`/`tag` when it syncs. However, there are two gaps:

1. **Sync timing:** `_sync_database_state` only runs when an image is explicitly listed or pulled. Between syncs, a stale record can sit in the DB with the old tag still attached, even though Docker has already moved it. The fix is straightforward: during `list_images()`, after querying the daemon, do a second pass over *all* DB records and mark any whose `image_id` is no longer present in the daemon response as dangling. This makes the DB consistent after every list call at minimal cost.

2. **Surfacing to the user:** Once dangling records are correctly tracked, show them on the Images page with a "Dangling — was `nginx:latest` / `nginx:1.29`" label. This is where the digest becomes useful (see below).

**Digest-based version resolution (preferred over simple previous_tag):**
Docker does not auto-apply version tags locally — if you only pulled `nginx:latest` you only have that one tag on disk. However, `RepoDigests` (e.g. `nginx@sha256:abc...`) survives dangling and we already store the digest in the `Image` model. Mutable tags like `latest` and `1.29` (minor-version pointer) typically share the same digest on Docker Hub at any given time, while patch-pinned tags like `1.29.0` point to a different one. Verified against live registry:

```
nginx:latest  -> sha256:7fe5dda2...   ← same
nginx:1.29    -> sha256:7fe5dda2...   ← same  (minor-version pointer)
nginx:1.29.0  -> sha256:3ab4ed06...   ← different (patch-pinned)
nginx:1.28    -> sha256:68334eae...   ← different
```

**Implementation approach — two-tier resolution:**
- **Tier 1 (fast, offline):** Add a `previous_tag` column to `Image`. In `_sync_database_state`, before overwriting `repository`/`tag` with `<none>`, save the current values. This always works and costs nothing.
- **Tier 2 (richer, network):** When displaying a dangling image, take its stored digest and call the registry tag-list endpoint for that repository. Find all tags whose manifest digest matches. Surface both the previous tag and any matching version tags (e.g. "was `latest` / also `1.29`"). This runs lazily on the UI side (only when the user views the Images page and there are dangling images) so it does not block anything.

**Relationship to FEAT-014:** FEAT-015 is the detection layer; FEAT-014 is the cleanup layer. FEAT-015 should land first so that by the time auto-prune runs, dangling images are already correctly labelled and aged.

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

### DEBT-003: Database Migration Strategy ✅ COMPLETE
**Priority:** High
**Status:** ✅ Completed February 2, 2026 (Sprint 3)
**Description:**
- Alembic configured (`alembic.ini`, `migrations/` directory)
- Initial migration generated for Image model
- `docker-entrypoint.sh` runs `alembic upgrade head` on every container start
- One-time `fix_migrations.py` script handles state conflicts during transition

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

### DEBT-006: Standardize Frontend JavaScript to Alpine.js
**Priority:** High
**Effort:** 2-3 hours
**Sprint:** 2 (Task 8 - Technical Debt)
**Status:** ✅ COMPLETE
**Completed:** February 2, 2026
**Dependencies:** Sprint 1 templates created
**Description:**
Current templates inconsistently mix Alpine.js (loaded in base.html) with plain JavaScript patterns (`onclick` handlers). This violates KISS principle and wastes bandwidth.

**Resolution:**
All templates verified to use Alpine.js exclusively:
- ✅ `frontend/templates/dashboard.html` - Uses navbar component (Alpine.js)
- ✅ `frontend/templates/containers.html` - Uses `containersComponent()` (Alpine.js)
- ✅ `frontend/templates/images.html` - Static content, no interactivity needed
- ✅ `frontend/templates/networks.html` - Static content, no interactivity needed
- ✅ `frontend/templates/settings.html` - Uses `settingsPage()` (Alpine.js)
- ✅ `frontend/templates/login.html` - Uses `loginPage()` (Alpine.js)
- ✅ `frontend/templates/setup.html` - Uses `setupPage()` (Alpine.js)

**Verification:**
- No inline `onclick`, `onchange`, `onsubmit`, or `onload` handlers found
- All JavaScript functions are Alpine.js component functions
- Navbar component centralized with Alpine.js patterns

**Pattern Migration:**

Before:
```html
<button onclick="logout()">Logout</button>
<script>
function logout() {
    fetch('/logout', { method: 'POST' })...
}
</script>
```

After:
```html
<div x-data="auth()">
    <button @click="handleLogout()">Logout</button>
</div>
<script>
function auth() {
    return {
        handleLogout() {
            fetch('/logout', { method: 'POST' })...
        }
    }
}
</script>
```

**Benefits:**
- Single JavaScript pattern across all templates
- Better state management for complex UIs
- Consistent with Alpine.js already loaded in base.html
- Reactive updates for container lists

**Success Criteria:**
- Zero `onclick`, `onchange`, `onsubmit` inline handlers
- All interactivity uses Alpine.js directives
- Shared navbar component created
- All templates follow standardized structure

---

### DEBT-007: Create Shared Navigation Component
**Priority:** High
**Effort:** 1 hour
**Sprint:** 2 (Task 8 - Technical Debt)
**Status:** ✅ COMPLETE
**Completed:** February 2, 2026 (discovered already implemented)
**Dependencies:** DEBT-006 (Alpine.js standardization)
**Description:**
Current templates duplicate navigation bar code (50+ lines per template). Extract to shared component for maintainability.

**Resolution:**
Component already implemented and in use across all pages:
- ✅ Created `frontend/templates/components/navbar.html`
- ✅ Uses Alpine.js `navbar()` component function
- ✅ Centralized logout logic with error handling
- ✅ Active link highlighting using `request.path`
- ✅ Included in all main templates

**Benefits Achieved:**
- Single source of truth for navigation (119 lines)
- Consistent styling across all pages
- No code duplication
- Easy to modify menu items in one place

**Files Using Navbar:**
- ✅ `frontend/templates/dashboard.html`
- ✅ `frontend/templates/containers.html`
- ✅ `frontend/templates/images.html`
- ✅ `frontend/templates/networks.html`
- ✅ `frontend/templates/settings.html`

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
- Sprint 4: Networks and volumes + image retag (REF-001, DEBT-002, FEAT-013)
- Sprint 5: System administration, image housekeeping, and polish (FEAT-002, FEAT-006, FEAT-008, FEAT-014, FEAT-015, FIX-002, SEC-001, SEC-002, SEC-003, SEC-004, DEBT-001, DEBT-005)
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

## SPRINT 3 COMPLETED ITEMS

### FEATURE-005: Show All Docker Containers ✅ COMPLETE (Feb 3, 2026)
- `list_all_docker_containers()` hybrid listing with managed/external distinction
- Docker labels (`com.dockermate.managed`, `com.dockermate.environment`) persist across DB resets
- Frontend toggle, disabled checkboxes/buttons for externals, bulk-select exclusion
- DockerMate container shown as external (KISS)

### FEATURE-006: Real-Time Dashboard ✅ COMPLETE (Feb 3, 2026)
- Alpine.js `dashboardComponent()` with 10 s polling
- Live container stats, hardware profile, capacity bar, environment distribution

### IMAGE MANAGEMENT (Tasks 1-4) ✅ COMPLETE (Feb 2-3, 2026)
- `backend/models/image.py` — Image model + Alembic migration
- `backend/services/image_manager.py` — CRUD, pull, tag, update-check
- `backend/api/images.py` — 6 REST endpoints
- `frontend/templates/images.html` — Full Alpine.js image management page

### BACKGROUND SCHEDULER (Task 7) ✅ COMPLETE (Feb 3, 2026)
- `backend/services/scheduler.py` — stdlib daemon thread, no extra deps
- Image update check every 6 h (configurable via `SCHEDULER_IMAGE_CHECK_HOURS`)
- Flask debug-mode reloader guard (`WERKZEUG_RUN_MAIN`)

### DATABASE SYNC / RECOVERY ✅ COMPLETE (Feb 3, 2026)
- `sync_managed_containers_to_database()` recovers labeled containers after DB reset
- `POST /api/containers/sync` endpoint
- Auto-sync on container startup via `docker-entrypoint.sh`

---

## VERSION HISTORY
- **v1.5** (2026-02-03): Sprint 3 finish — update/rollback endpoints, FEAT-013 (retag), FEAT-014 (unused image prune), FEAT-015 (tag drift detection) added to backlog
- **v1.4** (2026-02-03): Sprint 3 — image management, show-all containers, dashboard, scheduler, DB sync
- **v1.3** (2026-01-29): DEBT-006: Standardize Frontend JavaScript to Alpine.js & DEBT-007: Create Shared Navigation Component
- **v1.2** (2026-01-27): Sprint 2 Task 4 strategic decisions + FEAT-011 health validation
- **v1.1** (2026-01-27): Sprint 2 Task 3 strategic decision items (FEAT-008, FEAT-009, REF-003)
- **v1.0** (2026-01-27): Initial creation after Sprint 1 completion