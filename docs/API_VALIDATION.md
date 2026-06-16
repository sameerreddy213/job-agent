# API Validation (Phase 4A)

Goal: prove the backend is correct **before** building the React UI. Everything
here runs against the existing APIs — no new backend logic.

## 0. Bring the stack up (TEST_MODE)
```bash
cp .env.example .env            # ensure TEST_MODE=true
docker compose up -d
# seed demo data: profile, sources, a sample blacklist, + 1 pipeline run (~50 jobs)
docker compose exec api python -m app.seed_demo
```
Base URL options:
- Direct to api container / local: `http://localhost:8000`
- Behind nginx in prod: `https://jobs.<domain>/api`

---

## 1. OpenAPI documentation review
FastAPI auto-generates the spec.
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **Raw schema:** `http://localhost:8000/openapi.json`

Export to a file for diffing / client generation:
```bash
docker compose exec api python scripts/export_openapi.py   # writes openapi.json
```
Review checklist: every router (auth, profile, resumes, sources, jobs, admin,
queue, dashboard, analytics, settings, audit) appears; protected routes show the
bearer lock; request/response schemas match `docs/API_SPEC.md`.

---

## 2. Automated test suite
One-shot (installs dev deps, seeds demo data, runs pytest):
```bash
docker compose exec api ./scripts/run-tests.sh
```
Or manually:
```bash
docker compose exec api pip install -r requirements-dev.txt
docker compose exec -e API_BASE=http://localhost:8000 api pytest
```
Covers: health, auth (login/refresh-rotation/logout/rate-limit/guarded routes),
queue (sorting, score filter, dedupe), jobs detail, dashboard, analytics,
settings + blacklist CRUD, audit logging, profile upsert, sources, resume summary.

> The image bundles `tests/`, `pytest.ini`, and `requirements-dev.txt`; dev deps
> are installed on demand (not baked into the runtime).

---

## 3. curl examples

### Health
```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8000/health/db
```

### Auth — login (save token)
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -d "username=admin" -d "password=change_me_strong_password" | jq -r .access_token)

REFRESH=$(curl -s -X POST http://localhost:8000/auth/login \
  -d "username=admin" -d "password=change_me_strong_password" | jq -r .refresh_token)

curl -s http://localhost:8000/auth/me -H "Authorization: Bearer $TOKEN"
```

### Auth — refresh rotation & logout
```bash
curl -s -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" -d "{\"refresh_token\":\"$REFRESH\"}"

curl -s -X POST http://localhost:8000/auth/logout \
  -H "Content-Type: application/json" -d "{\"refresh_token\":\"$REFRESH\"}" -i
```

### Rate limiting (expect 429 after 5 failures)
```bash
for i in $(seq 1 7); do
  curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8000/auth/login \
    -d "username=probe" -d "password=wrong"
done
```

### Pipeline run + queue
```bash
curl -s -X POST http://localhost:8000/admin/run-now -H "Authorization: Bearer $TOKEN"
curl -s "http://localhost:8000/queue?limit=10" -H "Authorization: Bearer $TOKEN"
curl -s http://localhost:8000/queue/counts -H "Authorization: Bearer $TOKEN"
curl -s "http://localhost:8000/jobs?min_score=90" -H "Authorization: Bearer $TOKEN"
```

### Dashboard & analytics
```bash
curl -s http://localhost:8000/dashboard/summary -H "Authorization: Bearer $TOKEN"
curl -s "http://localhost:8000/analytics/overview?days=30&top_n=10" -H "Authorization: Bearer $TOKEN"
```

### Settings / blacklist / audit
```bash
curl -s http://localhost:8000/settings -H "Authorization: Bearer $TOKEN"

curl -s -X POST http://localhost:8000/settings/blacklist/companies \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"company":"Initech","reason":"not interested"}'

curl -s "http://localhost:8000/audit?limit=20" -H "Authorization: Bearer $TOKEN"
```

### Profile & resumes
```bash
curl -s http://localhost:8000/resumes/summary -H "Authorization: Bearer $TOKEN"

curl -s -X POST http://localhost:8000/resumes/SDE/versions \
  -H "Authorization: Bearer $TOKEN" -F "file=@/path/to/resume.pdf"
```

---

## 4. Postman collection
Import `docs/postman_collection.json`. Set collection variables `baseUrl`,
`adminUser`, `adminPass`. Run **Auth > Login** first — it auto-stores
`accessToken`/`refreshToken` for every other request.

---

## 5. Validation checklist (map to requirements)

| Area | Check | Pass criteria |
|------|-------|---------------|
| Health | `/health`, `/health/db`, `/health/sources` | 200; db up; per-source status enum |
| Auth flow | login / me / refresh / logout / rate limit | rotation revokes old token; 429 after 5 fails; guarded routes 401 without token |
| Queue | `/queue` sorting + filters | score-descending; only AUTO/REVIEW; `min_score` honored |
| Dedupe | `/jobs` fingerprints | no duplicate fingerprints (3 sample dups suppressed) |
| Filtering | senior / "2+ years" / blacklist | such jobs are `REJECTED_FILTER`, never in queue |
| Scoring | classifications | totals 0-100; thresholds 90 / 70 applied |
| Analytics | `/analytics/overview` | all keys present; apps/interview = 0 with `note` |
| Dashboard | `/dashboard/summary` | counts consistent with `/jobs` + `/queue/counts` |
| Settings | blacklist CRUD | create 201, duplicate 409, delete 204, bad applies_to 400 |
| Audit | `/audit` | login + run-now + blacklist actions recorded |

---

## 6. Expected demo numbers (TEST_MODE, after one run)
- ~50 sample jobs discovered; 3 exact duplicates suppressed (~47 stored).
- Senior / Manager / Principal / "2+ years" roles → `REJECTED_FILTER`.
- Remaining fresher roles split across `AUTO_APPROVE_ELIGIBLE` / `REVIEW_QUEUE`.
- `Initech` jobs filtered out once the demo company blacklist is seeded.

When all checks pass, the backend contract is verified and Phase 4B (React) can
build against it with confidence.
