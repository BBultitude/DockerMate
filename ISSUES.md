# DockerMate - Issues Tracker

**Version:** v1.0.0-rc1
**Last Updated:** February 7, 2026
**Status:** RC1 deployed and testing - 1 known deployment issue (manual restart required)

This document consolidates all known issues, UI fixes, and feature tracking for DockerMate. Issues are categorized by priority and type, with comprehensive resolution tracking.

---

## Known Issues - RC1 Deployment

### DEPLOY-001: Manual Container Restart Required After First-Time Setup
**Status:** KNOWN ISSUE (RC1)
**Priority:** MEDIUM
**Affects:** First-time deployment only

**Issue:**
After completing the `/setup` wizard and creating the admin password, the container continues running in HTTP mode. The app only checks for the `setup_complete` file at startup, so it doesn't automatically switch to HTTPS mode after setup completes.

**Symptoms:**
- Setup page works correctly (HTTP)
- After setup, browser redirects to `/login`
- Server sends 301 redirect to HTTPS
- Browser tries HTTPS but gets SSL handshake errors (400 Bad Request)
- Logs show: `"GET /login HTTP/1.1" 301` followed by SSL errors

**Workaround:**
After completing setup, manually restart the container:
```bash
docker restart dockermate
```
Then access `https://your-ip:5000` to login.

**Root Cause:**
The `if __name__ == '__main__'` block in `app.py` checks for `setup_complete` only once at startup. After setup creates the file, the Flask process continues running in HTTP mode until restarted.

**Potential Fixes (post-RC1):**
1. Add instruction in setup completion message: "Setup complete! Restart container to enable HTTPS"
2. Use Flask-Restart or similar to auto-restart after setup
3. Use a supervisor process (gunicorn/uwsgi) that detects file changes
4. Accept HTTP for first login after setup, then enforce HTTPS

**Decision:** Document as known issue for RC1. Fix in v1.0.1 or v1.1.0.

---

## Summary Statistics

| Category | Critical | High | Medium | Low | Total |
|----------|----------|------|--------|-----|-------|
| **Deployment/RC1** | **0** | **0** | **1** | **0** | **1** |
| Authentication/Security | 0 | 0 | 1 | 1 | 2 |
| Frontend Issues | 0 | 0 | 1 | 1 | 2 |
| Backend API | 0 | 0 | 4 | 0 | 4 |
| Database/Models | 0 | 0 | 3 | 1 | 4 |
| Code Quality | 0 | 0 | 5 | 1 | 6 |
| Error Handling | 0 | 0 | 4 | 0 | 4 |
| Documentation | 0 | 0 | 1 | 3 | 4 |
| Performance | 0 | 0 | 1 | 3 | 4 |
| Testing | 0 | 0 | 2 | 1 | 3 |
| UI Issues | 0 | 0 | 0 | 0 | 0 |
| **TOTAL OPEN** | **0** | **0** | **22** | **11** | **33** |

**Total Resolved:** 28 issues (Sprint 1-5)
**Design Decisions (Not Issues):** 2 items
**RC1 Known Issues:** 1 (manual restart after setup)
**Status:** RC1 deployed to Raspberry Pi. 1 known deployment issue (workaround documented). No blockers for live testing.

---

## Recently Resolved (Sprint 5)

### Sprint 5 Completions
**Resolved:** February 2-6, 2026

**Major Features Completed:**
- FEAT-012: Import unmanaged containers
- FEAT-013: Retag & redeploy workflow
- FEAT-017: Adopt/release networks
- FEAT-019: Full health monitoring page (6 domains)
- Volume management (create, delete, inspect, prune)
- Stack management (deploy, scale, stop, remove)
- Docker Compose file converter
- Storage path configuration system

**Security & Production:**
- SECURITY-001: Session cookie security in production mode
- SECURITY-003: CSRF token validation (21 mutation operations across 5 templates)
- Production mode implementation with SSL/TLS enforcement
- Rate limiting on authentication endpoints

**Configuration & Infrastructure:**
- CONFIG-001: Hard-coded SSL paths now configurable via `DOCKERMATE_SSL_DIR`
- CONFIG-003: SSL directory creation in docker-entrypoint.sh
- Storage path validation and configuration

**UI Fixes (All 8 Issues):**
- UI-001: Start/Stop/Restart buttons not clickable
- UI-002: Port mappings display empty
- UI-003: Alpine.js x-for invalid keys
- UI-004: Port duplication (IPv4/IPv6)
- UI-005: Environment variables missing from details modal
- UI-006: Volume mounts displayed as `[object Object]`
- UI-007: Container refresh flicker (scroll position preserved)
- UI-008: Managed/unmanaged filter implementation

### Previously Resolved (Sprints 1-4)

**Sprint 4:**
- NETWORK-001: Recommended subnets flagged as oversized
- Full network management system
- Topology visualization and container-network connections

**Sprint 3:**
- FEATURE-001: System health check endpoint
- FEATURE-002: Sync endpoint implementation
- FEATURE-005: Show all Docker containers (managed vs external)
- FEATURE-006: Dashboard page complete overhaul
- Image management system with update/rollback
- Advanced log viewer with filtering

**Sprint 2:**
- FRONTEND-001: Form validation translation (ports, volumes)
- FRONTEND-002: Health check polling with exponential backoff
- Container creation and management features

**Sprint 1:**
- Initial infrastructure and database setup
- Basic container operations

---

## UI Issues

### ALL UI ISSUES RESOLVED

All 8 identified UI issues from the original tracker have been resolved during Sprint 2-5 development.

### UI-001: Start/Stop/Restart Buttons Not Clickable
**Status:** RESOLVED (January 31, 2026)
**Location:** `frontend/templates/containers.html`

**Root Cause:**
1. Alpine.js x-for loops had invalid `:key` attributes causing component crash
2. `actionLoading` object returned `undefined` for container names, which Alpine treated as disabled

**Resolution:**
- Fixed x-for keys to use unique index-based keys
- Explicitly initialize `actionLoading[container.name] = false` in `loadContainers()`
- Changed cleanup from `delete actionLoading[id]` to `actionLoading[id] = false` for reactivity

---

### UI-002: Port Mappings Display Empty
**Status:** RESOLVED (January 31, 2026)
**Location:** `backend/services/container_manager.py`, `frontend/templates/containers.html`

**Root Causes:**
1. Backend wasn't parsing protocol from Docker's port format (`"80/tcp"`)
2. Docker returns both IPv4 and IPv6 bindings causing duplicate entries
3. Alpine.js x-for loop had invalid key causing render failure

**Resolution:**
- Backend now splits `"80/tcp"` into `port="80"` and `protocol="tcp"` separately
- Added deduplication using `seen_ports` set to prevent IPv4/IPv6 duplicates
- Fixed x-for loop to use index-based key

---

### UI-003: Alpine.js x-for Invalid Keys
**Status:** RESOLVED (January 31, 2026)
**Location:** `frontend/templates/containers.html` (lines 118, 133, 143)

**Resolution:**
Changed all x-for loops to use index-based keys for proper rendering.

---

### UI-004: Port Duplication (IPv4/IPv6)
**Status:** RESOLVED (January 31, 2026)
**Location:** `backend/services/container_manager.py` (lines 539-564)

**Resolution:**
Added `seen_ports` set to deduplicate IPv4/IPv6 bindings.

---

### UI-005: Environment Variables Missing From Details Modal
**Status:** RESOLVED (February 5, 2026)
**Location:** `frontend/templates/containers.html`

**Root Cause:**
`showDetails(container)` passed list view data which doesn't include env_vars, volumes, cpu_limit, or memory_limit. These fields are only populated by the single-container endpoint.

**Resolution:**
- Made `showDetails()` async
- Sets modal immediately with list data (instant feedback)
- For managed containers, fetches full data via `GET /api/containers/<id>` and replaces modal content
- Unmanaged containers keep using list data with conditional field display

---

### UI-006: Volume Mounts Displayed as `[object Object]`
**Status:** RESOLVED (February 5, 2026)
**Location:** `frontend/templates/containers.html`

**Root Cause:**
Backend returns volume mount objects `{source, destination, mode, type, rw}` but template stringified the object directly.

**Resolution:**
Both detail modal and Docker command generator now format volumes as standard Docker `source:destination:mode` string:
- Detail modal: `x-text="volume.source + ':' + volume.destination + ':' + volume.mode"`
- Docker command: `` `-v ${volume.source}:${volume.destination}:${volume.mode}` ``

---

### UI-007: Container Refresh Flicker
**Status:** PARTIAL (February 6, 2026)
**Location:** `frontend/templates/containers.html`

**Root Cause:**
`loadContainers()` replaces entire array every 10s causing full re-render, scroll position lost, and visual flicker.

**Resolution:**
- Implemented intelligent merge in `loadContainers()` and `applyFilters()`
- Scroll position now preserved by comparing containers by `container_id`
- Only changed items updated in place
- Filters reapplied without losing scroll position

**Remaining:**
Visual flicker still present (DOM elements briefly flash during update). Deferred to v1.1 as it requires deeper Alpine.js optimization (keyed rendering strategy or virtual DOM approach).

---

### UI-008: Managed/Unmanaged Filter
**Status:** RESOLVED (February 6, 2026)
**Location:** `frontend/templates/containers.html`

**Root Cause:**
"Show all Docker containers" checkbox was outdated after FEAT-012 (import) and FEAT-017 (adopt) made managed/external distinction more important.

**Resolution:**
- Replaced "Show all" checkbox with "Managed Status" dropdown filter
- Options: All / Managed / External
- Default to "All" (preserves existing behavior)
- Expanded filter grid to 5 columns
- Added `filters.managedStatus` to filtering logic
- MANAGED/EXTERNAL badges now always visible
- URL persistence works with new filter

---

### UI-009: Rollback Button Clickable With No History
**Status:** RESOLVED (February 5, 2026)
**Location:** `backend/services/container_manager.py`, `frontend/templates/containers.html`

**Root Cause:**
Rollback button had no visibility/disabled condition tied to update history existence.

**Resolution:**
- Backend: `list_all_docker_containers()` runs bulk query against `UpdateHistory` and sets `rollback_available: true/false` flag
- Frontend: Button `:disabled` includes `|| !container.rollback_available`
- Tooltip changes to "No previous version to roll back to" when disabled
- Tailwind disabled classes dim the button

---

### UI-010: Release/Delete Buttons Hidden After Adopting DockerMate Networks
**Status:** RESOLVED (February 5, 2026)
**Location:** `frontend/templates/networks.html`, `backend/services/network_manager.py`

**Root Cause:**
Button `x-show` conditions used `!network.name.toLowerCase().includes('dockermate')` which matched any network with "dockermate" in the name, including user-adopted ones like `dockermate_dockermate-net`.

**Resolution:**
- Frontend: Replaced substring check with explicit default-network allowlist: `!['bridge','host','none'].includes(network.name)`
- Backend: Removed redundant `'dockermate' in net.name.lower()` guard from `delete_network()`
- "Containers attached" check provides the real safety net

---

## Medium Priority Issues

### AUTH-001: Password Validation Not Fully NIST Compliant
**Status:** OPEN
**Priority:** MEDIUM
**Location:** `backend/auth/password_manager.py:197-300`

**Issue:**
Current password validation only performs basic pattern checks and doesn't fully comply with NIST SP 800-63B recommendations. The validation allows weak passwords like "TestPassword123!" which contain common dictionary words with simple modifications.

**Current Validation:**
- Minimum 12 characters ✓
- Uppercase, lowercase, digits required ✓
- Blocks common words ONLY when used alone (e.g., "password123") ✓
- Basic sequential pattern detection ✓

**Missing NIST Requirements:**
- No check against known breached password databases (e.g., Have I Been Pwned)
- Doesn't detect dictionary words with modifications (e.g., "TestPassword")
- No sophisticated pattern detection for keyboard patterns
- Should allow spaces and all printable characters per NIST
- Feedback could be more specific about why passwords are rejected

**Fix Required:**
1. Integrate with breached password database (zxcvbn library or HIBP API)
2. Enhance dictionary word detection to catch modified words
3. Improve pattern detection (leet speak, keyboard walks)
4. Follow NIST SP 800-63B Section 5.1.1 more closely

**Workaround:**
Users can still set reasonably strong passwords by avoiding common words entirely and using random character combinations or passphrases.

**Note:**
Deferred to v1.1 - requires third-party library integration and testing.

---

### FRONTEND-003: Login Error Handling Incomplete
**Status:** OPEN
**Priority:** MEDIUM
**Location:** `frontend/templates/login.html:94-105`

**Issue:**
Frontend assumes successful JSON response but doesn't handle HTTP errors. If endpoint returns 404 or 500, `response.json()` will fail.

**Fix Required:**
```javascript
if (!response.ok) {
    // handle error before parsing JSON
}
```

---

### API-001: Port Conflict Detection JSON Parsing
**Status:** OPEN
**Priority:** MEDIUM
**Location:** `backend/api/containers.py:216-230`

**Issue:**
JSON parsing in conflict detection uses bare `json.loads()` without validation. Malformed JSON in database could crash server.

**Fix Required:**
Use schema validation or handle ValueError more specifically.

---

### API-002: Memory Limit Conversion Inconsistency
**Status:** OPEN
**Priority:** MEDIUM
**Location:** `frontend/templates/containers.html:1245`

**Issue:**
Frontend converts MB to bytes (`* 1024 * 1024`) but backend expects bytes directly. Unclear if API or frontend is wrong - potential memory limit mismatch.

**Fix Required:**
Clarify API documentation and ensure consistent conversion.

---

### DB-001: Ports JSON Storage Format Not Documented
**Status:** OPEN
**Priority:** MEDIUM
**Location:** `backend/models/container.py:99-100`

**Issue:**
Ports stored as JSON string but format not clearly documented. Parsing assumes specific structure without validation.

**Impact:**
Could cause issues if format changes or becomes corrupted.

---

### DB-002: Environment Variable Storage Format Unclear
**Status:** OPEN
**Priority:** MEDIUM
**Location:** `backend/models/container.py`

**Issue:**
`env_vars_json` storage format not documented - unclear if array or dict. Frontend expects array format but backend format unknown.

---

### DB-003: Database Path Inconsistency
**Status:** OPEN
**Priority:** MEDIUM
**Location:** Multiple files

**Issue:**
- `app.py`: Uses `/app/data/dockermate.db`
- `database.py`: Uses `/tmp/dockermate.db`

**Impact:**
Different defaults for production vs dev environments.

---

### CODE-001: Broad Exception Catching
**Status:** OPEN
**Priority:** MEDIUM
**Location:** `backend/auth/middleware.py:89-106` and multiple API routes

**Issue:**
Catches generic `Exception` instead of specific exception types, hiding unexpected errors that should be fixed.

**Fix Required:**
Catch specific exception types and let others bubble up.

---

### CODE-002: Missing Input Validation in Volume Parsing
**Status:** OPEN
**Priority:** MEDIUM
**Location:** `backend/api/containers.py:130-142`

**Issue:**
Volume validation only checks structure, not actual path validity. Could create containers with invalid volume mounts.

**Fix Required:**
Add path existence checks, permission checks.

---

### CODE-004: Missing Health Check Endpoint Error Cases
**Status:** OPEN
**Priority:** MEDIUM
**Location:** `backend/api/containers.py:651-741`

**Issue:**
`get_container_health()` doesn't document all error cases (paused state, just deleted, etc.).

---

### ERROR-001: Inadequate Error Messages to Users
**Status:** OPEN
**Priority:** MEDIUM
**Location:** `backend/api/containers.py` (multiple)

**Issue:**
Generic "An unexpected error occurred" messages don't help users understand what went wrong.

**Fix Required:**
More specific error types (ValidationError, DockerError, etc.).

---

### ERROR-002: Inconsistent Error Response Format
**Status:** OPEN
**Priority:** MEDIUM
**Location:** `auth.py`, `containers.py`, `system.py`

**Issue:**
Different response structures:
- `auth.py`: `{"success": False, "error": "..."}`
- `containers.py`: `{"success": False, "error": "...", "error_type": "..."}`

**Fix Required:**
Standardize error response format across all endpoints.

---

### ERROR-003: Missing Logging in Container Operations
**Status:** OPEN
**Priority:** MEDIUM
**Location:** `backend/services/container_manager.py`

**Issue:**
Some operations not logged (deletion, updates, health checks).

---

### DOC-001: API Contract Documentation Incomplete
**Status:** OPEN
**Priority:** MEDIUM
**Location:** Docstrings in `backend/api/containers.py`

**Issue:**
Response schemas documented but not request body validation rules.

---

### PERF-001: Health Check Polling Without Backoff
**Status:** OPEN
**Priority:** MEDIUM
**Location:** `frontend/templates/containers.html:864-915`

**Issue:**
Frontend polls every 2 seconds for 10 attempts without exponential backoff. Could hammer API if many containers created at once.

**Note:**
Container list polling already has exponential backoff implemented.

---

### TEST-001: Database Initialization Tests Failing
**Status:** KNOWN
**Priority:** MEDIUM
**Location:** `tests/unit/test_database.py`

**Issue:**
2 failing tests:
- `test_init_db_creates_file`
- `test_init_db_creates_tables`

**Note:**
Documented in `sprint1_known_issues.md` as expected for Sprint 1.

---

### TEST-002: No Integration Tests for API Workflows
**Status:** OPEN
**Priority:** MEDIUM
**Location:** Test directory structure

**Issue:**
Only unit tests for individual components, no end-to-end workflow tests.

**Fix Required:**
Test complete user workflows (create → start → stop → delete).

---

## Low Priority Issues

### FRONTEND-004: Responsive Design Gap
**Status:** OPEN
**Priority:** LOW
**Location:** `frontend/templates/containers.html:168`

**Issue:**
Create modal has `max-h-[90vh]` but no min-height guarantee. Modal might be cut off on small screens.

---

### API-003: Empty JSON Body Handling
**Status:** OPEN
**Priority:** LOW
**Location:** `backend/api/containers.py:377-383`

**Issue:**
`request.get_json(force=True)` can raise exceptions not caught.

**Fix Required:**
Use `silent=True` or `force=False` with explicit error handling.

---

### API-004: Container ID Lookup Ambiguity
**Status:** OPEN
**Priority:** LOW
**Location:** `backend/api/containers.py` (multiple endpoints)

**Issue:**
Endpoints accept "container_id" that could be name or ID, not consistently documented.

**Impact:**
API documentation confusion.

---

### DB-004: Session Management Not Using Context Managers
**Status:** OPEN
**Priority:** LOW
**Location:** Multiple backend files

**Issue:**
Manual `db.close()` calls instead of context managers.

**Current Pattern:**
```python
db = SessionLocal()
try:
    ...
finally:
    db.close()
```

**Better Approach:**
Use context manager or dependency injection.

---

### CODE-003: Restart Policy Default Mismatch
**Status:** OPEN
**Priority:** LOW
**Location:** `backend/api/containers.py:398`

**Issue:**
- API default: `'no'`
- Frontend default: `'unless-stopped'`

**Impact:**
User expects different behavior than what's configured.

---

### CODE-005: Unused Imports
**Status:** OPEN
**Priority:** LOW
**Location:** `backend/auth/password_manager.py`

**Issue:**
Possible unused imports (needs verification).

---

### CODE-006: Missing Type Hints
**Status:** OPEN
**Priority:** LOW
**Location:** Multiple API routes

**Issue:**
Functions like `validate_create_request()` lack return type hints.

---

### CONFIG-002: Missing Config Validation
**Status:** OPEN
**Priority:** LOW
**Location:** `config.py`

**Issue:**
No validation that parsed durations are positive (non-critical edge case).

---

### ERROR-004: Docker Error Messages Not Exposed
**Status:** OPEN
**Priority:** LOW
**Location:** `backend/api/containers.py` (multiple)

**Issue:**
Docker SDK errors wrapped with generic messages, losing original error details.

---

### DOC-002: Endpoint Path Inconsistency in Docs
**Status:** OPEN
**Priority:** LOW
**Location:** `backend/api/containers.py:652`

**Issue:**
Docs say `GET /api/containers/<name>/health` but code accepts both name/ID.

---

### DOC-003: Missing Setup Instructions for Frontend
**Status:** OPEN
**Priority:** LOW
**Location:** Frontend configuration

**Issue:**
No documentation on Alpine.js or Tailwind CSS version requirements.

---

### DOC-004: Hardware Profile Documentation Scattered
**Status:** OPEN
**Priority:** LOW
**Location:** Multiple files

**Issue:**
Hardware profiles defined in:
- `config.py` comments
- `host_config.py` module docstring
- `hardware_detector.py` implementation

**Fix Required:**
Single authoritative source.

---

### SECURITY-002: Content Security Policy (CSP) Headers
**Status:** OPEN (Optional for v1.1)
**Priority:** LOW
**Location:** `app.py` response headers

**Issue:**
No CSP headers configured for defense-in-depth.

**Impact:**
Low - Perimeter security model (DESIGN-v2.md) already provides adequate protection.

**Note:**
Deferred to v1.1 as optional enhancement. Alpine.js/Tailwind/Chart.js from CDN already whitelisted for functionality.

---

### PERF-002: Auto-refresh Without Debouncing
**Status:** OPEN
**Priority:** LOW
**Location:** `frontend/templates/containers.html:1379`

**Issue:**
Container list refreshes every 10 seconds regardless of user interaction.

**Fix:**
Already checks if modal is open, but could be improved.

---

### PERF-003: No Caching in Hardware Profile
**Status:** OPEN
**Priority:** LOW
**Location:** `backend/api/system.py:73`

**Issue:**
Hardware profile loaded from database on every request.

**Fix Required:**
Cache in HostConfig singleton or memory.

---

### PERF-004: Database Query in List Filter
**Status:** OPEN
**Priority:** LOW
**Location:** `backend/api/containers.py:201`

**Issue:**
Port conflict check queries all containers on every request.

**Fix Required:**
Index on `ports_json` or denormalize active ports.

---

### TEST-003: Mock Docker Client Insufficient
**Status:** OPEN
**Priority:** LOW
**Location:** Unit tests

**Issue:**
Mocks don't accurately reflect Docker SDK behavior.

---

## Design Decisions (Not Issues)

These are intentional design choices per DESIGN-v2.md, not bugs to fix.

### DESIGN-001: API Routes Without Authentication
**Status:** BY DESIGN (DESIGN-v2.md Section 15.3)
**Location:** `backend/api/containers.py`, `images.py`, `networks.py`, etc.

**What Was Observed:**
API endpoints have commented-out or missing `@require_auth(api=True)` decorators.

**Why This Is Correct:**
DESIGN-v2.md (v2.0.0) implements a **Perimeter Security Model** for home lab environments:
- UI routes protected with `@require_auth()`
- API routes unprotected (same-origin trust)
- Browser same-origin policy prevents external API access
- Network isolation required (firewall + VLAN)

**Security Model:**
```
Layer 1: Infrastructure (firewall, VLAN)
Layer 2: Transport (HTTPS/TLS)
Layer 3: Perimeter (UI authentication)
Layer 4: Browser (same-origin policy)
```

**Reference:** DESIGN-v2.md lines 1228-1350

---

### DESIGN-002: Login Endpoint Path
**Status:** CORRECT (verified)
**Location:** `frontend/templates/login.html`

**What Was Observed:**
Frontend sends POST to `/login` but API is at `/api/auth/login`.

**Verification:**
Flask route `/login` exists as the correct endpoint per application structure.

---

## Feature Tracking

### FEATURE-003: Container Full Reconfigure Modal
**Status:** ACCEPTABLE (Workaround available)
**Priority:** LOW
**Location:** Container management workflow

**Issue:**
No single modal to change all container settings (ports, volumes, env vars, etc.).

**Workaround:**
- FEAT-013 (Retag & Redeploy) handles image version changes
- For full config changes: delete container and recreate with new settings
- Configuration is preserved in database for reference

**Note:**
Deferred to v1.1 - current workflow is adequate for v1.0.

---

## Progress Tracking

### Sprint Summary

**Sprint 1:**
- Issues Identified: 2
- Issues Resolved: 2
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

**Sprint 5:**
- Issues Resolved: 20+ (All Sprint 5 tasks, SECURITY-001, SECURITY-003, CONFIG-001, CONFIG-003, all UI bugs)
- Issues Remaining: 31 (all Medium/Low priority)

**Current Status (v1.0.0-rc1):**
- Total Open Issues: 31
- Critical/High Priority: 0
- Medium Priority: 20
- Low Priority: 11
- No blockers for v1.0.0 release

---

## Issue Tracking Guide

### How to Use This Document

1. **When starting work on a task/sprint:**
   - Review relevant issues
   - Mark issues as "in progress" if working on them

2. **When fixing an issue:**
   - Update status to RESOLVED
   - Add resolution date
   - Document the fix applied
   - Move to "Recently Resolved" section

3. **When discovering new issues:**
   - Add to appropriate category
   - Assign priority (HIGH/MEDIUM/LOW)
   - Add location and impact
   - Reference related issues if applicable

### Status Legend

- OPEN - Not yet addressed
- KNOWN - Acknowledged, documented, planned for future
- IN PROGRESS - Currently being worked on
- RESOLVED - Fixed and tested
- BY DESIGN - Intentional behavior, not a bug

### Priority Definitions

- **CRITICAL:** Prevents application from running or causes data loss
- **HIGH:** Significant functionality broken or security vulnerability
- **MEDIUM:** Feature incomplete or buggy but workarounds exist
- **LOW:** Minor inconvenience, cosmetic issue, or nice-to-have improvement

---

## Quick Wins (Easy Fixes)

These can be fixed quickly with high impact:

1. Add `if (!response.ok)` check in login error handling (FRONTEND-003)
2. Fix restart policy default mismatch (CODE-003)
3. Standardize error response format across endpoints (ERROR-002)
4. Add Docker error message passthrough (ERROR-004)
5. Document port and env_vars JSON storage formats (DB-001, DB-002)

---

**Last Updated:** February 6, 2026
**Version:** v1.0.0-rc1
**Next Review:** v1.1 planning
**Status:** Ready for v1.0.0 release
