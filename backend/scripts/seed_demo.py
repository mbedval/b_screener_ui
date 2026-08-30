"""Create the dashboard's PostgreSQL entities and seed non-production demo data.

Run from the backend directory after creating bsa_db:
    .venv/bin/python -m scripts.seed_demo
"""
from datetime import datetime, timedelta
from psycopg import sql
from app.database import get_connection

SECTORS = ["cables", "pharma", "ems", "defence", "cdmo", "financials", "midcap150", "smallcap250", "niche_manufacturing", "infra_industrial_tech", "technology", "special_sectors", "new_sectors", "all_sectors"]
DEMO_RUN_ID = "DEMO_SEED_V1"

SCANNER_COLUMNS = {
    "quicktrade_timestamp": "company_name TEXT, close DOUBLE PRECISION, overall_score DOUBLE PRECISION, confidence DOUBLE PRECISION, overall_signal TEXT, sector TEXT, entry_price DOUBLE PRECISION, stop_loss DOUBLE PRECISION, target_price DOUBLE PRECISION, reasons TEXT",
    "screener_timestamp": "close DOUBLE PRECISION, day_change DOUBLE PRECISION, period_change DOUBLE PRECISION, ema_signal TEXT, vwap_signal TEXT, supertrend_signal TEXT, rsi DOUBLE PRECISION, volume_ratio DOUBLE PRECISION, overall_call TEXT, score INTEGER",
    "operatorfootprint": "close DOUBLE PRECISION, phase TEXT, confidence INTEGER, footprint_score INTEGER, accumulation_score INTEGER, distribution_score INTEGER",
    "swinger": "close DOUBLE PRECISION, week_change DOUBLE PRECISION, ema_signal TEXT, vwap_signal TEXT, supertrend_signal TEXT, rsi DOUBLE PRECISION, ichimoku_signal TEXT, ema26_signal TEXT, sma100_signal TEXT, macd_signal TEXT, obv_signal TEXT, volume_ratio DOUBLE PRECISION, overall_call TEXT, score INTEGER",
    "monthly_swinger": "close DOUBLE PRECISION, month_change DOUBLE PRECISION, sma100_signal TEXT, sma200_signal TEXT, ichimoku_signal TEXT, fibonacci_signal TEXT, adx_signal TEXT, volume_profile_signal TEXT, overall_call TEXT, score INTEGER",
    "breakout": "close DOUBLE PRECISION, day_change DOUBLE PRECISION, donchian_upper DOUBLE PRECISION, donchian_lower DOUBLE PRECISION, breakout_signal TEXT, volume_surge TEXT, adx_signal TEXT, supertrend_signal TEXT, overall_call TEXT, score INTEGER",
    "trend_trading": "close DOUBLE PRECISION, day_change DOUBLE PRECISION, ichimoku_signal TEXT, supertrend_signal TEXT, ema20_signal TEXT, adx_signal TEXT, overall_call TEXT, score INTEGER",
    "reversal_trading": "close DOUBLE PRECISION, day_change DOUBLE PRECISION, rsi DOUBLE PRECISION, mfi DOUBLE PRECISION, bollinger_signal TEXT, fibonacci_signal TEXT, overall_call TEXT, score INTEGER",
    "support_resistance": "close DOUBLE PRECISION, day_change DOUBLE PRECISION, fibonacci_signal TEXT, volume_profile_signal TEXT, pivot_signal TEXT, ichimoku_signal TEXT, overall_call TEXT, score INTEGER",
}


def create_tables(cur):
    cur.execute("""CREATE TABLE IF NOT EXISTS historical_calls (
        uniqueid TEXT NOT NULL, ticker TEXT NOT NULL, recommended_call TEXT, confidence DOUBLE PRECISION,
        cmp DOUBLE PRECISION, stop_loss DOUBLE PRECISION, target_price DOUBLE PRECISION, rr_ratio TEXT,
        status TEXT DEFAULT 'OPEN', timestamp TEXT, review_date TEXT, latest_cmp DOUBLE PRECISION,
        call_status TEXT DEFAULT 'OPEN', closest TEXT, PRIMARY KEY (uniqueid, ticker))""")
    cur.execute("""CREATE TABLE IF NOT EXISTS intraday_call (
        uniqueid TEXT NOT NULL, ticker TEXT NOT NULL, signal TEXT, bet TEXT, confidence DOUBLE PRECISION,
        entry_price DOUBLE PRECISION, stop_loss DOUBLE PRECISION, target_price DOUBLE PRECISION, cmp DOUBLE PRECISION,
        actionable_insight TEXT, fo_buildup TEXT, tech_reason TEXT, analysed_at TEXT, pcr TEXT,
        support DOUBLE PRECISION, resistance DOUBLE PRECISION, PRIMARY KEY (uniqueid, ticker))""")
    for table, columns in SCANNER_COLUMNS.items():
        cur.execute(sql.SQL("CREATE TABLE IF NOT EXISTS {} (run_time TEXT NOT NULL, ticker TEXT NOT NULL, {}, PRIMARY KEY (run_time, ticker))").format(sql.Identifier(table), sql.SQL(columns)))
    cur.execute("CREATE TABLE IF NOT EXISTS price_history (ticker TEXT NOT NULL, date TEXT NOT NULL, open DOUBLE PRECISION, high DOUBLE PRECISION, low DOUBLE PRECISION, close DOUBLE PRECISION, volume BIGINT, PRIMARY KEY (ticker, date))")
    cur.execute("CREATE TABLE IF NOT EXISTS raw_fundamentals (ticker TEXT PRIMARY KEY, stock_name TEXT, sector TEXT, market_cap DOUBLE PRECISION, pe DOUBLE PRECISION, pb DOUBLE PRECISION, dividend_yield DOUBLE PRECISION, pat DOUBLE PRECISION, roe DOUBLE PRECISION, debt_to_equity DOUBLE PRECISION, last_updated TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS delivery_history (ticker TEXT NOT NULL, date TEXT NOT NULL, delivery_ratio DOUBLE PRECISION, PRIMARY KEY (ticker, date))")
    for sector in SECTORS:
        cur.execute(sql.SQL("CREATE TABLE IF NOT EXISTS {} (ticker TEXT PRIMARY KEY, stock_name TEXT, sector TEXT, market_cap DOUBLE PRECISION, dividend_yield DOUBLE PRECISION, pe DOUBLE PRECISION, pb DOUBLE PRECISION, pat DOUBLE PRECISION, roe DOUBLE PRECISION, debt_to_equity DOUBLE PRECISION, score DOUBLE PRECISION, last_updated TEXT)").format(sql.Identifier(sector)))
        cur.execute(sql.SQL("CREATE TABLE IF NOT EXISTS {} (ticker TEXT PRIMARY KEY, stock_name TEXT, monthly_avg DOUBLE PRECISION, weekly_avg DOUBLE PRECISION, latest_ratio DOUBLE PRECISION, latest_date TEXT, prev_day_ratio DOUBLE PRECISION, prev_day_date TEXT, prev_to_prev_ratio DOUBLE PRECISION, prev_to_prev_date TEXT, deviation DOUBLE PRECISION, is_spike INTEGER, insight TEXT, last_updated TEXT)").format(sql.Identifier(f"{sector}_delivery")))


def upsert(cur, table, columns, rows, keys):
    identifiers = sql.SQL(", ").join(map(sql.Identifier, columns))
    placeholders = sql.SQL(", ").join(sql.Placeholder() for _ in columns)
    updates = sql.SQL(", ").join(sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(col), sql.Identifier(col)) for col in columns if col not in keys)
    statement = sql.SQL("INSERT INTO {} ({}) VALUES ({}) ON CONFLICT ({}) DO UPDATE SET {}").format(sql.Identifier(table), identifiers, placeholders, sql.SQL(", ").join(map(sql.Identifier, keys)), updates)
    cur.executemany(statement, rows)


def seed(cur):
    # A stable marker makes cleanup exact and prevents repeated demo runs from adding rows.
    stamp = DEMO_RUN_ID
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    calls = [
        (stamp, "SONACOMS", "BUY", 78.4, 815.0, 769.4, 915.4, "1:2.20", "OPEN", now, now, 823.6, "OPEN", "CSL: 769.40, CTL: 915.40"),
        (stamp, "SYNGENE", "HOLD", 93.9, 403.4, 388.4, 418.4, "1:1.00", "OPEN", now, now, 401.2, "OPEN", "CSL: 388.36, CTL: 418.44"),
        (stamp, "COFORGE", "BUY", 74.1, 2014.6, 1952.5, 2151.3, "1:2.20", "OPEN", now, now, 2038.7, "OPEN", "CSL: 1952.47, CTL: 2151.29"),
        (stamp, "TATAPOWER", "BUY", 68.5, 448.2, 427.1, 491.0, "1:2.00", "SUCCESS", now, now, 469.8, "SUCCESS", "Target progression"),
        (stamp, "MGL", "HOLD", 84.5, 1092.8, 1047.3, 1138.3, "1:1.00", "OPEN", now, now, 1085.4, "OPEN", "Range-bound"),
    ]
    upsert(cur, "historical_calls", ["uniqueid", "ticker", "recommended_call", "confidence", "cmp", "stop_loss", "target_price", "rr_ratio", "status", "timestamp", "review_date", "latest_cmp", "call_status", "closest"], calls, ["uniqueid", "ticker"])
    intra = [(stamp, "NIFTY", "BUY", "+", 81.0, 24810, 24720, 24980, 24856, "Above VWAP with broad market support", "Long buildup", "EMA alignment and positive breadth", now, "1.18", 24720, 24980), (stamp, "RELIANCE", "BUY", "+", 74.0, 1412, 1386, 1450, 1420, "Volume confirms a range breakout", "Long buildup", "Supertrend flipped positive", now, "1.09", 1386, 1450), (stamp, "HDFCBANK", "HOLD", "^", 62.0, 1943, 1918, 1970, 1940, "Wait for a decisive close above resistance", "Neutral", "RSI cooling near midpoint", now, "0.96", 1918, 1970)]
    upsert(cur, "intraday_call", ["uniqueid", "ticker", "signal", "bet", "confidence", "entry_price", "stop_loss", "target_price", "cmp", "actionable_insight", "fo_buildup", "tech_reason", "analysed_at", "pcr", "support", "resistance"], intra, ["uniqueid", "ticker"])
    common = {"close": 823.6, "day_change": 2.35, "period_change": 8.40, "week_change": 5.60, "month_change": 12.10, "rsi": 63.2, "mfi": 61.5, "volume_ratio": 1.82, "overall_call": "BUY", "overall_signal": "STRONG BUY", "score": 82, "confidence": 82.0, "ema_signal": "BULLISH", "vwap_signal": "ABOVE VWAP", "supertrend_signal": "BULLISH", "ichimoku_signal": "BULLISH", "ema26_signal": "BULLISH", "ema20_signal": "BULLISH", "sma100_signal": "ABOVE SMA100", "sma200_signal": "ABOVE SMA200", "macd_signal": "BULLISH CROSSOVER", "obv_signal": "RISING", "fibonacci_signal": "SUPPORT HOLD", "adx_signal": "STRONG TREND", "volume_profile_signal": "HIGH VOLUME NODE", "bollinger_signal": "MEAN REVERSION", "pivot_signal": "ABOVE PIVOT", "donchian_upper": 820.0, "donchian_lower": 748.0, "breakout_signal": "BREAKOUT", "volume_surge": "SURGE", "company_name": "Sona BLW Precision", "overall_score": 84.0, "sector": "Automobiles", "entry_price": 815.0, "stop_loss": 769.4, "target_price": 915.4, "reasons": "Momentum; volume expansion; trend confirmation", "phase": "Accumulation", "footprint_score": 86, "accumulation_score": 91, "distribution_score": 18}
    for table, definition in SCANNER_COLUMNS.items():
        columns = ["run_time", "ticker"] + [part.strip().split()[0] for part in definition.split(",")]
        row = [stamp, "SONACOMS"] + [common.get(column, "BULLISH") for column in columns[2:]]
        upsert(cur, table, columns, [row], ["run_time", "ticker"])
    stocks = [("POLYCAB", "Polycab India", "Cables", 520000, 58.1, 12.8, 0.55, 6050, 29.8, 0.12), ("SYNGENE", "Syngene International", "Pharma", 170000, 49.2, 6.1, 0.0, 520, 14.3, 0.08), ("KAYNES", "Kaynes Technology", "EMS", 350000, 117.3, 17.5, 0.0, 410, 18.7, 0.20), ("BEL", "Bharat Electronics", "Defence", 290000, 49.5, 12.2, 0.95, 5140, 27.5, 0.02), ("DIVISLAB", "Divi's Laboratories", "CDMO", 160000, 74.0, 8.9, 0.50, 2005, 12.1, 0.01)]
    upsert(cur, "raw_fundamentals", ["ticker", "stock_name", "sector", "market_cap", "pe", "pb", "dividend_yield", "pat", "roe", "debt_to_equity", "last_updated"], [(*s, now) for s in stocks], ["ticker"])
    for index, sector in enumerate(SECTORS):
        stock = stocks[index % len(stocks)]
        entry = (stock[0], stock[1], stock[2], stock[3], stock[6], stock[4], stock[5], stock[7], stock[8], stock[9], round(71 + index * 1.3, 1), now)
        upsert(cur, sector, ["ticker", "stock_name", "sector", "market_cap", "dividend_yield", "pe", "pb", "pat", "roe", "debt_to_equity", "score", "last_updated"], [entry], ["ticker"])
        delivery = (stock[0], stock[1], 43.5, 47.8, 74.2, now[:10], 45.1, (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"), 41.8, (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"), 70.6, 1, "Delivery ratio is 70.6% above the 30-day average — accumulation watch.", now)
        upsert(cur, f"{sector}_delivery", ["ticker", "stock_name", "monthly_avg", "weekly_avg", "latest_ratio", "latest_date", "prev_day_ratio", "prev_day_date", "prev_to_prev_ratio", "prev_to_prev_date", "deviation", "is_spike", "insight", "last_updated"], [delivery], ["ticker"])
    price_rows, delivery_rows = [], []
    for days_ago in range(12, -1, -1):
        day = datetime.now() - timedelta(days=days_ago)
        close = 785 + (12 - days_ago) * 3.1
        price_rows.append(("SONACOMS", day.strftime("%Y-%m-%d"), close - 5, close + 9, close - 8, close, 1200000 + days_ago * 15000))
        delivery_rows.append(("SONACOMS", day.strftime("%Y-%m-%d"), 39 + (days_ago % 4) * 7.2))
    upsert(cur, "price_history", ["ticker", "date", "open", "high", "low", "close", "volume"], price_rows, ["ticker", "date"])
    upsert(cur, "delivery_history", ["ticker", "date", "delivery_ratio"], delivery_rows, ["ticker", "date"])


def main():
    with get_connection() as connection, connection.cursor() as cursor:
        create_tables(cursor)
        seed(cursor)
        connection.commit()
    print("Created BSA demo entities and seeded dashboard data.")


if __name__ == "__main__":
    main()
