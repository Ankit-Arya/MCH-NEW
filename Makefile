.PHONY: up down logs migrate seed test backend-shell backup restore

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

migrate:
	docker compose exec api alembic upgrade head

seed:
	docker compose exec api python -m app.seeds.seed

test:
	docker compose exec api pytest -q

backend-shell:
	docker compose exec api bash

backup:
	bash scripts/backup_postgres.sh

restore:
	bash scripts/restore_postgres.sh


restart-api:
	docker compose restart api

restart-frontend:
	docker compose restart frontend

restart-nginx:
	docker compose restart nginx

migrate:
	docker compose exec api alembic upgrade head

logs-api:
	docker compose logs -f api

logs-frontend:
	docker compose logs -f frontend
