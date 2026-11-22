# CivicPulse AI — Docker Containerization & Deployment Verification

## 1. Architectural Strategy

CivicPulse AI provides dual deployment execution paradigms:
1. **Containerized Production Topology (Docker & Docker Compose)**: Multi-container orchestration incorporating PostGIS spatial database, FastAPI ASGI backend, and Nginx-served static React 19 frontend with reverse-proxy routing.
2. **Native Lightweight Local Execution**: Standalone Python 3.11 + Vite development servers utilizing embedded SQLite with registered spherical mathematics functions for environments where Docker daemon virtualization is unavailable.

---

## 2. Docker Compose Service Topology

```
+---------------------------------------------------------------------------------+
|                                 docker-compose.yml                              |
+---------------------------------------------------------------------------------+
           |                                       |
           v                                       v
+-----------------------+              +-----------------------+
|   civicpulse-frontend |              |    civicpulse-db      |
|  - Nginx Alpine       |              |  - postgis:16-3.4     |
|  - React 19 SPA       |              |  - Port 5432          |
|  - Port 3000 -> 80    |              |  - Volume: postgres_  |
+-----------------------+              +-----------------------+
           |                                       ^
           v                                       |
+--------------------------------------------------+----+
|                  civicpulse-backend                   |
|  - Python 3.11-slim + Uvicorn ASGI                    |
|  - Port 8000 -> 8000                                  |
|  - Depends on DB (service_healthy)                    |
|  - Mounts: ./backend/uploads -> /app/uploads          |
+-------------------------------------------------------+
```

---

## 3. Deployment Commands & Verification

### 3.1 Production Container Launch
To build and start all three isolated containers:
```bash
docker-compose up --build -d
```

### 3.2 Health Check Verification
1. Verify database container is ready:
   ```bash
   docker exec -it civicpulse-db pg_isready -U postgres -d civicpulse_db
   ```
2. Verify backend REST API health endpoint:
   ```bash
   curl -I http://localhost:8000/api/reports/categories
   ```
3. Verify frontend web application:
   ```bash
   curl -I http://localhost:3000
   ```

### 3.3 Container Teardown
```bash
docker-compose down
# Or to wipe all volumes:
docker-compose down -v
```

---

## 4. Local Development Fallback (Windows / macOS / Linux)

For developers running on local machines without an active Docker daemon:

### Windows Batch Launcher (`start_servers.bat`):
Double-click `start_servers.bat` to launch backend and frontend in separate command windows:
```cmd
@echo off
echo Starting CivicPulse AI Local Stack...
start "CivicPulse Backend" cmd /k "python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
cd frontend
start "CivicPulse Frontend" cmd /k "npm run dev"
```

### Windows PowerShell Launcher (`start_servers.ps1`):
```powershell
.\start_servers.ps1
```

### Manual Terminal Commands:
- **Backend**:
  ```bash
  python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
  ```
- **Frontend**:
  ```bash
  cd frontend
  npm run dev
  ```
- Access Frontend at `http://localhost:5173` and Backend Swagger UI at `http://localhost:8000/docs`.
