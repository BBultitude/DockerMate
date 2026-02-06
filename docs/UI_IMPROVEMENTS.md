# UI Improvements Backlog

This document tracks UI/UX improvements identified for future sprints.

## Priority: High

### 1. Favicon - Whale Image
**Issue**: No favicon currently set
**Improvement**: Use Docker whale image as favicon
**Impact**: Branding, professional appearance
**Effort**: 30 minutes
**Files**: `frontend/static/favicon.ico`, `frontend/templates/base.html`

### 2. Dashboard Flickering on Refresh
**Issue**: Content refreshes cause text to flicker across all cards. No stable sort order for networks, images, etc.
**Improvement**:
- Only update DOM elements that have actually changed
- Implement stable sort order (by name or creation date)
- Use differential updates instead of full re-renders
**Impact**: Much better UX, less distracting
**Effort**: 4-6 hours
**Files**:
- `frontend/templates/dashboard.html` (Alpine.js component)
- All resource list pages (containers, images, networks, volumes)
**Technical Approach**:
- Track previous state and compare before updating
- Use Alpine.js `x-for` with `:key` properly
- Add default sort to all API endpoints or client-side

### 3. Stack Resources Not Auto-Imported
**Issue**: Containers, volumes, networks created via stacks are not automatically imported/tracked by DockerMate
**Improvement**:
- Mark stack-created resources as managed automatically
- Sync stack resources to their respective tables on deployment
- Show "Created by Stack: {name}" in resource lists
**Impact**: Better integration, clearer resource ownership
**Effort**: 3-4 hours
**Files**:
- `backend/services/stack_manager.py` - Update deploy methods
- `backend/services/container_manager.py` - Sync from labels
- `backend/services/volume_manager.py` - Adopt volumes with stack label
- `backend/services/network_manager.py` - Adopt networks with stack label
**Technical Approach**:
- After stack deployment, query created resources by label `com.dockermate.stack={name}`
- Sync to database with `managed=True`
- Link back to stack

## Priority: Medium

### 4. Dashboard Layout Optimization
**Issue**: Hardware profile and containers cards take too much vertical space
**Improvement**:
- Split hardware profile card horizontally (2 rows instead of 1)
- Split containers card horizontally (2 rows instead of 1)
- Stack them vertically to save space
**Impact**: More compact dashboard, see more info above fold
**Effort**: 2 hours
**Files**: `frontend/templates/dashboard.html`
**Before**:
```
[Hardware Profile - wide card]
[Containers - wide card]
```
**After**:
```
[Hardware Profile - Top Half]
[Hardware Profile - Bottom Half]
[Containers - Top Half]
[Containers - Bottom Half]
```

### 5. Health Card - Simplified Warnings
**Issue**: Health card shows detailed warning/error messages which clutter the dashboard
**Improvement**:
- Remove detailed warning messages
- Keep only status indicators (✅ ⚠️ ❌)
- Keep overall health status
- Add "View Details" link to full health page for warnings
**Impact**: Cleaner dashboard, less clutter
**Effort**: 1 hour
**Files**: `frontend/templates/dashboard.html`

### 6. Stack YAML Formatting Help
**Issue**: Users unfamiliar with YAML may struggle with indentation and syntax
**Improvement**:
- Add YAML syntax guide in create/edit stack modal
- Show indentation guidelines (2 spaces per level)
- Add "Validate YAML" button before submit
- Consider YAML syntax highlighting in textarea
**Impact**: Better user experience, fewer YAML errors
**Effort**: 2-3 hours
**Files**: `frontend/templates/stacks.html`
**Features to Add**:
- Collapsible help section with examples
- Common patterns (ports, volumes, environment)
- Indentation rules
- Optional: Real-time YAML validation

## Implementation Priority Order

For v1.0 Polish Sprint:
1. **Favicon** (quick win, 30 min)
2. **Stack resources auto-import** (critical for integration, 3-4 hours)
3. **Dashboard flickering fix** (UX critical, 4-6 hours)
4. **Dashboard layout optimization** (nice-to-have, 2 hours)
5. **Health card simplification** (cleanup, 1 hour)
6. **YAML formatting help** (helpful, 2-3 hours)

**Total Effort**: ~13-17 hours for all improvements

## Technical Notes

### Differential Updates Pattern
Instead of:
```javascript
async loadData() {
    this.containers = await fetch('/api/containers').then(r => r.json());
}
```

Use:
```javascript
async loadData() {
    const newData = await fetch('/api/containers').then(r => r.json());

    // Only update if changed
    if (JSON.stringify(this.containers) !== JSON.stringify(newData.containers)) {
        this.containers = newData.containers;
    }
}
```

Or better - use Alpine.js reactivity properly with stable keys:
```html
<template x-for="container in sortedContainers" :key="container.id">
    <!-- Content updates automatically without flicker -->
</template>
```

### Stack Resource Sync Pattern
After stack deployment:
```python
# In StackManager.deploy_stack()
created_containers = self._create_services(...)

# Sync to container manager
from backend.services.container_manager import ContainerManager
container_mgr = ContainerManager(self.db)
for container in created_containers:
    # This syncs container to containers table with managed=True
    container_mgr._sync_database_state(container, environment=None)
```

## Related Issues

- Performance optimization for large resource lists
- Add pagination for resources (100+ items)
- Implement search/filter across all resource pages
- Add bulk operations UI improvements

## User Feedback

These improvements were identified during user testing and feedback collection.

Last Updated: 2026-02-06
