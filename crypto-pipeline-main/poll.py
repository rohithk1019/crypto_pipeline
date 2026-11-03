"""
Polls CoinGecko for top-20 coin market data and appends it to a DuckDB
time-series table. Designed to be run repeatedly (via cron or a loop) --
every run is safe to re-run: duplicate (polled_at, coin_id) rows are
silently skipped, never overwritten.

Run once manually to test:      python poll.py
Run continuously every 5 min:   python poll.py --loop 300
"""

import argparse
import datetime as dt
import logging
import os
import sys
import time

import duckdb
import requests

DB_PATH = "db/crypto.duckdb"
SCHEMA_PATH = "schema.sql"
LOG_PATH = "poll.log"

COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/markets"
COINGECKO_PARAMS = {
    "vs_currency": "usd",
    "order": "market_cap_desc",
    "per_page": 20,
    "page": 1,
    "price_change_percentage": "1h,24h",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_PATH), logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


def round_to_minute(ts: dt.datetime) -> dt.datetime:
    """Round a timestamp down to the nearest minute.

    Why: near-simultaneous polls (e.g. a manual run seconds after a cron
    run) should collapse to the same polled_at value instead of creating
    two 'unique' rows a few seconds apart. This is what makes the
    (polled_at, coin_id) primary key an effective dedup key rather than
    a no-op.
    """
    return ts.replace(second=0, microsecond=0, tzinfo=None)


def fetch_market_data(retries: int = 2, backoff_seconds: int = 5) -> list[dict]:
    """Call CoinGecko. Retries on transient failure; never raises past
    this point -- a failed poll should skip a cycle, not crash the loop."""
    for attempt in range(1, retries + 2):
        try:
            resp = requests.get(COINGECKO_URL, params=COINGECKO_PARAMS, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            log.warning("Fetch attempt %d/%d failed: %s", attempt, retries + 1, e)
            if attempt <= retries:
                time.sleep(backoff_seconds)
    log.error("All fetch attempts failed for this cycle -- skipping.")
    return []


def store(con: duckdb.DuckDBPyConnection, rows: list[dict], polled_at: dt.datetime) -> int:
    """Insert rows, skipping any that violate the (polled_at, coin_id)
    primary key. Returns count actually inserted."""
    inserted = 0
    for coin in rows:
        try:
            con.execute(
                """
                INSERT INTO coin_prices
                    (polled_at, coin_id, symbol, price_usd, market_cap_usd,
                     volume_24h_usd, change_1h_pct, change_24h_pct)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    polled_at,
                    coin.get("id"),
                    coin.get("symbol"),
                    coin.get("current_price"),
                    coin.get("market_cap"),
                    coin.get("total_volume"),
                    coin.get("price_change_percentage_1h_in_currency"),
                    coin.get("price_change_percentage_24h_in_currency"),
                ],
            )
            inserted += 1
        except duckdb.ConstraintException:
            # Already have this (polled_at, coin_id) -- expected on restart, not an error.
            pass
    return inserted


def verify_stored(con: duckdb.DuckDBPyConnection, polled_at: dt.datetime, expected_count: int) -> None:
    """Self-check after every insert -- catches silent data problems that
    a clean-looking log line would otherwise hide. This exists because a
    script printing 'success' is a claim, not a fact, until the table
    itself confirms it."""
    row = con.execute(
        """
        SELECT COUNT(*) AS n,
               COUNT(price_usd) AS priced,
               COUNT(coin_id) AS ided
        FROM coin_prices WHERE polled_at = ?
        """,
        [polled_at],
    ).fetchone()
    n, priced, ided = row
    if n == 0:
        log.error("VERIFY FAILED: no rows found for polled_at=%s -- insert silently did nothing.", polled_at)
    elif priced < n or ided < n:
        log.error(
            "VERIFY FAILED: %d/%d rows have null price_usd or coin_id at polled_at=%s -- "
            "API response shape may have changed.", n - min(priced, ided), n, polled_at
        )
    elif n < expected_count:
        log.warning(
            "VERIFY: only %d/%d expected coins present for polled_at=%s (rest were likely dedup skips, "
            "or fewer coins were returned this cycle).", n, expected_count, polled_at
        )
    else:
        log.info("VERIFY OK: %d rows for polled_at=%s, all priced and identified.", n, polled_at)


def run_once(con: duckdb.DuckDBPyConnection) -> None:
    polled_at = round_to_minute(dt.datetime.now(dt.timezone.utc))
    rows = fetch_market_data()
    if not rows:
        return  # failure already logged inside fetch_market_data
    n = store(con, rows, polled_at)
    con.commit()
    log.info("Polled at %s -- %d/%d coins stored (rest were dedup skips)", polled_at, n, len(rows))
    verify_stored(con, polled_at, expected_count=len(rows))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", type=int, default=0,
                         help="If set, poll every N seconds forever. Otherwise poll once and exit.")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    con = duckdb.connect(DB_PATH)
    con.execute(open(SCHEMA_PATH).read())

    if args.loop:
        log.info("Starting continuous polling every %d seconds. Ctrl+C to stop.", args.loop)
        while True:
            run_once(con)
            time.sleep(args.loop)
    else:
        run_once(con)


if __name__ == "__main__":
    main()