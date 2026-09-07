.PHONY: help up down logs build lint test-backend test-frontend migrate seed clean eval

help:
	@echo "RegPulse Development Commands:"
	@echo ""
	@echo "  make up              Start all services (docker compose)"
	@echo "  make down            Stop all services"
	@echo "  make logs            Follow logs (all services)"
	@echo "  make build           Build all Docker images"
	@echo "  make lint            Run ruff + black (backend) + eslint (frontend)"
	@echo "  make test-backend    Run backend pytest"
	@echo "  make test-frontend   Run frontend build (type-check + lint)"
	@echo "  make migrate         Run Alembic migrations"
	@echo "  make seed            Seed admin user + initial prompt"
	@echo "  make clean           Remove build artifacts"
	@echo ""
	@echo "Jira Commands:"
	@echo "  make jira-status ISSUE=RP-2"
	@echo "  make jira-done ISSUE=RP-2 MSG='...'"

# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------
up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

build:
	docker compose build

# ---------------------------------------------------------------------------
# Quality
# ---------------------------------------------------------------------------
lint:
	cd backend && ruff check . && black --check --line-length 100 .
	cd frontend && npx next lint

test-backend:
	PYTHONPATH=backend pytest backend/tests/unit/ -v

test-frontend:
	cd frontend && npx tsc --noEmit && npx next lint && npx next build

test: test-backend test-frontend

eval:
	docker compose run --rm --build \
		-e PYTHONPATH=/app \
		backend bash -c "pip install -q pytest pytest-asyncio && pytest tests/evals/ -v"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
migrate:
	cd backend && alembic upgrade head

seed:
	@echo "Seed command — implement via backend/scripts/seed.py"

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf frontend/.next 2>/dev/null || true

# ---------------------------------------------------------------------------
# Jira integration
# ---------------------------------------------------------------------------
jira-status:
	@./scripts/jira.sh status $(ISSUE)

jira-transitions:
	@./scripts/jira.sh transitions $(ISSUE)

jira-move:
	@./scripts/jira.sh move $(ISSUE) "$(STATUS)"

jira-comment:
	@./scripts/jira.sh comment $(ISSUE) "$(MSG)"

jira-done:
	@./scripts/jira.sh update $(ISSUE) "Done" "$(MSG)"

jira-progress:
	@./scripts/jira.sh update $(ISSUE) "In Progress" "$(MSG)"
