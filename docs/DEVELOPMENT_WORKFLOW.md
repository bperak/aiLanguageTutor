# 🔧 Development Workflow Guide

## ⚠️ CRITICAL: This Project Uses Docker

**All services (frontend, backend, databases) run in Docker containers.**  
**DO NOT try to run services manually with `npm run dev` or `poetry run uvicorn` directly.**

## 🚀 Making Code Changes

### Frontend Changes (Next.js)

When you modify frontend code (`frontend/src/**`):

1. **Save your changes** - Files are automatically synced via Docker volumes
2. **Restart the frontend container**:
   ```powershell
   docker-compose restart frontend
   ```
3. **Wait 10-15 seconds** for Next.js to recompile
4. **Hard refresh browser**: Press `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac)
5. **Verify changes** are applied

**Why restart?** Next.js hot reload works, but sometimes the `.next` cache needs to be cleared. Restarting the container ensures a clean rebuild.

### Backend Changes (FastAPI)

When you modify backend code (`backend/app/**`):

1. **Save your changes** - Files are automatically synced via Docker volumes
2. **Restart the backend container**:
   ```powershell
   docker-compose restart backend
   ```
3. **Check logs** to verify it started:
   ```powershell
   docker-compose logs backend
   ```

**Note:** FastAPI with `--reload` should auto-reload, but restarting ensures changes are picked up.

### Database Schema Changes

1. **Update migration files** in `backend/migrations/`
2. **Restart PostgreSQL container**:
   ```powershell
   docker-compose restart postgres
   ```

## 🔍 Verifying Changes

### Check Container Status
```powershell
docker-compose ps
```

All services should show `Up` status.

### View Logs
```powershell
# Frontend logs
docker-compose logs frontend

# Backend logs  
docker-compose logs backend

# Follow logs in real-time
docker-compose logs -f frontend
```

### Test Changes in Browser

1. **Navigate to the page** (e.g., `http://localhost:3000/cando`)
2. **Hard refresh**: `Ctrl+Shift+R` or `Cmd+Shift+R`
3. **Check browser console** for errors
4. **Verify the changes** are visible

## 🛠️ Common Scenarios

### Scenario 1: Frontend Changes Not Showing

**Symptoms:** Code changes saved but browser shows old version

**Solution:**
```powershell
# 1. Restart frontend container
docker-compose restart frontend

# 2. Wait 10-15 seconds

# 3. Hard refresh browser (Ctrl+Shift+R)

# 4. If still not working, clear Next.js cache
docker-compose exec frontend rm -rf .next
docker-compose restart frontend
```

### Scenario 2: Backend Changes Not Reflecting

**Symptoms:** API changes not working

**Solution:**
```powershell
# 1. Restart backend container
docker-compose restart backend

# 2. Check logs for errors
docker-compose logs backend

# 3. Verify API is responding
curl http://localhost:8000/health
```

### Scenario 3: Need Complete Fresh Start

**Symptoms:** Everything seems broken, cache issues

**Solution:**
```powershell
# 1. Stop all containers
docker-compose down

# 2. Remove volumes (WARNING: deletes data)
docker-compose down -v

# 3. Rebuild and start
docker-compose up --build -d

# 4. Check status
docker-compose ps
```

## 📋 Quick Reference Commands

### Container Management
```powershell
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Restart specific service
docker-compose restart frontend
docker-compose restart backend

# View logs
docker-compose logs -f [service-name]

# Check status
docker-compose ps
```

### Development Commands (Inside Containers)
```powershell
# Run frontend tests (inside container)
docker-compose exec frontend npm run test:ui

# Run backend tests (inside container)
docker-compose exec backend poetry run pytest

# Access container shell
docker-compose exec frontend sh
docker-compose exec backend bash
```

## ⚡ Hot Reload vs Restart

### When Hot Reload Works
- **Frontend**: CSS changes, minor component updates
- **Backend**: Python code changes (with `--reload` flag)

### When You MUST Restart
- **Frontend**: 
  - New dependencies added to `package.json`
  - Changes to `next.config.js`
  - Major component refactoring
  - Changes not showing after hot reload
- **Backend**:
  - New dependencies added to `pyproject.toml`
  - Changes to environment variables
  - Database schema changes
  - Changes not showing after auto-reload

## 🎯 Best Practices

1. **Always restart containers after major changes** - Don't rely on hot reload
2. **Check logs** if something doesn't work
3. **Hard refresh browser** after frontend changes
4. **Verify in browser console** - Check for JavaScript errors
5. **Test API endpoints** - Use `curl` or browser dev tools

## 🚨 Troubleshooting

### Port Already in Use
```powershell
# Find what's using the port
netstat -ano | findstr :3000
netstat -ano | findstr :8000

# Kill the process (replace PID with actual process ID)
taskkill /PID [PID] /F
```

### Container Won't Start
```powershell
# Check logs for errors
docker-compose logs [service-name]

# Rebuild the container
docker-compose up --build [service-name]
```

### Changes Still Not Showing
1. **Verify file was saved** - Check file timestamp
2. **Check Docker volumes** - Ensure files are mounted correctly
3. **Clear browser cache** - Use incognito/private window
4. **Restart container** - Force a clean rebuild
5. **Check for syntax errors** - Look in container logs

## 📝 Summary

**Remember:**
- ✅ **DO**: Use `docker-compose restart [service]` for changes
- ✅ **DO**: Hard refresh browser after frontend changes
- ✅ **DO**: Check logs if something doesn't work
- ❌ **DON'T**: Try to run services outside Docker
- ❌ **DON'T**: Assume hot reload will always work
- ❌ **DON'T**: Forget to verify changes in browser

**When in doubt, restart the container!** 🐳

