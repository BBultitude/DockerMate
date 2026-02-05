# DockerMate - Known Issues Tracker

**Created:** January 31, 2026
**Last Updated:** February 5, 2026 (Sprint 5 in progress)
**Current Sprint:** Sprint 5 — SEC-001, FIX-002, FEAT-017, FEAT-019 delivered; UI bug fixes applied

This document tracks all known issues identified during development. Issues are categorized by priority and can be checked off as they're resolved.

---

## 🎯 Summary Statistics

| Category | Critical | High | Medium | Low | Total |
|----------|----------|------|--------|-----|-------|
| Authentication/Security | 0 | 0 | 4 | 2 | 6 |
| Frontend Issues | 0 | 0 | 1 | 1 | 2 |
| Backend API | 0 | 0 | 4 | 0 | 4 |
| Database/Models | 0 | 0 | 4 | 0 | 4 |
| Code Quality | 0 | 0 | 6 | 0 | 6 |
| Configuration | 0 | 0 | 2 | 2 | 4 |
| Error Handling | 0 | 0 | 4 | 0 | 4 |
| Documentation | 0 | 0 | 1 | 3 | 4 |
| Performance | 0 | 0 | 2 | 2 | 4 |
| Testing | 0 | 0 | 2 | 1 | 3 |
| Missing Features | 0 | 0 | 4 | 0 | 4 |
| Network | 0 | 0 | 0 | 0 | 0 |
| **TOTAL** | **0** | **0** | **35** | **12** | **47** |

**Recently Resolved (Sprint 3-4):** NETWORK-001 (oversized false-positive on empty networks), FEATURE-005 (show all containers), FEATURE-006 (real-time dashboard), FEATURE-002 (container sync), FEATURE-001 (system health checks)
**Previously Resolved:** 7 issues (Sprint 2 Task 7), PROJECT_STATUS.md created (Sprint 2 Task 8)
**Reclassified as Design:** 2 issues (API auth, perimeter security) - intentional per DESIGN-v2.md
**New (Sprint 4):** FEATURE-007 (health page stub + dashboard health card incomplete)
**Resolved (Sprint 4):** NETWORK-001 (recommended subnets flagged as oversized — fixed)
**Resolved (Sprint 5 — Feb 5):** NETWORK-002, NETWORK-003, SSL-001 (previous session); FEATURE-007 (full health page + expanded API — SEC-001 rate limiting, FIX-002 password reset CLI, FEAT-017 adopt/release networks, FEAT-019 health page); FEATURE-004 (password reset — now `manage.py reset-password`); SECURITY-004 (password reset workflow — implemented via manage.py); UI-003 (rollback button clickable with no history — `rollback_available` flag); UI-004 (Release/Delete hidden for adopted dockermate network — overly broad name filter removed); UI-005 (env vars missing from container details — showDetails now fetches full detail); UI-006 (volumes rendered as [object Object] — fixed to source:destination:mode)
**Total Open Issues:** 38

---

## 🔴 HIGH PRIORITY ISSUES

### ⚠️ NO HIGH PRIORITY ISSUES CURRENTLY OPEN

All previously identified authentication "issues" are intentional design decisions per DESIGN-v2.md (v2.0.0 Perimeter Security Model).

---

## 🟡 MEDIUM PRIORITY ISSUES

### FRONTEND-001: Form Validation Not Translating Properly ⚠️ MEDIUM
**Status:** ✅ RESOLVED
**Location:** `frontend/templates/containers.html:271-295, 1037-1040, 1213-1221`
**Resolved:** January 31, 2026 (Sprint 2 Task 7)

**Issue:**
Port format in form uses separate fields but API expects dict format. Volume format has similar mismatch.

**Resolution:**
- Added protocol dropdown (TCP/UDP) for better UX
- Split port input into: container port (number) + protocol (dropdown) + host port
- Fixed transformation: combines `port.container + "/" + port.protocol` → API format
- Added error message displays for ports, volumes, env vars (not just red borders)

---

### FRONTEND-002: Health Check Polling May Start Before Container Exists ⚠️ MEDIUM
**Status:** ✅ RESOLVED
**Location:** `frontend/templates/containers.html:886-964, 1326-1330`
**Resolved:** January 31, 2026 (Sprint 2 Task 7)

**Issue:**
`startHealthCheckPolling()` called with 2-second delay which might be insufficient

**Resolution:**
- Implemented exponential backoff: 3s, 5s, 8s, 12s, 15s, 20s... (max 10 attempts)
- Changed from setInterval to setTimeout for variable delays
- First check after 3 seconds (gives container time to start)
- Removed wrapper setTimeout when starting polling

---

### FRONTEND-003: Login Error Handling Incomplete ⚠️ MEDIUM
**Status:** 🔴 OPEN
**Location:** `frontend/templates/login.html:94-105`

**Issue:**
Frontend assumes successful JSON response but doesn't handle HTTP errors

**Impact:**
If endpoint returns 404 or 500, `response.json()` will fail

**Fix Required:**
```javascript
if (!response.ok) {
    // handle error before parsing JSON
}
```

---

### FRONTEND-004: Responsive Design Gap ⚠️ LOW
**Status:** 🔴 OPEN
**Location:** `frontend/templates/containers.html:168`

**Issue:**
Create modal has `max-h-[90vh]` but no min-height guarantee

**Impact:**
Modal might be cut off on small screens

---

### API-001: Port Conflict Detection JSON Parsing ⚠️ MEDIUM
**Status:** 🔴 OPEN
**Location:** `backend/api/containers.py:216-230`

**Issue:**
JSON parsing in conflict detection uses bare `json.loads()` without validation

**Impact:**
Malformed JSON in database could crash server

**Fix Required:**
Use schema validation or handle ValueError more specifically

---

### API-002: Memory Limit Conversion Inconsistency ⚠️ MEDIUM
**Status:** 🔴 OPEN
**Location:** `frontend/templates/containers.html:1245`

**Issue:**
Frontend converts MB to bytes (`* 1024 * 1024`) but backend expects bytes directly

**Impact:**
Unclear if API or frontend is wrong - potential memory limit mismatch

**Fix Required:**
Clarify API documentation and ensure consistent conversion

---

### API-003: Empty JSON Body Handling ⚠️ LOW
**Status:** 🔴 OPEN
**Location:** `backend/api/containers.py:377-383`

**Issue:**
`request.get_json(force=True)` can raise exceptions not caught

**Fix Required:**
Use `silent=True` or `force=False` with explicit error handling

---

### API-004: Container ID Lookup Ambiguity ⚠️ LOW
**Status:** 🔴 OPEN
**Location:** `backend/api/containers.py` (multiple endpoints)

**Issue:**
Endpoints accept "container_id" that could be name or ID, not consistently documented

**Impact:**
API documentation confusion

---

### DB-001: Ports JSON Storage Format Not Documented ⚠️ MEDIUM
**Status:** 🔴 OPEN
**Location:** `backend/models/container.py:99-100`

**Issue:**
Ports stored as JSON string but format not clearly documented

**Impact:**
Parsing assumes specific structure without validation

---

### DB-002: Environment Variable Storage Format Unclear ⚠️ MEDIUM
**Status:** 🔴 OPEN
**Location:** `backend/models/container.py`

**Issue:**
env_vars_json storage format not documented - unclear if array or dict

**Impact:**
Frontend expects array format but backend format unknown

---

### DB-003: Database Path Inconsistency ⚠️ MEDIUM
**Status:** 🔴 OPEN
**Location:** Multiple files

**Issue:**
- `app.py`: Uses `/app/data/dockermate.db`
- `database.py`: Uses `/tmp/dockermate.db`

**Impact:**
Different defaults for production vs dev

---

### DB-004: Session Management Not Using Context Managers ⚠️ LOW
**Status:** 🔴 OPEN
**Location:** Multiple backend files

**Issue:**
Manual `db.close()` calls instead of context managers

**Pattern:**
```python
db = SessionLocal()
try:
    ...
finally:
    db.close()
```

**Better:**
Use context manager or dependency injection

---

### CODE-001: Broad Exception Catching ⚠️ MEDIUM
**Status:** 🔴 OPEN
**Location:** `backend/auth/middleware.py:89-106` and multiple API routes

**Issue:**
Catches generic `Exception` instead of specific exception types

**Impact:**
Hides unexpected errors that should be fixed

**Fix Required:**
Catch specific exception types and let others bubble up

---

### CODE-002: Missing Input Validation in Volume Parsing ⚠️ MEDIUM
**Status:** 🔴 OPEN
**Location:** `backend/api/containers.py:130-142`

**Issue:**
Volume validation only checks structure, not actual path validity

**Impact:**
Could create containers with invalid volume mounts

**Fix Required:**
Add path existence checks, permission checks

---

### CODE-003: Restart Policy Default Mismatch ⚠️ LOW
**Status:** 🔴 OPEN
**Location:** `backend/api/containers.py:398`

**Issue:**
- API default: `'no'`
- Frontend default: `'unless-stopped'`

**Impact:**
User expects different behavior than what's configured

---

### CODE-004: Missing Health Check Endpoint Error Cases ⚠️ MEDIUM
**Status:** 🔴 OPEN
**Location:** `backend/api/containers.py:651-741`

**Issue:**
`get_container_health()` doesn't document all error cases (paused state, just deleted, etc.)

---

### CODE-005: Unused Imports ⚠️ LOW
**Status:** 🔴 OPEN
**Location:** `backend/auth/password_manager.py`

**Issue:**
Possible unused imports (needs verification)

---

### CODE-006: Missing Type Hints ⚠️ LOW
**Status:** 🔴 OPEN
**Location:** Multiple API routes

**Issue:**
Functions like `validate_create_request()` lack return type hints

---

### CONFIG-001: Hard-coded Paths in app.py ⚠️ MEDIUM
**Status:** 🔴 OPEN
**Location:** `app.py:81-82`

**Issue:**
SSL cert path hard-coded to `/app/data/ssl/cert.pem` instead of using config object

**Fix Required:**
Use `Config.SSL_DIR` from config.py

---

### CONFIG-002: Missing Config Validation ⚠️ LOW
**Status:** 🔴 OPEN
**Location:** `config.py`

**Issue:**
No validation that parsed durations are positive

---

### CONFIG-003: SSL Directory Creation Missing ⚠️ LOW
**Status:** 🔴 OPEN
**Location:** `app.py:81-92`

**Issue:**
SSL cert generation assumes `/app/data/ssl/` exists

**Fix Required:**
Add directory creation step

---

### ERROR-001: Inadequate Error Messages to Users ⚠️ MEDIUM
**Status:** 🔴 OPEN
**Location:** `backend/api/containers.py` (multiple)

**Issue:**
Generic "An unexpected error occurred" messages

**Fix Required:**
More specific error types (ValidationError, DockerError, etc.)

---

### ERROR-002: Inconsistent Error Response Format ⚠️ MEDIUM
**Status:** 🔴 OPEN
**Location:** `auth.py`, `containers.py`, `system.py`

**Issue:**
Different response structures:
- `auth.py`: `{"success": False, "error": "..."}`
- `containers.py`: `{"success": False, "error": "...", "error_type": "..."}`

**Fix Required:**
Standardize error response format

---

### ERROR-003: Missing Logging in Container Operations ⚠️ MEDIUM
**Status:** 🔴 OPEN
**Location:** `backend/services/container_manager.py`

**Issue:**
Some operations not logged (deletion, updates, health checks)

---

### ERROR-004: Docker Error Messages Not Exposed ⚠️ LOW
**Status:** 🔴 OPEN
**Location:** `backend/api/containers.py` (multiple)

**Issue:**
Docker SDK errors wrapped with generic messages, losing original error details

---

### DOC-001: API Contract Documentation Incomplete ⚠️ MEDIUM
**Status:** 🔴 OPEN
**Location:** Docstrings in `backend/api/containers.py`

**Issue:**
Response schemas documented but not request body validation rules

---

### DOC-002: Endpoint Path Inconsistency in Docs ⚠️ LOW
**Status:** 🔴 OPEN
**Location:** `backend/api/containers.py:652`

**Issue:**
Docs say `GET /api/containers/<name>/health` but code accepts both name/ID

---

### DOC-003: Missing Setup Instructions for Frontend ⚠️ LOW
**Status:** 🔴 OPEN
**Location:** Frontend configuration

**Issue:**
No documentation on Alpine.js or Tailwind CSS version requirements

---

### DOC-004: Hardware Profile Documentation Scattered ⚠️ LOW
**Status:** 🔴 OPEN
**Location:** Multiple files

**Issue:**
Hardware profiles defined in:
- `config.py` comments
- `host_config.py` module docstring
- `hardware_detector.py` implementation

**Fix Required:**
Single authoritative source

---

### DOC-005: Missing PROJECT_STATUS.MD Tracking Document ⚠️ HIGH
**Status:** ✅ RESOLVED
**Location:** `/PROJECT_STATUS.md`
**Reported:** February 2, 2026
**Resolved:** February 2, 2026

**Issue:**
No centralized project status tracking document exists to show:
- Current project phase and completion status
- Roadmap breakdown by version
- Sprint breakdown within each version
- Sub-task status within sprints
- Integration with KNOWN_ISSUES.md and UI_Issues.md
- Overall progress visualization

**Impact:**
- Difficult to understand where project stands
- No clear view of what's completed vs in-progress vs planned
- Cannot easily plan future work
- Hard to prioritize fixes vs features
- No consolidated view of sprint progress

**Fix Required:**
Create `PROJECT_STATUS.MD` with:
1. Executive summary (current phase, overall completion %)
2. Roadmap structure (v0.1.0 Alpha → v0.5.0 Beta → v1.0.0 Release)
3. Sprint breakdown per version with completion tracking
4. Sub-task status within each sprint
5. Links to KNOWN_ISSUES.md and UI_Issues.md for detailed tracking
6. Completion criteria for each milestone
7. Deferred features and technical debt tracking

---

### SECURITY-001: Session Cookie Security in Development ⚠️ MEDIUM
**Status:** 🔴 OPEN
**Location:** `backend/api/auth.py:171-173`

**Issue:**
Cookie set with `secure=True` unconditionally, even in development

**Impact:**
Browsers reject secure cookies over HTTP in testing mode

**Fix Required:**
```python
secure = not app.config.get('TESTING')
```

---

### SECURITY-002: HTTP Redirect Skipped During Setup ⚠️ MEDIUM
**Status:** 🔴 OPEN
**Location:** `app.py:105-131`

**Issue:**
HTTP redirect skipped during setup phase

**Impact:**
Setup could be exposed over plain HTTP

---

### SECURITY-003: Missing CSRF Token Validation ⚠️ MEDIUM
**Status:** 🔴 OPEN
**Location:** `backend/api/containers.py` (POST/DELETE endpoints)

**Issue:**
No CSRF token validation on API endpoints

**Note:**
README says "SameSite=Strict cookies prevent CSRF" but explicit validation is better

---

### SECURITY-004: Password Reset Workflow Incomplete ✅ RESOLVED
**Status:** ✅ RESOLVED
**Location:** `manage.py`
**Resolved:** February 5, 2026 (Sprint 5 — FIX-002)

**Resolution:** See FEATURE-004 above. CLI-only (no web endpoint) as originally specified.

---

### PERF-001: Health Check Polling Without Backoff ⚠️ MEDIUM
**Status:** 🔴 OPEN
**Location:** `frontend/templates/containers.html:864-915`

**Issue:**
Frontend polls every 2 seconds for 10 attempts without exponential backoff

**Impact:**
Could hammer API if many containers created at once

---

### PERF-002: Auto-refresh Without Debouncing ⚠️ LOW
**Status:** 🔴 OPEN
**Location:** `frontend/templates/containers.html:1379`

**Issue:**
Container list refreshes every 10 seconds regardless of user interaction

**Fix:**
Already checks if modal is open, but could be improved

---

### PERF-003: No Caching in Hardware Profile ⚠️ LOW
**Status:** 🔴 OPEN
**Location:** `backend/api/system.py:73`

**Issue:**
Hardware profile loaded from database on every request

**Fix Required:**
Cache in HostConfig singleton or memory

---

### PERF-004: Database Query in List Filter ⚠️ LOW
**Status:** 🔴 OPEN
**Location:** `backend/api/containers.py:201`

**Issue:**
Port conflict check queries all containers on every request

**Fix Required:**
Index on ports_json or denormalize active ports

---

### TEST-001: Database Initialization Tests Failing ⚠️ MEDIUM
**Status:** 🟡 KNOWN
**Location:** `tests/unit/test_database.py`

**Issue:**
2 failing tests:
- `test_init_db_creates_file`
- `test_init_db_creates_tables`

**Note:**
Documented in `sprint1_known_issues.md` as expected for Sprint 1

**Resolution Plan:**
Sprint 2 completion should resolve

---

### TEST-002: No Integration Tests for API Workflows ⚠️ MEDIUM
**Status:** 🔴 OPEN
**Location:** Test directory structure

**Issue:**
Only unit tests for individual components, no end-to-end workflow tests

**Fix Required:**
Test complete user workflows (create → start → stop → delete)

---

### TEST-003: Mock Docker Client Insufficient ⚠️ LOW
**Status:** 🔴 OPEN
**Location:** Unit tests

**Issue:**
Mocks don't accurately reflect Docker SDK behavior

---

### FEATURE-001: System Health Check ✅ RESOLVED
**Status:** ✅ RESOLVED
**Location:** `backend/api/system.py` — `GET /api/system/health`
**Resolved:** February 3, 2026 (Sprint 3)

**Resolution:**
- Live database connectivity check (`SELECT 1`)
- Docker daemon ping check
- Exited container scan (flags containers worth investigating)
- Capacity warning when container count ≥ 80% of hardware-profile limit
- Returns structured `{ status, checks, warnings }` response used by dashboard health card

---

### FEATURE-002: Sync Endpoint Not Implemented ✅ RESOLVED
**Status:** ✅ RESOLVED
**Location:** `backend/api/containers.py` — `POST /api/containers/sync`
**Resolved:** February 3, 2026 (Sprint 3)

**Resolution:**
- `sync_managed_containers_to_database()` in ContainerManager scans Docker for containers with `com.dockermate.managed=true` label that are missing from the DB and re-adds them with full metadata (ports, volumes, env vars, environment tag)
- `POST /api/containers/sync` API endpoint exposes this
- `docker-entrypoint.sh` calls sync automatically on every container start (non-fatal)
- Redundant "Sync with Docker" UI button removed (auto-refresh + startup sync makes it unnecessary)

---

### FEATURE-003: Container Update Phase 2 Deferred ⚠️ LOW
**Status:** 🔴 OPEN
**Location:** `backend/api/containers.py:247-274`

**Issue:**
Only Phase 1 (labels) supported, full updates deferred to Phase 2/Task 6

**Missing:**
Port changes, volume changes, env var changes

---

### FEATURE-004: Password Reset Script Missing ✅ RESOLVED
**Status:** ✅ RESOLVED
**Location:** `manage.py`
**Resolved:** February 5, 2026 (Sprint 5 — FIX-002)

**Resolution:**
- `python manage.py reset-password` added (must run inside container: `docker exec dockermate-dev python3 /app/manage.py reset-password`)
- `--temp` flag generates a secure random password and sets `force_password_change=True`
- Interactive mode prompts twice, validates password strength via `PasswordManager`
- Lazy imports — runs without Flask app context

---

### FEATURE-007: Health Page Is a Stub + Dashboard Health Card Only Covers Two Domains ✅ RESOLVED
**Status:** ✅ RESOLVED
**Location:** `frontend/templates/health.html`, `frontend/templates/dashboard.html`, `backend/api/system.py`
**Reported:** February 3, 2026 (Sprint 4)
**Resolved:** February 5, 2026 (Sprint 5 — FEAT-019)

**Resolution:**
- `/api/system/health` expanded to 6 check domains: `database`, `docker`, `containers`, `images`, `networks`, `dockermate`. All warnings carry a `domain` tag for grouping.
- Dashboard health card replaced hardcoded two-dot row with dynamic `healthDots` computed property — one coloured dot per check key.
- `/health` page fully implemented: stats row (overall status, warning count, checks passing, last checked), per-domain detail cards with status badges, actionable links (→ View Containers / Images / Networks), Infrastructure card merges docker+database. Auto-refreshes every 10 s.

---

### FEATURE-005: Container List Only Shows DockerMate-Created Containers ✅ RESOLVED
**Status:** ✅ RESOLVED
**Location:** `backend/services/container_manager.py` — `list_all_docker_containers()`
**Resolved:** February 3, 2026 (Sprint 3)

**Resolution:**
- `list_all_docker_containers()` queries Docker daemon for ALL containers
- Cross-references with database to flag managed vs external
- DockerMate's own container shown as external (KISS — protected from actions by disabled buttons/checkboxes)
- Frontend toggle "Show all Docker containers" added to containers page
- External containers: action buttons hidden, checkboxes disabled, excluded from bulk ops
- `com.dockermate.managed` and `com.dockermate.environment` labels stamped on creation for persistence
- `POST /api/containers/sync` endpoint recovers labeled containers missing from DB after reset
- Sync runs automatically on container startup via `docker-entrypoint.sh`

---

### FEATURE-006: Dashboard Page Needs Update ✅ RESOLVED
**Status:** ✅ RESOLVED
**Location:** `frontend/templates/dashboard.html`
**Resolved:** February 3, 2026 (Sprint 3)

**Resolution:**
- Complete dashboard rewrite with Alpine.js `dashboardComponent()`
- Real-time stats: total/running/stopped container counts (includes ALL containers on host)
- Hardware profile card (CPU, RAM, max containers from `/api/system/hardware`)
- Capacity bar with colour thresholds (green → yellow → red at 60%/80%)
- Environment distribution grid
- Auto-refresh polling every 10 seconds
- Quick action links to Containers, Images, Settings

---

## ✅ DESIGN DECISIONS (NOT ISSUES)

### DESIGN-001: API Routes Without Authentication ✅ BY DESIGN
**Status:** ✅ INTENTIONAL (DESIGN-v2.md Section 15.3)
**Locations:** `backend/api/containers.py`, `images.py`, `networks.py`, etc.

**What Was Observed:**
API endpoints have commented-out or missing `@require_auth(api=True)` decorators

**Why This Is Correct:**
DESIGN-v2.md (v2.0.0) implements a **Perimeter Security Model** for home lab environments:
- ✅ UI routes protected with `@require_auth()`
- ✅ API routes unprotected (same-origin trust)
- ✅ Browser same-origin policy prevents external API access
- ✅ Network isolation required (firewall + VLAN)

**Security Model:**
```
Layer 1: Infrastructure (firewall, VLAN)
Layer 2: Transport (HTTPS/TLS)
Layer 3: Perimeter (UI authentication)
Layer 4: Browser (same-origin policy)
```

**Reference:** DESIGN-v2.md lines 1228-1350

---

### DESIGN-002: Login Endpoint Path ✅ BY DESIGN
**Status:** ✅ CORRECT (needs verification)
**Location:** `frontend/templates/login.html`

**What Was Observed:**
Frontend sends POST to `/login` but API is at `/api/auth/login`

**Verification Needed:**
Check if Flask route `/login` exists as a redirect/alias to `/api/auth/login`

---

## ✅ RECENTLY RESOLVED ISSUES

### NETWORK-001: Recommended Subnets Flagged as Oversized ✅ FIXED
**Resolved:** February 4, 2026 (Sprint 4)
**Root Cause:** `_is_oversized()` used `max(container_count * 4, 10)` as the threshold. With 0 containers on a new network, any subnet with >10 usable hosts was flagged oversized. All hardware-recommended subnets (/25=126, /26=62, /27=30) exceed 10.

**Fix:**
- Added early-return guard in `_is_oversized()`: if `container_count == 0` return `False`
- Empty networks are "unused", not "oversized" — the 4× ratio is meaningless with zero containers
- Location: `backend/services/network_manager.py`

---

### UI-001: Start/Stop/Restart Buttons Not Clickable ✅ FIXED
**Resolved:** January 31, 2026
**Root Cause:** Alpine.js x-for loops had invalid keys + actionLoading returned undefined

**Fix:**
- Fixed x-for keys to use index-based unique keys
- Explicitly initialize actionLoading[container.name] = false

---

### UI-002: Port Mappings Display Empty ✅ FIXED
**Resolved:** January 31, 2026
**Root Cause:** Backend didn't parse protocol separately + IPv4/IPv6 duplicates + invalid x-for key

**Fix:**
- Parse protocol from "80/tcp" format
- Deduplicate IPv4/IPv6 bindings
- Fixed x-for key

---

### UI-003: Alpine.js x-for Invalid Keys ✅ FIXED
**Resolved:** January 31, 2026
**Locations:** Lines 118, 133, 143

**Fix:**
Changed all x-for loops to use index-based keys

---

### UI-004: Port Duplication (IPv4/IPv6) ✅ FIXED
**Resolved:** January 31, 2026
**Location:** `backend/services/container_manager.py:539-564`

**Fix:**
Added seen_ports set to deduplicate

---

## 📋 Issue Tracking

### How to Use This Document

1. **When starting work on a task/sprint:**
   - Review relevant issues
   - Mark issues as "in progress" if working on them

2. **When fixing an issue:**
   - Update status to ✅ FIXED
   - Add resolution date
   - Move to "Recently Resolved" section

3. **When discovering new issues:**
   - Add to appropriate category
   - Assign priority (HIGH/MEDIUM/LOW)
   - Add location and impact

### Status Legend

- 🔴 OPEN - Not yet addressed
- 🟡 KNOWN - Acknowledged, documented, planned for future
- 🟢 IN PROGRESS - Currently being worked on
- ✅ FIXED - Resolved and tested

---

## 🎯 Quick Wins (Easy Fixes)

These can be fixed quickly with high impact:

1. ✅ ~~Fix login endpoint URL~~ → **PENDING: Change `/login` to `/api/auth/login`**
2. ✅ ~~Uncomment authentication decorators~~ → **PENDING: Remove comments or implement blueprint auth**
3. Add `if (!response.ok)` check in login error handling
4. Fix restart policy default mismatch

---

## 📊 Progress Tracking

**Sprint 1:**
- Issues Identified: 2
- Issues Resolved: 2 (documented as expected)
- Issues Remaining: 0

**Sprint 2:**
- Issues Identified: 53
- Issues Resolved: 4 (UI fixes)
- Issues Remaining: 49

**Sprint 3:**
- Issues Resolved: 4 (FEATURE-005, FEATURE-006, FEATURE-002, FEATURE-001)
- New issues identified: 0
- Issues Remaining: 44

**Sprint 4:**
- Issues Resolved: 1 (NETWORK-001)
- New issues identified: 1 (FEATURE-007)
- Issues Remaining: 44

**Sprint 5 (current):**
- Issues Resolved: 6 (FEATURE-007, FEATURE-004, SECURITY-004, UI-003, UI-004, UI-005, UI-006)
- New issues identified: 4 (UI-003 through UI-006 — all resolved same session)
- Issues Remaining: 38

---

**Last Scan:** February 5, 2026
**Next Review:** Sprint 5 completion
