# Docker Fast Development Workflow

This patch adds `docker-compose.override.yml` and `nginx/default.dev.conf`.

## Goal

You should not rebuild frontend image every time you change Vue files. You should not manually clear browser cache. Backend Python changes should reload quickly.

## How it works

### Backend

`api` now runs:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --reload
```

Because `./backend:/app` is mounted, Python code changes are visible inside the container. Uvicorn reload restarts the app process automatically.

### Frontend

`frontend` now uses Node + Vite dev server instead of the production NGINX image:

```bash
npm run dev -- --host 0.0.0.0 --port 5173
```

Because `./frontend:/app` is mounted, Vue changes update through Vite HMR.

### NGINX

NGINX proxies:

```text
/api/* → api:8000
/*     → frontend:5173
```

It also sends no-cache headers during development.

## Daily commands

Start all:

```bash
docker compose up -d
```

After Python/backend code change:

```bash
# usually automatic because uvicorn --reload is active
# if something gets stuck:
docker compose restart api
```

After Vue/frontend code change:

```bash
# usually automatic because Vite HMR is active
# if something gets stuck:
docker compose restart frontend
```

After NGINX config change:

```bash
docker compose restart nginx
```

After package.json dependency change:

```bash
docker compose restart frontend
```

After requirements.txt change:

```bash
docker compose build api worker scheduler
docker compose up -d api worker scheduler
```

After database model/migration change:

```bash
docker compose exec api alembic upgrade head
docker compose restart api
```

## Production note

Do not use this override in production. For production, deploy without `docker-compose.override.yml`, or explicitly use a production compose file.

Production should build static Vue assets and serve them through NGINX. Development should use Vite HMR.
