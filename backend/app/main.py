from datetime import date
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from psycopg import sql
from psycopg.errors import OperationalError

from .catalog import FIXED_TABLES, RAW_DATA_TABLES, SYSTEM_TABLES, display_name
from .config import settings
from .database import get_connection

app = FastAPI(title="BSA Data Portal API", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
DATASETS = {"rawdata": settings.rawdata_postgres_dsn, "intelligence": settings.bsa_postgres_dsn}


def get_dsn(dataset: str) -> str:
    if dataset not in DATASETS:
        raise HTTPException(404, "Unknown data application.")
    return DATASETS[dataset]


def database_error(error: Exception) -> HTTPException:
    return HTTPException(status_code=503, detail=f"PostgreSQL is unavailable: {error}")


def table_names(dsn: str) -> list[str]:
    try:
        with get_connection(dsn) as conn, conn.cursor() as cur:
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = %s AND table_type = 'BASE TABLE'", (settings.database_schema,))
            return [row["table_name"] for row in cur.fetchall()]
    except OperationalError as error:
        raise database_error(error)


def catalog_for(dsn: str, dataset: str) -> list[dict[str, str]]:
    names = table_names(dsn)
    entries = []
    if dataset == "intelligence":
        entries.extend({"name": name, **info} for name, info in FIXED_TABLES.items() if name in names)
    entries.extend({"name": name, **info} for name, info in RAW_DATA_TABLES.items() if name in names)
    known = set(FIXED_TABLES) | set(RAW_DATA_TABLES) | SYSTEM_TABLES
    for name in names:
        if name.endswith("_delivery"):
            entries.append({"name": name, "label": display_name(name), "group": "Delivery spikes"})
        elif name not in known and not name.startswith("pg_"):
            entries.append({"name": name, "label": display_name(name), "group": "Data tables" if dataset == "rawdata" else "Sectors"})
    return entries


def database_info_for(dsn: str) -> dict[str, Any]:
    try:
        with get_connection(dsn) as conn, conn.cursor() as cur:
            cur.execute("SELECT current_database() AS name, current_user AS user_name")
            current = cur.fetchone()
            cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname")
            databases = [row["datname"] for row in cur.fetchall()]
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = %s AND table_type = 'BASE TABLE' ORDER BY table_name", (settings.database_schema,))
            return {"database": current["name"], "user": current["user_name"], "schema": settings.database_schema, "available_databases": databases, "tables": cur.fetchall()}
    except OperationalError as error:
        raise database_error(error)


def table_data_for(dsn: str, table_name: str, limit: int, offset: int, search: str | None, ticker: str | None) -> dict[str, Any]:
    if table_name not in table_names(dsn):
        raise HTTPException(404, f"Table '{table_name}' was not found in schema '{settings.database_schema}'.")
    try:
        with get_connection(dsn) as conn, conn.cursor() as cur:
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position", (settings.database_schema, table_name))
            columns = [row["column_name"] for row in cur.fetchall()]
            conditions, params = [], []
            if ticker and "ticker" in columns:
                conditions.append(sql.SQL("ticker ILIKE %s")); params.append(f"%{ticker}%")
            if search:
                searchable = [c for c in columns if c in {"ticker", "stock_name", "company_name", "sector", "overall_call", "overall_signal", "signal", "phase", "insight"}]
                if searchable:
                    conditions.append(sql.SQL("(") + sql.SQL(" OR ").join(sql.SQL("{}::text ILIKE %s").format(sql.Identifier(c)) for c in searchable) + sql.SQL(")"))
                    params.extend([f"%{search}%"] * len(searchable))
            where = sql.SQL(" WHERE ") + sql.SQL(" AND ").join(conditions) if conditions else sql.SQL("")
            order_column = next((c for c in ("run_time", "timestamp", "analysed_at", "last_updated", "latest_date", "trade_date", "date") if c in columns), columns[0])
            base = sql.SQL(" FROM {}.{} ").format(sql.Identifier(settings.database_schema), sql.Identifier(table_name))
            cur.execute(sql.SQL("SELECT count(*) AS total") + base + where, params)
            total = cur.fetchone()["total"]
            query = sql.SQL("SELECT *") + base + where + sql.SQL(" ORDER BY {} DESC NULLS LAST LIMIT %s OFFSET %s").format(sql.Identifier(order_column))
            cur.execute(query, [*params, limit, offset])
            return {"table": table_name, "columns": columns, "rows": cur.fetchall(), "total": total, "limit": limit, "offset": offset}
    except OperationalError as error:
        raise database_error(error)


def overview_for(dsn: str) -> dict[str, Any]:
    names = set(table_names(dsn)); wanted = ["historical_calls", "intraday_call", "quicktrade_timestamp", "screener_timestamp"]; counts = {}
    try:
        with get_connection(dsn) as conn, conn.cursor() as cur:
            for name in wanted:
                if name in names:
                    cur.execute(sql.SQL("SELECT count(*) AS count FROM {}.{}").format(sql.Identifier(settings.database_schema), sql.Identifier(name)))
                    counts[name] = cur.fetchone()["count"]
            return {"counts": counts, "tables": len(names), "as_of": date.today().isoformat()}
    except OperationalError as error:
        raise database_error(error)


@app.get("/api/{dataset}/health")
def health(dataset: str) -> dict[str, str]:
    database_info_for(get_dsn(dataset))
    return {"status": "connected", "application": dataset}


@app.get("/api/{dataset}/catalog")
def catalog(dataset: str) -> list[dict[str, str]]:
    return catalog_for(get_dsn(dataset), dataset)


@app.get("/api/{dataset}/database-info")
def database_info(dataset: str) -> dict[str, Any]:
    return database_info_for(get_dsn(dataset))


@app.get("/api/{dataset}/overview")
def overview(dataset: str) -> dict[str, Any]:
    return overview_for(get_dsn(dataset))


@app.get("/api/{dataset}/tables/{table_name}")
def table_data(dataset: str, table_name: str, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), search: str | None = None, ticker: str | None = None) -> dict[str, Any]:
    return table_data_for(get_dsn(dataset), table_name, limit, offset, search, ticker)


FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if (FRONTEND_DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")


@app.get("/{path:path}", include_in_schema=False)
def portal(path: str):
    index = FRONTEND_DIST / "index.html"
    if not index.exists():
        raise HTTPException(503, "Frontend not built. Run 'npm --prefix frontend run build'.")
    return FileResponse(index)
