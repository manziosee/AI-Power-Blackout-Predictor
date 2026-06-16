# AI Power Blackout Predictor — Full System Structure

## Overview

Global AI-powered electricity outage prediction platform with crowdsourced reporting,
ML-based predictions, neighborhood heatmaps, and multi-channel alerts (SMS via Jasmin/SMPP,
push notifications, web). Works worldwide, offline-capable PWA.

---

## Folder Structure

```
ai-power-blackout-predictor/
│
├── backend/                          # FastAPI — main application API
│   ├── app/
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── endpoints/
│   │   │   │   │   ├── predictions.py      # GET predictions for area/cell
│   │   │   │   │   ├── outages.py          # CRUD outage reports
│   │   │   │   │   ├── alerts.py           # Manage user alert settings
│   │   │   │   │   ├── users.py            # Auth, profile, phone registration
│   │   │   │   │   ├── neighborhoods.py    # H3 cell lookup, heatmap data
│   │   │   │   │   └── reports.py          # User-submitted outage reports
│   │   │   │   └── router.py
│   │   │   └── deps.py                     # Auth dependencies, DB session
│   │   ├── core/
│   │   │   ├── config.py                   # Settings (env vars, secrets)
│   │   │   ├── security.py                 # JWT, password hashing
│   │   │   └── database.py                 # SQLAlchemy engine + session
│   │   ├── models/                         # SQLAlchemy ORM models
│   │   │   ├── user.py
│   │   │   ├── outage.py
│   │   │   ├── prediction.py
│   │   │   ├── alert.py
│   │   │   ├── weather.py
│   │   │   └── neighborhood.py
│   │   ├── schemas/                        # Pydantic request/response schemas
│   │   │   ├── user.py
│   │   │   ├── outage.py
│   │   │   ├── prediction.py
│   │   │   └── alert.py
│   │   ├── services/
│   │   │   ├── prediction_service.py       # Call ML engine, store results
│   │   │   ├── alert_service.py            # Trigger SMS + push notifications
│   │   │   ├── weather_service.py          # Fetch + cache weather data
│   │   │   └── outage_service.py           # Outage report verification logic
│   │   ├── tasks/                          # Celery background tasks
│   │   │   ├── predict.py                  # Run predictions every 4h
│   │   │   ├── alert.py                    # Send alerts when threshold crossed
│   │   │   └── weather_fetch.py            # Poll OpenWeatherMap every hour
│   │   └── main.py                         # FastAPI app entry point
│   ├── migrations/                         # Alembic database migrations
│   │   └── versions/
│   ├── tests/
│   │   ├── test_predictions.py
│   │   ├── test_alerts.py
│   │   └── test_outages.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── sms-gateway/                      # Custom SMS Gateway (Jasmin + SMPP)
│   ├── api/                          # FastAPI wrapper — your SMS API
│   │   ├── routes/
│   │   │   ├── send.py               # POST /sms/send
│   │   │   ├── status.py             # GET /sms/status/{message_id}
│   │   │   └── webhook.py            # Delivery receipts from telecoms
│   │   ├── services/
│   │   │   ├── router.py             # Route by country code → SMPP connector
│   │   │   └── templates.py          # Format messages per language
│   │   └── main.py
│   ├── connectors/                   # SMPP connectors — operator-agnostic
│   │   ├── base.py                   # Abstract base connector
│   │   ├── jasmin.py                 # Generic JasminConnector (all countries/operators)
│   │   └── fallback.py               # No-op fallback (logs, never throws)
│   ├── templates/                    # SMS message templates per language
│   │   ├── en.json
│   │   ├── fr.json
│   │   ├── sw.json                   # Swahili
│   │   ├── ar.json
│   │   ├── es.json
│   │   ├── pt.json
│   │   └── rw.json                   # Kinyarwanda
│   ├── jasmin/                       # Jasmin SMS Gateway config
│   │   ├── jasmin.cfg                # Main Jasmin config
│   │   └── connectors.cfg            # SMPP connector definitions
│   ├── requirements.txt
│   └── Dockerfile
│
├── ml-engine/                        # ML Prediction Engine
│   ├── models/
│   │   ├── base_model.py             # Abstract base model interface
│   │   ├── xgboost_model.py          # XGBoost classifier (outage yes/no in 4h)
│   │   ├── prophet_model.py          # Facebook Prophet for 7-day trend
│   │   └── ensemble.py               # Combine XGBoost + Prophet → final score
│   ├── features/
│   │   ├── weather_features.py       # Rainfall, temp, wind, humidity
│   │   ├── temporal_features.py      # Hour, weekday, month, season
│   │   ├── historical_features.py    # Past outage frequency per H3 cell
│   │   └── grid_features.py          # Grid zone, infrastructure age (if available)
│   ├── training/
│   │   ├── train.py                  # Training pipeline per region
│   │   ├── evaluate.py               # Model accuracy, F1, precision/recall
│   │   └── registry.py               # Save/load models by region key
│   ├── inference/
│   │   ├── predictor.py              # Real-time single cell prediction
│   │   └── batch_predict.py          # Bulk predict all H3 cells in a region
│   ├── data/
│   │   ├── collectors/
│   │   │   ├── weather_collector.py  # Pull from OpenWeatherMap
│   │   │   ├── outage_collector.py   # Pull from PostgreSQL outage_reports
│   │   │   ├── entso_collector.py    # ENTSO-E grid data (Europe)
│   │   │   └── eia_collector.py      # EIA grid data (USA)
│   │   └── processors/
│   │       ├── cleaner.py            # Remove duplicates, fill gaps
│   │       └── feature_builder.py    # Build feature matrix for training
│   ├── notebooks/                    # Jupyter notebooks for exploration
│   │   ├── 01_eda.ipynb
│   │   ├── 02_feature_engineering.ipynb
│   │   └── 03_model_evaluation.ipynb
│   ├── model_store/                  # Saved model artifacts per region
│   │   ├── africa_east/
│   │   │   ├── xgboost_v1.pkl
│   │   │   └── prophet_v1.pkl
│   │   ├── europe_central/
│   │   ├── north_america_east/
│   │   ├── north_america_west/
│   │   ├── asia_south/
│   │   └── latin_america/
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                         # React PWA — Web Application
│   ├── public/
│   │   ├── manifest.json             # PWA manifest
│   │   └── sw.js                     # Service Worker (offline support)
│   ├── src/
│   │   ├── components/
│   │   │   ├── Map/
│   │   │   │   ├── HeatmapLayer.tsx      # Mapbox heatmap of risk zones
│   │   │   │   ├── NeighborhoodGrid.tsx  # H3 hexagon grid overlay
│   │   │   │   └── OutageMarkers.tsx     # Live reported outage pins
│   │   │   ├── Alerts/
│   │   │   │   ├── AlertBanner.tsx       # Top-of-page warning banner
│   │   │   │   ├── AlertList.tsx         # List of recent/upcoming alerts
│   │   │   │   └── AlertSettings.tsx     # SMS/push threshold config
│   │   │   ├── Dashboard/
│   │   │   │   ├── PredictionCard.tsx    # Probability % for your area
│   │   │   │   ├── OutageHistory.tsx     # Chart of past outages
│   │   │   │   └── RiskMeter.tsx         # Visual risk gauge (low/med/high)
│   │   │   ├── Report/
│   │   │   │   └── ReportOutageForm.tsx  # User report form (works offline)
│   │   │   └── common/
│   │   │       ├── LanguageSwitcher.tsx
│   │   │       └── OfflineBadge.tsx      # Shows when app is offline
│   │   ├── pages/
│   │   │   ├── Home.tsx                  # Landing + quick prediction view
│   │   │   ├── Dashboard.tsx             # Full user dashboard
│   │   │   ├── Map.tsx                   # Global heatmap view
│   │   │   ├── AlertSettings.tsx         # Manage locations + alert prefs
│   │   │   ├── ReportOutage.tsx          # Report current outage
│   │   │   └── Profile.tsx               # User profile + phone number
│   │   ├── hooks/
│   │   │   ├── usePredictions.ts         # Fetch + cache predictions
│   │   │   ├── useOfflineSync.ts         # Queue reports when offline
│   │   │   └── useGeolocation.ts         # Get user coordinates
│   │   ├── store/                        # Zustand global state
│   │   │   ├── predictions.ts
│   │   │   ├── alerts.ts
│   │   │   └── user.ts
│   │   ├── services/
│   │   │   ├── api.ts                    # Axios client → backend API
│   │   │   ├── offline.ts                # IndexedDB wrapper (Dexie.js)
│   │   │   └── push.ts                   # Web Push subscription
│   │   ├── i18n/
│   │   │   ├── index.ts                  # i18next setup
│   │   │   └── locales/
│   │   │       ├── en.json
│   │   │       ├── fr.json
│   │   │       ├── sw.json
│   │   │       ├── ar.json
│   │   │       ├── es.json
│   │   │       ├── pt.json
│   │   │       └── rw.json
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   └── Dockerfile
│
├── data-pipeline/                    # ETL — Data collection & processing
│   ├── collectors/
│   │   ├── weather.py                # Poll OpenWeatherMap every hour per region
│   │   ├── grid_entso.py             # ENTSO-E (Europe grid load data)
│   │   ├── grid_eia.py               # EIA API (USA grid data)
│   │   └── crowdsource.py            # Process + verify user outage reports
│   ├── processors/
│   │   ├── h3_mapper.py              # Map lat/lng → H3 cell index
│   │   ├── normalizer.py             # Normalize data per region
│   │   └── aggregator.py             # Aggregate cell-level stats
│   ├── schedulers/
│   │   └── cron.py                   # APScheduler job definitions
│   ├── requirements.txt
│   └── Dockerfile
│
├── infrastructure/                   # Docker + deployment config
│   ├── docker-compose.yml            # Full local dev stack
│   ├── docker-compose.prod.yml       # Production overrides
│   ├── nginx/
│   │   └── nginx.conf                # Reverse proxy (frontend + backend + sms)
│   ├── postgres/
│   │   └── init.sql                  # PostGIS extension setup
│   └── redis/
│       └── redis.conf
│
└── docs/
    ├── API.md                        # REST API documentation
    ├── SMS_GATEWAY.md                # SMPP setup guide per operator
    ├── ML_MODEL.md                   # Model training + evaluation guide
    └── DEPLOYMENT.md                 # Production deployment steps
```

---

## Database Schema (PostgreSQL + PostGIS)

```sql
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR UNIQUE,
    phone           VARCHAR UNIQUE NOT NULL,       -- E.164 format: +250788123456
    country_code    VARCHAR(5) NOT NULL,            -- RW, KE, US, FR ...
    language        VARCHAR(5) DEFAULT 'en',
    password_hash   VARCHAR,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- H3 hexagonal grid cells (neighborhoods)
CREATE TABLE h3_cells (
    h3_index        VARCHAR(15) PRIMARY KEY,       -- Uber H3 cell ID
    center_lat      DECIMAL(10, 7),
    center_lng      DECIMAL(10, 7),
    country_code    VARCHAR(5),
    region          VARCHAR(100),
    city            VARCHAR(100),
    resolution      INTEGER DEFAULT 8              -- H3 resolution 7-9 for neighborhoods
);

-- Users can track multiple locations
CREATE TABLE user_locations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    h3_index        VARCHAR(15) REFERENCES h3_cells(h3_index),
    label           VARCHAR(50),                   -- "Home", "Office", "Parents"
    is_primary      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- Crowdsourced outage reports
CREATE TABLE outage_reports (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID REFERENCES users(id),
    h3_index            VARCHAR(15),
    location            GEOGRAPHY(POINT, 4326),    -- PostGIS point
    reported_at         TIMESTAMP DEFAULT NOW(),
    resolved_at         TIMESTAMP,
    duration_minutes    INTEGER,
    source              VARCHAR(20),               -- 'app', 'sms', 'ussd', 'api'
    verified            BOOLEAN DEFAULT FALSE,
    verification_count  INTEGER DEFAULT 1          -- # users confirmed same outage
);
CREATE INDEX idx_outage_h3 ON outage_reports(h3_index);
CREATE INDEX idx_outage_time ON outage_reports(reported_at);

-- ML predictions per H3 cell
CREATE TABLE predictions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    h3_index                VARCHAR(15),
    predicted_at            TIMESTAMP DEFAULT NOW(),
    window_start            TIMESTAMP,             -- prediction covers this window
    window_end              TIMESTAMP,
    probability             DECIMAL(5, 4),         -- 0.0 to 1.0
    confidence              DECIMAL(5, 4),
    risk_level              VARCHAR(10),           -- 'low', 'medium', 'high', 'critical'
    model_version           VARCHAR(20),
    region_model            VARCHAR(50),           -- 'africa_east', 'europe_central'
    features_snapshot       JSONB                  -- feature values used in prediction
);
CREATE INDEX idx_pred_h3_time ON predictions(h3_index, predicted_at);

-- Hourly weather snapshots per H3 cell
CREATE TABLE weather_snapshots (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    h3_index        VARCHAR(15),
    recorded_at     TIMESTAMP DEFAULT NOW(),
    temperature_c   DECIMAL(5, 2),
    rainfall_mm     DECIMAL(6, 2),
    wind_speed_ms   DECIMAL(5, 2),
    humidity_pct    INTEGER,
    weather_code    INTEGER,                       -- OpenWeatherMap code
    is_forecast     BOOLEAN DEFAULT FALSE          -- true = future forecast
);

-- SMS alerts log
CREATE TABLE sms_alerts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id),
    phone           VARCHAR NOT NULL,
    message         TEXT NOT NULL,
    language        VARCHAR(5),
    prediction_id   UUID REFERENCES predictions(id),
    sent_at         TIMESTAMP DEFAULT NOW(),
    status          VARCHAR(20),                   -- 'queued', 'sent', 'delivered', 'failed'
    provider        VARCHAR(30),                   -- 'jasmin', 'fallback'
    smpp_message_id VARCHAR(50),
    error_message   TEXT
);

-- Alert subscriptions (what triggers an SMS/push for a user)
CREATE TABLE alert_subscriptions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID REFERENCES users(id) ON DELETE CASCADE,
    h3_index                VARCHAR(15),
    threshold_probability   DECIMAL(4, 3) DEFAULT 0.70,   -- alert when >= 70%
    channels                JSONB DEFAULT '["sms", "push"]',
    quiet_hours_start       TIME,                          -- don't SMS between these hours
    quiet_hours_end         TIME,
    is_active               BOOLEAN DEFAULT TRUE
);
```

---

## SMS Gateway — Message Flow

```
[Backend: Alert Service]
    │
    │  POST /sms/send
    │  { "to": "+250788123456", "country": "RW", "lang": "rw",
    │    "template": "outage_warning", "vars": { "time": "18:00", "prob": "82%" } }
    ▼
[SMS Gateway API — FastAPI]
    │
    ├── 1. Load template in user's language
    │       "Imbaraga: amashanyarazi azima mu gace kawe saa 12:00 (82%)"
    │
    ├── 2. Route via JASMIN_CONNECTOR_{CC} env var (country-agnostic)
    │
    └── 3. Submit to Jasmin HTTP API → Jasmin → SMPP → Any operator worldwide → Phone
```

### SMS Templates Example (outage_warning)
```json
{
  "en": "POWER ALERT: {prob}% chance of outage in your area at {time}. Charge devices now.",
  "fr": "ALERTE: {prob}% de risque de coupure dans votre zone à {time}. Chargez vos appareils.",
  "sw": "TAHADHARI: Uwezekano wa {prob}% wa kukatiwa umeme saa {time}. Chaji vifaa vyako.",
  "rw": "IMBARAGA: {prob}% y'amashanyarazi azima mu gace kawe saa {time}. Shaza ibikoresho."
}
```

---

## ML Prediction Pipeline

```
Every 4 hours (Celery task):

1. FETCH
   OpenWeatherMap → next 24h forecast for each tracked H3 cell

2. BUILD FEATURES
   [rainfall_mm, temp_c, wind_ms, humidity]          ← weather
   [hour, weekday, month, is_holiday]                ← temporal
   [outages_last_7d, outages_last_30d, avg_duration] ← historical
   [h3_resolution, country_code, grid_zone]           ← spatial

3. PREDICT
   XGBoost  → P(outage in next 4h)   → short-term score
   Prophet  → trend over next 7 days → long-term trend
   Ensemble → weighted combination   → final_probability

4. STORE
   INSERT INTO predictions (h3_index, probability, window_start, ...)

5. ALERT CHECK
   For each prediction WHERE probability >= user_threshold:
     → Queue SMS alert task
     → Queue push notification task
```

---

## Tech Stack Summary

| Layer | Technology | Purpose |
|---|---|---|
| Backend API | FastAPI (Python) | Main REST API |
| Database | PostgreSQL + PostGIS | Data + geospatial queries |
| Cache | Redis | Session cache, Celery broker |
| Task Queue | Celery | Background jobs, SMS sending |
| ML Short-term | XGBoost | Outage classification |
| ML Long-term | Facebook Prophet | 7-day trend forecasting |
| Geospatial Grid | Uber H3 | Hexagonal neighborhood cells |
| Weather | OpenWeatherMap API | Global weather + forecasts |
| SMS Gateway | Jasmin + SMPP | Your own SMS infrastructure |
| SMS Protocol | SMPP v3.4 | Telecom operator connection |
| Frontend | React + Vite | Web application |
| PWA/Offline | Service Workers + Dexie.js (IndexedDB) | Offline support |
| Maps | Mapbox GL JS | Global heatmap rendering |
| State | Zustand | Frontend state management |
| i18n | i18next | Multi-language support |
| Styling | Tailwind CSS | Mobile-first UI |
| Auth | JWT (FastAPI) | Authentication |
| Reverse Proxy | Nginx | Route traffic to services |
| Containerization | Docker + Docker Compose | All services containerized |

---

## Services Port Map (Local Dev)

| Service | Port | Description |
|---|---|---|
| Backend API | 8000 | FastAPI main app |
| SMS Gateway API | 8001 | SMS send/status API |
| Jasmin HTTP API | 8080 | Jasmin internal API |
| Jasmin CLI | 8990 | Jasmin management |
| RabbitMQ | 5672 | Jasmin message queue |
| RabbitMQ UI | 15672 | RabbitMQ management |
| PostgreSQL | 5432 | Main database |
| Redis | 6379 | Cache + Celery broker |
| Frontend | 5173 | React dev server |
| Nginx | 80 / 443 | Reverse proxy (prod) |

---

## Supported Languages (Phase 1)

| Code | Language | Regions |
|---|---|---|
| en | English | Global |
| fr | French | Africa (Francophone), Europe |
| sw | Swahili | East Africa |
| rw | Kinyarwanda | Rwanda |
| ar | Arabic | Middle East, North Africa |
| es | Spanish | Latin America, Spain |
| pt | Portuguese | Brazil, Angola, Mozambique |

---

## Build Phases

### Phase 1 — Foundation (Weeks 1-3)
- [ ] PostgreSQL schema + PostGIS setup
- [ ] FastAPI backend (users, outage reports, H3 cell lookup)
- [ ] OpenWeatherMap integration
- [ ] Jasmin SMS gateway Docker setup + first SMPP connector
- [ ] React frontend (home, report outage, basic map)
- [ ] SMS alert on manual outage report confirmation

### Phase 2 — Intelligence (Weeks 4-6)
- [ ] XGBoost model training on collected data + weather
- [ ] Prophet trend model
- [ ] Celery prediction jobs every 4h
- [ ] Mapbox heatmap with H3 grid overlay
- [ ] Risk level classification (low / medium / high / critical)
- [ ] Alert subscription system (threshold per user)

### Phase 3 — Scale & Polish (Weeks 7-9)
- [ ] PWA Service Worker + IndexedDB offline support
- [ ] i18n all 7 languages
- [ ] Additional SMPP connectors (per country)
- [ ] Web Push notifications
- [ ] USSD fallback (feature phones, via Africa's Talking or Jasmin)
- [ ] Public API for utilities / enterprises
- [ ] Stripe billing (Pro + Business tiers)
