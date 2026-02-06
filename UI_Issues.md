# UI Issues - DockerMate

## ✅ RESOLVED ISSUES

### Issue 1: Buttons Not Clickable ✅ FIXED
**Status:** RESOLVED
**Reported:** Start/Stop/Restart buttons exist but not clickable and don't respond to clicks. Details button does.

**Root Cause:**
1. Alpine.js x-for loops had invalid `:key` attributes causing component crash
2. `actionLoading` object returned `undefined` for container names, which Alpine treated as disabled

**Fix Applied:**
- Fixed x-for keys to use unique index-based keys: `:key="\`port-${index}\`"`
- Explicitly initialize `actionLoading[container.name] = false` in `loadContainers()`
- Changed cleanup from `delete actionLoading[id]` to `actionLoading[id] = false` for reactivity

**Files Modified:**
- `frontend/templates/containers.html` (lines 118, 133, 143, 774-776, 862)

---

### Issue 2: Port Mappings Display ✅ FIXED
**Status:** RESOLVED
**Reported:** Port Mapping displaying nothing in details Modal

**Root Causes:**
1. Backend wasn't parsing protocol from Docker's port format (`"80/tcp"`)
2. Docker returns both IPv4 and IPv6 bindings causing duplicate entries
3. Alpine.js x-for loop had invalid key causing render failure

**Fix Applied:**
- Backend now splits `"80/tcp"` into `port="80"` and `protocol="tcp"` separately
- Added deduplication using `seen_ports` set to prevent IPv4/IPv6 duplicates
- Fixed x-for loop to use index-based key: `:key="\`port-${index}\`"`

**Files Modified:**
- `backend/services/container_manager.py` (lines 539-564)
- `frontend/templates/containers.html` (line 118)

---

---

### Issue 3: Rollback Button Clickable With No History ✅ FIXED
**Status:** RESOLVED
**Reported:** February 5, 2026 (Sprint 5)

**Root Cause:**
Rollback button had no visibility or disabled condition tied to whether update history existed. Clicking it always hit the backend, which returned a 404 toast — poor UX.

**Fix Applied:**
- Backend: `list_all_docker_containers()` now runs a single bulk query against `UpdateHistory` (status='success', distinct container_name) and sets `rollback_available: true/false` on each managed container. No N+1 queries.
- Frontend: Button `:disabled` includes `|| !container.rollback_available`. Tooltip changes to "No previous version to roll back to" when disabled. Tailwind disabled classes dim the button (`bg-slate-700 text-slate-500`).

**Files Modified:**
- `backend/services/container_manager.py` (bulk query + flag)
- `frontend/templates/containers.html` (button disabled + title + styling)

---

### Issue 4: Release/Delete Buttons Hidden After Adopting `dockermate_dockermate-net` ✅ FIXED
**Status:** RESOLVED
**Reported:** February 5, 2026 (Sprint 5)

**Root Cause:**
Both Release and Delete button `x-show` conditions used `!network.name.toLowerCase().includes('dockermate')` to protect DockerMate's own compose network. This blanket-matched any network with "dockermate" anywhere in the name — including user-adopted ones like `dockermate_dockermate-net`. The backend `delete_network()` had the same overly broad check.

**Fix Applied:**
- Frontend: Replaced the substring check with an explicit default-network allowlist: `!['bridge','host','none'].includes(network.name)`. Release and Delete are now visible for all non-default networks.
- Backend: Removed the redundant `'dockermate' in net.name.lower()` guard from `delete_network()`. The existing "containers attached" check (which fires for any network with active containers, including DockerMate's own) is the real safety net.

**Files Modified:**
- `frontend/templates/networks.html` (Release + Delete x-show conditions)
- `backend/services/network_manager.py` (delete_network guard removed)

---

### Issue 5: Environment Variables Missing From Container Details Modal ✅ FIXED
**Status:** RESOLVED
**Reported:** February 5, 2026 (Sprint 5)

**Root Cause:**
`showDetails(container)` passed the container object from the list view directly into the modal. The list endpoint (`list_all_docker_containers`) does not include `env_vars`, `volumes`, `cpu_limit`, or `memory_limit` — those fields are only populated by `_sync_database_state()`, which is called by the single-container endpoint (`GET /api/containers/<id>`).

**Fix Applied:**
- `showDetails()` made async. It sets the modal immediately with list data (instant feedback), then for managed containers fetches `GET /api/containers/<container_id>` and replaces the modal data with the full response. Unmanaged containers keep using list data; the env_vars section is already conditionally hidden when the field is absent.

**Files Modified:**
- `frontend/templates/containers.html` (showDetails method)

---

### Issue 6: Volume Mounts Displayed as `[object Object]` ✅ FIXED
**Status:** RESOLVED
**Reported:** February 5, 2026 (Sprint 5)

**Root Cause:**
Backend returns each volume mount as an object `{source, destination, mode, type, rw}`. Two places in the template stringified the object directly instead of reading its fields:
1. Detail modal: `x-text="volume"` → renders as `[object Object]`
2. Docker command generator: `` `-v ${volume}` `` → same

**Fix Applied:**
Both spots now format the volume as the standard Docker `source:destination:mode` string:
- Detail modal: `x-text="volume.source + ':' + volume.destination + ':' + volume.mode"`
- Docker command: `` `-v ${volume.source}:${volume.destination}:${volume.mode}` ``

**Files Modified:**
- `frontend/templates/containers.html` (detail modal x-text + generateDockerCommand)

---

---

### Issue 7: Container Refresh Flicker ⚠️ PARTIAL
**Status:** PARTIAL (Scroll fixed, visual flicker deferred)
**Reported:** February 6, 2026 (Sprint 5 Phase 1)

**Root Cause:**
`loadContainers()` replaces entire array every 10s causing full re-render, scroll position lost, and visual flicker.

**Fix Applied:**
- Implemented intelligent merge in `loadContainers()` and `applyFilters()`
- Scroll position now preserved by comparing old vs new containers by `container_id`
- Only changed items updated in place
- Filters reapplied without losing scroll position

**Remaining Issue:**
Visual flicker still present (DOM elements briefly flash during update). Deferred to later sprint as it requires deeper Alpine.js optimization (keyed rendering strategy or virtual DOM approach).

**Files Modified:**
- `frontend/templates/containers.html` (loadContainers, applyFilters methods)

---

### Issue 8: Managed/Unmanaged Filter ✅ FIXED
**Status:** RESOLVED
**Reported:** February 6, 2026 (Sprint 5 Phase 1)

**Root Cause:**
"Show all Docker containers" checkbox was outdated pattern after FEAT-012 (import) and FEAT-017 (adopt) made managed/external distinction more important. No way to filter by managed status.

**Fix Applied:**
- Replaced "Show all" checkbox with "Managed Status" dropdown filter
- Options: All / Managed / External
- Default to "All" (preserves existing behavior)
- Expanded filter grid from 4 to 5 columns to accommodate new filter
- Added `filters.managedStatus` to `applyFilters()` logic
- MANAGED/EXTERNAL badges now always visible (no longer dependent on "show all" toggle)
- URL persistence works with new filter

**Files Modified:**
- `frontend/templates/containers.html` (filter UI, applyFilters logic)

---

## Notes
- All UI issues from initial reports have been resolved
- Test containers show proper port mappings without duplicates
- All action buttons (Start/Stop/Restart/Delete) are now fully functional
- Container details modal now fetches full data (env_vars, volumes, limits) for managed containers
- Network adopt/release lifecycle fully functional including for compose-generated networks
- Managed/unmanaged filtering now integrated with always-visible badges
- Scroll position preserved during container list refresh (visual flicker remains as known limitation)

## Sprint 5 New Features (UI Patterns)

### FEAT-012: Import Unmanaged Containers
**UI Pattern:** Inline action button within info banner
- **Location:** External container info bar (orange banner, bottom of card)
- **Button Style:** `bg-blue-600` — primary action for import operation
- **Loading State:** Button text changes to "⏳" while `actionLoading[container.name]` is true
- **Toast Messages:** Success toast includes warning that import won't survive DB reset (metadata-only)
- **Disabled State:** Button disabled via `actionLoading` during the import operation
- **No Modal:** Import is a one-click operation (no confirmation required)

**Edge Cases Handled:**
- Already-managed containers: Backend rejects with error toast
- DockerMate's own container: Backend rejects to prevent self-import
- After import: Container card refreshes and gains MANAGED badge + all action buttons appear

### FEAT-013: Retag & Redeploy
**UI Pattern:** Modal-based form with validation
- **Trigger:** Retag button (indigo `bg-indigo-600`) on managed container cards, between Rollback and Delete
- **Modal:** `retagModal` with container name, current image display, and new tag text input
- **Validation:** Submit button disabled when tag field is empty (`:disabled="retagModal.loading || !retagModal.newTag.trim()"`)
- **Error Display:** Inline error message (`retagModal.error`) shown below input field in red
- **Loading State:** Button text changes "Retag & Redeploy" → "Retagging..." while loading
- **Success:** Modal closes, toast shows old_image → new_image transition, containers list refreshes

**Edge Cases Handled:**
- Empty tag validation: Frontend prevents submission, inline error shown
- Pull failure: Backend returns error, modal stays open with error message
- Recreate failure: Backend returns error, UpdateHistory marked as failed
- Auto-refresh pause: Polling guard includes `!this.retagModal.show` to prevent list refresh during modal interaction

**Polling Guard Note:**
The `startPolling()` function now checks for `retagModal.show` alongside other modals (`deleteModal`, `createModal`, `bulkModal`, `detailsModal`). This prevents the container list from refreshing mid-retag, which would close the modal unexpectedly.
