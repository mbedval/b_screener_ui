"""The fixed BSA tables plus safe, runtime-discovered sector tables."""

FIXED_TABLES = {
    "historical_calls": {"label": "Historical calls", "group": "Calls"},
    "intraday_call": {"label": "Intraday calls", "group": "Calls"},
    "quicktrade_timestamp": {"label": "QuickTrade", "group": "Scanners"},
    "screener_timestamp": {"label": "Screener", "group": "Scanners"},
    "operatorfootprint": {"label": "Operator footprint", "group": "Scanners"},
    "swinger": {"label": "Swinger", "group": "Scanners"},
    "monthly_swinger": {"label": "Monthly swinger", "group": "Scanners"},
    "breakout": {"label": "Breakout", "group": "Scanners"},
    "trend_trading": {"label": "Trend trading", "group": "Scanners"},
    "reversal_trading": {"label": "Reversal trading", "group": "Scanners"},
    "support_resistance": {"label": "Support & resistance", "group": "Scanners"},
    "price_history": {"label": "Price history", "group": "Shared cache"},
    "raw_fundamentals": {"label": "Raw fundamentals", "group": "Shared cache"},
    "delivery_history": {"label": "Delivery history", "group": "Shared cache"},
}

RAW_DATA_TABLES = {
    "ohlcv_daily": {"label": "OHLCV daily", "group": "Raw data"},
    "indicators_daily": {"label": "Indicators daily", "group": "Raw data"},
    "fundamentals": {"label": "Fundamentals", "group": "Raw data"},
    "stock_meta": {"label": "Stock metadata", "group": "Raw data"},
    "subscribers": {"label": "Subscribers", "group": "Reference"},
    "cash_flow_summary": {"label": "Cash flow summary", "group": "Analysis"},
    "delivery_to_trade": {"label": "Delivery to trade", "group": "Analysis"},
}

SYSTEM_TABLES = set()


def display_name(name: str) -> str:
    return name.replace("_delivery", " delivery spikes").replace("_", " ").title()
