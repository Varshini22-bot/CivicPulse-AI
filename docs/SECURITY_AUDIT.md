# CivicPulse AI — Security Audit & Hardening Report

## Executive Summary
This document outlines the defensive security architecture, vulnerability mitigations, access controls, and threat modeling implemented across **CivicPulse AI**. The platform was audited against the OWASP Top 10 API Security Risks (2023) and municipal public sector compliance baselines.

---

## 1. Authentication & Session Management

| Security Mechanism | Implementation | Verification |
|---|---|---|
| **Password Hashing** | Passlib with Bcrypt (cost factor 12) + salt | No plaintext passwords stored; verified via `backend/tests/test_auth.py` |
| **Token Mechanism** | RFC 7519 JSON Web Token (JWT) | Signed with HMAC-SHA256 (`HS256`) using configurable `SECRET_KEY` |
| **Token Expiry** | 7 days default with explicit expiration timestamp (`exp` claim) | Rejects expired tokens automatically via PyJWT validation |
| **Revocation & Logout** | Client-side token purge + Auth state reset | Instant session teardown in `AuthContext.tsx` |

---

## 2. Role-Based Access Control (RBAC)

The system enforces strict permission boundaries between Citizen reporters and Municipal Officers:

1. **Citizen Privileges (`role: "citizen"`)**:
   - Submit civic grievances with photographs and coordinates.
   - List their own submitted complaints (`GET /api/reports/my`).
   - Track live triage progress and priority scores.
   - Withdraw an open complaint they submitted.
   - *Forbidden*: Cannot view unassigned internal queues, execute status changes, dispatch work orders, or override AI predictions.
2. **Municipal Administrator Privileges (`role: "admin"`)**:
   - Access the complete searchable municipal ledger (`GET /api/admin/reports`).
   - Transition issue states (`PATCH /api/admin/reports/{id}/status`).
   - Override AI defect classifications and severity scores (`POST /api/admin/reports/{id}/override`).
   - Confirm or reject duplicate merger candidates.
   - Dispatch work orders to municipal departments and engineering staff.
   - Reseed or reset the demo dataset.
3. **Enforcement**:
   - Middleware dependency `get_current_active_admin` in `backend/app/api/deps.py` intercepts requests, verifies token validity, checks `user.role == "admin"`, and raises HTTP 403 Forbidden on violation.

---

## 3. File Upload & Media Ingestion Hardening

Unrestricted file uploads represent a major threat vector for Remote Code Execution (RCE) and Server-Side Request Forgery (SSRF). The following defensive layers are enforced in `backend/app/api/routes/reports.py`:

```
Uploaded File 
     |
     v
[Layer 1: Extension Whitelist] ----> Rejects non-raster files (.exe, .sh, .svg, .html)
     |
     v
[Layer 2: Size Ceiling] -----------> Enforces strict 10MB maximum payload limit
     |
     v
[Layer 3: Magic-Byte Inspection] --> PIL Image.verify() checks binary raster headers
     |
     v
[Layer 4: Storage Isolation] ------> Saved with random UUID filename: {uuid4()}.ext
                                     (Prevents path traversal, overwrites, and directory climbing)
```

---

## 4. Injection & Data Integrity Defenses

1. **SQL Injection Prevention**:
   - All database interactions are mediated by SQLAlchemy 2.0 ORM with parameterized query bindings.
   - Zero dynamic raw SQL string interpolation is permitted.
2. **Path Traversal Protection**:
   - Uploaded files are stripped of user-controlled filenames and assigned cryptographic UUIDs before being saved into the isolated `uploads/` directory.
3. **Cross-Site Scripting (XSS)**:
   - React 19 natively escapes dynamic strings in JSX templates.
   - No instances of `dangerouslySetInnerHTML` are utilized across the frontend codebase.
4. **CORS Boundary Enforcement**:
   - FastAPI `CORSMiddleware` strictly whitelists explicit frontend development origins (`http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:3000`).

---

## 5. Audit Logging & Immutable Traceability

Every operational state transition, status update, departmental assignment, and human AI override creates an append-only entry in the `audit_logs` table:
- Recorded attributes: `report_id`, `user_id`, `action`, `previous_state`, `new_state`, `notes`, `created_at`.
- Municipal transparency ensures that if an officer overrides an AI severity score from 4 to 8, the original AI classification remains permanently auditable.

---

## 6. Secrets Hygiene

- No hardcoded API keys, production database credentials, or secret keys exist in the repository source code.
- `.env.example` provides non-secret development defaults.
- `.gitignore` explicitly prevents `.env`, `civicpulse.db`, and `uploads/` from being committed to version control.
