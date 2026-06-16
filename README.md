# job-agent

Production-grade Job Discovery & Application Management Platform (single-user).

- **Deploy target:** `jobs.<your-domain>`
- **Host:** AWS EC2 `t3.small` (2 vCPU / 2 GB / 50 GB gp3), Ubuntu 24.04 LTS, Docker Compose — upgrade path `t3.medium`
- **Future AWS services:** S3 (backups), CloudWatch (monitoring), Route53 (DNS, optional)
- **Stack:** FastAPI (backend) · React (frontend) · PostgreSQL · Nginx + Let's Encrypt
- **Repo:** https://github.com/sameerreddy213/job-agent

> ⚠️ Phase 0 = infrastructure scaffold only. Application logic is added in later phases.

## Project structure

```
job-agent/
├── docker-compose.yml          # Orchestrates nginx, frontend, api, worker, postgres
├── .env.example                # Template for environment variables (copy to .env)
├── .gitignore                  # Excludes secrets, resumes, dumps, screenshots
├── README.md
│
├── backend/                    # FastAPI API + pipeline worker (same image)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       └── main.py             # health stub only (Phase 0)
│
├── frontend/                   # React mobile-first dashboard
│   ├── Dockerfile
│   ├── package.json
│   └── public/
│       └── index.html          # placeholder (Phase 0)
│
├── nginx/
│   ├── nginx.conf              # global config
│   └── conf.d/
│       └── jobs.conf           # jobs.<domain> reverse proxy + TLS
│
├── postgres/
│   └── init/
│       └── 01-init.sql         # DB + extensions bootstrap (schema added Phase 1)
│
├── scripts/
│   ├── deploy.sh               # pull + build + up on the VM
│   ├── backup-db.sh            # nightly pg_dump (kept OUT of git)
│   └── github-backup.sh        # daily commit of infra/config drift
│
├── infra/
│   └── aws-ec2-setup.md        # EC2 provisioning + Security Group + DNS runbook
│
└── .github/
    └── workflows/
        └── backup.yml          # scheduled daily backup workflow
```

## Quick start (after Phase 0 approval)

```bash
cp .env.example .env        # fill in values (never commit .env)
docker compose build
docker compose up -d
```

## What is NEVER committed

`.env`, resume files, database dumps, screenshots, TLS keys, any secret.
Enforced by `.gitignore`.
