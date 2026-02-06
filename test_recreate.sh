#!/bin/bash
# Test script for FEATURE-003 Container Recreate
# Tests the new POST /api/containers/<id>/recreate endpoint

echo "=========================================="
echo "Testing Container Recreate Endpoint"
echo "=========================================="
echo ""

# Get auth token (assuming you're logged in)
# Note: You'll need to be logged in to DockerMate for this to work

echo "1. Current container status:"
docker ps --filter name=test-recreate --format "  Name: {{.Names}}\n  Status: {{.Status}}\n  Ports: {{.Ports}}\n  Image: {{.Image}}"
echo ""

echo "2. Current environment variables:"
docker inspect test-recreate --format '{{range .Config.Env}}  {{println .}}{{end}}' | grep TEST_VAR || echo "  (none found)"
echo ""

echo "3. Testing recreate with new configuration..."
echo "   - Changing port: 8888 -> 9999"
echo "   - Adding env var: NEW_VAR=updated"
echo "   - Changing restart policy: no -> always"
echo ""

# Call the API (you'll need to get CSRF token and session cookie)
# For now, this is a manual test guide

cat << 'EOF'
📋 Manual API Test Steps:
--------------------------

1. Login to DockerMate at https://localhost:5000
2. Open Browser DevTools (F12) → Console tab
3. Run this JavaScript:

fetch('/api/containers/test-recreate/recreate', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
    },
    body: JSON.stringify({
        ports: {
            '80/tcp': [{'HostPort': '9999'}]
        },
        environment: {
            'TEST_VAR': 'original',
            'NEW_VAR': 'updated'
        },
        restart_policy: 'always'
    })
})
.then(r => r.json())
.then(d => console.log('Response:', d))
.catch(e => console.error('Error:', e));

4. Expected response:
{
    "success": true,
    "data": {
        "container_id": "<new_id>",
        "name": "test-recreate",
        "changes": ["ports", "environment", "restart_policy"],
        "status": "success"
    },
    "message": "Container reconfigured: ports, environment, restart_policy"
}

5. Verify changes:
EOF

echo ""
echo "After running the API call, verify with:"
echo "  docker ps --filter name=test-recreate --format 'Ports: {{.Ports}}'"
echo "  docker inspect test-recreate --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -E '(TEST_VAR|NEW_VAR)'"
echo "  docker inspect test-recreate --format '{{.HostConfig.RestartPolicy.Name}}'"
echo ""

echo "=========================================="
echo "Alternative: Test with curl (requires auth)"
echo "=========================================="
echo ""
echo "If you have session cookies:"
echo ""
echo 'curl -k -X POST https://localhost:5000/api/containers/test-recreate/recreate \'
echo '  -H "Content-Type: application/json" \'
echo '  -H "X-CSRFToken: YOUR_CSRF_TOKEN" \'
echo '  -H "Cookie: auth_session=YOUR_SESSION" \'
echo '  -d '"'"'{'
echo '    "ports": {"80/tcp": [{"HostPort": "9999"}]},'
echo '    "environment": {"TEST_VAR": "original", "NEW_VAR": "updated"},'
echo '    "restart_policy": "always"'
echo '  }'"'"
echo ""
