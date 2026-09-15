.PHONY: dev dev-stop api web mock-llm install lint test build clean

dev:
	docker compose -f infra/docker-compose.dev.yml up -d
	@echo "Dev deps up. Run 'make api' and 'make web' in two terminals."

dev-stop:
	docker compose -f infra/docker-compose.dev.yml down

api:
	cd apps/api && poetry run uvicorn app.main:app --reload --port 8000

web:
	cd apps/web && pnpm dev

mock-llm:
	cd apps/api && poetry run python mock_llm_server.py --port 9000 --frame-delay 1.0

install:
	cd apps/api && poetry install --no-root
	pnpm install

lint:
	cd apps/api && poetry run ruff check . && poetry run mypy app
	cd apps/web && pnpm lint && pnpm tsc --noEmit

test:
	cd apps/api && poetry run pytest -v
	cd apps/web && pnpm test --run

build:
	cd apps/web && pnpm build

clean:
	cd apps/api && rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	cd apps/web && rm -rf dist node_modules/.vite
