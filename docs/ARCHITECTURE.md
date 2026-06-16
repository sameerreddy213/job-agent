# Architecture — job-agent

Single-user Job Discovery & Application Management Platform.

## Overview
A modular pipeline runs on one AWS EC2 host via Docker Compose. PostgreSQL is the
single source of truth. The dashboard is the only approval interface. AI is fully
abstracted (MVP uses deterministic rule/template engines; an LLM can be slotted in
later behind the same interface without touching business logic).

## Components
| Container | Role |
|-----------|------|
| `nginx`   | Reverse proxy, TLS termination (Let's Encrypt), security headers |
| `frontend`| React mobile-first dashboard (Phase 4) |
| `api`     | FastAPI REST API + JWT auth (Phase 1+) |
| `worker`  | Hourly discovery pipeline + scheduler (Phase 2+) |
| `postgres`| Source of truth (internal network only) |
| `certbot` | TLS issuance + auto-renewal |

## Pipeline (Phase 2+)
`connectors → normalize → dedupe (fingerprint) → rule filter → score → persist`

Sources & apply policy:
- **Auto-apply after approval:** Greenhouse, Lever, Ashby, company career pages
- **Discovery + assist only (you submit):** LinkedIn, Naukri, Indeed

## Scoring (Phase 3)
`score = 0.40·freshers + 0.30·skills + 0.10·location + 0.20·role`
Thresholds: ≥90 auto-approve-eligible · 70–89 review · <70 reject.
(Auto-submit additionally requires an auto-policy source and no restricted manual fields.)

## Hard rules
- Truthfulness: never invent skills/experience/projects.
- Never auto-answer diversity / disability / veteran / legal declarations.
- No submission without dashboard approval. No Telegram approval.

## Build phases
0. Infra scaffold ✅
1. DB schema, migrations, resume versioning, JWT auth, profile/resume/user models, base API ✅
2. Discovery pipeline + connectors (Greenhouse/Lever/Ashby) + TEST_MODE ✅
3. Dashboard backend APIs (queue, analytics, settings, audit) + refresh tokens, rate limit, blacklists ✅
4A. API validation layer (tests, Postman, seed/demo) ✅
4. Observability (structured JSON logs, health checks, /metrics) ✅
4B. React dashboard UI (mobile-first, dark mode) ✅
5A. Resume Intelligence Layer (rule engine: parse, skills, categorize, recommend, match, confidence) ✅
6A. Materials Generation Engine (deterministic templates → cover letter / summary / answers; PDF/DOCX/TXT) + refresh-token reuse detection ✅
6B. Google Sheets one-way mirror (Jobs/Applications/Sources/Runs/Resume Stats; incremental sync; manual + scheduled) ✅
6C. Telegram notifications (high-match, daily/evening summaries, failures, security) + read-only bot commands ✅
7A. Workflow engine (11-state machine, review-queue actions, bulk ops, transition audit) ✅ ← current
7B. Apply engine (READY_TO_APPLY → APPLIED; auto-submit ATS / manual-assist)
8. Ops hardening
6. Integrations (Sheets, Telegram) + ops (backups, retention, health alerts)
7. Hardening
