-- 1. Latest snapshot per coin
SELECT * FROM coin_prices
QUALIFY ROW_NUMBER() OVER (PARTITION BY coin_id ORDER BY polled_at DESC) = 1;

-- 2. Rolling moving average (last 6 polls)
SELECT coin_id, polled_at,
       AVG(price_usd) OVER (
           PARTITION BY coin_id ORDER BY polled_at
           ROWS BETWEEN 5 PRECEDING AND CURRENT ROW
       ) AS moving_avg_price
FROM coin_prices;

-- 3. Top gainers / losers over the observed window
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
ORDER BY pct_change DESC;

-- 4. Volatility ranking (price standard deviation)
SELECT coin_id, ROUND(STDDEV(price_usd), 4) AS volatility
FROM coin_prices
GROUP BY coin_id
ORDER BY volatility DESC;

-- 5. Ingestion gap detection -- flags any interval where a poll was
-- likely missed (e.g. machine asleep/offline), rather than hiding it
SELECT coin_id, polled_at,
       polled_at - LAG(polled_at) OVER (PARTITION BY coin_id ORDER BY polled_at) AS gap
FROM coin_prices
QUALIFY gap > INTERVAL 10 MINUTE
ORDER BY polled_at;
