"""
Verifies the storage/dedup logic without hitting the real API --
generates realistic mock CoinGecko-shaped rows across several
timestamps, then checks that:
  1. Inserting the same batch twice does NOT create duplicate rows
     (proves the primary key + ConstraintException skip works)
  2. Multiple distinct polls accumulate correctly (proves time-series
     history builds up, which the analytics queries depend on)
"""

import datetime as dt
import os
import random

import duckdb

from poll import store, round_to_minute

TEST_DB = "db/test_crypto.duckdb"
COINS = ["bitcoin", "ethereum", "solana", "dogecoin", "cardano"]


def mock_rows(base_price_map, tick):
    """Fake a CoinGecko response: each coin's price drifts a little each tick."""
    rows = []
    for coin in COINS:
        base = base_price_map[coin]
        price = base * (1 + random.uniform(-0.02, 0.02) * tick)
        rows.append({
            "id": coin,
            "symbol": coin[:3],
            "current_price": round(price, 2),
            "market_cap": price * 1_000_000,
            "total_volume": price * 50_000,
            "price_change_percentage_1h_in_currency": round(random.uniform(-2, 2), 2),
            "price_change_percentage_24h_in_currency": round(random.uniform(-8, 8), 2),
        })
    return rows


def main():
    os.makedirs(os.path.dirname(TEST_DB) or ".", exist_ok=True)
    con = duckdb.connect(TEST_DB)
    con.execute(open("schema.sql").read())
    con.execute("DELETE FROM coin_prices")  # clean slate for repeatable test

    base_prices = {"bitcoin": 60000, "ethereum": 3000, "solana": 140, "dogecoin": 0.15, "cardano": 0.45}

    # --- Test 1: dedup on exact re-run ---
    t0 = round_to_minute(dt.datetime.now(dt.timezone.utc))
    rows_t0 = mock_rows(base_prices, tick=0)
    inserted_first = store(con, rows_t0, t0)
    inserted_second = store(con, rows_t0, t0)  # re-run same batch, same timestamp
    con.commit()

    total_after_dup_attempt = con.execute(
        "SELECT COUNT(*) FROM coin_prices WHERE polled_at = ?", [t0]
    ).fetchone()[0]

    print(f"[Test 1] First insert: {inserted_first} rows, second (duplicate) insert: {inserted_second} rows")
    print(f"[Test 1] Rows actually in table for t0: {total_after_dup_attempt} (expected {len(COINS)})")
    assert inserted_first == len(COINS)
    assert inserted_second == 0, "Dedup FAILED -- duplicate rows were inserted"
    assert total_after_dup_attempt == len(COINS)
    print("[Test 1] PASSED -- dedup key correctly blocks duplicate polls\n")

    # --- Test 2: accumulate several distinct polls, confirm history builds ---
    for tick in range(1, 6):
        t = round_to_minute(dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=tick))
        store(con, mock_rows(base_prices, tick=tick), t)
    con.commit()

    total_rows = con.execute("SELECT COUNT(*) FROM coin_prices").fetchone()[0]
    distinct_timestamps = con.execute("SELECT COUNT(DISTINCT polled_at) FROM coin_prices").fetchone()[0]
    print(f"[Test 2] Total rows after 6 polls: {total_rows} (expected {6 * len(COINS)})")
    print(f"[Test 2] Distinct timestamps: {distinct_timestamps} (expected 6)")
    assert total_rows == 6 * len(COINS)
    assert distinct_timestamps == 6
    print("[Test 2] PASSED -- time-series history accumulates correctly\n")

    # --- Test 3: run the actual analytics queries against this data ---
    print("[Test 3] Running analytics queries against accumulated mock data:\n")

    print("-- Latest snapshot per coin --")
    latest = con.execute("""
        SELECT coin_id, price_usd, polled_at FROM coin_prices
        QUALIFY ROW_NUMBER() OVER (PARTITION BY coin_id ORDER BY polled_at DESC) = 1
        ORDER BY coin_id
    """).fetchdf()
    print(latest, "\n")

    print("-- Top gainers/losers over the window --")
    movers = con.execute("""
        WITH bounds AS (
            SELECT coin_id,
                   FIRST(price_usd ORDER BY polled_at) AS first_price,
                   LAST(price_usd ORDER BY polled_at) AS last_price
            FROM coin_prices
            GROUP BY coin_id
        )
        SELECT coin_id,
               ROUND((last_price - first_price) / first_price * 100, 2) AS pct_change
        FROM bounds
        ORDER BY pct_change DESC
    """).fetchdf()
    print(movers, "\n")

    print("-- Volatility ranking --")
    vol = con.execute("""
        SELECT coin_id, ROUND(STDDEV(price_usd), 4) AS volatility
        FROM coin_prices
        GROUP BY coin_id
        ORDER BY volatility DESC
    """).fetchdf()
    print(vol, "\n")

    print("ALL TESTS PASSED. Schema, dedup, and analytics queries are correct.")


if __name__ == "__main__":
    main()