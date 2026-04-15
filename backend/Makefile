.PHONY: dev test lint install migrate docker-dev docker-prod docker-down docker-down-prod db-shell eval

install:
	pip install -e ".[dev]"

dev:
	uvicorn app.main:create_app --factory --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v --tb=short

lint:
	ruff check app/ tests/
	mypy app/

migrate:
	alembic upgrade head

docker-dev:
	docker compose up -d --build

docker-prod:
	docker compose -f docker-compose.prod.yml up -d --build

docker-down:
	docker compose down

docker-down-prod:
	docker compose -f docker-compose.prod.yml down

db-shell:
	docker compose exec postgres psql -U cookd

eval:
	python -m app.testing

eval-judge:
	python -m app.testing --variants default --runs 3 --judge

eval-compare:
	python -m app.testing --variants default minimal no_critique no_examples --runs 2
