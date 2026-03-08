.PHONY: dev test lint install migrate docker-up docker-down eval

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

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

eval:
	python -m app.testing.runner
