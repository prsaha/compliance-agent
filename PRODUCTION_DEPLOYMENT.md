# Production Deployment Guide - SOD Compliance System

## Document Information

| Property | Value |
|----------|-------|
| **Version** | 1.0.0 |
| **Last Updated** | 2026-02-09 |
| **Environment** | Production |
| **Status** | Pre-Production Checklist |

---

## Table of Contents

1. [Pre-Deployment Checklist](#1-pre-deployment-checklist)
2. [Infrastructure Setup](#2-infrastructure-setup)
3. [Security Hardening](#3-security-hardening)
4. [Database Setup](#4-database-setup)
5. [Application Deployment](#5-application-deployment)
6. [Configuration](#6-configuration)
7. [Testing & Validation](#7-testing--validation)
8. [Monitoring & Alerting](#8-monitoring--alerting)
9. [Backup & Recovery](#9-backup--recovery)
10. [Rollback Plan](#10-rollback-plan)

---

## 1. Pre-Deployment Checklist

### 1.1 Code Readiness

- [ ] All features tested in staging environment
- [ ] Code review completed and approved
- [ ] Security audit passed
- [ ] Performance testing completed
- [ ] Load testing passed (target: 100 req/s)
- [ ] All tests passing (unit, integration, E2E)
- [ ] Documentation updated
- [ ] CHANGELOG.md updated

### 1.2 Infrastructure Readiness

- [ ] Production environment provisioned
- [ ] Database server configured
- [ ] Redis/Celery infrastructure ready
- [ ] Load balancer configured
- [ ] SSL/TLS certificates installed
- [ ] DNS records configured
- [ ] Firewall rules configured

### 1.3 Credentials & Secrets

- [ ] Production API keys obtained (Claude, NetSuite, SendGrid, Slack)
- [ ] Secrets stored in secure vault (AWS Secrets Manager, HashiCorp Vault)
- [ ] Database credentials rotated
- [ ] Service accounts created with least privilege
- [ ] OAuth credentials configured for production NetSuite

### 1.4 Compliance & Legal

- [ ] Data privacy policy reviewed
- [ ] GDPR compliance verified
- [ ] SOX audit requirements met
- [ ] Security incident response plan documented
- [ ] Data retention policy configured

---

## 2. Infrastructure Setup

### 2.1 Production Architecture

```
┌─────────────────────────────────────────────────┐
│          Internet / VPN Access                   │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│        Load Balancer (AWS ALB / Nginx)          │
│              HTTPS (Port 443)                    │
└──────────────────┬──────────────────────────────┘
                   │
        ┌──────────┼──────────┐
        │          │          │
        ▼          ▼          ▼
┌───────────┐ ┌───────────┐ ┌───────────┐
│ FastAPI   │ │ FastAPI   │ │ FastAPI   │
│ Instance 1│ │ Instance 2│ │ Instance 3│
│ (Pod/VM)  │ │ (Pod/VM)  │ │ (Pod/VM)  │
└─────┬─────┘ └─────┬─────┘ └─────┬─────┘
      │             │             │
      └─────────────┼─────────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
        ▼           ▼           ▼
┌───────────┐ ┌───────────┐ ┌───────────┐
│  Celery   │ │  Celery   │ │  Celery   │
│  Worker 1 │ │  Worker 2 │ │  Worker 3 │
└─────┬─────┘ └─────┬─────┘ └─────┬─────┘
      │             │             │
      └─────────────┼─────────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
        ▼           ▼           ▼
┌───────────┐ ┌───────────┐ ┌───────────┐
│PostgreSQL │ │   Redis   │ │  SendGrid │
│  Primary  │ │  Cluster  │ │  + Slack  │
│ +Replica  │ │           │ │           │
└───────────┘ └───────────┘ └───────────┘
```

### 2.2 Server Specifications

**API Servers** (3 instances minimum):
- CPU: 4 cores
- RAM: 8 GB
- Disk: 50 GB SSD
- OS: Ubuntu 22.04 LTS or Amazon Linux 2

**Celery Workers** (3 instances minimum):
- CPU: 4 cores
- RAM: 8 GB
- Disk: 50 GB SSD
- OS: Ubuntu 22.04 LTS or Amazon Linux 2

**Database Server**:
- CPU: 8 cores
- RAM: 32 GB
- Disk: 500 GB SSD (with auto-scaling)
- Backup: Daily automated snapshots
- High Availability: Primary + Read Replica

**Redis Cluster**:
- CPU: 2 cores
- RAM: 8 GB
- Disk: 50 GB SSD
- High Availability: Master + 2 Replicas

### 2.3 Network Configuration

```bash
# VPC Configuration
VPC CIDR: 10.0.0.0/16

# Subnets
Public Subnet:  10.0.1.0/24 (Load Balancer)
Private Subnet: 10.0.2.0/24 (API Servers)
Private Subnet: 10.0.3.0/24 (Workers)
Private Subnet: 10.0.4.0/24 (Database)
Private Subnet: 10.0.5.0/24 (Redis)

# Security Groups
- ALB: Inbound 443 from Internet, Outbound to API servers
- API: Inbound 8000 from ALB, Outbound to DB/Redis/Internet
- Workers: Outbound to DB/Redis/Internet only
- DB: Inbound 5432 from API/Workers only
- Redis: Inbound 6379 from API/Workers only
```

---

## 3. Security Hardening

### 3.1 API Security

**Enable HTTPS Only**:
```python
# api/main.py
from fastapi import FastAPI
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

app = FastAPI()
app.add_middleware(HTTPSRedirectMiddleware)
```

**Enable CORS** (restrict to production domains):
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://compliance.yourcompany.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

**Rate Limiting**:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/api/users")
@limiter.limit("100/minute")
async def get_users():
    pass
```

**JWT Authentication** (implement before production):
```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### 3.2 Database Security

**PostgreSQL Configuration**:
```sql
-- Enable SSL connections only
ALTER SYSTEM SET ssl = on;
ALTER SYSTEM SET ssl_cert_file = '/path/to/server.crt';
ALTER SYSTEM SET ssl_key_file = '/path/to/server.key';

-- Restrict connections
ALTER SYSTEM SET listen_addresses = '10.0.4.0/24';

-- Password encryption
ALTER SYSTEM SET password_encryption = 'scram-sha-256';

-- Connection limits
ALTER SYSTEM SET max_connections = 200;

-- Enable audit logging
ALTER SYSTEM SET log_connections = on;
ALTER SYSTEM SET log_disconnections = on;
ALTER SYSTEM SET log_statement = 'mod';  -- Log modifications only
```

**Row-Level Security**:
```sql
-- Enable RLS on sensitive tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_isolation_policy ON users
    USING (department = current_setting('app.current_department'));
```

### 3.3 Secrets Management

**AWS Secrets Manager** (Recommended):
```python
import boto3
import json

def get_secret(secret_name):
    client = boto3.client('secretsmanager', region_name='us-east-1')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

# Usage
secrets = get_secret('prod/compliance-agent/credentials')
ANTHROPIC_API_KEY = secrets['ANTHROPIC_API_KEY']
DATABASE_URL = secrets['DATABASE_URL']
```

**Environment Variables** (Production):
```bash
# NEVER commit these to git
export ENVIRONMENT=production
export DEBUG=false
export SECRET_KEY=<strong-random-key-here>
export DATABASE_URL=<from-secrets-manager>
export ANTHROPIC_API_KEY=<from-secrets-manager>
export NETSUITE_CONSUMER_KEY=<from-secrets-manager>
export SENDGRID_API_KEY=<from-secrets-manager>
export SLACK_WEBHOOK_URL=<from-secrets-manager>
```

---

## 4. Database Setup

### 4.1 Production Database Installation

**PostgreSQL 16 with pgvector**:
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y postgresql-16 postgresql-16-pgvector

# Enable and start
sudo systemctl enable postgresql
sudo systemctl start postgresql

# Verify
sudo -u postgres psql -c "SELECT version();"
```

### 4.2 Database Initialization

```bash
# 1. Create production database and user
sudo -u postgres psql << EOF
CREATE USER compliance_user WITH PASSWORD '<strong-password>';
CREATE DATABASE compliance_db OWNER compliance_user;
GRANT ALL PRIVILEGES ON DATABASE compliance_db TO compliance_user;
ALTER USER compliance_user WITH SUPERUSER;  -- For pgvector
EOF

# 2. Enable pgvector
sudo -u postgres psql -d compliance_db << EOF
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;
EOF

# 3. Apply schema
psql -U compliance_user -d compliance_db < database/schema.sql

# 4. Load SOD rules
python3 scripts/init_database.py --load-rules

# 5. Verify
psql -U compliance_user -d compliance_db -c "
SELECT
    schemaname,
    tablename,
    (SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public') as total_tables
FROM pg_tables
WHERE schemaname = 'public'
LIMIT 1;
"
```

### 4.3 Database Backup Configuration

**Automated Backups**:
```bash
#!/bin/bash
# /usr/local/bin/backup-compliance-db.sh

BACKUP_DIR="/backups/compliance-db"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_NAME="compliance_db"
DB_USER="compliance_user"

# Create backup
pg_dump -U $DB_USER -d $DB_NAME -F c -f "$BACKUP_DIR/backup_$TIMESTAMP.dump"

# Compress
gzip "$BACKUP_DIR/backup_$TIMESTAMP.dump"

# Upload to S3
aws s3 cp "$BACKUP_DIR/backup_$TIMESTAMP.dump.gz" \
    s3://your-backup-bucket/compliance-db/

# Cleanup old local backups (keep 7 days)
find $BACKUP_DIR -name "backup_*.dump.gz" -mtime +7 -delete

# Log
echo "$(date): Backup completed - backup_$TIMESTAMP.dump.gz" >> /var/log/compliance-backup.log
```

**Cron Schedule**:
```bash
# Daily at 2 AM
0 2 * * * /usr/local/bin/backup-compliance-db.sh
```

---

## 5. Application Deployment

### 5.1 Docker Deployment (Recommended)

**Build Production Image**:
```bash
# Build
docker build -t compliance-agent:1.0.0 -f Dockerfile.prod .

# Tag for registry
docker tag compliance-agent:1.0.0 your-registry.com/compliance-agent:1.0.0

# Push
docker push your-registry.com/compliance-agent:1.0.0
```

**Production Dockerfile**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

**Deploy with docker-compose**:
```yaml
version: '3.8'

services:
  api:
    image: your-registry.com/compliance-agent:1.0.0
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    env_file:
      - .env.production
    restart: unless-stopped
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 4G

  worker:
    image: your-registry.com/compliance-agent:1.0.0
    command: celery -A celery_app worker -l info --concurrency=4
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    env_file:
      - .env.production
    restart: unless-stopped
    deploy:
      replicas: 3

  beat:
    image: your-registry.com/compliance-agent:1.0.0
    command: celery -A celery_app beat -l info
    environment:
      - REDIS_URL=${REDIS_URL}
    restart: unless-stopped
```

### 5.2 Kubernetes Deployment

**Deploy to K8s**:
```bash
# Apply configurations
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml

# Verify
kubectl get pods -n compliance-agent
kubectl get svc -n compliance-agent
kubectl logs -f deployment/compliance-api -n compliance-agent
```

### 5.3 Traditional VM Deployment

**Systemd Service** (if not using containers):
```ini
# /etc/systemd/system/compliance-api.service
[Unit]
Description=SOD Compliance API
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=compliance
Group=compliance
WorkingDirectory=/opt/compliance-agent
Environment="PATH=/opt/compliance-agent/.venv/bin"
EnvironmentFile=/opt/compliance-agent/.env.production
ExecStart=/opt/compliance-agent/.venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable compliance-api
sudo systemctl start compliance-api
sudo systemctl status compliance-api
```

---

## 6. Configuration

### 6.1 Production Environment Variables

**Create `.env.production`**:
```bash
# CRITICAL: Never commit this file to git

# Environment
ENVIRONMENT=production
DEBUG=false

# Database
DATABASE_URL=postgresql://compliance_user:PROD_PASSWORD@db.internal:5432/compliance_db
PGVECTOR_DIMENSION=1536

# Redis
REDIS_URL=redis://redis.internal:6379/0
CELERY_BROKER_URL=redis://redis.internal:6379/0
CELERY_RESULT_BACKEND=redis://redis.internal:6379/0

# Claude API
ANTHROPIC_API_KEY=sk-ant-prod-xxxxxxxxxx
CLAUDE_MODEL_FAST=claude-sonnet-4-5-20250929
CLAUDE_MODEL_REASONING=claude-opus-4-6

# NetSuite (PRODUCTION)
NETSUITE_ACCOUNT_ID=1234567
NETSUITE_REALM=1234567
NETSUITE_CONSUMER_KEY=prod_consumer_key
NETSUITE_CONSUMER_SECRET=prod_consumer_secret
NETSUITE_TOKEN_ID=prod_token_id
NETSUITE_TOKEN_SECRET=prod_token_secret
NETSUITE_RESTLET_URL=https://1234567.restlets.api.netsuite.com/app/site/hosting/restlet.nl?script=XXXX&deploy=1

# Notifications
SENDGRID_API_KEY=SG.prod_key_here
SENDGRID_FROM_EMAIL=compliance-alerts@yourcompany.com
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/PROD/WEBHOOK/URL
SLACK_CHANNEL=#compliance-alerts

# Security
SECRET_KEY=<generate-with-openssl-rand-hex-32>
JWT_SECRET=<generate-with-openssl-rand-hex-32>

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Scheduling
SCAN_INTERVAL_HOURS=4
SCAN_TIMEZONE=America/New_York

# Risk Thresholds
CRITICAL_THRESHOLD=90
HIGH_THRESHOLD=70
MEDIUM_THRESHOLD=40

# Notifications
NOTIFY_CRITICAL_IMMEDIATELY=true
NOTIFY_HIGH_DAILY=true
NOTIFY_MEDIUM_WEEKLY=true

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Rate Limiting
NETSUITE_API_RATE_LIMIT=10
CLAUDE_API_RATE_LIMIT=50

# Features
ENABLE_VECTOR_SEARCH=true
ENABLE_HISTORICAL_ANALYSIS=true
USE_MOCK_DATA=false
```

### 6.2 Generate Secrets

```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Generate JWT_SECRET
openssl rand -hex 32

# Store in secrets manager
aws secretsmanager create-secret \
    --name prod/compliance-agent/secrets \
    --secret-string '{
        "SECRET_KEY": "generated-key-here",
        "JWT_SECRET": "generated-jwt-here",
        "DATABASE_PASSWORD": "strong-db-password"
    }'
```

---

## 7. Testing & Validation

### 7.1 Pre-Production Testing

**Smoke Tests**:
```bash
# 1. Health check
curl https://compliance.yourcompany.com/health
# Expected: {"status":"healthy","timestamp":"..."}

# 2. Database connectivity
python3 << EOF
from models.database_config import get_db_config
db = get_db_config()
assert db.test_connection(), "Database connection failed"
print("✓ Database OK")
EOF

# 3. NetSuite connectivity
python3 << EOF
from services.netsuite_client import NetSuiteClient
client = NetSuiteClient()
assert client.test_connection(), "NetSuite connection failed"
print("✓ NetSuite OK")
EOF

# 4. Redis connectivity
redis-cli -h redis.internal ping
# Expected: PONG

# 5. Run quick test
PYTHONPATH=. python3 demos/quick_test.py
```

### 7.2 Load Testing

**Run Load Tests** (before going live):
```bash
# Install locust
pip install locust

# Run load test
locust -f tests/locustfile.py \
    --host https://compliance.yourcompany.com \
    --users 100 \
    --spawn-rate 10 \
    --run-time 10m \
    --headless

# Target metrics:
# - 95th percentile response time < 500ms
# - Error rate < 1%
# - Throughput > 100 req/s
```

### 7.3 Security Testing

```bash
# 1. SSL/TLS verification
sslyze --regular compliance.yourcompany.com

# 2. Security headers check
curl -I https://compliance.yourcompany.com | grep -E "Strict-Transport-Security|X-Frame-Options|X-Content-Type-Options"

# 3. Dependency vulnerability scan
pip install safety
safety check -r requirements.txt

# 4. OWASP ZAP scan
docker run -t owasp/zap2docker-stable zap-baseline.py \
    -t https://compliance.yourcompany.com
```

---

## 8. Monitoring & Alerting

### 8.1 Application Monitoring

**Setup Prometheus + Grafana**:
```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'compliance-api'
    static_configs:
      - targets: ['api-1:8000', 'api-2:8000', 'api-3:8000']
```

**Key Metrics to Monitor**:
- API response time (p50, p95, p99)
- Error rate
- Request rate
- Database connection pool usage
- Celery queue length
- Worker task completion rate
- Violation detection rate
- System resources (CPU, memory, disk)

### 8.2 Log Aggregation

**Setup ELK Stack** or **CloudWatch Logs**:
```python
# Configure structured logging
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'service': 'compliance-api',
            'module': record.module,
            'message': record.getMessage(),
            'trace_id': getattr(record, 'trace_id', None)
        }
        return json.dumps(log_data)

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logging.root.addHandler(handler)
```

### 8.3 Alerts Configuration

**Critical Alerts** (PagerDuty/Opsgenie):
```yaml
# alertmanager/alerts.yml
groups:
  - name: critical_alerts
    rules:
      - alert: APIDown
        expr: up{job="compliance-api"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "API is down"

      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical

      - alert: DatabaseConnectionsFull
        expr: pg_stat_database_connections > 180
        for: 2m
        labels:
          severity: warning
```

---

## 9. Backup & Recovery

### 9.1 Backup Strategy

**Daily Backups**:
- Database: Full backup at 2 AM daily
- Retention: 30 days
- Storage: AWS S3 with versioning

**Recovery Testing**:
```bash
# Test restore monthly
pg_restore -U compliance_user -d compliance_db_test backup_20260209.dump

# Verify data integrity
psql -U compliance_user -d compliance_db_test -c "
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM violations;
SELECT COUNT(*) FROM sod_rules;
"
```

### 9.2 Disaster Recovery

**RTO/RPO**:
- Recovery Time Objective (RTO): 1 hour
- Recovery Point Objective (RPO): 24 hours

**DR Runbook**:
1. Restore database from latest backup
2. Verify data integrity
3. Deploy application from last known good image
4. Run smoke tests
5. Update DNS to failover region (if applicable)

---

## 10. Rollback Plan

### 10.1 Quick Rollback Procedure

```bash
# 1. Identify last working version
docker images | grep compliance-agent

# 2. Rollback to previous version
kubectl set image deployment/compliance-api \
    api=your-registry.com/compliance-agent:0.9.0

# Or with docker-compose
docker-compose down
docker-compose up -d --image your-registry.com/compliance-agent:0.9.0

# 3. Verify rollback
curl https://compliance.yourcompany.com/health

# 4. Notify team
echo "Rollback completed to version 0.9.0" | \
    slack-cli chat send -c #compliance-alerts
```

---

## Deployment Checklist

### Week Before Deployment
- [ ] Staging environment fully tested
- [ ] Load tests passed
- [ ] Security audit completed
- [ ] Documentation reviewed
- [ ] Backup procedures tested
- [ ] Rollback plan documented

### Day Before Deployment
- [ ] Stakeholders notified
- [ ] Maintenance window scheduled
- [ ] On-call team briefed
- [ ] Production credentials verified
- [ ] Monitoring dashboards prepared

### Deployment Day
- [ ] Final staging test
- [ ] Database backup taken
- [ ] Deploy to production
- [ ] Run smoke tests
- [ ] Monitor for 2 hours
- [ ] Send success notification

### Post-Deployment
- [ ] Monitor for 24 hours
- [ ] Review error logs
- [ ] Check alert configuration
- [ ] Document any issues
- [ ] Post-mortem if needed

---

## Quick Reference Commands

```bash
# Health check
curl https://compliance.yourcompany.com/health

# View logs
kubectl logs -f deployment/compliance-api
# or
docker-compose logs -f api

# Restart service
kubectl rollout restart deployment/compliance-api
# or
docker-compose restart api

# Database connection
psql postgresql://compliance_user:PASSWORD@db.internal:5432/compliance_db

# Redis connection
redis-cli -h redis.internal

# Check Celery workers
celery -A celery_app inspect active

# Manual compliance scan
curl -X POST https://compliance.yourcompany.com/api/scans/full \
    -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Support Contacts

- **On-Call Engineer**: pagerduty.com/escalate
- **Database Admin**: dba-team@yourcompany.com
- **Security Team**: security@yourcompany.com
- **DevOps Team**: devops@yourcompany.com

---

**END OF PRODUCTION DEPLOYMENT GUIDE**
