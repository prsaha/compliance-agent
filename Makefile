.PHONY: help setup start stop restart logs db-shell db-helper verify clean test install

# Default target
help:
	@echo "SOD Compliance Agent - Development Commands"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make setup          - Run local development setup"
	@echo "  make install        - Install Python dependencies"
	@echo ""
	@echo "Container Management:"
	@echo "  make start          - Start all containers"
	@echo "  make stop           - Stop all containers"
	@echo "  make restart        - Restart all containers"
	@echo "  make logs           - View container logs"
	@echo "  make logs-api       - View API logs"
	@echo "  make logs-db        - View database logs"
	@echo ""
	@echo "Database:"
	@echo "  make db-shell       - Connect to Postgres shell"
	@echo "  make db-helper      - Database helper menu"
	@echo "  make db-reset       - Reset database (WARNING: deletes data)"
	@echo ""
	@echo "Development:"
	@echo "  make verify         - Verify local setup"
	@echo "  make test           - Run tests"
	@echo "  make format         - Format code with black"
	@echo "  make lint           - Lint code with ruff"
	@echo ""
	@echo "Running:"
	@echo "  make run-api        - Start FastAPI server"
	@echo "  make run-worker     - Start Celery worker"
	@echo "  make run-scan       - Run compliance scan"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean          - Remove generated files"
	@echo "  make clean-all      - Remove everything (containers, volumes, cache)"

# Setup
setup:
	@./local-dev-setup.sh

install:
	@echo "Installing dependencies with Poetry..."
	@poetry install

# Container management
start:
	@echo "Starting containers..."
	@docker compose up -d

stop:
	@echo "Stopping containers..."
	@docker compose down

restart:
	@echo "Restarting containers..."
	@docker compose restart

logs:
	@docker compose logs -f

logs-api:
	@docker compose logs -f app

logs-db:
	@docker compose logs -f postgres

# Database
db-shell:
	@docker exec -it compliance-postgres psql -U compliance_user -d compliance_db

db-helper:
	@./scripts/db_helper.sh

db-reset:
	@echo "⚠️  WARNING: This will delete all data!"
	@read -p "Type 'yes' to confirm: " confirm && [ "$$confirm" = "yes" ] && \
		docker exec compliance-postgres psql -U compliance_user -d compliance_db -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" && \
		docker exec -i compliance-postgres psql -U compliance_user -d compliance_db < database/schema.sql && \
		echo "✓ Database reset complete"

# Development
verify:
	@poetry run python scripts/verify_setup.py

test:
	@poetry run pytest -v

test-cov:
	@poetry run pytest --cov --cov-report=html

format:
	@poetry run black .

lint:
	@poetry run ruff check .

# Running
run-api:
	@poetry run uvicorn api.main:app --reload

run-worker:
	@poetry run celery -A workflows.tasks worker --loglevel=info

run-beat:
	@poetry run celery -A workflows.tasks beat --loglevel=info

run-scan:
	@poetry run python scripts/run_scan.py

# Cleanup
clean:
	@echo "Cleaning up generated files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@rm -rf htmlcov .coverage
	@echo "✓ Cleanup complete"

clean-all: clean stop
	@echo "⚠️  WARNING: This will remove all containers and volumes!"
	@read -p "Type 'yes' to confirm: " confirm && [ "$$confirm" = "yes" ] && \
		docker compose down -v && \
		echo "✓ Complete cleanup done"

# Status
status:
	@echo "Container Status:"
	@docker ps --filter "name=compliance-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
	@echo ""
	@echo "Database Info:"
	@docker exec compliance-postgres psql -U compliance_user -d compliance_db -t -c "SELECT 'Users: ' || COUNT(*) FROM users;" 2>/dev/null || echo "Database not ready"
	@docker exec compliance-postgres psql -U compliance_user -d compliance_db -t -c "SELECT 'SOD Rules: ' || COUNT(*) FROM sod_rules;" 2>/dev/null || echo "Database not ready"
	@docker exec compliance-postgres psql -U compliance_user -d compliance_db -t -c "SELECT 'Violations: ' || COUNT(*) FROM violations;" 2>/dev/null || echo "Database not ready"

# Poetry shell
shell:
	@poetry shell

# Quick development cycle
dev: start verify
	@echo "✓ Development environment ready!"
	@echo ""
	@echo "Next: Open a new terminal and run:"
	@echo "  make run-api    (to start API server)"
	@echo "  make run-worker (to start Celery worker)"
