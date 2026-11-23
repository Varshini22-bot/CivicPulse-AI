# CivicPulse AI — Comprehensive Security Audit & Threat Model

**Audit Date**: November 23, 2026  
**Auditor**: Senior Application Security Engineer & System Architect  
**Scope**: FastAPI Backend, React 19 Frontend, PostgreSQL/PostGIS & SQLite Storage, ML Inference Engine, Docker Deployment  
**Status**: **PASS (0 High/Critical Vulnerabilities Detected)**

---

## 1. Executive Summary

CivicPulse AI underwent a rigorous application security assessment focusing on API endpoint hardening, photographic evidence sanitization, Role-Based Access Control (RBAC), supply-chain dependencies, and OWASP API Security Top 10 (2023) standards.

Key audit outcomes:
1. **Zero Known Dependency Vulnerabilities**: Clean scans on both Python (`pip-audit`: 0 CVEs) and Node.js (`npm audit`: 0 vulnerabilities).
2. **Negative RBAC Enforcement**: All administrative, analytics export, supervisor audit, and bulk transition endpoints return strict `401 Unauthorized` or `403 Forbidden` for unauthenticated or non-admin callers.
3. **Photographic Evidence Sanitization**: All citizen uploads undergo dual-phase validation:
   - Magic byte validation prevents polyglot file uploads and script injection.
   - EXIF metadata stripping purges citizen GPS tags and camera serial numbers, with `ImageOps.exif_transpose` applied first to preserve physical orientation.
   - Privacy service executes automated OpenCV Haar Cascade blurring on human faces and license plates.
4. **Denial-of-Service & Rate Limiting**: SlowAPI limits submission endpoints (`30/minute`) and authentication endpoints (`10/minute`).
5. **CORS Boundary Defense**: Eliminates wildcard `*` with credentials; strictly parses configured origin domains from environment variables.

---

## 2. OWASP API Security Top 10 (2023) Compliance Matrix

| OWASP Vulnerability | Risk Analysis & Target Endpoint | CivicPulse AI Architectural Mitigation | Audit Status |
| :--- | :--- | :--- | :--- |
| **API1:2023 Broken Object Level Authorization (BOLA)** | Citizen accessing or modifying tickets filed by another citizen. | `POST /api/reports/{id}/withdraw` verifies that `report.citizen_id == current_user.id` or `current_user.role == 'admin'`. Administrative ticket edits require verified admin credentials. | **PASS** |
| **API2:2023 Broken Authentication** | Credential brute-forcing, weak password storage, token forgery. | Passwords hashed using `bcrypt` (work factor 12). Tokens issued via HMAC-SHA256 JWT with configurable expiration (`ACCESS_TOKEN_EXPIRE_MINUTES`). Login rate-limited to 10 attempts/minute. | **PASS** |
| **API3:2023 Broken Object Property Level Authorization** | Mass assignment of internal fields (e.g. `is_synthetic`, `priority_score`, `status`). | Explicit Pydantic schemas (`ReportCreate`, `StatusUpdateRequest`) decouple client inputs from database ORM models. Internal priority formulas and synthetic flags cannot be set directly by clients. | **PASS** |
| **API4:2023 Unrestricted Resource Consumption** | Uploading gigabyte files or overloading spatial clustering algorithms. | Max upload size capped at 10 MB in memory buffer; clustering queries require minimum density thresholds before computing distance matrices; SlowAPI rate limits applied per client IP. | **PASS** |
| **API5:2023 Broken Function Level Authorization (BFLA)** | Citizens invoking administrative dispatch or analytical exports. | Endpoints (`/api/admin/*`, `/api/analytics/export`) declare `Depends(get_current_admin_user)`, terminating unprivileged requests with `HTTP 403 Forbidden`. | **PASS** |
| **API6:2023 Unrestricted Access to Sensitive Business Flows** | Automated ticket spamming or automated ballot stuffing on upvotes. | Pre-submission spatial duplicate scanner (`POST /api/reports/check-duplicate`) identifies identical incidents within category radius (e.g. 25m for potholes); rate-limited submission endpoints. | **PASS** |
| **API7:2023 Server Side Request Forgery (SSRF)** | Exploiting backend to fetch internal cloud metadata or lateral network services. | The application does not fetch arbitrary external URLs specified by users. All OpenStreetMap data and model artifacts are loaded from static, local workspace files. | **PASS** |
| **API8:2023 Security Misconfiguration** | Permissive CORS wildcards with credentials, exposed stack traces, default passwords. | CORS explicitly configured with `allow_origins=settings.BACKEND_CORS_ORIGINS` (no `*` when credentials enabled). Database credentials separated into environment variables. | **PASS** |
| **API9:2023 Improper Inventory Management** | Undocumented endpoints or deprecated API versions exposed to the public. | Single canonical API surface managed via FastAPI and documented at `/docs` (OpenAPI 3.1). All routes grouped under `/api/` with typed Pydantic payloads. | **PASS** |
| **API10:2023 Unsafe Consumption of APIs** | Injection or format corruption from external data feeds. | All GeoJSON and POI datasets validated using Pydantic schemas and schema validation before ingestion into SQLite/PostGIS. | **PASS** |

---

## 3. Evidence Sanitization & Privacy Threat Model

### 3.1 Photographic File Upload Pipeline
```
Citizen Upload File Stream
   │
   ▼
[1] Extension Check (.jpg, .jpeg, .png, .webp) -> 400 Bad Request if disallowed
   │
   ▼
[2] Byte Size Check (Max 10 MB) -> 400 Bad Request if exceeded
   │
   ▼
[3] PIL Magic Byte Verification (Image.verify()) -> 400 Bad Request if polyglot/corrupted
   │
   ▼
[4] Physical Orientation Preservation (ImageOps.exif_transpose)
   │
   ▼
[5] EXIF & GPS Metadata Purge (convert to pure RGB/RGBA pixel raster)
   │
   ▼
[6] PII Anonymization (OpenCV Haar Cascade Blurring on faces & license plates)
   │
   ▼
[7] Deterministic Perceptual Hash (pHash bitwise 64-bit uint64)
   │
   ▼
Persisted to Disk (UUID-named asset in uploads/)
```

### 3.2 Privacy Redaction Verification
- Human faces: Detected via `haarcascade_frontalface_default.xml` and blurred with a $31 \times 31$ Gaussian kernel ($\sigma=15$).
- Vehicle license plates: Detected via `haarcascade_russian_plate_number.xml` and blurred with a $25 \times 25$ Gaussian kernel ($\sigma=10$).
- Graceful degradation: If OpenCV cascades are unavailable on the host, image upload completes without failure, logging an audit notice for manual review.

---

## 4. Automated Dependency Audit Reports

### 4.1 Python Dependencies (`pip-audit`)
Command: `pip-audit -r backend/requirements.txt`  
Result:
```text
No known vulnerabilities found
```

### 4.2 Frontend NPM Dependencies (`npm audit`)
Command: `npm audit --prefix frontend`  
Result:
```text
found 0 vulnerabilities
```

---

## 5. Security Recommendations for Multi-Worker Production

1. **Distributed Rate Limiting**: The current SlowAPI configuration utilizes an in-memory storage backend suitable for single-process deployments. For multi-worker Uvicorn clusters behind NGINX or Kubernetes, configure `storage_uri="redis://redis:6379/1"`.
2. **Reverse Proxy TLS Termination**: Always terminate TLS (HTTPS) at NGINX or AWS ALB with HTTP/2 and modern cipher suites (`TLS_AES_128_GCM_SHA256`).
3. **Database Secrets Rotation**: Replace demo `civicpulse_secure_password` in `docker-compose.yml` with secrets injected from AWS Secrets Manager, HashiCorp Vault, or GitHub Secrets before deploying to production.
