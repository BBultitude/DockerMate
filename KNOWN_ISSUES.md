# DockerMate - Known Issues Tracker

**Created:** January 31, 2026
**Last Updated:** January 31, 2026 (Sprint 2 Task 7 completed)
**Current Sprint:** Sprint 3 (Container UI)

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
| **TOTAL** | **0** | **0** | **32** | **11** | **43** |

**Recently Resolved:** 6 issues (Sprint 2 Task 7: port validation, health check polling, login endpoint, restart policy, memory conversion docs)
**Reclassified as Design:** 2 issues (API auth, perimeter security) - intentional per DESIGN-v2.md

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

### SECURITY-004: Password Reset Workflow Incomplete ⚠️ MEDIUM
**Status:** 🔴 OPEN
**Location:** Documentation mentions password reset

**Issue:**
README shows `reset_password.py` but not implemented in codebase

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

### FEATURE-001: System Health Check Not Implemented ⚠️ MEDIUM
**Status:** 🔴 OPEN
**Location:** `backend/api/system.py:154-159`

**Issue:**
Health check endpoint returns hardcoded "ok"

**Missing:**
- Database connectivity check
- Docker daemon health check
- Disk space check

**Comment:**
"TODO: Add actual health checks in future sprint"

---

### FEATURE-002: Sync Endpoint Not Implemented ⚠️ MEDIUM
**Status:** 🔴 OPEN
**Location:** `frontend/templates/containers.html:793-805`

**Issue:**
Sync button calls `loadContainers()` instead of actual sync endpoint

**Missing:**
Reconcile database state with Docker daemon

---

### FEATURE-003: Container Update Phase 2 Deferred ⚠️ LOW
**Status:** 🔴 OPEN
**Location:** `backend/api/containers.py:247-274`

**Issue:**
Only Phase 1 (labels) supported, full updates deferred to Phase 2/Task 6

**Missing:**
Port changes, volume changes, env var changes

---

### FEATURE-004: Password Reset Script Missing ⚠️ MEDIUM
**Status:** 🔴 OPEN
**Location:** README references

**Issue:**
Referenced in documentation but not in codebase

**Note:**
`seed_test_user.py` exists as test helper

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

---

**Last Scan:** January 31, 2026
**Next Review:** Sprint 2 completion
