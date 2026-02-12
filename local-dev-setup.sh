#!/bin/bash

# NetSuite SOD Compliance Agent - Local Development Setup
# This script sets up a complete local development environment

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Main setup
print_header "SOD Compliance Agent - Local Setup"

echo "This script will:"
echo "  1. Check prerequisites"
echo "  2. Set up environment configuration"
echo "  3. Start Docker containers (Postgres + Redis)"
echo "  4. Initialize database schema"
echo "  5. Load sample SOD rules"
echo "  6. Verify the setup"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 0
fi

# Step 1: Check Prerequisites
print_header "Step 1: Checking Prerequisites"

MISSING_DEPS=0

if command_exists docker; then
    print_success "Docker is installed ($(docker --version | cut -d' ' -f3))"
else
    print_error "Docker is not installed"
    print_info "Install from: https://docs.docker.com/get-docker/"
    MISSING_DEPS=1
fi

if command_exists docker-compose || docker compose version >/dev/null 2>&1; then
    print_success "Docker Compose is available"
else
    print_error "Docker Compose is not available"
    MISSING_DEPS=1
fi

if command_exists python3; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_success "Python is installed (v$PYTHON_VERSION)"

    # Check if Python version is >= 3.11
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
    if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]; }; then
        print_warning "Python 3.11+ is recommended (you have $PYTHON_VERSION)"
    fi
else
    print_error "Python 3 is not installed"
    MISSING_DEPS=1
fi

if command_exists poetry; then
    print_success "Poetry is installed ($(poetry --version | cut -d' ' -f3))"
else
    print_warning "Poetry is not installed (optional but recommended)"
    print_info "Install: curl -sSL https://install.python-poetry.org | python3 -"
fi

if [ $MISSING_DEPS -eq 1 ]; then
    print_error "Missing required dependencies. Please install them and run this script again."
    exit 1
fi

# Step 2: Environment Configuration
print_header "Step 2: Setting Up Environment Configuration"

if [ -f .env ]; then
    print_warning ".env file already exists"
    read -p "Do you want to overwrite it? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Skipping .env creation"
    else
        cp .env.example .env
        print_success "Created .env from .env.example"
    fi
else
    cp .env.example .env
    print_success "Created .env from .env.example"
fi

# Check if API keys are set
print_info "Checking for required API keys in .env..."

if grep -q "ANTHROPIC_API_KEY=sk-ant-xxxxx" .env; then
    print_warning "Claude API key not set in .env"
    echo -n "Enter your Anthropic API key (or press Enter to skip): "
    read ANTHROPIC_KEY
    if [ ! -z "$ANTHROPIC_KEY" ]; then
        sed -i.bak "s/ANTHROPIC_API_KEY=.*/ANTHROPIC_API_KEY=$ANTHROPIC_KEY/" .env
        rm .env.bak 2>/dev/null || true
        print_success "Claude API key configured"
    else
        print_warning "Continuing without Claude API key (mock mode only)"
    fi
fi

# Ask about mock mode
print_info "For local development, you can use mock data (no NetSuite connection needed)"
read -p "Enable mock mode? (recommended for initial testing) (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "" >> .env
    echo "# Mock mode for local development" >> .env
    echo "USE_MOCK_DATA=true" >> .env
    echo "MOCK_USERS_COUNT=50" >> .env
    echo "MOCK_VIOLATIONS_RATE=0.15" >> .env
    print_success "Mock mode enabled"
else
    print_info "Mock mode disabled - you'll need NetSuite credentials"
fi

# Step 3: Start Docker Containers
print_header "Step 3: Starting Docker Containers"

print_info "Starting PostgreSQL and Redis..."
if docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

$COMPOSE_CMD up -d postgres redis

print_info "Waiting for PostgreSQL to be ready..."
sleep 5

# Wait for Postgres to be healthy
MAX_RETRIES=30
RETRY_COUNT=0
until docker exec compliance-postgres pg_isready -U compliance_user -d compliance_db >/dev/null 2>&1; do
    RETRY_COUNT=$((RETRY_COUNT+1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        print_error "PostgreSQL failed to start after $MAX_RETRIES attempts"
        exit 1
    fi
    echo -n "."
    sleep 2
done
echo ""
print_success "PostgreSQL is ready"

# Check Redis
if docker exec compliance-redis redis-cli ping >/dev/null 2>&1; then
    print_success "Redis is ready"
else
    print_warning "Redis may not be ready yet"
fi

# Step 4: Initialize Database
print_header "Step 4: Initializing Database Schema"

print_info "Applying database schema..."
docker exec -i compliance-postgres psql -U compliance_user -d compliance_db < database/schema.sql 2>&1 | grep -v "NOTICE" || true

print_success "Database schema applied"

# Verify schema
TABLE_COUNT=$(docker exec compliance-postgres psql -U compliance_user -d compliance_db -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | xargs)
print_info "Created $TABLE_COUNT tables"

# Check pgvector extension
if docker exec compliance-postgres psql -U compliance_user -d compliance_db -t -c "SELECT extname FROM pg_extension WHERE extname = 'vector';" | grep -q "vector"; then
    print_success "pgvector extension is enabled"
else
    print_warning "pgvector extension not found (may need manual installation)"
fi

# Step 5: Load Sample SOD Rules
print_header "Step 5: Loading Sample SOD Rules"

# Create a simple Python script to load rules
cat > /tmp/load_sod_rules.py << 'PYEOF'
import json
import psycopg2
import sys

try:
    # Read rules from JSON
    with open('database/seed_data/sod_rules.json', 'r') as f:
        rules = json.load(f)

    # Connect to database
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='compliance_db',
        user='compliance_user',
        password='compliance_pass'
    )
    cur = conn.cursor()

    # Insert rules
    for rule in rules:
        cur.execute("""
            INSERT INTO sod_rules (
                rule_id, rule_name, description, rule_type,
                conflicting_permissions, severity, regulatory_framework,
                remediation_guidance, is_active
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (rule_id) DO NOTHING
        """, (
            rule['rule_id'],
            rule['rule_name'],
            rule['description'],
            rule['rule_type'],
            json.dumps(rule['conflicting_permissions']),
            rule['severity'],
            rule['regulatory_framework'],
            rule['remediation_guidance'],
            True
        ))

    conn.commit()
    cur.close()
    conn.close()

    print(f"Loaded {len(rules)} SOD rules")
    sys.exit(0)

except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
PYEOF

print_info "Loading SOD rules into database..."
if python3 /tmp/load_sod_rules.py 2>/dev/null; then
    print_success "Sample SOD rules loaded"
else
    print_warning "Could not load rules automatically (psycopg2 may not be installed)"
    print_info "You can load them later with: poetry run python scripts/seed_rules.py"
fi
rm /tmp/load_sod_rules.py 2>/dev/null || true

# Verify rules
RULE_COUNT=$(docker exec compliance-postgres psql -U compliance_user -d compliance_db -t -c "SELECT COUNT(*) FROM sod_rules;" 2>/dev/null | xargs || echo "0")
print_info "Total SOD rules in database: $RULE_COUNT"

# Step 6: Install Python Dependencies (Optional)
print_header "Step 6: Python Dependencies"

if command_exists poetry; then
    read -p "Install Python dependencies with Poetry? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Installing dependencies (this may take a few minutes)..."
        poetry install
        print_success "Python dependencies installed"
    else
        print_info "Skipping dependency installation"
        print_warning "Run 'poetry install' manually before running the agents"
    fi
else
    print_info "Poetry not found - skipping Python dependency installation"
    print_info "Install Poetry: curl -sSL https://install.python-poetry.org | python3 -"
fi

# Step 7: Verification
print_header "Step 7: Verifying Setup"

print_info "Running verification tests..."

# Test 1: Postgres connection
if docker exec compliance-postgres psql -U compliance_user -d compliance_db -c "SELECT 1" >/dev/null 2>&1; then
    print_success "PostgreSQL connection test passed"
else
    print_error "PostgreSQL connection test failed"
fi

# Test 2: Redis connection
if docker exec compliance-redis redis-cli ping >/dev/null 2>&1; then
    print_success "Redis connection test passed"
else
    print_error "Redis connection test failed"
fi

# Test 3: Database tables
if docker exec compliance-postgres psql -U compliance_user -d compliance_db -t -c "SELECT COUNT(*) FROM sod_rules;" >/dev/null 2>&1; then
    print_success "Database schema test passed"
else
    print_error "Database schema test failed"
fi

# Final Summary
print_header "Setup Complete! 🎉"

echo -e "${GREEN}Your local development environment is ready!${NC}\n"

echo "📊 Environment Status:"
echo "  • PostgreSQL: running on localhost:5432"
echo "  • Redis: running on localhost:6379"
echo "  • Database: compliance_db"
echo "  • SOD Rules: $RULE_COUNT loaded"
echo ""

echo "🔧 Quick Commands:"
echo ""
echo "  # Check running containers"
echo "  docker ps"
echo ""
echo "  # View Postgres logs"
echo "  docker logs compliance-postgres"
echo ""
echo "  # Connect to database"
echo "  docker exec -it compliance-postgres psql -U compliance_user -d compliance_db"
echo ""
echo "  # Stop containers"
echo "  $COMPOSE_CMD down"
echo ""
echo "  # Restart containers"
echo "  $COMPOSE_CMD restart"
echo ""

if command_exists poetry; then
    echo "🚀 Next Steps:"
    echo ""
    echo "  1. Activate poetry shell:"
    echo "     poetry shell"
    echo ""
    echo "  2. Test the setup:"
    echo "     python -c 'from config.settings import settings; print(settings)'"
    echo ""
    echo "  3. Start building agents in agents/ directory"
    echo ""
    echo "  4. Run a test scan (once implemented):"
    echo "     poetry run python scripts/run_scan.py --test-mode"
    echo ""
fi

echo "📚 Documentation:"
echo "  • Architecture: SOD_COMPLIANCE_ARCHITECTURE.md"
echo "  • README: README.md"
echo "  • Project Structure: PROJECT_STRUCTURE.md"
echo ""

echo "💡 Tips:"
echo "  • Use mock mode for development (already enabled in .env)"
echo "  • Check database with: docker exec -it compliance-postgres psql -U compliance_user -d compliance_db"
echo "  • View all rules: SELECT rule_id, rule_name, severity FROM sod_rules;"
echo ""

print_success "Happy coding! 🚀"
