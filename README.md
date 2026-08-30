# BSA Market Data Console

React + Vite frontend and FastAPI backend for exploring the BSA PostgreSQL schema.

## Run

1. Create a backend environment and install dependencies:
   `cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
2. Create the local database once, using a PostgreSQL superuser: `sudo -u postgres createdb -O jmbx bsa_db`.
3. Set `POSTGRES_DSN` (for a passwordless local install: `postgresql:///bsa_db?host=/var/run/postgresql`) and seed the demo database:
   `cd backend && .venv/bin/python -m scripts.seed_demo`
4. Start the API:
   `uvicorn app.main:app --reload --port 8000`
5. In another terminal, start the UI:
   `cd frontend && npm install && npm run dev`

The Vite server proxies `/api` to FastAPI. If PostgreSQL is unavailable, the UI displays a clear connection-state message rather than fabricated market data.

## Demo bootstrap

`backend/scripts/seed_demo.py` is safe to run repeatedly. It creates the call, scanner, shared-cache, sector, and sector-delivery tables represented in `schema.md`, then upserts a compact, clearly non-production dataset. It intentionally does not remove existing records.

To remove only those demo rows while preserving every table and other data, run: `cd backend && .venv/bin/python -m scripts.clean_demo`.

## Full data reset

`clean_all` preserves the database and table structures but removes every row from the BSA-owned market, call, scanner, cache, sector, delivery, and subscriber tables. It starts in dry-run mode:

```bash
cd backend
.venv/bin/python -m scripts.clean_all
```

To perform the irreversible reset after reviewing its printed table scope:

```bash
.venv/bin/python -m scripts.clean_all --confirm-reset-all
```
