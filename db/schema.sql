-- Trading Knowledge Database Schema
-- PostgreSQL database for crypto trading system

-- Extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Prices table: stores OHLCV candle data
CREATE TABLE IF NOT EXISTS prices (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,  -- 1m, 5m, 15m, 1h, 4h, 1d
    timestamp TIMESTAMP NOT NULL,
    open DECIMAL(20, 8) NOT NULL,
    high DECIMAL(20, 8) NOT NULL,
    low DECIMAL(20, 8) NOT NULL,
    close DECIMAL(20, 8) NOT NULL,
    volume DECIMAL(20, 8) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(symbol, timeframe, timestamp)
);

CREATE INDEX idx_prices_symbol_timeframe_timestamp ON prices(symbol, timeframe, timestamp DESC);

-- Features table: stores computed technical indicators
CREATE TABLE IF NOT EXISTS features (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    -- Moving Averages
    ema_9 DECIMAL(20, 8),
    ema_21 DECIMAL(20, 8),
    ema_50 DECIMAL(20, 8),
    ema_200 DECIMAL(20, 8),
    -- RSI
    rsi_14 DECIMAL(10, 2),
    -- MACD
    macd DECIMAL(20, 8),
    macd_signal DECIMAL(20, 8),
    macd_histogram DECIMAL(20, 8),
    -- Bollinger Bands
    bb_upper DECIMAL(20, 8),
    bb_middle DECIMAL(20, 8),
    bb_lower DECIMAL(20, 8),
    -- Volume indicators
    volume_sma_20 DECIMAL(20, 8),
    -- Custom features (JSON for flexibility)
    custom_features JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(symbol, timeframe, timestamp)
);

CREATE INDEX idx_features_symbol_timeframe_timestamp ON features(symbol, timeframe, timestamp DESC);

-- Trade signals table: stores BUY/SELL/HOLD signals
CREATE TABLE IF NOT EXISTS trade_signals (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    signal_type VARCHAR(10) NOT NULL,  -- BUY, SELL, HOLD
    confidence DECIMAL(5, 2) NOT NULL,  -- 0-100
    timestamp TIMESTAMP NOT NULL,
    -- Trade parameters
    entry_price DECIMAL(20, 8),
    stop_loss DECIMAL(20, 8),
    take_profit DECIMAL(20, 8),
    position_size_usd DECIMAL(20, 2),
    -- Signal metadata
    strategy VARCHAR(50),
    timeframe VARCHAR(10),
    reason TEXT,
    indicators_snapshot JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_trade_signals_symbol_timestamp ON trade_signals(symbol, timestamp DESC);
CREATE INDEX idx_trade_signals_type ON trade_signals(signal_type);

-- Orders table: stores executed orders
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(100) UNIQUE,  -- Exchange order ID
    signal_id INTEGER REFERENCES trade_signals(id),
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,  -- BUY, SELL
    order_type VARCHAR(20) NOT NULL,  -- MARKET, LIMIT, STOP_LOSS
    status VARCHAR(20) NOT NULL,  -- NEW, FILLED, PARTIALLY_FILLED, CANCELED, REJECTED
    -- Order details
    quantity DECIMAL(20, 8),
    price DECIMAL(20, 8),
    filled_quantity DECIMAL(20, 8) DEFAULT 0,
    avg_fill_price DECIMAL(20, 8),
    -- Paper trading flag
    is_paper BOOLEAN DEFAULT TRUE,
    -- Timestamps
    placed_at TIMESTAMP NOT NULL,
    filled_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_orders_symbol ON orders(symbol);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_placed_at ON orders(placed_at DESC);

-- Positions table: stores current and historical positions
CREATE TABLE IF NOT EXISTS positions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,  -- LONG, SHORT
    status VARCHAR(20) NOT NULL,  -- OPEN, CLOSED
    -- Position details
    entry_price DECIMAL(20, 8) NOT NULL,
    exit_price DECIMAL(20, 8),
    quantity DECIMAL(20, 8) NOT NULL,
    -- Risk management
    stop_loss DECIMAL(20, 8),
    take_profit DECIMAL(20, 8),
    -- P&L tracking
    realized_pnl DECIMAL(20, 2),
    unrealized_pnl DECIMAL(20, 2),
    -- Paper trading flag
    is_paper BOOLEAN DEFAULT TRUE,
    -- Entry/Exit orders
    entry_order_id INTEGER REFERENCES orders(id),
    exit_order_id INTEGER REFERENCES orders(id),
    -- Timestamps
    opened_at TIMESTAMP NOT NULL,
    closed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_positions_symbol_status ON positions(symbol, status);
CREATE INDEX idx_positions_opened_at ON positions(opened_at DESC);

-- News events table: stores web/news intelligence
CREATE TABLE IF NOT EXISTS news_events (
    id SERIAL PRIMARY KEY,
    source VARCHAR(100) NOT NULL,  -- twitter, reddit, news_api, etc.
    title TEXT NOT NULL,
    content TEXT,
    url TEXT,
    -- Sentiment analysis
    sentiment VARCHAR(20),  -- positive, negative, neutral
    sentiment_score DECIMAL(5, 2),  -- -1.0 to 1.0
    -- Relevance
    symbols TEXT[],  -- Array of affected symbols
    impact_level VARCHAR(20),  -- high, medium, low
    -- Classification
    category VARCHAR(50),  -- regulation, technical, market, etc.
    keywords TEXT[],
    -- Metadata
    published_at TIMESTAMP,
    ingested_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_news_events_published_at ON news_events(published_at DESC);
CREATE INDEX idx_news_events_symbols ON news_events USING GIN(symbols);
CREATE INDEX idx_news_events_sentiment ON news_events(sentiment);

-- System flags table: stores system-wide control flags
CREATE TABLE IF NOT EXISTS system_flags (
    id SERIAL PRIMARY KEY,
    flag_name VARCHAR(50) NOT NULL UNIQUE,
    flag_value BOOLEAN NOT NULL DEFAULT FALSE,
    reason TEXT,
    set_by VARCHAR(50),  -- service name that set the flag
    set_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Insert default TRADE_PAUSE flag
INSERT INTO system_flags (flag_name, flag_value, reason, set_by)
VALUES ('TRADE_PAUSE', FALSE, 'System initialized', 'init')
ON CONFLICT (flag_name) DO NOTHING;

CREATE INDEX idx_system_flags_name ON system_flags(flag_name);

-- Audit log table: tracks all system actions
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    service VARCHAR(50) NOT NULL,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),  -- order, position, signal, etc.
    entity_id INTEGER,
    details JSONB,
    status VARCHAR(20),  -- success, failure
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_log_service ON audit_log(service);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at DESC);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_orders_updated_at BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_positions_updated_at BEFORE UPDATE ON positions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_flags_updated_at BEFORE UPDATE ON system_flags
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
