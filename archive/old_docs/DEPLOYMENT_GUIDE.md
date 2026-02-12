# Deployment Guide - SOD Compliance System

## Quick Start (5 minutes)

### 1. Prerequisites
```bash
# Required
- Python 3.9+
- PostgreSQL 16+
- Redis 7+
- Docker (recommended)

# Optional
- SendGrid account (for email)
- Slack workspace (for notifications)
```

### 2. Clone and Setup
```bash
cd /path/to/compliance-agent

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
# Create .env file
cat > .env << 'EOF'
# Database
DATABASE_URL=postgresql://compliance_user:compliance_pass@localhost:5432/compliance_db

# Claude API
ANTHROPIC_API_KEY=your_anthropic_api_key

# NetSuite (already configured)
NETSUITE_ACCOUNT=5260239-SB1
NETSUITE_CONSUMER_KEY=...
NETSUITE_CONSUMER_SECRET=...
NETSUITE_TOKEN_ID=...
NETSUITE_TOKEN_SECRET=...
NETSUITE_RESTLET_URL=https://5260239-sb1.restlets.api.netsuite.com/...

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Notifications (optional)
SENDGRID_API_KEY=your_sendgrid_key
SENDGRID_FROM_EMAIL=noreply@yourcompany.com
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
COMPLIANCE_NOTIFICATION_EMAILS=admin@company.com,compliance@company.com
EOF
```

### 4. Start Infrastructure
```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Wait for services to be ready (10 seconds)
sleep 10

# Initialize database
python3 scripts/init_database.py

# Sync NetSuite data (first time - takes 2-3 minutes)
python3 scripts/sync_from_netsuite.py --limit 100
```

### 5. Test the System
```bash
# Quick validation (10 seconds)
python3 demos/quick_test.py

# Run analyzer demo
python3 demos/demo_analyzer.py
```

---

## Production Deployment

### Architecture

```
                    ┌─────────────┐
                    │   Nginx     │  (Load Balancer)
                    │   Reverse   │
                    │   Proxy     │
                    └──────┬──────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │ FastAPI  │    │ FastAPI  │    │ FastAPI  │
    │ Instance │    │ Instance │    │ Instance │
    │  (API)   │    │  (API)   │    │  (API)   │
    └─────┬────┘    └─────┬────┘    └─────┬────┘
          │               │               │
          └───────────────┼───────────────┘
                          │
                          ▼
                 ┌────────────────┐
                 │   PostgreSQL   │
                 │    (RDS/RO)    │
                 └────────────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
          ▼               ▼               ▼
   ┌──────────┐    ┌──────────┐    ┌──────────┐
   │  Celery  │    │  Celery  │    │  Celery  │
   │  Worker  │    │  Worker  │    │  Worker  │
   └─────┬────┘    └─────┬────┘    └─────┬────┘
         │               │               │
         └───────────────┼───────────────┘
                         │
                    ┌────┴─────┐
                    │  Redis   │
                    │ElastiCache│
                    └──────────┘
```

### Option 1: Docker Deployment

#### Build Images
```bash
# Build all images
docker-compose -f docker-compose.prod.yml build

# Tag images
docker tag compliance-agent-api:latest your-registry/compliance-agent-api:v1.0.0
docker tag compliance-agent-worker:latest your-registry/compliance-agent-worker:v1.0.0

# Push to registry
docker push your-registry/compliance-agent-api:v1.0.0
docker push your-registry/compliance-agent-worker:v1.0.0
```

#### Deploy
```bash
# Deploy stack
docker-compose -f docker-compose.prod.yml up -d

# Scale workers
docker-compose -f docker-compose.prod.yml up -d --scale worker=4

# Check status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f api worker beat
```

### Option 2: Kubernetes Deployment

#### Create Kubernetes Manifests

**api-deployment.yaml**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: compliance-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: compliance-api
  template:
    metadata:
      labels:
        app: compliance-api
    spec:
      containers:
      - name: api
        image: your-registry/compliance-agent-api:v1.0.0
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: compliance-secrets
              key: database-url
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: compliance-secrets
              key: anthropic-api-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

**worker-deployment.yaml**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: compliance-worker
spec:
  replicas: 4
  selector:
    matchLabels:
      app: compliance-worker
  template:
    metadata:
      labels:
        app: compliance-worker
    spec:
      containers:
      - name: worker
        image: your-registry/compliance-agent-worker:v1.0.0
        command: ["celery", "-A", "celery_app", "worker", "-l", "info"]
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: compliance-secrets
              key: database-url
        - name: CELERY_BROKER_URL
          value: "redis://redis-service:6379/0"
        resources:
          requests:
            memory: "1Gi"
            cpu: "1000m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
```

**service.yaml**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: compliance-api-service
spec:
  type: LoadBalancer
  selector:
    app: compliance-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
```

#### Deploy to Kubernetes
```bash
# Create secrets
kubectl create secret generic compliance-secrets \
  --from-literal=database-url="postgresql://..." \
  --from-literal=anthropic-api-key="sk-..." \
  --from-literal=sendgrid-api-key="SG..."

# Deploy
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/worker-deployment.yaml
kubectl apply -f k8s/beat-deployment.yaml
kubectl apply -f k8s/service.yaml

# Check status
kubectl get pods
kubectl get services

# View logs
kubectl logs -f deployment/compliance-api
```

### Option 3: AWS Deployment

#### Infrastructure (Terraform)
```hcl
# RDS PostgreSQL
resource "aws_db_instance" "compliance_db" {
  identifier           = "compliance-db"
  engine              = "postgres"
  engine_version      = "16.1"
  instance_class      = "db.t3.medium"
  allocated_storage   = 100
  storage_encrypted   = true
  db_name             = "compliance_db"
  username            = "compliance_user"
  password            = var.db_password

  vpc_security_group_ids = [aws_security_group.db_sg.id]
  db_subnet_group_name   = aws_db_subnet_group.db_subnet.name

  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
}

# ElastiCache Redis
resource "aws_elasticache_cluster" "compliance_redis" {
  cluster_id           = "compliance-redis"
  engine              = "redis"
  node_type           = "cache.t3.medium"
  num_cache_nodes     = 1
  parameter_group_name = "default.redis7"
  port                = 6379

  security_group_ids = [aws_security_group.redis_sg.id]
  subnet_group_name  = aws_elasticache_subnet_group.redis_subnet.name
}

# ECS Cluster
resource "aws_ecs_cluster" "compliance_cluster" {
  name = "compliance-cluster"
}

# ECS Task Definition - API
resource "aws_ecs_task_definition" "api" {
  family                   = "compliance-api"
  network_mode            = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                     = "1024"
  memory                  = "2048"

  container_definitions = jsonencode([{
    name  = "api"
    image = "your-registry/compliance-agent-api:v1.0.0"
    portMappings = [{
      containerPort = 8000
      protocol      = "tcp"
    }]
    environment = [
      {name = "DATABASE_URL", value = "postgresql://..."},
      {name = "ANTHROPIC_API_KEY", valueFrom = "arn:aws:secretsmanager:..."}
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = "/ecs/compliance-api"
        "awslogs-region"        = "us-east-1"
        "awslogs-stream-prefix" = "api"
      }
    }
  }])
}

# ECS Service - API
resource "aws_ecs_service" "api" {
  name            = "compliance-api"
  cluster         = aws_ecs_cluster.compliance_cluster.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = 3
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = aws_subnet.private[*].id
    security_groups = [aws_security_group.api_sg.id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api_tg.arn
    container_name   = "api"
    container_port   = 8000
  }
}
```

#### Deploy to AWS ECS
```bash
# Build and push images
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin your-account.dkr.ecr.us-east-1.amazonaws.com

docker build -t compliance-agent-api .
docker tag compliance-agent-api:latest your-account.dkr.ecr.us-east-1.amazonaws.com/compliance-agent-api:v1.0.0
docker push your-account.dkr.ecr.us-east-1.amazonaws.com/compliance-agent-api:v1.0.0

# Apply Terraform
cd terraform/
terraform init
terraform plan
terraform apply

# Update ECS service
aws ecs update-service \
  --cluster compliance-cluster \
  --service compliance-api \
  --force-new-deployment
```

---

## Monitoring & Operations

### Health Checks
```bash
# API health
curl http://your-api-url/health

# Celery worker status
celery -A celery_app inspect active

# Database connection
python3 -c "from models.database_config import DatabaseConfig; print('OK' if DatabaseConfig().test_connection() else 'FAIL')"
```

### Monitoring Tools

#### Flower (Celery Monitoring)
```bash
# Start Flower
celery -A celery_app flower --port=5555

# Access dashboard
open http://localhost:5555
```

#### API Metrics (Prometheus)
```python
# Add to api/main.py
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)
```

#### Logs
```bash
# API logs
tail -f logs/api.log

# Worker logs
tail -f logs/worker.log

# Celery beat logs
tail -f logs/beat.log
```

### Backup & Recovery

#### Database Backup
```bash
# Manual backup
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# Automated daily backup (cron)
0 2 * * * pg_dump $DATABASE_URL > /backups/compliance_$(date +\%Y\%m\%d).sql
```

#### Restore Database
```bash
# Restore from backup
psql $DATABASE_URL < backup_20260209_020000.sql
```

---

## Scaling Guidelines

### API Scaling
- **Light load**: 2-3 instances (handles ~1000 req/min)
- **Medium load**: 5-10 instances (handles ~5000 req/min)
- **Heavy load**: 10+ instances with auto-scaling

### Worker Scaling
- **Baseline**: 2-4 workers
- **Compliance scans**: Add 1 worker per 1000 users
- **Peak times**: Scale up 2-3x during scheduled scans

### Database Scaling
- **Read replicas**: Add for read-heavy workloads
- **Connection pooling**: Set max_connections=100
- **Indexes**: Ensure indexes on email, user_id, status

---

## Security Checklist

### Pre-Production
- [ ] Change all default passwords
- [ ] Enable SSL/TLS for all connections
- [ ] Configure firewall rules (restrict database access)
- [ ] Set up VPC/private subnets
- [ ] Enable database encryption at rest
- [ ] Rotate API keys regularly
- [ ] Enable audit logging

### Production
- [ ] Implement API authentication (JWT/OAuth2)
- [ ] Set up rate limiting (10 req/sec per user)
- [ ] Enable CORS only for known domains
- [ ] Use AWS Secrets Manager / HashiCorp Vault
- [ ] Set up intrusion detection
- [ ] Enable DDoS protection (CloudFlare/AWS Shield)
- [ ] Configure WAF rules

---

## Troubleshooting

### Common Issues

**1. Database connection fails**
```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Test connection
psql $DATABASE_URL

# Check firewall
telnet localhost 5432
```

**2. Celery tasks not running**
```bash
# Check Redis
redis-cli ping

# Check workers
celery -A celery_app inspect active

# Restart workers
docker-compose restart worker
```

**3. API returns 500 errors**
```bash
# Check logs
docker-compose logs api

# Check database
python3 scripts/init_database.py

# Verify environment variables
env | grep DATABASE_URL
```

**4. High memory usage**
```bash
# Check worker memory
docker stats

# Reduce concurrency
celery -A celery_app worker --concurrency=2

# Enable memory optimization
celery -A celery_app worker --max-tasks-per-child=100
```

---

## Maintenance

### Weekly Tasks
- [ ] Review violation reports
- [ ] Check for failed Celery tasks
- [ ] Monitor API response times
- [ ] Review error logs

### Monthly Tasks
- [ ] Database vacuum and analyze
- [ ] Review and update SOD rules
- [ ] Audit user access
- [ ] Review security logs

### Quarterly Tasks
- [ ] Update dependencies
- [ ] Review and optimize database indexes
- [ ] Load testing
- [ ] Security audit

---

## Support

**Documentation**: See `docs/` directory
**Issues**: Check logs in `logs/` or Flower dashboard
**Updates**: Pull latest code and run migrations

---

**Status**: Production Ready ✅

**Last Updated**: 2026-02-09
