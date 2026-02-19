-- Trade Knowledge System Database Schema
-- PostgreSQL 15+

-- ============================================================
-- TABLE: prices
-- Stores raw OHLCV candlestick data from exchange
-- ============================================================
CREATE TABLE IF NOT EXISTS prices (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    ts TIMESTAMP NOT NULL,
    open NUMERIC(20, 8) NOT NULL,
    high NUMERIC(20, 8) NOT NULL,
    low NUMERIC(20, 8) NOT NULL,
    close NUMERIC(20, 8) NOT NULL,
    volume NUMERIC(20, 8) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(symbol, timeframe, ts)
);

CREATE INDEX idx_prices_symbol_ts ON prices(symbol, ts DESC);
CREATE INDEX idx_prices_timeframe ON prices(timeframe);

-- ============================================================
-- TABLE: features
-- Stores computed technical indicators
-- ============================================================
CREATE TABLE IF NOT EXISTS features (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    ts TIMESTAMP NOT NULL,
    ema20 NUMERIC(20, 8),
    ema50 NUMERIC(20, 8),
    rsi14 NUMERIC(10, 4),
    macd NUMERIC(20, 8),
    macd_signal NUMERIC(20, 8),
    macd_hist NUMERIC(20, 8),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(symbol, timeframe, ts)
);

CREATE INDEX idx_features_symbol_ts ON features(symbol, ts DESC);

-- ============================================================
-- TABLE: trade_signals
-- Stores generated trading signals
-- ============================================================
CREATE TABLE IF NOT EXISTS trade_signals (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    ts TIMESTAMP NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('BUY', 'SELL', 'HOLD')),
    confidence NUMERIC(5, 2) NOT NULL CHECK (confidence >= 0 AND confidence <= 100),
    entry NUMERIC(20, 8),
    stop NUMERIC(20, 8),
    take_profit NUMERIC(20, 8),
    reason TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_signals_symbol_ts ON trade_signals(symbol, ts DESC);
CREATE INDEX idx_signals_side ON trade_signals(side);
CREATE INDEX idx_signals_created ON trade_signals(created_at DESC);

-- ============================================================
-- TABLE: orders
-- Stores executed orders (paper or live)
-- ============================================================
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    signal_id INTEGER REFERENCES trade_signals(id),
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('BUY', 'SELL')),
    qty NUMERIC(20, 8) NOT NULL,
    price NUMERIC(20, 8) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'NEW' CHECK (status IN ('NEW', 'FILLED', 'REJECTED', 'CANCELLED')),
    mode VARCHAR(10) NOT NULL DEFAULT 'PAPER' CHECK (mode IN ('PAPER', 'LIVE')),
    created_at TIMESTAMP DEFAULT NOW(),
    filled_at TIMESTAMP
);

CREATE INDEX idx_orders_symbol ON orders(symbol);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created ON orders(created_at DESC);

-- ============================================================
-- TABLE: positions
-- Stores current positions (one row per symbol)
-- ============================================================
CREATE TABLE IF NOT EXISTS positions (
    symbol VARCHAR(20) PRIMARY KEY,
    qty NUMERIC(20, 8) NOT NULL DEFAULT 0,
    avg_price NUMERIC(20, 8) NOT NULL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- TABLE: news_events
-- Stores web intelligence / news events
-- ============================================================
CREATE TABLE IF NOT EXISTS news_events (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20),
    published_at TIMESTAMP NOT NULL,
    title TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    source VARCHAR(100),
    summary TEXT,
    impact VARCHAR(20) CHECK (impact IN ('bullish', 'bearish', 'neutral')),
    confidence NUMERIC(5, 2) CHECK (confidence >= 0 AND confidence <= 100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_news_symbol ON news_events(symbol);
CREATE INDEX idx_news_published ON news_events(published_at DESC);
CREATE INDEX idx_news_impact ON news_events(impact);

-- ============================================================
-- TABLE: system_flags
-- Stores global system configuration flags
-- ============================================================
CREATE TABLE IF NOT EXISTS system_flags (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Initialize default system flags
INSERT INTO system_flags (key, value) VALUES 
    ('TRADE_PAUSE', 'false'),
    ('TRADE_PAUSE_REASON', '')
ON CONFLICT (key) DO NOTHING;

-- ============================================================
-- VIEWS for convenience
-- ============================================================

-- Latest signals per symbol
CREATE OR REPLACE VIEW latest_signals AS
SELECT DISTINCT ON (symbol) *
FROM trade_signals
ORDER BY symbol, created_at DESC;

-- Current positions with unrealized P&L (requires current price join)
CREATE OR REPLACE VIEW positions_summary AS
SELECT 
    p.symbol,
    p.qty,
    p.avg_price,
    p.updated_at,
    CASE WHEN p.qty != 0 THEN p.qty * p.avg_price ELSE 0 END as position_value
FROM positions p
WHERE p.qty != 0;

-- ============================================================
-- UTILITY FUNCTIONS
-- ============================================================

-- Function to get latest price for a symbol
CREATE OR REPLACE FUNCTION get_latest_price(p_symbol VARCHAR, p_timeframe VARCHAR)
RETURNS NUMERIC AS $$
DECLARE
    latest_price NUMERIC;
BEGIN
    SELECT close INTO latest_price
    FROM prices
    WHERE symbol = p_symbol AND timeframe = p_timeframe
    ORDER BY ts DESC
    LIMIT 1;
    
    RETURN latest_price;
END;
$$ LANGUAGE plpgsql;

-- Function to check if trading is paused
CREATE OR REPLACE FUNCTION is_trading_paused()
RETURNS BOOLEAN AS $$
DECLARE
    paused BOOLEAN;
BEGIN
    SELECT value::BOOLEAN INTO paused
    FROM system_flags
    WHERE key = 'TRADE_PAUSE';
    
    RETURN COALESCE(paused, false);
END;
$$ LANGUAGE plpgsql;
