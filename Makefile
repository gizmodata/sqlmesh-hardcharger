.PHONY: install install-dev test unit-test integration-test ducklake-test all-tests upstream-test lint format build docker-up docker-down

COMPOSE = docker compose -p sqlmesh-hardcharger -f tests/integration/docker/compose.hardcharger.yaml

install:
	uv sync

install-dev:
	uv sync --extra dev --frozen

test: unit-test

unit-test:
	uv run pytest -m "not integration"

integration-test:
	uv run pytest -m "integration and not ducklake"

docker-up:
	$(COMPOSE) up -d --wait

docker-down:
	$(COMPOSE) down

ducklake-test: docker-up
	POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=55441 uv run pytest -m ducklake

all-tests: docker-up
	POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=55441 uv run pytest -m "integration or not integration"

upstream-test:
	uv run python scripts/test-upstream.py

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy sqlmesh_hardcharger

format:
	uv run ruff check --fix .
	uv run ruff format .

build:
	uv run python -m build
	uv run twine check --strict dist/*
