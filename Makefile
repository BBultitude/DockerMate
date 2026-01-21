.PHONY: help build run stop clean test lint format dev

help:
	@echo "DockerMate Development Commands"
	@echo "================================"
	@echo "make build    - Build Docker image"
	@echo "make run      - Run DockerMate"
	@echo "make stop     - Stop DockerMate"
	@echo "make clean    - Remove containers and images"
	@echo "make test     - Run tests"
	@echo "make lint     - Run linters"
	@echo "make format   - Format code"
	@echo "make dev      - Run in development mode"

build:
	docker compose build

run:
	docker compose up -d
	@echo "DockerMate running at https://localhost:5000"

stop:
	docker compose down

clean:
	docker compose down -v
	docker rmi dockermate/dockermate:latest || true

test:
	python -m pytest tests/ -v --cov=backend

lint:
	black --check backend/ tests/
	flake8 backend/ tests/
	pylint backend/
	mypy backend/

format:
	black backend/ tests/
	isort backend/ tests/

dev:
	python app.py

install-dev:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pre-commit install

setup-dirs:
	mkdir -p data/ssl data/backups stacks exports