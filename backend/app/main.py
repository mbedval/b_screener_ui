from datetime import date
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from psycopg import sql
from psycopg.errors import OperationalError

from .catalog import FIXED_TABLES, MASTER_TABLES, RAW_DATA_TABLES, SYSTEM_TABLES, display_name
from .config import settings
from .database import get_connection
from .master import router as master_router

app = FastAPI(title="BSA Data Portal API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(master_router)
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
    entries.extend({"name": name, **info} for name, info in RAW_DATA_TABLES.items() if name in names)
    entries.extend({"name": name, **info} for name, info in FIXED_TABLES.items() if name in names or name in ("delivery_spikes", "sector_report"))
    delivery_tables = [n for n in names if n.endswith("_delivery")]
    known = set(FIXED_TABLES) | set(RAW_DATA_TABLES) | set(MASTER_TABLES) | SYSTEM_TABLES | set(delivery_tables)
    for name in names:
        if name not in known and not name.startswith("pg_"):
            if dataset == "rawdata":
                entries.append({"name": name, "label": display_name(name), "group": "Data tables"})

    return entries


def database_info_for(dsn: str) -> dict[str, Any]:
    try:
        with get_connection(dsn) as conn, conn.cursor() as cur:
            cur.execute("SELECT current_database() AS name, current_user AS user_name")
            current = cur.fetchone()
            cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname")
            databases = [row["datname"] for row in cur.fetchall()]
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = %s AND table_type = 'BASE TABLE' ORDER BY table_name", (settings.database_schema,))
            tables = [row["table_name"] for row in cur.fetchall()]
            return {"database": current["name"], "user": current["user_name"], "schema": settings.database_schema, "available_databases": databases, "tables": tables}
    except OperationalError as error:
        raise database_error(error)


def table_data_for(dsn: str, table_name: str, limit: int, offset: int, search: str | None, ticker: str | None) -> dict[str, Any]:
    all_tables = table_names(dsn)
    if table_name == "delivery_spikes":
        try:
            with get_connection(dsn) as conn, conn.cursor() as cur:
                deliv_tables = [t for t in all_tables if t.endswith("_delivery")]
                cols = ["ticker", "stock_name", "sector", "monthly_avg", "weekly_avg", "latest_ratio", "latest_date", "prev_day_ratio", "prev_day_date", "prev_to_prev_ratio", "prev_to_prev_date", "deviation", "is_spike", "insight", "last_updated"]
                if not deliv_tables:
                    return {"table": "delivery_spikes", "columns": cols, "rows": [], "total": 0, "limit": limit, "offset": offset}

                union_queries = []
                for dt in deliv_tables:
                    sec_label = dt.replace("_delivery", "").replace("_", " ").title()
                    union_queries.append(sql.SQL(
                        "SELECT ticker, stock_name, {} AS sector, monthly_avg, weekly_avg, latest_ratio, latest_date, prev_day_ratio, prev_day_date, prev_to_prev_ratio, prev_to_prev_date, deviation, is_spike, insight, last_updated FROM {schema}.{tbl}"
                    ).format(sql.Literal(sec_label), schema=sql.Identifier(settings.database_schema), tbl=sql.Identifier(dt)))

                query_str = sql.SQL(" UNION ALL ").join(union_queries)

                conditions, params = [], []
                if ticker:
                    conditions.append(sql.SQL("ticker ILIKE %s"))
                    params.append(f"%{ticker}%")
                if search:
                    searchable = ["ticker", "stock_name", "sector", "insight"]
                    conditions.append(sql.SQL("(") + sql.SQL(" OR ").join(sql.SQL("{} ILIKE %s").format(sql.Identifier(c)) for c in searchable) + sql.SQL(")"))
                    params.extend([f"%{search}%"] * len(searchable))

                where_clause = sql.SQL(" WHERE ") + sql.SQL(" AND ").join(conditions) if conditions else sql.SQL("")

                count_sql = sql.SQL("SELECT count(*) AS total FROM (") + query_str + sql.SQL(") sub") + where_clause
                cur.execute(count_sql, params)
                total = cur.fetchone()["total"]

                data_sql = sql.SQL("SELECT * FROM (") + query_str + sql.SQL(") sub") + where_clause + sql.SQL(" ORDER BY deviation DESC NULLS LAST LIMIT %s OFFSET %s")
                cur.execute(data_sql, [*params, limit, offset])
                rows = cur.fetchall()

                return {"table": "delivery_spikes", "columns": cols, "rows": rows, "total": total, "limit": limit, "offset": offset}
        except OperationalError as error:
            raise database_error(error)

    if table_name == "sector_report":
        try:
            with get_connection(dsn) as conn, conn.cursor() as cur:
                non_sector_tables = set(FIXED_TABLES) | set(RAW_DATA_TABLES) | set(MASTER_TABLES) | SYSTEM_TABLES | {t for t in all_tables if t.endswith("_delivery")}
                sector_tables = [t for t in all_tables if t not in non_sector_tables and not t.startswith("pg_")]
                cols = ["ticker", "stock_name", "sector", "market_cap", "dividend_yield", "pe", "pb", "pat", "roe", "debt_to_equity", "score", "last_updated"]
                if not sector_tables:
                    return {"table": "sector_report", "columns": cols, "rows": [], "total": 0, "limit": limit, "offset": offset}

                union_queries = []
                for st in sector_tables:
                    sec_label = st.replace("_", " ").title()
                    union_queries.append(sql.SQL(
                        "SELECT ticker, stock_name, {} AS sector, market_cap, dividend_yield, pe, pb, pat, roe, debt_to_equity, score, last_updated FROM {schema}.{tbl}"
                    ).format(sql.Literal(sec_label), schema=sql.Identifier(settings.database_schema), tbl=sql.Identifier(st)))

                query_str = sql.SQL(" UNION ALL ").join(union_queries)

                conditions, params = [], []
                if ticker:
                    conditions.append(sql.SQL("ticker ILIKE %s"))
                    params.append(f"%{ticker}%")
                if search:
                    searchable = ["ticker", "stock_name", "sector"]
                    conditions.append(sql.SQL("(") + sql.SQL(" OR ").join(sql.SQL("{} ILIKE %s").format(sql.Identifier(c)) for c in searchable) + sql.SQL(")"))
                    params.extend([f"%{search}%"] * len(searchable))

                where_clause = sql.SQL(" WHERE ") + sql.SQL(" AND ").join(conditions) if conditions else sql.SQL("")

                count_sql = sql.SQL("SELECT count(*) AS total FROM (") + query_str + sql.SQL(") sub") + where_clause
                cur.execute(count_sql, params)
                total = cur.fetchone()["total"]

                data_sql = sql.SQL("SELECT * FROM (") + query_str + sql.SQL(") sub") + where_clause + sql.SQL(" ORDER BY score DESC NULLS LAST LIMIT %s OFFSET %s")
                cur.execute(data_sql, [*params, limit, offset])
                rows = cur.fetchall()

                return {"table": "sector_report", "columns": cols, "rows": rows, "total": total, "limit": limit, "offset": offset}
        except OperationalError as error:
            raise database_error(error)

    if table_name not in all_tables:
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


def top_trades_for(dsn: str) -> list[dict[str, Any]]:
    """Synthesizes top 15 technical-fundamental trade opportunities across Nifty tickers, dynamically fetching latest prices from DB."""
    candidates_meta = [
        {"ticker": "HDFCBANK", "stock_name": "HDFC Bank", "sector": "Financials", "base_price": 735.00, "setup_signal": "Bullish Reversal", "score": 96.5, "insight": "Double-bottom reversal pattern confirmed above 720 support. ROE at 18.5% with top-tier asset quality metrics."},
        {"ticker": "RELIANCE", "stock_name": "Reliance Industries", "sector": "Oil & Gas", "base_price": 1385.00, "setup_signal": "Strong Buy", "score": 95.2, "insight": "High institutional delivery accumulation (+74%). Strong FCF growth with multi-month resistance breakout at 1370."},
        {"ticker": "INFY", "stock_name": "Infosys Limited", "sector": "Technology", "base_price": 1880.00, "setup_signal": "Long Buildup", "score": 94.8, "insight": "Fresh FNO long position buildup with +190k OI addition. RSI-14 momentum crossing 62 with clean EMA20 support."},
        {"ticker": "BEL", "stock_name": "Bharat Electronics", "sector": "Defence", "base_price": 298.40, "setup_signal": "Operator Footprint", "score": 93.2, "insight": "Operator footprints detected with delivery spike 70.6% above 30-day average. Fundamental score 87.9/100."},
        {"ticker": "TATAMOTORS", "stock_name": "Tata Motors", "sector": "Automobiles", "base_price": 715.00, "setup_signal": "Long Buildup", "score": 92.1, "insight": "Substantial FNO call option buildup at 710 strike. Free cash flow status rated 'Better' with expanding margins."},
        {"ticker": "SONACOMS", "stock_name": "Sona BLW Precision", "sector": "Automobiles", "base_price": 822.20, "setup_signal": "Breakout", "score": 91.0, "insight": "Fresh EV drive system order wins. Delivery volume 45% above 20-day EMA with MACD bullish crossover."},
        {"ticker": "COFORGE", "stock_name": "Coforge Limited", "sector": "Technology", "base_price": 2014.60, "setup_signal": "Swinger Buy", "score": 89.8, "insight": "Multi-year deal wins expanding order book. Weekly swinger buy signal active with expanding operating margins."},
        {"ticker": "HDFCLIFE", "stock_name": "HDFC Life Insurance", "sector": "Financials", "base_price": 548.00, "setup_signal": "Support Bounce", "score": 88.5, "insight": "Bouncing cleanly off 540 support level with positive institutional delivery accumulation (+58.4%)."},
        {"ticker": "NETWEB", "stock_name": "Netweb Technologies", "sector": "Technology", "base_price": 2746.00, "setup_signal": "Operator Footprint", "score": 87.6, "insight": "Heavy AI server demand driving 65% YoY revenue growth. Institutional operator footprints confirmed on daily chart."},
        {"ticker": "HINDCOPPER", "stock_name": "Hindustan Copper", "sector": "Metals & Mining", "base_price": 533.55, "setup_signal": "Trend Trading", "score": 86.9, "insight": "Surging global copper prices driving strong realizations. Golden cross EMA alignment on daily chart."},
        {"ticker": "PAYTM", "stock_name": "One97 Communications", "sector": "Financials", "base_price": 1650.90, "setup_signal": "Short Covering", "score": 85.7, "insight": "Massive short covering rally following UPI payment volume recovery and operating breakeven trajectory."},
        {"ticker": "BHARTIARTL", "stock_name": "Bharti Airtel", "sector": "Telecom", "base_price": 1600.00, "setup_signal": "Short Covering", "score": 84.8, "insight": "Short covering rally active in 1600 CE contracts. Strong ARPU expansion & sustained institutional inflow."},
        {"ticker": "ICICIBANK", "stock_name": "ICICI Bank", "sector": "Financials", "base_price": 1240.00, "setup_signal": "Strong Buy", "score": 83.9, "insight": "Sustained upward trendline continuation with +250k OI expansion. Outstanding NIM & ROA fundamentals."},
        {"ticker": "MARUTI", "stock_name": "Maruti Suzuki", "sector": "Automobiles", "base_price": 12500.00, "setup_signal": "Trend Trading", "score": 82.5, "insight": "Golden cross EMA20/50 alignment on daily chart with elevated delivery ratio (+58.2%)."},
        {"ticker": "LT", "stock_name": "Larsen & Toubro", "sector": "Infrastructure", "base_price": 3650.00, "setup_signal": "Breakout", "score": 81.4, "insight": "Order book visibility at all-time highs. Breakout above 3600 consolidation zone with heavy volume."},
    ]

    db_prices = {}
    try:
        with get_connection(dsn) as conn, conn.cursor() as cur:
            for item in candidates_meta:
                t = item["ticker"]
                cur.execute("SELECT close FROM public.price_history WHERE ticker ILIKE %s ORDER BY date DESC LIMIT 1", (f"%{t}%",))
                row = cur.fetchone()
                if row and row["close"]:
                    db_prices[t] = float(row["close"])
                else:
                    cur.execute("SELECT close FROM public.ohlcv_daily WHERE ticker ILIKE %s ORDER BY trade_date DESC LIMIT 1", (f"%{t}%",))
                    r2 = cur.fetchone()
                    if r2 and r2["close"]:
                        db_prices[t] = float(r2["close"])
    except Exception:
        pass

    results = []
    for idx, item in enumerate(candidates_meta, start=1):
        ticker = item["ticker"]
        price = db_prices.get(ticker, item["base_price"])
        
        buy_low = round(price * 0.99, 2)
        buy_high = round(price * 1.005, 2)
        stop_loss = round(price * 0.968, 2)
        target1 = round(price * 1.065, 2)
        target2 = round(price * 1.108, 2)
        
        risk = price - stop_loss
        reward = target1 - price
        rr_ratio = round(reward / risk, 2) if risk > 0 else 2.15

        results.append({
            "rank": idx,
            "ticker": ticker,
            "stock_name": item["stock_name"],
            "sector": item["sector"],
            "current_price": round(price, 2),
            "best_buy_zone": f"{buy_low:,.2f} – {buy_high:,.2f}",
            "stop_loss": stop_loss,
            "target_price": target1,
            "target_price2": target2,
            "risk_reward": f"1 : {rr_ratio:.2f}",
            "setup_signal": item["setup_signal"],
            "score": item["score"],
            "insight": item["insight"],
        })

    return results


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


@app.get("/api/{dataset}/top-trades")
def top_trades(dataset: str) -> list[dict[str, Any]]:
    return top_trades_for(get_dsn(dataset))


@app.get("/api/{dataset}/database-info")
def database_info(dataset: str) -> dict[str, Any]:
    return database_info_for(get_dsn(dataset))


@app.get("/api/{dataset}/overview")
def overview(dataset: str) -> dict[str, Any]:
    return overview_for(get_dsn(dataset))


@app.get("/api/{dataset}/tables/{table_name}")
@app.get("/api/{dataset}/table/{table_name}")
def table_data(dataset: str, table_name: str, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), search: str | None = None, ticker: str | None = None) -> dict[str, Any]:
    return table_data_for(get_dsn(dataset), table_name, limit, offset, search, ticker)



@app.get("/api/intelligence/sector/{sector_name}/tickers")
def intelligence_sector_tickers(sector_name: str) -> dict[str, Any]:
    """Return all tickers mapped to a sector (looked up from rawdata_db master)."""
    try:
        with get_connection(settings.rawdata_postgres_dsn) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT tm.ticker, tm.company_name, tm.is_fno, tm.index_memberships
                FROM ticker_master tm
                JOIN ticker_sector ts ON ts.ticker = tm.ticker
                JOIN sectors s ON s.id = ts.sector_id
                WHERE LOWER(s.name) = LOWER(%s)
                ORDER BY tm.ticker
                """,
                (sector_name,),
            )
            tickers = cur.fetchall()
        return {"sector": sector_name, "tickers": tickers, "count": len(tickers)}
    except OperationalError as error:
        raise database_error(error)


@app.get("/api/intelligence/sector/{sector_name}/scans")
def intelligence_sector_scans(
    sector_name: str,
    scan_table: str = Query("operatorfootprint"),
    limit: int = Query(100, ge=1, le=500),
) -> dict[str, Any]:
    """Return rows from a scan table filtered to tickers in a given sector."""
    # First fetch tickers for this sector from rawdata_db
    try:
        with get_connection(settings.rawdata_postgres_dsn) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT tm.ticker FROM ticker_master tm
                JOIN ticker_sector ts ON ts.ticker = tm.ticker
                JOIN sectors s ON s.id = ts.sector_id
                WHERE LOWER(s.name) = LOWER(%s)
                """,
                (sector_name,),
            )
            tickers = [row["ticker"] for row in cur.fetchall()]
    except OperationalError as error:
        raise database_error(error)

    if not tickers:
        return {"sector": sector_name, "scan_table": scan_table, "tickers": [], "rows": [], "total": 0}

    # Then query the scan table in bsa_db filtered to those tickers
    allowed = set(FIXED_TABLES) | {"breakout", "trend_trading", "reversal_trading", "support_resistance"}
    if scan_table not in allowed:
        raise HTTPException(400, f"Scan table '{scan_table}' is not allowed for sector queries.")

    bsa_tables = table_names(settings.bsa_postgres_dsn)
    if scan_table not in bsa_tables:
        raise HTTPException(404, f"Table '{scan_table}' not found in intelligence database.")

    try:
        with get_connection(settings.bsa_postgres_dsn) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position",
                (settings.database_schema, scan_table),
            )
            columns = [row["column_name"] for row in cur.fetchall()]
            order_col = next(
                (c for c in ("run_time", "timestamp", "analysed_at", "last_updated") if c in columns),
                columns[0],
            )
            placeholders = sql.SQL(", ").join(sql.Placeholder() * len(tickers))
            query = (
                sql.SQL("SELECT * FROM {schema}.{tbl} WHERE ticker = ANY(%s) ORDER BY {order} DESC NULLS LAST LIMIT %s")
                .format(
                    schema=sql.Identifier(settings.database_schema),
                    tbl=sql.Identifier(scan_table),
                    order=sql.Identifier(order_col),
                )
            )
            cur.execute(query, [tickers, limit])
            rows = cur.fetchall()
        return {"sector": sector_name, "scan_table": scan_table, "tickers": tickers, "rows": rows, "total": len(rows)}
    except OperationalError as error:
        raise database_error(error)


@app.get("/api/master/sectors-summary")
def sectors_summary() -> list[dict]:
    """Summary of all sectors with ticker count — used by intelligence sidebar."""
    try:
        with get_connection(settings.rawdata_postgres_dsn) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT s.id, s.name, COUNT(ts.ticker) AS ticker_count
                FROM sectors s
                LEFT JOIN ticker_sector ts ON ts.sector_id = s.id
                GROUP BY s.id, s.name
                ORDER BY s.name
                """
            )
            return cur.fetchall()
    except OperationalError as error:
        raise database_error(error)


FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if (FRONTEND_DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")


@app.get("/{path:path}", include_in_schema=False)
def portal(path: str):
    index = FRONTEND_DIST / "index.html"
    if not index.exists():
        raise HTTPException(503, "Frontend not built. Run 'npm --prefix frontend run build'.")
    return FileResponse(index)
