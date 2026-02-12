# Quick Start Guide - Local Development

Get your SOD Compliance Agent running locally in 5 minutes!

## 🚀 One-Command Setup

```bash
./local-dev-setup.sh
```

This script will:
- ✅ Check prerequisites (Docker, Python, Poetry)
- ✅ Create `.env` configuration
- ✅ Start PostgreSQL + Redis containers
- ✅ Initialize database schema with pgvector
- ✅ Load 18 sample SOD rules
- ✅ Verify everything works

## 📋 Prerequisites

Before running the setup script, make sure you have:

- **Docker Desktop** - [Install](https://docs.docker.com/get-docker/)
- **Python 3.11+** - Check with `python3 --version`
- **Poetry** (optional but recommended) - [Install](https://python-poetry.org/docs/#installation)

## 🎯 Step-by-Step Manual Setup

If you prefer manual setup:

### 1. Install Dependencies
```bash
poetry install
# or if not using Poetry:
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env and add your API keys
nano .env
```

**Required settings:**
```bash
ANTHROPIC_API_KEY=sk-ant-your-key-here
DATABASE_URL=postgresql://compliance_user:compliance_pass@localhost:5432/compliance_db
REDIS_URL=redis://localhost:6379/0
```

**For local testing (no NetSuite needed):**
```bash
USE_MOCK_DATA=true
```

### 3. Start Infrastructure
```bash
docker-compose up -d
# or use make:
make start
```

### 4. Verify Setup
```bash
poetry run python scripts/verify_setup.py
# or use make:
make verify
```

## 🔧 Common Commands (Makefile)

We've created a Makefile with helpful shortcuts:

```bash
# View all available commands
make help

# Setup and verify environment
make setup          # Run setup script
make verify         # Verify everything works
make status         # Check container status

# Container management
make start          # Start Postgres + Redis
make stop           # Stop containers
make restart        # Restart containers
make logs           # View all logs

# Database operations
make db-shell       # Connect to Postgres
make db-helper      # Interactive database menu
make db-reset       # Reset database (careful!)

# Development
make install        # Install dependencies
make format         # Format code
make lint           # Lint code
make test           # Run tests

# Running the application (when implemented)
make run-api        # Start FastAPI server
make run-worker     # Start Celery worker
make run-scan       # Run compliance scan
```

## 🗃️ Database Operations

### Quick Database Commands

```bash
# Connect to database
docker exec -it compliance-postgres psql -U compliance_user -d compliance_db

# View SOD rules
SELECT rule_id, rule_name, severity FROM sod_rules;

# Check if pgvector is enabled
SELECT * FROM pg_extension WHERE extname = 'vector';

# View table list
\dt
```

### Using the Database Helper

```bash
./scripts/db_helper.sh
# or
make db-helper
```

Interactive menu with options:
- View all SOD rules
- View database schema
- View recent violations
- Backup database
- Run custom queries
- And more!

## 🧪 Verify Your Setup

After running the setup, test each component:

```bash
# Test database
docker exec compliance-postgres psql -U compliance_user -d compliance_db -c "SELECT 'DB OK' as status;"

# Test Redis
docker exec compliance-redis redis-cli ping

# Test Python environment
poetry run python -c "from config.settings import settings; print('Python OK')"

# Run full verification
poetry run python scripts/verify_setup.py
```

## 📂 Project Structure

```
compliance-agent/
├── local-dev-setup.sh      # Automated setup script ⭐
├── Makefile                # Convenient commands ⭐
├── docker-compose.yml      # Container definitions
├── .env                    # Your configuration (create from .env.example)
│
├── agents/                 # LangChain agents (you'll build these)
├── database/
│   ├── schema.sql         # Database schema
│   └── seed_data/         # Sample SOD rules
├── scripts/
│   ├── verify_setup.py    # Verification script
│   └── db_helper.sh       # Database helper
│
└── [Your code here]       # Start building!
```

## 🎓 Next Steps After Setup

### 1. Explore the Database
```bash
make db-shell
```
```sql
-- See all SOD rules
SELECT rule_id, rule_name, severity, rule_type FROM sod_rules;

-- See rule details
SELECT * FROM sod_rules WHERE rule_id = 'SOD-FIN-001';
```

### 2. Test Python Environment
```bash
poetry shell
python
```
```python
# Test imports
from config.settings import settings
print(settings.database_url)

# Test database connection
import psycopg2
conn = psycopg2.connect(settings.database_url)
print("Database connected!")
```

### 3. Start Building Your First Agent

Create `agents/data_collector.py`:
```python
from langchain_anthropic import ChatAnthropic
from langchain.agents import tool

@tool
def fetch_users():
    """Fetch users from NetSuite"""
    # Your implementation here
    return []

# Create agent
llm = ChatAnthropic(model="claude-sonnet-4-5-20250929")
agent = create_react_agent(llm, tools=[fetch_users])
```

### 4. Run Tests (when you write them)
```bash
make test
```

## 🆘 Troubleshooting

### Port Already in Use
```bash
# Check what's using port 5432 (Postgres)
lsof -i :5432

# Or use different ports in docker-compose.yml
ports:
  - "5433:5432"  # Map to different host port
```

### Database Connection Failed
```bash
# Check container status
docker ps

# View Postgres logs
docker logs compliance-postgres

# Restart Postgres
docker-compose restart postgres
```

### Poetry Not Found
```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Or use pip
pip install poetry
```

### Docker Permission Issues (Linux)
```bash
# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

## 💡 Development Tips

### Use Mock Mode for Development
Set in `.env`:
```bash
USE_MOCK_DATA=true
MOCK_USERS_COUNT=50
```

This lets you develop without NetSuite access!

### Hot Reload
When running the API:
```bash
make run-api
# Changes to Python files auto-reload
```

### View Logs in Real-Time
```bash
# All logs
make logs

# Just database
docker logs -f compliance-postgres

# Just Redis
docker logs -f compliance-redis
```

### Database Snapshots
```bash
# Backup before major changes
make db-helper  # Choose "Backup database"

# Or manually
docker exec compliance-postgres pg_dump -U compliance_user compliance_db > backup.sql

# Restore
docker exec -i compliance-postgres psql -U compliance_user -d compliance_db < backup.sql
```

## 📚 Documentation Links

- **[Architecture](./SOD_COMPLIANCE_ARCHITECTURE.md)** - Complete system design
- **[README](./README.md)** - Full project documentation
- **[Project Structure](./PROJECT_STRUCTURE.md)** - Code organization

## ✅ Checklist

Before you start building, make sure:

- [ ] Docker is running (`docker ps` works)
- [ ] Postgres container is healthy (`make status`)
- [ ] Redis container is healthy (`make status`)
- [ ] Database has SOD rules (`make db-shell` → `SELECT COUNT(*) FROM sod_rules;`)
- [ ] Python dependencies installed (`poetry install`)
- [ ] Verification passes (`make verify`)
- [ ] `.env` file configured

## 🎉 You're Ready!

Everything is set up for local development. Start building your agents in the `agents/` directory!

```bash
# Quick verification
make verify

# Check status
make status

# Start coding!
code .
```

---

**Need help?** Check the main [README.md](./README.md) or review the [Architecture Document](./SOD_COMPLIANCE_ARCHITECTURE.md).
