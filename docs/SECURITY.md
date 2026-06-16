# Security — job-agent

## Authentication
- Single admin user. **JWT** (HS256): short-lived access token + refresh token.
- **Refresh-token rotation**: each `/auth/refresh` revokes the presented token and
  issues a new pair; tokens tracked in `refresh_tokens` (jti). `/auth/logout` revokes.
- **Refresh-token reuse detection (family tracking)**: every token from one login
  shares a `family_id`. Presenting an already-rotated/revoked token revokes ALL of
  the user's active tokens, forces re-authentication, writes a
  `security.refresh_reuse` audit event, and increments the `refresh_reuse_detected`
  metric.
- **Login rate limiting**: in-process sliding window, `LOGIN_MAX_ATTEMPTS` per
  `LOGIN_WINDOW_SECONDS` → HTTP 429 (`app/ratelimit.py`).
- Passwords hashed with **argon2** (passlib).
- Admin seeded on first boot from `ADMIN_USERNAME` / `ADMIN_PASSWORD` (`app/seed.py`).

## Audit
- `audit_log` records login success/failure/lockout, source updates, blacklist
  changes, and manual pipeline runs (`app/audit.py`). Approval/submit actions added
  in later phases.

## Transport
- HTTPS only (Let's Encrypt). Nginx: HTTP→HTTPS redirect, HSTS, `X-Frame-Options`,
  `X-Content-Type-Options`, `Referrer-Policy`.

## Secrets
- All secrets in `.env` (chmod 600), never committed.
- Three guards keep secrets out of git: `.gitignore`, `github-backup.sh` abort check,
  CI workflow assertion.
- Future: AWS Secrets Manager / SSM Parameter Store via instance IAM role.

## Network
- Security Group: SSH from your IP only; only 80/443 public.
- PostgreSQL on Docker internal network — never host-exposed.

## Data / PII
- Profile + resumes restricted to the app; EBS encrypted at rest (enable on volume).
- Resume files stored on a Docker volume, not in git.

## Application safety (later phases)
- Restricted fields (diversity/disability/veteran/legal) enforced server-side;
  auto-submit refuses if any are unanswered.
- Truthfulness guard in material generation (facts-only).
- Audit log of every approval/submit.
