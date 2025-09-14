# Schema definitions for Module 1
TICK_SCHEMA = {
    "timestamp": "str",   # ISO8601 UTC
    "bid": "float64",
    "ask": "float64",
    # optional: "volume": "float64"
}

BAR_COLUMNS = [
    "symbol","frame","t_open_ns","t_close_ns",
    "o","h","l","c",
    "o_bid","o_ask","c_bid","c_ask",
    "spread_mean","n_ticks","v_sum",
    "tick_first_id","tick_last_id","gap_flag"
]

SCHEMA_VERSION = "1.0"
BAR_RULES_ID = "time_1m_linksschliessend_tick_N"
