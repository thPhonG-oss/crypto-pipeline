-- Tạo table để lưu crypto prices
CREATE TABLE IF NOT EXISTS crypto_prices (
    id SERIAL PRIMARY KEY,
    execution_date TIMESTAMP NOT NULL,
    coin_id VARCHAR(50) NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    current_price DECIMAL(18, 8) NOT NULL,
    market_cap BIGINT,
    total_volume BIGINT,
    price_change_24h DECIMAL(10, 4),
    price_change_percentage_24h DECIMAL(10, 4),
    last_updated TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Unique constraint để tránh duplicate khi backfill
    UNIQUE(execution_date, coin_id)
);

-- Index để query nhanh hơn
CREATE INDEX IF NOT EXISTS idx_coin_date
ON crypto_prices(coin_id, execution_date DESC);

CREATE INDEX IF NOT EXISTS idx_execution_date
ON crypto_prices(execution_date DESC);