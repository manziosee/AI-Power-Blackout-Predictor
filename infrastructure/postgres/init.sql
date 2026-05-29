-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- H3 hexagonal grid cells (neighborhoods)
CREATE TABLE IF NOT EXISTS h3_cells (
    h3_index        VARCHAR(15) PRIMARY KEY,
    center_lat      DECIMAL(10, 7),
    center_lng      DECIMAL(10, 7),
    country_code    VARCHAR(5),
    region          VARCHAR(100),
    city            VARCHAR(100),
    resolution      INTEGER DEFAULT 8
);

-- Users
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) UNIQUE,
    phone           VARCHAR(20)  UNIQUE NOT NULL,
    country_code    VARCHAR(5)   NOT NULL,
    language        VARCHAR(5)   DEFAULT 'en',
    password_hash   VARCHAR(255),
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- User tracked locations
CREATE TABLE IF NOT EXISTS user_locations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    h3_index    VARCHAR(15) REFERENCES h3_cells(h3_index),
    label       VARCHAR(50),
    is_primary  BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Crowdsourced outage reports
CREATE TABLE IF NOT EXISTS outage_reports (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID,
    h3_index            VARCHAR(15)  NOT NULL,
    lat                 DECIMAL(10,7),
    lng                 DECIMAL(10,7),
    reported_at         TIMESTAMPTZ  DEFAULT NOW(),
    resolved_at         TIMESTAMPTZ,
    duration_minutes    INTEGER,
    source              VARCHAR(20)  DEFAULT 'app',
    verified            BOOLEAN      DEFAULT FALSE,
    verification_count  INTEGER      DEFAULT 1,
    notes               TEXT
);
CREATE INDEX IF NOT EXISTS idx_outage_h3   ON outage_reports(h3_index);
CREATE INDEX IF NOT EXISTS idx_outage_time ON outage_reports(reported_at);

-- ML predictions
CREATE TABLE IF NOT EXISTS predictions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    h3_index            VARCHAR(15)  NOT NULL,
    predicted_at        TIMESTAMPTZ  DEFAULT NOW(),
    window_start        TIMESTAMPTZ  NOT NULL,
    window_end          TIMESTAMPTZ  NOT NULL,
    probability         DECIMAL(5,4) NOT NULL,
    confidence          DECIMAL(5,4) NOT NULL,
    risk_level          VARCHAR(10)  NOT NULL,
    model_version       VARCHAR(20)  NOT NULL,
    region_model        VARCHAR(50)  NOT NULL,
    features_snapshot   JSONB
);
CREATE INDEX IF NOT EXISTS idx_pred_h3_time ON predictions(h3_index, predicted_at DESC);

-- Hourly weather snapshots
CREATE TABLE IF NOT EXISTS weather_snapshots (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    h3_index        VARCHAR(15)  NOT NULL,
    recorded_at     TIMESTAMPTZ  DEFAULT NOW(),
    temperature_c   DECIMAL(5,2),
    rainfall_mm     DECIMAL(6,2),
    wind_speed_ms   DECIMAL(5,2),
    humidity_pct    INTEGER,
    weather_code    INTEGER,
    is_forecast     BOOLEAN      DEFAULT FALSE,
    forecast_source VARCHAR(30)  DEFAULT 'openweathermap'
);
CREATE INDEX IF NOT EXISTS idx_weather_h3_time ON weather_snapshots(h3_index, recorded_at DESC);

-- Alert subscriptions
CREATE TABLE IF NOT EXISTS alert_subscriptions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID REFERENCES users(id) ON DELETE CASCADE,
    h3_index                VARCHAR(15) NOT NULL,
    threshold_probability   DECIMAL(4,3) DEFAULT 0.70,
    channels                JSONB        DEFAULT '["sms","push"]',
    quiet_hours_start       TIME,
    quiet_hours_end         TIME,
    is_active               BOOLEAN DEFAULT TRUE
);

-- SMS alerts log
CREATE TABLE IF NOT EXISTS sms_alerts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID,
    phone           VARCHAR(20)  NOT NULL,
    message         TEXT         NOT NULL,
    language        VARCHAR(5)   DEFAULT 'en',
    prediction_id   UUID,
    sent_at         TIMESTAMPTZ  DEFAULT NOW(),
    status          VARCHAR(20)  DEFAULT 'queued',
    provider        VARCHAR(30),
    smpp_message_id VARCHAR(50),
    error_message   TEXT
);
CREATE INDEX IF NOT EXISTS idx_sms_user ON sms_alerts(user_id, sent_at DESC);
