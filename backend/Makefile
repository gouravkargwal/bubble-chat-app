.PHONY: dev test lint install migrate docker-dev docker-prod docker-down docker-down-prod db-shell eval eval-compare eval-category eval-before eval-after eval-diff cache-clear-before cache-clear-after

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

eval-category:
	python -m app.testing --category $(CATEGORY)

# Before/after prompt comparison workflow:
#   1. make eval-before          (run baseline, cached as variant "before")
#   2. edit your prompts
#   3. make eval-after           (run new prompts, cached as variant "after")
#   4. make eval-diff            (show both variants side by side)
eval-before:
	python -u -m app.testing --variants before | tee before.txt

eval-after:
	python -u -m app.testing --variants after | tee after.txt

eval-diff:
	python -u -m app.testing --variants before after

eval-compare:
	python -m app.testing --variants default minimal no_critique no_examples --runs 2

cache-clear-before:
	python -c "import sqlite3; c=sqlite3.connect('app/testing/eval_cache.db'); c.execute(\"DELETE FROM eval_results WHERE variant_id='before'\"); c.commit(); print('Deleted', c.total_changes, 'rows')"

cache-clear-after:
	python -c "import sqlite3; c=sqlite3.connect('app/testing/eval_cache.db'); c.execute(\"DELETE FROM eval_results WHERE variant_id='after'\"); c.commit(); print('Deleted', c.total_changes, 'rows')"
