-- Trading Knowledge System Database Schema

-- Market data table: stores historical price and volume data
CREATE TABLE IF NOT EXISTS market_data (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timestamp BIGINT NOT NULL,
    open DECIMAL(20, 8) NOT NULL,
    high DECIMAL(20, 8) NOT NULL,
    low DECIMAL(20, 8) NOT NULL,
    close DECIMAL(20, 8) NOT NULL,
    volume DECIMAL(20, 8) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, timestamp)
);

CREATE INDEX idx_market_data_symbol_timestamp ON market_data(symbol, timestamp DESC);

-- Features table: stores calculated technical indicators and features
CREATE TABLE IF NOT EXISTS features (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timestamp BIGINT NOT NULL,
    rsi DECIMAL(10, 4),
    macd DECIMAL(20, 8),
    macd_signal DECIMAL(20, 8),
    ema_12 DECIMAL(20, 8),
    ema_26 DECIMAL(20, 8),
    sma_50 DECIMAL(20, 8),
    sma_200 DECIMAL(20, 8),
    volatility DECIMAL(10, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, timestamp)
);

CREATE INDEX idx_features_symbol_timestamp ON features(symbol, timestamp DESC);

-- Signals table: stores trading signals generated from features
CREATE TABLE IF NOT EXISTS signals (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timestamp BIGINT NOT NULL,
    signal_type VARCHAR(10) NOT NULL CHECK (signal_type IN ('BUY', 'SELL', 'HOLD')),
    strength DECIMAL(5, 4) NOT NULL CHECK (strength >= 0 AND strength <= 1),
    confidence DECIMAL(5, 4) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    reasons TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_signals_symbol_timestamp ON signals(symbol, timestamp DESC);
CREATE INDEX idx_signals_type ON signals(signal_type);

-- Paper trades table: tracks simulated trades
CREATE TABLE IF NOT EXISTS paper_trades (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('BUY', 'SELL')),
    quantity DECIMAL(20, 8) NOT NULL,
    price DECIMAL(20, 8) NOT NULL,
    total_value DECIMAL(20, 8) NOT NULL,
    signal_id INTEGER REFERENCES signals(id),
    timestamp BIGINT NOT NULL,
    status VARCHAR(20) DEFAULT 'EXECUTED' CHECK (status IN ('EXECUTED', 'CANCELLED', 'FAILED')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_paper_trades_symbol ON paper_trades(symbol);
CREATE INDEX idx_paper_trades_timestamp ON paper_trades(timestamp DESC);

-- Web intelligence data: stores news and web scraped data
CREATE TABLE IF NOT EXISTS web_intelligence (
    id SERIAL PRIMARY KEY,
    source VARCHAR(100) NOT NULL,
    title TEXT NOT NULL,
    content TEXT,
    url TEXT,
    symbols VARCHAR(20)[],
    sentiment VARCHAR(20) CHECK (sentiment IN ('POSITIVE', 'NEGATIVE', 'NEUTRAL')),
    sentiment_score DECIMAL(5, 4),
    published_at BIGINT,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_web_intelligence_symbols ON web_intelligence USING GIN (symbols);
CREATE INDEX idx_web_intelligence_published ON web_intelligence(published_at DESC);

-- Safety flags: controls system behavior
CREATE TABLE IF NOT EXISTS safety_flags (
    id SERIAL PRIMARY KEY,
    flag_name VARCHAR(50) UNIQUE NOT NULL,
    is_paused BOOLEAN DEFAULT FALSE,
    reason TEXT,
    paused_at TIMESTAMP,
    paused_by VARCHAR(100),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default safety flags
INSERT INTO safety_flags (flag_name, is_paused, reason) 
VALUES 
    ('TRADING_ENABLED', FALSE, 'System operational'),
    ('DATA_INGESTION_ENABLED', FALSE, 'Normal operation'),
    ('SIGNAL_GENERATION_ENABLED', FALSE, 'Normal operation'),
    ('WEB_INTELLIGENCE_ENABLED', FALSE, 'Normal operation')
ON CONFLICT (flag_name) DO NOTHING;

-- Performance metrics table
CREATE TABLE IF NOT EXISTS performance_metrics (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    period_start BIGINT NOT NULL,
    period_end BIGINT NOT NULL,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    total_pnl DECIMAL(20, 8) DEFAULT 0,
    win_rate DECIMAL(5, 4),
    sharpe_ratio DECIMAL(10, 4),
    max_drawdown DECIMAL(10, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_performance_symbol ON performance_metrics(symbol);
CREATE INDEX idx_performance_period ON performance_metrics(period_end DESC);
