# AWS Deployment — job-agent

Authoritative provisioning steps live in [`infra/aws-ec2-setup.md`](../infra/aws-ec2-setup.md).
This doc summarizes the target topology.

## Topology
- **Compute:** 1× EC2 `t3.small` (2 vCPU / 2 GB), Ubuntu 24.04 LTS, 50 GB gp3 EBS.
  Upgrade path: `t3.medium` (4 GB).
- **Networking:** Elastic IP; Security Group — 22 (your IP /32), 80, 443 only.
  PostgreSQL 5432 never exposed (Docker internal network).
- **DNS:** A record `jobs.<domain>` → Elastic IP (Route53 optional).
- **TLS:** Nginx + Certbot (Let's Encrypt), 12h auto-renew loop.
- **IAM:** instance role for future S3 backups + CloudWatch (no static keys).

## Future AWS services
- **S3:** off-host DB/config backups (`backup-db.sh` extension).
- **CloudWatch:** host/container metrics, log shipping, billing alarms.
- **Route53:** managed DNS + health checks.

## Deploy flow
```
git clone → cp .env.example .env (chmod 600) → set domain in nginx →
issue cert (certbot once) → ./scripts/deploy.sh → verify /api/health
```

## Cost
- `t3.small` on-demand ≈ $15/mo (less with Savings Plan). EBS 50 GB gp3 ≈ $4/mo.
- AWS Budgets alert at 50/80/90%; enable free-tier alerts.
