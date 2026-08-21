# Dr. Rashida Ahmad — FastAPI Backend

Backend API for the Dr. Rashida Ahmad consultation platform, migrated from the original
Next.js API routes to a standalone FastAPI service backed by the same PostgreSQL database.

## Stack

- Python 3.12, FastAPI, Uvicorn
- SQLAlchemy 2.x (mapped onto the existing Prisma-managed PostgreSQL schema)
- Alembic (for future migrations only — the existing schema was **not** altered during migration)
- Pydantic v2 request/response validation
- bcrypt password hashing + JWT (HS256) session cookies, compatible with the original Next.js auth

## Project layout

```
app/
├── main.py            FastAPI app + CORS setup
├── core/               settings, security (bcrypt/JWT), auth dependencies
├── db/                 SQLAlchemy engine/session
├── models/             SQLAlchemy models mirroring the Prisma schema exactly
├── schemas/             Pydantic request/response models
├── services/            business logic (availability, appointment booking, notifications)
├── api/routes/          FastAPI routers (one per original Next.js API group)
└── workers/              standalone scripts for queued notifications/reminders (run on a schedule)
alembic/                 migration environment (baseline stamped against the existing schema)
```

## Local development

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt  # macOS/Linux

cp .env.example .env   # fill in real values, never commit .env

uvicorn app.main:app --reload --port 8000
```

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health check: http://localhost:8000/api/health

## Environment variables

See `.env.example`. Required: `DATABASE_URL`, `APP_URL`, `AUTH_SECRET`, `CORS_ORIGINS`.
`AUTH_SECRET` must match the frontend's session-signing secret during the transition period
if you want existing sessions to remain valid; otherwise users simply log in again.

## Database migrations

The existing database was created and is still managed by Prisma migrations on the frontend
side; this backend's Alembic setup starts from a **no-op baseline** stamped against the current
schema (`alembic stamp head`), so no destructive or altering migration was ever run against
production data. For any *new* schema changes going forward, generate and review migrations
with:

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

Never run `alembic downgrade` or drop tables against production without a reviewed migration.

## Deployment (Railway)

- Build: Dockerfile (`pip install -r requirements.txt`)
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT` (defaults to 8080 when `PORT` is unset)
- Public domain: `https://api.rashida.zadcart.com` (custom domain on the backend service)
- Internal domain `drrashida-be.railway.internal` is for Railway-to-Railway calls only; never use it in browser code.
- Set `DATABASE_URL` from Railway's Postgres plugin reference (do not hardcode credentials).
- Set `CORS_ORIGINS` to the deployed frontend's origin(s), comma-separated.

## Background workers

Run on a schedule (Railway cron job or similar):

```bash
python -m app.workers.notifications_worker
python -m app.workers.reminders_worker
```
