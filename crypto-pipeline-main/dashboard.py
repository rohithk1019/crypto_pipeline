"""
Live crypto price dashboard. Reads from db/crypto.duckdb (populated by
poll.py running separately via cron or --loop). Run with:

    streamlit run dashboard.py
"""

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DB_PATH = "db/crypto.duckdb"

st.set_page_config(page_title="Crypto price pipeline", layout="wide")
st.title("Live crypto price pipeline")
st.caption("Data polled from CoinGecko every few minutes. This is a portfolio DE project, not financial advice.")


@st.cache_data(ttl=60)
def load_price_history() -> pd.DataFrame:
    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.execute("SELECT * FROM coin_prices ORDER BY polled_at").fetchdf()
    con.close()
    return df


@st.cache_data(ttl=60)
def load_movers() -> pd.DataFrame:
    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.execute("""
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
    con.close()
    return df


@st.cache_data(ttl=60)
def load_volatility() -> pd.DataFrame:
    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.execute("""
        SELECT coin_id, ROUND(STDDEV(price_usd), 4) AS volatility
        FROM coin_prices
        GROUP BY coin_id
        ORDER BY volatility DESC
    """).fetchdf()
    con.close()
    return df


@st.cache_data(ttl=60)
def load_gaps() -> pd.DataFrame:
    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.execute("""
        SELECT polled_at, gap, COUNT(DISTINCT coin_id) AS coins_affected
        FROM (
            SELECT coin_id, polled_at,
                   polled_at - LAG(polled_at) OVER (PARTITION BY coin_id ORDER BY polled_at) AS gap
            FROM coin_prices
        ) t
        WHERE gap > INTERVAL 10 MINUTE
        GROUP BY polled_at, gap
        ORDER BY polled_at
    """).fetchdf()
    con.close()
    return df


history = load_price_history()

if history.empty:
    st.warning("No data yet. Run `python poll.py` at least once (and let it accumulate a few polls) before loading this dashboard.")
    st.stop()

coins = sorted(history["coin_id"].unique())
selected = st.selectbox("Coin", coins, index=coins.index("bitcoin") if "bitcoin" in coins else 0)

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader(f"{selected} price over time")
    coin_history = history[history["coin_id"] == selected].sort_values("polled_at")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=coin_history["polled_at"], y=coin_history["price_usd"],
        mode="lines", line=dict(color="#22d3ee", width=2),
        fill="tozeroy", fillcolor="rgba(34, 211, 238, 0.08)",
        hovertemplate="%{x}<br>$%{y:,.2f}<extra></extra>",
    ))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=10, b=10),
        height=380,
        xaxis_title=None, yaxis_title="USD",
        yaxis_tickprefix="$",
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    latest = coin_history.iloc[-1]
    st.metric("Latest price (USD)", f"${latest['price_usd']:,.2f}")
    st.metric("1h change", f"{latest['change_1h_pct']:.2f}%")
    st.metric("24h change", f"{latest['change_24h_pct']:.2f}%")

st.divider()

col3, col4 = st.columns(2)

with col3:
    st.subheader("Top gainers / losers")
    movers = load_movers()
    colors = ["#22c55e" if v >= 0 else "#ef4444" for v in movers["pct_change"]]
    fig2 = go.Figure(go.Bar(
        x=movers["pct_change"], y=movers["coin_id"],
        orientation="h", marker_color=colors,
        hovertemplate="%{y}: %{x:.2f}%<extra></extra>",
    ))
    fig2.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=10, b=10),
        height=400,
        xaxis_title="% change", yaxis_title=None,
    )
    st.plotly_chart(fig2, use_container_width=True)

with col4:
    st.subheader("Volatility ranking")
    st.dataframe(load_volatility(), use_container_width=True, hide_index=True)

st.caption(f"Total polls recorded: {history['polled_at'].nunique()} | Rows: {len(history)}")

gaps = load_gaps()
if not gaps.empty:
    st.warning(f"{len(gaps)} ingestion gap(s) detected -- each affected {int(gaps['coins_affected'].mean())} coins on average, consistent with machine sleep/offline periods rather than per-coin anomalies.")
    st.dataframe(gaps, use_container_width=True, hide_index=True)
else:
    st.success("No ingestion gaps detected -- continuous polling confirmed.")