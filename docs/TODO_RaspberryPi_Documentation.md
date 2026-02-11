# TODO: Raspberry Pi Deployment Documentation

**Reference for future documentation** (deferred from this session)

## Content to Document

Based on week-long Raspberry Pi deployment testing (February 4-11, 2026), document the following:

### 1. Health Check Settings for Raspberry Pi

**Issue:** Default health checks too aggressive for Pi with USB storage

**Recommended docker run flags:**
```bash
--health-cmd="curl -fk https://localhost:5000/api/health || exit 1"
--health-interval=90s
--health-timeout=30s
--health-retries=5
--health-start-period=180s
```

**Explanation:**
- `interval=90s` (was 30s) - Check less frequently for slower hardware
- `timeout=30s` (was 10s) - Allow more time for USB I/O + database queries
- `retries=5` (was 3) - More tolerant of occasional slowness
- `start-period=180s` (was 40s) - Give Pi more time to fully initialize

### 2. USB Storage Considerations

**Issue:** Database on USB storage (`/srv/sda1/Appdata/DockerMate/`) causes slow I/O

**Recommendations:**
- Consider using SD card for database if faster
- Or use internal storage if available
- USB 3.0 preferred over USB 2.0
- Health check timeout must account for storage speed

### 3. Complete docker run Command for Pi

```bash
sudo docker run -d \
  --name dockermate \
  --restart unless-stopped \
  --group-add $(getent group docker | cut -d: -f3) \
  -p 5000:5000 \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v /path/to/data:/app/data \
  -v /path/to/stacks:/app/stacks \
  -v /path/to/exports:/app/exports \
  -e TZ=Your/Timezone \
  -e DOCKERMATE_SSL_MODE=self-signed \
  -e DOCKERMATE_SESSION_EXPIRY=8h \
  -e DOCKERMATE_REMEMBER_ME_EXPIRY=7d \
  --health-cmd="curl -fk https://localhost:5000/api/health || exit 1" \
  --health-interval=90s \
  --health-timeout=30s \
  --health-retries=5 \
  --health-start-period=180s \
  dockermate:latest
```

### 4. Pi-Specific Notes

- ✅ Web interface works perfectly on Pi
- ✅ All features functional (containers, images, networks, volumes, stacks, health)
- ✅ Week-long uptime stable
- ⚠️ Container shows "unhealthy" with default health check settings (workaround above fixes this)
- ⚠️ HTTPS required (not HTTP) - browser must access https://pi-ip:5000

### 5. Performance Expectations

- Container list page: ~1-2s load time
- Health check endpoint: 10-30s response time (depending on storage)
- Stack deployment: Comparable to x86 for small stacks
- Image pulls: Network-dependent, Pi network speed is bottleneck

### 6. Troubleshooting

**Problem:** Container marked unhealthy but web works
**Solution:** Apply adjusted health check settings above

**Problem:** Slow page loads
**Solution:** Check USB storage speed, consider moving database to faster storage

**Problem:** Can't access web interface
**Solution:** Use https:// not http://

## File Location

Should be created as: `docs/RaspberryPi_Deployment_Guide.md`

## Related Issues

- DEPLOY-002: Health checks too aggressive for Pi (documented in ISSUES.md)
- All findings from February 11, 2026 testing session

---

**Status:** Deferred to future session
**Priority:** Medium (helps Pi users)
**Effort:** 15-20 minutes to write properly formatted guide
