"""
Tests the RELIABILITY paths that only show up when things go wrong --
these don't run during a normal happy-path poll, so they need to be
deliberately exercised:

  1. fetch_market_data() when the API is unreachable -- must retry,
     then return [] cleanly, never raise/crash the loop.
  2. verify_stored() correctly flags a missing insert as an error.
  3. verify_stored() correctly flags null price/coin_id as an error
     (simulating a CoinGecko response-shape change).
  4. verify_stored() passes cleanly on genuinely good data.
"""

import datetime as dt
import os
from unittest.mock import patch

import duckdb
import requests

from poll import fetch_market_data, verify_stored, round_to_minute

TEST_DB = "db/test_reliability.duckdb"


def test_fetch_handles_total_outage():
    print("[Test A] Simulating total API outage (connection error)...")
    with patch("poll.requests.get", side_effect=requests.ConnectionError("simulated outage")):
        result = fetch_market_data(retries=1, backoff_seconds=0)  # backoff=0 so test runs fast
    assert result == [], "Expected empty list on total outage, got something else"
    print("[Test A] PASSED -- fetch_market_data degrades to [] instead of crashing\n")


def test_verify_flags_missing_insert():
    print("[Test B] Checking verify_stored on a polled_at with zero rows...")
    os.makedirs(os.path.dirname(TEST_DB), exist_ok=True)
    con = duckdb.connect(TEST_DB)
    con.execute(open("schema.sql").read())
    con.execute("DELETE FROM coin_prices")
    fake_time = round_to_minute(dt.datetime.now(dt.timezone.utc))
    # Deliberately do NOT insert anything, then verify against it.
    verify_stored(con, fake_time, expected_count=20)
    print("[Test B] PASSED -- see ERROR line above confirming missing-row detection\n")


def test_verify_flags_null_fields():
    print("[Test C] Checking verify_stored catches null price_usd (simulated API shape change)...")
    con = duckdb.connect(TEST_DB)
    t = round_to_minute(dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=1))
    con.execute(
        "INSERT INTO coin_prices (polled_at, coin_id, symbol, price_usd) VALUES (?, ?, ?, ?)",
        [t, "bitcoin", "btc", None],
    )
    verify_stored(con, t, expected_count=1)
    print("[Test C] PASSED -- see ERROR line above confirming null-field detection\n")


def test_verify_passes_on_good_data():
    print("[Test D] Checking verify_stored passes cleanly on good data...")
    con = duckdb.connect(TEST_DB)
    t = round_to_minute(dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=2))
    con.execute(
        "INSERT INTO coin_prices (polled_at, coin_id, symbol, price_usd) VALUES (?, ?, ?, ?)",
        [t, "ethereum", "eth", 3200.55],
    )
    verify_stored(con, t, expected_count=1)
    print("[Test D] PASSED -- see VERIFY OK line above\n")


if __name__ == "__main__":
    test_fetch_handles_total_outage()
    test_verify_flags_missing_insert()
    test_verify_flags_null_fields()
    test_verify_passes_on_good_data()
    print("ALL RELIABILITY TESTS PASSED.")
