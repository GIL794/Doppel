# DoppelAI Development & Governance Guidelines

This file serves as the permanent context and operational guideline for AI coding assistants and developers working on the DoppelAI codebase.

---

## 1. System Architecture & Boundaries

* **Frontend**: React 18 (Create React App + CRACO for `@/` import alias). High-contrast neo-brutalist UI.
* **Backend**: FastAPI + SQLite (local development) / PostgreSQL via `DATABASE_URL` (production).
* **Storage**: Local filesystem (`blobstore.LocalStore`) or private Supabase bucket (`blobstore.SupabaseStore`).
* **Serving**: In production, FastAPI serves both `/api/*` endpoints and the compiled React production bundle (`build/`) from a single origin (`APP_ENV=production`), ensuring session cookies (`access_token`, `refresh_token`) work securely without cross-origin friction.

---

## 2. Core Non-Negotiable Invariants

### A. The Script Approval Gate ("Approve Before Render")
* **Rule**: Under no circumstances shall an external video rendering job (Fal.ai / Veed) be triggered without explicit, recorded customer approval of the generated script (`production_status = 'in_production'`).
* Customer revisions (`change_note`) take priority and trigger a script redraft, not a video render.

### B. Money-Safety & Billable Automation
* **Provider Gating**: Background automation only triggers billable external API calls (Gemini script drafting, Fal.ai video rendering) when:
  1. `ORDER_AUTOMATION=on`
  2. The relevant provider keys are set (`GEMINI_API_KEY`, `FAL_KEY`)
  3. The order payment is **verified real money** (`provider='stripe'` and `payment_status='paid'`).
* **Mock Payments**: Mock orders (`provider='mock'`) must never trigger billable external provider calls under any circumstances.
* **Idempotency**: Video render jobs submit at most once per order. Immediately upon submit, record `video_request_id` and `video_request_model`. Ambient failures must not auto-resubmit; they fall back to manual admin review to avoid duplicate billing.

### C. Biometric & Legal Compliance (UK GDPR & EU AI Act)
* **Consent Audit Trail**: Every checkout submission must provide `consent_terms=True` and `consent_likeness=True`. The backend must reject orders lacking these flags with HTTP 422 and store `consent_timestamp` in the database.
* **Biometric Purge**: Raw portrait photos (`photo_file_id`) are retained for a maximum of 30 days post-delivery to allow minor touch-ups, after which they must be purged pursuant to SOP-002.
* **Acceptable Use & Deepfake Ban**: Photos of politicians, public figures, celebrities, or minors without documented proof are strictly prohibited. Violations must trigger immediate cancellation and refund under SOP-003.

---

## 3. Standard Operating Procedures (SOPs)

All operational changes and feature developments must align with the documentation under `docs/sop/`:
* `docs/sop/SOP-001_ORDER_FULFILLMENT.md`: End-to-end commercial order lifecycle & QA criteria.
* `docs/sop/SOP-002_DATA_GOVERNANCE_AND_BIOMETRICS.md`: Handling biometric likeness data & GDPR erasure.
* `docs/sop/SOP-003_ACCEPTABLE_USE_AND_AI_SAFETY.md`: Content moderation, deepfake prevention & watermarking.
* `docs/sop/SOP-004_CUSTOMER_SUPPORT_AND_REFUNDS.md`: Revision policies & consumer rights cooling-off handling.
* `docs/sop/SOP-005_INCIDENT_RESPONSE.md`: P1–P4 severity triage & 72-hour ICO breach reporting.

---

## 4. ISO Governance Framework Alignment

Architectural decisions and new integrations must preserve compliance with `docs/governance/ISO_ALIGNMENT.md`:
* **ISO/IEC 42001:2023** (Artificial Intelligence Management System): Human oversight, transparency, provider provenance.
* **ISO/IEC 27001:2022** (Information Security Management System): Access controls, secure cookie sessions, cryptographic protections.
* **ISO/IEC 27701:2019** (Privacy Information Management): Minimization, consent lifecycle, data subject rights.

---

## 5. Development & Testing Conventions

* **Cross-Platform File Paths**: Never hardcode `/tmp/` in Python code or tests. Always use `tempfile.gettempdir()` or `pathlib.Path` to support Windows and Linux environments.
* **Windows Sandbox & Pytest**: FastAPI tests using `TestClient` rely on `anyio` threadpool loopback communication, which requires `BypassSandbox: true` on Windows sandbox environments.
* **Frontend Builds**: Always run `npm test -- --watchAll=false` and `npm run build` after editing UI components to ensure zero build errors or broken imports.

