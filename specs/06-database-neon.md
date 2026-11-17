# 06 — Database (Neon PostgreSQL)

## Goal
Persist profiles, trades, and reports on Neon with migrations.

## Files
`app/db.py`, `app/models.py`, `alembic.ini`, `migrations/`, `tests/conftest.py`

## Neon setup
- One Neon project, branches: `main` (production), `dev` (local development), `test` (pytest).
- Each branch gives two strings; the only difference is `-pooler` in the hostname:
  - pooled → `DATABASE_URL=PLACE_HOLDER` (app runtime)
  - direct → `DATABASE_URL_DIRECT` (Alembic only)
- Keep `sslmode=require&channel_binding=require` in both strings.
- SQLAlchemy URL scheme: `postgresql+psycopg://...`

## db.py
```python
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,          # Neon compute may scale to zero
    pool_size=5, max_overflow=5, pool_recycle=300,
    connect_args={"prepare_threshold": None},  # pooler runs PgBouncer transaction mode
)
def get_session() -> Iterator[Session]  # FastAPI dependency
```

## Tables (models.py)
```
profiles  id uuid pk, created_at timestamptz, answers jsonb, score int, tier text, level text, persona_id text null
trades    id bigserial pk, profile_id uuid fk on delete cascade, row_no int,
          trade_date date, symbol text, side text check in ('BUY','SELL'),
          quantity int, price bigint, fee bigint, tax bigint
          index (profile_id, trade_date)
reports   id uuid pk, profile_id uuid fk, created_at timestamptz, data_hash text,
          formula_version text, model text, attempts int, passed bool,
          violations jsonb, latency_ms int, metrics jsonb, content jsonb
          index (profile_id, created_at desc)
```
`data_hash = sha256(sorted trades CSV + formula_version)`; reuse the latest report with the same hash.

## Migrations
- `uv run alembic revision --autogenerate -m "init"`; `uv run alembic upgrade head` with `DATABASE_URL_DIRECT`.
- DB constraints mirror pydantic ones: `CHECK (quantity > 0)`, `CHECK (price > 0)`, `CHECK (fee >= 0)`, `CHECK (tax >= 0)`, `CHECK (tier IN (...))`.
- No `create_all` in app startup.

## Tests
- `core` tests never touch the DB.
- API tests use `TEST_DATABASE_URL` (Neon `test` branch); truncate tables per test.

## Acceptance
- `alembic upgrade head` on an empty branch creates 3 tables.
- Replacing a profile's trades deletes old rows in one transaction.
