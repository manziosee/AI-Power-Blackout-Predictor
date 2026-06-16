-- ============================================================
-- AI Power Blackout Predictor — Supabase Bootstrap SQL
-- Run this ONCE in the Supabase SQL Editor to create all tables.
-- After it completes, alembic will see the DB as fully migrated (rev 0007).
-- ============================================================

-- ── Extensions ───────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Alembic version tracking ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- ════════════════════════════════════════════════════════════
--  0001 — initial schema
-- ════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS h3_cells (
    h3_index     VARCHAR(15)    PRIMARY KEY,
    center_lat   NUMERIC(10,7),
    center_lng   NUMERIC(10,7),
    country_code VARCHAR(5),
    region       VARCHAR(100),
    city         VARCHAR(100),
    resolution   INTEGER        DEFAULT 8
);

CREATE TABLE IF NOT EXISTS users (
    id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    email         VARCHAR(255) UNIQUE,
    phone         VARCHAR(20)  UNIQUE NOT NULL,
    country_code  VARCHAR(5)   NOT NULL,
    language      VARCHAR(5)   DEFAULT 'en',
    password_hash VARCHAR(255),
    is_active     BOOLEAN      DEFAULT TRUE,
    created_at    TIMESTAMPTZ  DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_locations (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    h3_index   VARCHAR(15) NOT NULL REFERENCES h3_cells(h3_index),
    label      VARCHAR(50),
    is_primary BOOLEAN     DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS outage_reports (
    id                 UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id            UUID,
    h3_index           VARCHAR(15) NOT NULL,
    lat                NUMERIC(10,7),
    lng                NUMERIC(10,7),
    reported_at        TIMESTAMPTZ DEFAULT NOW(),
    resolved_at        TIMESTAMPTZ,
    duration_minutes   INTEGER,
    source             VARCHAR(20) DEFAULT 'app',
    verified           BOOLEAN     DEFAULT FALSE,
    verification_count INTEGER     DEFAULT 1,
    notes              TEXT
);
CREATE INDEX IF NOT EXISTS idx_outage_h3   ON outage_reports(h3_index);
CREATE INDEX IF NOT EXISTS idx_outage_time ON outage_reports(reported_at);

CREATE TABLE IF NOT EXISTS predictions (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    h3_index      VARCHAR(15) NOT NULL,
    predicted_at  TIMESTAMPTZ DEFAULT NOW(),
    window_start  TIMESTAMPTZ NOT NULL,
    window_end    TIMESTAMPTZ NOT NULL,
    probability   FLOAT       NOT NULL,
    confidence    FLOAT       NOT NULL,
    risk_level    VARCHAR(10) NOT NULL,
    model_version VARCHAR(20) NOT NULL,
    region_model  VARCHAR(50) NOT NULL,
    features_snapshot JSONB
);
CREATE INDEX IF NOT EXISTS idx_pred_h3_time ON predictions(h3_index, predicted_at);

CREATE TABLE IF NOT EXISTS weather_snapshots (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    h3_index        VARCHAR(15) NOT NULL,
    recorded_at     TIMESTAMPTZ DEFAULT NOW(),
    temperature_c   NUMERIC(5,2),
    rainfall_mm     NUMERIC(6,2),
    wind_speed_ms   NUMERIC(5,2),
    humidity_pct    INTEGER,
    weather_code    INTEGER,
    is_forecast     BOOLEAN     DEFAULT FALSE,
    forecast_source VARCHAR(30) DEFAULT 'openweathermap'
);
CREATE INDEX IF NOT EXISTS idx_weather_h3_time ON weather_snapshots(h3_index, recorded_at);

CREATE TABLE IF NOT EXISTS alert_subscriptions (
    id                    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id               UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    h3_index              VARCHAR(15) NOT NULL,
    threshold_probability NUMERIC(4,3) DEFAULT 0.70,
    channels              JSONB        DEFAULT '["sms","push"]',
    quiet_hours_start     TIME,
    quiet_hours_end       TIME,
    is_active             BOOLEAN     DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS push_subscriptions (
    id         UUID  PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID  NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    endpoint   TEXT  NOT NULL,
    p256dh     TEXT  NOT NULL,
    auth       TEXT  NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_push_user ON push_subscriptions(user_id);

CREATE TABLE IF NOT EXISTS sms_alerts (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID        REFERENCES users(id) ON DELETE SET NULL,
    phone           VARCHAR(20) NOT NULL,
    message         TEXT        NOT NULL,
    language        VARCHAR(5)  DEFAULT 'en',
    prediction_id   UUID,
    sent_at         TIMESTAMPTZ DEFAULT NOW(),
    status          VARCHAR(20) DEFAULT 'queued',
    provider        VARCHAR(30),
    smpp_message_id VARCHAR(50),
    error_message   TEXT
);
CREATE INDEX IF NOT EXISTS idx_sms_user_time ON sms_alerts(user_id, sent_at);

-- ════════════════════════════════════════════════════════════
--  0002 — notification channels
-- ════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS whatsapp_subscriptions (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    phone       VARCHAR(20) NOT NULL UNIQUE,
    is_active   BOOLEAN     DEFAULT TRUE,
    opted_in_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_wa_user ON whatsapp_subscriptions(user_id);

CREATE TABLE IF NOT EXISTS telegram_subscriptions (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID,
    chat_id       VARCHAR(30) NOT NULL UNIQUE,
    username      VARCHAR(100),
    h3_index      VARCHAR(15),
    is_active     BOOLEAN     DEFAULT TRUE,
    registered_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_tg_user ON telegram_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_tg_h3   ON telegram_subscriptions(h3_index);

CREATE TABLE IF NOT EXISTS email_subscriptions (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    email          VARCHAR(255) NOT NULL,
    h3_index       VARCHAR(15) NOT NULL,
    is_active      BOOLEAN     DEFAULT TRUE,
    subscribed_at  TIMESTAMPTZ DEFAULT NOW(),
    last_digest_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_email_user ON email_subscriptions(user_id);

-- ════════════════════════════════════════════════════════════
--  0003 — analytics
-- ════════════════════════════════════════════════════════════

ALTER TABLE predictions
    ADD COLUMN IF NOT EXISTS predicted_duration_min    INTEGER,
    ADD COLUMN IF NOT EXISTS predicted_duration_max    INTEGER,
    ADD COLUMN IF NOT EXISTS predicted_duration_median INTEGER;

CREATE TABLE IF NOT EXISTS prediction_accuracy (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    h3_index          VARCHAR(15) NOT NULL,
    period_start      TIMESTAMPTZ NOT NULL,
    period_end        TIMESTAMPTZ NOT NULL,
    total_predictions INTEGER     NOT NULL DEFAULT 0,
    true_positives    INTEGER     NOT NULL DEFAULT 0,
    false_positives   INTEGER     NOT NULL DEFAULT 0,
    true_negatives    INTEGER     NOT NULL DEFAULT 0,
    false_negatives   INTEGER     NOT NULL DEFAULT 0,
    accuracy          FLOAT,
    precision         FLOAT,
    recall            FLOAT,
    f1_score          FLOAT,
    computed_at       TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_accuracy_h3_period ON prediction_accuracy(h3_index, period_start);

CREATE TABLE IF NOT EXISTS neighborhood_stats (
    h3_index           VARCHAR(15) PRIMARY KEY,
    country_code       VARCHAR(5),
    city               VARCHAR(100),
    outages_7d         INTEGER     DEFAULT 0,
    outages_30d        INTEGER     DEFAULT 0,
    outages_90d        INTEGER     DEFAULT 0,
    avg_duration_minutes FLOAT,
    avg_probability_7d FLOAT,
    rank_country       INTEGER,
    rank_city          INTEGER,
    updated_at         TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_stats_country ON neighborhood_stats(country_code, outages_30d);
CREATE INDEX IF NOT EXISTS idx_stats_city    ON neighborhood_stats(city, outages_30d);

-- ════════════════════════════════════════════════════════════
--  0004 — community engagement
-- ════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS user_points (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID        NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    total_points        INTEGER     DEFAULT 0,
    weekly_points       INTEGER     DEFAULT 0,
    monthly_points      INTEGER     DEFAULT 0,
    report_count        INTEGER     DEFAULT 0,
    confirm_count       INTEGER     DEFAULT 0,
    note_count          INTEGER     DEFAULT 0,
    current_streak_days INTEGER     DEFAULT 0,
    last_action_at      TIMESTAMPTZ,
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_points_user   ON user_points(user_id);
CREATE INDEX IF NOT EXISTS idx_points_weekly ON user_points(weekly_points);

CREATE TABLE IF NOT EXISTS user_badges (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    badge_key         VARCHAR(50)  NOT NULL,
    badge_name        VARCHAR(100) NOT NULL,
    badge_emoji       VARCHAR(10)  NOT NULL,
    badge_description VARCHAR(200) NOT NULL,
    earned_at         TIMESTAMPTZ  DEFAULT NOW(),
    CONSTRAINT uq_user_badge UNIQUE (user_id, badge_key)
);
CREATE INDEX IF NOT EXISTS idx_badges_user ON user_badges(user_id);

CREATE TABLE IF NOT EXISTS point_transactions (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    points       INTEGER     NOT NULL,
    action       VARCHAR(50) NOT NULL,
    reference_id VARCHAR(50),
    created_at   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_tx_user ON point_transactions(user_id, created_at);

CREATE TABLE IF NOT EXISTS community_notes (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    h3_index   VARCHAR(15) NOT NULL,
    body       VARCHAR(280) NOT NULL,
    upvotes    INTEGER     DEFAULT 0,
    is_active  BOOLEAN     DEFAULT TRUE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_notes_h3_active ON community_notes(h3_index, is_active);

CREATE TABLE IF NOT EXISTS note_upvotes (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    note_id    UUID        NOT NULL REFERENCES community_notes(id) ON DELETE CASCADE,
    user_id    UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_note_upvote UNIQUE (note_id, user_id)
);

CREATE TABLE IF NOT EXISTS neighbor_alert_log (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    h3_index                VARCHAR(15) NOT NULL,
    triggered_by_report_id  VARCHAR(50) NOT NULL,
    sent_at                 TIMESTAMPTZ DEFAULT NOW(),
    recipients_count        INTEGER     DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_neighbor_log_h3 ON neighbor_alert_log(h3_index, sent_at);

-- ════════════════════════════════════════════════════════════
--  0005 — enterprise
-- ════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS utility_companies (
    id                    UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    name                  VARCHAR(200) NOT NULL,
    country_code          VARCHAR(5)   NOT NULL,
    service_area_h3_cells JSONB,
    api_key               VARCHAR(60)  UNIQUE NOT NULL,
    contact_email         VARCHAR(255) NOT NULL,
    is_active             BOOLEAN      DEFAULT TRUE,
    plan                  VARCHAR(20)  DEFAULT 'trial',
    created_at            TIMESTAMPTZ  DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_utility_api_key ON utility_companies(api_key);
CREATE INDEX IF NOT EXISTS idx_utility_country ON utility_companies(country_code);

CREATE TABLE IF NOT EXISTS business_profiles (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id              UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    h3_index             VARCHAR(15) NOT NULL,
    business_type        VARCHAR(50) NOT NULL,
    name                 VARCHAR(200),
    monthly_revenue_usd  FLOAT,
    employees            INTEGER,
    created_at           TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_biz_user ON business_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_biz_h3   ON business_profiles(h3_index);

CREATE TABLE IF NOT EXISTS webhook_subscriptions (
    id                    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id               UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    h3_index              VARCHAR(15) NOT NULL,
    url                   TEXT        NOT NULL,
    secret                VARCHAR(60) NOT NULL,
    threshold_probability FLOAT       DEFAULT 0.70,
    events                JSONB       DEFAULT '["prediction_threshold","outage_confirmed"]',
    is_active             BOOLEAN     DEFAULT TRUE,
    last_triggered_at     TIMESTAMPTZ,
    created_at            TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_webhook_user ON webhook_subscriptions(user_id);

CREATE TABLE IF NOT EXISTS webhook_events (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID        NOT NULL REFERENCES webhook_subscriptions(id) ON DELETE CASCADE,
    event_type      VARCHAR(50) NOT NULL,
    payload         JSONB       NOT NULL,
    response_status INTEGER,
    attempt         INTEGER     DEFAULT 1,
    success         BOOLEAN     DEFAULT FALSE,
    fired_at        TIMESTAMPTZ DEFAULT NOW(),
    error_message   TEXT
);
CREATE INDEX IF NOT EXISTS idx_webhook_events_sub ON webhook_events(subscription_id, fired_at);

-- ════════════════════════════════════════════════════════════
--  0006 — platform ops
-- ════════════════════════════════════════════════════════════

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE user_locations
    ADD COLUMN IF NOT EXISTS is_active          BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS alert_threshold    FLOAT   NOT NULL DEFAULT 0.70,
    ADD COLUMN IF NOT EXISTS quiet_hours_start  TIME,
    ADD COLUMN IF NOT EXISTS quiet_hours_end    TIME,
    ADD COLUMN IF NOT EXISTS notify_channels    JSONB   NOT NULL DEFAULT '["sms","push"]';

CREATE TABLE IF NOT EXISTS fraud_flags (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID,
    report_id   UUID,
    rule        VARCHAR(50) NOT NULL,
    detail      TEXT,
    severity    VARCHAR(10) DEFAULT 'medium',
    resolved    BOOLEAN     DEFAULT FALSE,
    resolved_by UUID,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_fraud_user       ON fraud_flags(user_id);
CREATE INDEX IF NOT EXISTS idx_fraud_created    ON fraud_flags(created_at);
CREATE INDEX IF NOT EXISTS idx_fraud_unresolved ON fraud_flags(resolved, created_at);

-- ════════════════════════════════════════════════════════════
--  0007 — accessibility (SMS inbound log)
-- ════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS sms_inbound_log (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    phone       VARCHAR(20) NOT NULL,
    message     VARCHAR(160) NOT NULL,
    command     VARCHAR(20) NOT NULL,
    reply       VARCHAR(160) NOT NULL,
    user_id     UUID        REFERENCES users(id) ON DELETE SET NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_sms_inbound_log_phone    ON sms_inbound_log(phone);
CREATE INDEX IF NOT EXISTS ix_sms_inbound_log_received ON sms_inbound_log(received_at);

-- ════════════════════════════════════════════════════════════
--  Mark alembic as fully migrated to revision 0007
-- ════════════════════════════════════════════════════════════

INSERT INTO alembic_version (version_num)
VALUES ('0007')
ON CONFLICT DO NOTHING;
