# AWS EC2 Setup Runbook — job-agent

Provisioning and first-deploy steps for the single Ubuntu 24.04 EC2 host.

## 1. Provision the EC2 instance
- **AMI:** Ubuntu Server 24.04 LTS (x86_64)
- **Type:** `t3.small` (2 vCPU / 2 GB) — recommended; future upgrade path `t3.medium` (2 vCPU / 4 GB)
- **Storage:** 50 GB gp3 EBS
- **Key pair:** create/download an SSH key pair for login
- **Elastic IP:** allocate and associate one (so DNS doesn't break on stop/start)

## 2. Security Group (inbound rules)
| Port | Source | Purpose |
|------|--------|---------|
| 22   | **Your IP only (x.x.x.x/32)** | SSH |
| 80   | 0.0.0.0/0 | HTTP (ACME challenge + redirect) |
| 443  | 0.0.0.0/0 | HTTPS (dashboard + API) |
| all else | Deny (default) | — |

PostgreSQL (5432) is **never** exposed — it stays on the Docker internal network.

## 3. DNS
Create an **A record**: `jobs.<your-domain>` → EC2 Elastic IP.
- If using **Route53**: create a hosted zone for your domain (optional) and add the A record there.
- Otherwise add the A record at your existing DNS provider.

Wait for propagation before issuing TLS certs.

## 4. IAM (for future S3 backups + CloudWatch)
Attach an **IAM role** to the instance (instance profile) instead of storing keys:
- `s3:PutObject` / `s3:ListBucket` scoped to your backup bucket (future S3 backups)
- `cloudwatch:PutMetricData` + CloudWatch Logs write (future monitoring)

For MVP these are optional; add the role when you enable S3/CloudWatch.

## 5. Install Docker
```bash
sudo apt-get update && sudo apt-get upgrade -y
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER       # re-login after this
```

## 6. Get the code
```bash
sudo mkdir -p /opt/job-agent && sudo chown $USER /opt/job-agent
git clone https://github.com/sameerreddy213/job-agent /opt/job-agent
cd /opt/job-agent
cp .env.example .env
chmod 600 .env
# edit .env: DOMAIN, ACME_EMAIL, passwords, JWT_SECRET, tokens
```

## 7. Set the real domain in nginx
Replace `jobs.example.com` with your domain in `nginx/conf.d/jobs.conf`.

## 8. Issue the TLS certificate (first time)
Start nginx on port 80 only, then run certbot once:
```bash
docker compose up -d nginx
docker compose run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  -d jobs.<your-domain> \
  --email "$ACME_EMAIL" --agree-tos --no-eff-email
docker compose restart nginx
```
The `certbot` service then auto-renews every 12h.

## 9. Deploy the stack
```bash
./scripts/deploy.sh
```

## 10. Schedule backups (cron)
```bash
crontab -e
# DB dump nightly at 02:00 (stays on EC2, git-ignored)
0 2 * * * /opt/job-agent/scripts/backup-db.sh >> /opt/job-agent/backups/backup.log 2>&1
# GitHub config/infra backup at 03:00
0 3 * * * /opt/job-agent/scripts/github-backup.sh >> /opt/job-agent/backups/github.log 2>&1
```

## 11. Future AWS services (not required for MVP)
- **S3 backups:** sync `./backups` to `s3://<bucket>/job-agent/` via IAM role (extend `backup-db.sh`).
- **CloudWatch:** install the CloudWatch agent for host/container metrics + log shipping; set billing/budget alarms.
- **Route53:** manage `jobs.<domain>` and health checks.

## 12. Cost guard
Create an **AWS Budgets** alert (Billing console) with notifications at 50/80/90%.
Enable free-tier usage alerts.

## Verify
```bash
docker compose ps                 # all services up
curl -k https://jobs.<domain>/api/health   # -> {"status":"ok","phase":0}
```
