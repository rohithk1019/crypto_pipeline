CREATE TABLE IF NOT EXISTS coin_prices (
    polled_at       TIMESTAMP NOT NULL,
    coin_id         VARCHAR NOT NULL,
    symbol          VARCHAR NOT NULL,
    price_usd       DOUBLE,
    market_cap_usd  DOUBLE,
    volume_24h_usd  DOUBLE,
    change_1h_pct   DOUBLE,
    change_24h_pct  DOUBLE,
    PRIMARY KEY (polled_at, coin_id)
);
