<div align="center">

# AI Power Blackout Predictor

**Predict electricity outages before they happen — anywhere in the world.**

AI-powered platform that combines crowdsourced outage reports, real-time weather data, and machine learning to predict power blackouts at the neighborhood level. Sends SMS alerts via your own SMPP gateway (Jasmin), renders live heatmaps, and works offline.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)
[![CI](https://github.com/manziosee/AI-Power-Blackout-Predictor/actions/workflows/ci.yml/badge.svg)](https://github.com/manziosee/AI-Power-Blackout-Predictor/actions)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=for-the-badge)](https://github.com/manziosee/AI-Power-Blackout-Predictor/pulls)

</div>

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Database Setup (Supabase)](#database-setup-supabase)
- [Environment Variables](#environment-variables)
- [SMS Gateway — Jasmin + SMPP](#sms-gateway--jasmin--smpp)
- [ML Engine](#ml-engine)
- [AI Insights (Groq LLM)](#ai-insights-groq-llm)
- [Supported Languages](#supported-languages)
- [API Reference](#api-reference)
- [CI/CD](#cicd)
- [Build Phases](#build-phases)
- [License](#license)

---

## Overview

Electricity outages are one of the most disruptive daily challenges across Africa, Asia, Latin America, and developing regions worldwide. This platform uses **AI + crowdsourcing** to predict outages hours before they happen and warn residents via SMS — even on feature phones with no internet.

Built to scale globally, with per-region ML models, multi-language SMS alerts, a fully offline-capable Progressive Web App, USSD fallback (`*384#`), and two-way SMS interaction.

---

## Key Features

| Feature | Description |
|---|---|
| **AI Predictions** | XGBoost + Prophet ensemble predicts outage probability per neighborhood cell |
| **AI Explanations** | Groq LLM (llama-3.1-8b-instant) generates plain-language risk summaries in 7 languages |
| **Own SMS Gateway** | Jasmin + SMPP connects directly to any telecom operator worldwide — no per-SMS vendor fees |
| **Neighborhood Heatmaps** | Uber H3 hexagonal grid renders real-time risk maps worldwide |
| **Offline Support** | PWA with Service Workers + IndexedDB — works without internet |
| **USSD Fallback** | `*384#` works on any feature phone, no internet required |
| **Two-Way SMS** | Users can report outages and query predictions by SMS |
| **Crowdsourced Reports** | App and SMS reports feed the ML model — 3-report consensus verifies outages |
| **7 Languages** | English, French, Swahili, Kinyarwanda, Arabic, Spanish, Portuguese |
| **4-Hour Predictions** | Runs every 4 hours, checks weather + history + grid patterns |
| **Multi-Channel Alerts** | SMS, push notifications, email, Telegram, WhatsApp — user-configurable thresholds |
| **Admin Dashboard** | Fraud detection, multi-location tracking, platform operations |
| **Enterprise API** | Utility companies and governments can subscribe via webhook |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND (PWA)                       │
│   React 18 · Mapbox Heatmap · Offline-first · i18n (7 lang)│
└───────────────────────┬─────────────────────────────────────┘
                        │ REST API (FastAPI)
┌───────────────────────▼─────────────────────────────────────┐
│                    BACKEND (FastAPI)                         │
│     Auth · Users · Predictions · Outages · Alerts           │
│     Admin · Analytics · Community · Enterprise · USSD       │
│                  Celery Beat (every 4h)                      │
└──────┬──────────────────────┬──────────────────────┬────────┘
       │                      │                      │
┌──────▼──────┐   ┌───────────▼──────────┐  ┌──────▼────────┐
│  ML ENGINE  │   │     DATA PIPELINE    │  │  SMS GATEWAY  │
│  XGBoost    │   │  OpenWeatherMap      │  │ Jasmin + SMPP │
│  Prophet    │   │  Crowdsource ingest  │  │  Generic env  │
│  Groq LLM   │   │  H3 Mapper · Cron   │  │  var routing  │
└─────────────┘   └──────────────────────┘  └───────────────┘
       │                      │                      │
┌──────▼──────────────────────▼──────────────────────▼────────┐
│           Supabase (PostgreSQL) · Redis · RabbitMQ           │
└─────────────────────────────────────────────────────────────┘
```

**Data flow:**
1. **OpenWeatherMap** → Weather snapshots stored per H3 cell hourly
2. **Users** → Report outages via app / SMS / USSD → 3-report consensus verifies
3. **Celery** → Runs predictions every 4h per cell → stores probability + risk level
4. **Groq LLM** → Generates human-readable explanation in user's language
5. **Alert checker** → Matches predictions against subscriptions → fires SMS / push / email / Telegram
6. **Frontend** → Reads predictions → renders heatmap → shows risk for user's location

---

## Tech Stack

### Backend
- **Python 3.12** · **FastAPI** (async) · **SQLAlchemy 2.x** · **Alembic** migrations
- **Celery + Celery Beat** for scheduled prediction tasks
- **Pydantic v2** for schema validation
- **passlib + bcrypt** for password hashing
- **python-jose** for JWT tokens

### Database & Cache
- **Supabase** (PostgreSQL 15) — cloud-hosted, free tier for development
- **Redis 7** — Celery broker + response cache
- **RabbitMQ** — Jasmin message queue

### Machine Learning
- **XGBoost** — primary classifier (70% ensemble weight)
- **Prophet** — 7-day trend model (30% ensemble weight)
- **scikit-learn** · **NumPy** · **Pandas**
- **Groq** (llama-3.1-8b-instant) — AI explanation generation

### SMS & Messaging
- **Jasmin** open-source SMS gateway (SMPP v3.4) — generic, works with any aggregator
- **SMPP** credentials via env vars — no country-specific connectors in code
- Inbound SMS parsing + two-way interaction
- USSD handler (`*384#`)

### Frontend
- **React 18** · **TypeScript** · **Vite** · **Tailwind CSS**
- **Mapbox GL JS** — heatmap visualization
- **Zustand** — state management
- **i18next** — 7-language support
- **PWA** with Service Worker + IndexedDB offline storage

### Geospatial
- **Uber H3** (resolution 8) — ~460m hexagonal cells, worldwide coverage

### Infrastructure
- **Docker Compose** — full local stack
- **Nginx** — reverse proxy (production)

### External APIs
- **OpenWeatherMap** — weather forecasts (free tier, global)
- **Groq API** — LLM inference (free tier available)

---

## Project Structure

```
ai-power-blackout-predictor/
│
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/   → auth, predictions, outages, alerts, insights, admin
│   │   ├── core/               → config, database, security
│   │   ├── models/             → SQLAlchemy ORM models
│   │   ├── schemas/            → Pydantic request/response schemas
│   │   ├── services/           → weather, SMS (Jasmin), Groq LLM
│   │   └── tasks/              → Celery tasks (predict, alert dispatch)
│   ├── migrations/versions/    → Alembic migration chain (0001→0007)
│   ├── scripts/
│   │   └── bootstrap_supabase.sql  → one-shot Supabase DB init
│   ├── tests/                  → pytest test suite
│   └── requirements.txt
│
├── frontend/                   → React PWA
├── sms-gateway/                → Jasmin wrapper microservice
├── ml-engine/                  → XGBoost + Prophet training + inference
├── data-pipeline/              → ETL cron jobs
└── docker-compose.yml
```

---

## Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- [Git](https://git-scm.com/)
- A [Supabase](https://supabase.com) project (free tier)
- An [OpenWeatherMap API key](https://openweathermap.org/api) (free tier)

### 1 — Clone & configure

```bash
git clone https://github.com/manziosee/AI-Power-Blackout-Predictor.git
cd AI-Power-Blackout-Predictor

cp .env.example .env
```

Edit `.env` with your credentials (see [Environment Variables](#environment-variables) below).

### 2 — Initialize the database

Open your Supabase project → **SQL Editor** and paste the entire contents of [backend/scripts/bootstrap_supabase.sql](backend/scripts/bootstrap_supabase.sql). Run it once. This creates all 20+ tables and marks Alembic as fully migrated to revision `0007`.

### 3 — Start all services

```bash
docker-compose up -d
```

### 4 — Seed neighborhood cells

```bash
docker-compose exec data-pipeline python processors/h3_mapper.py
```

### 5 — Open the app

| URL | Description |
|---|---|
| `http://localhost:5173` | React frontend |
| `http://localhost:8000/docs` | Swagger API docs |
| `http://localhost:8000/redoc` | ReDoc API docs |
| `http://localhost:15672` | RabbitMQ dashboard (`guest/guest`) |

### Local development (without Docker)

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# Run tests
cd backend
pytest
```

---

## Database Setup (Supabase)

All tables are defined in [backend/scripts/bootstrap_supabase.sql](backend/scripts/bootstrap_supabase.sql). Run it once in the Supabase SQL Editor.

Tables created (grouped by migration revision):

| Revision | Tables |
|---|---|
| 0001 | `h3_cells`, `users`, `user_locations`, `outage_reports`, `predictions`, `weather_snapshots`, `alert_subscriptions`, `push_subscriptions`, `sms_alerts` |
| 0002 | `whatsapp_subscriptions`, `telegram_subscriptions`, `email_subscriptions` |
| 0003 | `prediction_accuracy`, `neighborhood_stats` (+ duration columns on `predictions`) |
| 0004 | `user_points`, `user_badges`, `point_transactions`, `community_notes`, `note_upvotes`, `neighbor_alert_log` |
| 0005 | `utility_companies`, `business_profiles`, `webhook_subscriptions`, `webhook_events` |
| 0006 | `fraud_flags` (+ `is_admin` on `users`, alert columns on `user_locations`) |
| 0007 | `sms_inbound_log` |

After running the SQL, the `alembic_version` table is set to `0007` so Alembic recognizes the DB as fully migrated.

---

## Environment Variables

Copy `.env.example` to `.env` and fill in:

| Variable | Description | Required |
|---|---|---|
| `SECRET_KEY` | JWT signing secret (64+ random chars) | Yes |
| `DATABASE_URL` | Async PostgreSQL URL (`postgresql+asyncpg://...`) | Yes |
| `SYNC_DATABASE_URL` | Sync PostgreSQL URL for Alembic (`postgresql://...`) | Yes |
| `REDIS_URL` | Redis connection string | Yes |
| `OPENWEATHERMAP_API_KEY` | OWM API key (free tier, global) | Yes |
| `GROQ_API_KEY` | Groq API key for AI explanations | Optional |
| `VITE_MAPBOX_TOKEN` | Mapbox GL JS token | Yes (frontend) |
| `JASMIN_HOST` | Jasmin container hostname | Yes (SMS) |
| `SMPP_HOST` | Your SMPP aggregator endpoint | Yes (SMS) |
| `SMPP_USERNAME` | SMPP username | Yes (SMS) |
| `SMPP_PASSWORD` | SMPP password | Yes (SMS) |
| `JASMIN_CONNECTOR_DEFAULT` | Default Jasmin connector ID | Yes (SMS) |
| `SMTP_HOST` | SMTP server for email alerts | Optional |
| `SMTP_PORT` | SMTP port (587 for TLS) | Optional |
| `SMTP_USERNAME` | SMTP username / email address | Optional |
| `SMTP_PASSWORD` | SMTP App Password (not account password) | Optional |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token from @BotFather | Optional |
| `USSD_SHORT_CODE` | USSD short code digits | Optional |
| `VAPID_PUBLIC_KEY` | Web Push VAPID public key | Optional |
| `VAPID_PRIVATE_KEY` | Web Push VAPID private key | Optional |

See [.env.example](.env.example) for the complete list with defaults.

---

## SMS Gateway — Jasmin + SMPP

All SMS routing goes through [Jasmin](https://docs.jasminsms.com/), an open-source Python SMS gateway that speaks SMPP v3.4 — the protocol used by every telecom operator worldwide.

```
Your App
   ↓  POST /send-sms  { phone, message }
SMS Gateway API  (Jasmin wrapper)
   ↓  Routes via JASMIN_CONNECTOR_DEFAULT env var
Jasmin Gateway
   ↓  SMPP v3.4 (operator-agnostic)
Any SMPP aggregator worldwide  (Sinch, Infobip, Vonage, direct operator, ...)
   ↓
User's Phone  (any country, any network)
```

**No country-specific connectors in code.** Routing is 100% controlled by environment variables. To add a new country or operator: update SMPP credentials in `.env` — no code changes needed.

### Cost comparison

| Provider | Cost per SMS | 100k SMS/month |
|---|---|---|
| Twilio | ~$0.05–0.08 | ~$6,500 |
| Africa's Talking | ~$0.01–0.03 | ~$2,000 |
| **Own SMPP (via Jasmin)** | **~$0.003–0.008** | **~$500** |

---

## ML Engine

### Prediction pipeline (Celery, every 4 hours)

```
1. FETCH      OpenWeatherMap forecast → next 24h per tracked H3 cell
2. FEATURES   Weather + temporal + historical outage + grid type
3. PREDICT    XGBoost  → P(outage in 4h)   [weight: 70%]
              Prophet  → 7-day trend        [weight: 30%]
              Ensemble → final probability
4. EXPLAIN    Groq LLM → human-readable summary in user's language
5. STORE      PostgreSQL predictions table
6. ALERT      Check subscriptions → SMS + push if threshold crossed
```

### Feature set

| Category | Features |
|---|---|
| Weather | `rainfall_mm`, `temperature_c`, `wind_speed_ms`, `humidity_pct`, `is_storm`, `is_heavy_rain` |
| Temporal | `hour`, `day_of_week`, `month`, `is_weekend`, `is_peak_hour` |
| Historical | `outages_last_7d`, `outages_last_30d`, `avg_duration_minutes`, `outage_frequency_per_week` |
| Grid | `grid_type`, `center_lat`, `center_lng` |

### Risk levels

| Level | Probability | Color |
|---|---|---|
| Low | < 40% | Green |
| Medium | 40–64% | Amber |
| High | 65–84% | Red |
| Critical | >= 85% | Purple |

### Train the model

```bash
cd ml-engine
python training/train.py --region all
```

---

## AI Insights (Groq LLM)

The `/api/v1/insights/` endpoints use the Groq API (`llama-3.1-8b-instant`) to generate plain-language explanations:

```
GET /api/v1/insights/prediction/{h3_index}?language=rw
→ "Amashanyarazi azima mu gace kawe saa 18:00 (82%). Shaza ibikoresho byawe nonaha."

GET /api/v1/insights/history/{h3_index}?language=en
→ "This area had 12 outages in the past 30 days, averaging 2.4 hours each..."
```

If `GROQ_API_KEY` is not set, these endpoints return an empty explanation string without failing — predictions continue to work normally.

---

## Supported Languages

| Code | Language | Primary Regions |
|---|---|---|
| `en` | English | Global default |
| `fr` | French | Francophone Africa, Europe |
| `sw` | Swahili | East Africa (KE, TZ, UG) |
| `rw` | Kinyarwanda | Rwanda |
| `ar` | Arabic | Middle East, North Africa |
| `es` | Spanish | Latin America, Spain |
| `pt` | Portuguese | Brazil, Angola, Mozambique |

SMS messages and AI explanations are generated in the user's registered language.

---

## API Reference

Base URL: `http://localhost:8000/api/v1`

Interactive docs: `http://localhost:8000/docs`

### Core endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/register` | No | Register new user |
| `POST` | `/auth/login` | No | Get JWT token |
| `GET` | `/auth/me` | Yes | Current user profile |
| `GET` | `/predictions/` | Yes | List predictions by H3 cell |
| `GET` | `/predictions/cell/{h3_index}` | Yes | Latest prediction for a cell |
| `POST` | `/outages/report` | Yes | Report a power outage |
| `GET` | `/outages/{h3_index}` | Yes | Outage history for a cell |
| `POST` | `/alerts/subscribe` | Yes | Subscribe to alerts |
| `GET` | `/alerts/my-subscriptions` | Yes | List my subscriptions |
| `GET` | `/insights/prediction/{h3_index}` | Yes | AI explanation for prediction |
| `GET` | `/insights/history/{h3_index}` | Yes | AI explanation for outage history |
| `GET` | `/admin/stats` | Admin | Platform statistics |
| `POST` | `/sms/inbound` | No | Inbound SMS webhook |
| `POST` | `/ussd` | No | USSD session handler |

### New feature endpoints (migration 0008–0021)

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/planned-outages/` | No | Upcoming planned outages for a cell |
| `POST` | `/planned-outages/` | Admin | Create a planned outage entry |
| `POST` | `/feedback/respond` | No | Record YES/NO response to feedback SMS |
| `GET` | `/feedback/accuracy/{h3_index}` | Yes | Prediction accuracy from user feedback |
| `POST` | `/medical-priority/register` | Yes | Self-register as medical priority user |
| `GET` | `/medical-priority/heatmap` | Admin | Count of priority users per cell |
| `GET` | `/resilience/{h3_index}` | Yes | Neighborhood resilience score (0–100) |
| `GET` | `/resilience/top` | No | Top 20 most resilient cells |
| `POST` | `/insurance/policies` | Yes | Create parametric insurance policy |
| `GET` | `/insurance/claims` | Yes | List own insurance claims |
| `POST` | `/data-marketplace/request` | No | Submit anonymized data export request |
| `GET` | `/data-marketplace/preview/{h3_index}` | No | Free aggregated data preview |
| `POST` | `/white-label/` | Admin | Create white-label config for a utility |
| `GET` | `/white-label/brand/{api_key}` | No | Get public branding for embed |
| `POST` | `/ivr/trigger` | Admin | Trigger IVR voice calls for a cell |
| `GET` | `/poi/` | No | List ATM/fuel stations in a cell |
| `POST` | `/poi/{id}/report` | Yes | Report POI operational status |
| `POST` | `/prepaid/meters` | Yes | Register prepaid electricity meter |
| `GET` | `/grid/transformers` | Admin | List grid transformers |
| `GET` | `/seasonal/{h3_index}` | Yes | 24-month seasonal outage breakdown |
| `GET` | `/seasonal/{h3_index}/worst-months` | Yes | Top 3 worst months historically |
| `GET` | `/transfer-learning/similar/{region}` | Admin | Similar regions for model bootstrap |
| `GET` | `/regulatory/reports` | Admin | Regulatory compliance reports |
| `POST` | `/regulatory/reports/generate` | Admin | Generate monthly compliance report |
| `GET` | `/dispatch/recommend` | Admin | Crew pre-positioning recommendations |

---

## CI/CD

Tests run on every push via GitHub Actions (`.github/workflows/ci.yml`).

The test suite uses **SQLite in-memory** (no external DB needed in CI) with monkey-patched JSONB and UUID support.

### Current test status

- Auth (register, login, me, unauthenticated): PASS
- Predictions API (list, report outage): PASS
- Outage reports: PASS
- Weather service: PASS
- Coverage threshold: >= 40%

### Run tests locally

```bash
cd backend
pip install -r requirements.txt
pytest -v --cov=app --cov-report=term-missing
```

---

## Build Phases

### Phase 1 — Foundation (Complete)
- [x] PostgreSQL schema + H3 cell seeder
- [x] FastAPI backend (auth, users, outage reports, H3 lookup, predictions)
- [x] OpenWeatherMap weather integration
- [x] Jasmin SMS gateway + SMPP routing via env vars (no vendor lock-in)
- [x] React PWA (home, report outage, map, dashboard)
- [x] Celery tasks (weather fetch + prediction + alert dispatch)
- [x] 7-language SMS templates (en/fr/sw/rw/ar/es/pt)
- [x] Alembic migration chain (0001→0007)
- [x] Supabase database bootstrap script (`bootstrap_supabase.sql`)
- [x] CI/CD pipeline (GitHub Actions, SQLite in-memory, coverage ≥ 40%)

### Phase 2 — Intelligence (Complete)
- [x] Groq LLM insights endpoint — plain-language risk summaries in 7 languages
- [x] Admin dashboard + fraud detection
- [x] USSD `*384#` fallback — works on any feature phone
- [x] Two-way SMS interaction (STATUS / REPORT / STOP / JOIN keywords)
- [x] Community features (points, badges, streaks, leaderboard, notes)
- [x] Enterprise API (webhooks, utility company portal)
- [x] **Planned outage calendar** — merge utility maintenance windows with predictions
- [x] **Feedback loop** — follow-up SMS 4h after alert ("Did power go out?") feeds ML
- [x] **Medical priority registry** — dialysis/oxygen users get 6h early alerts
- [x] **Neighborhood resilience score** — 0–100 grade per H3 cell (A–F)
- [x] **Parametric insurance** — auto-trigger claims when outage exceeds threshold
- [x] **Data marketplace** — anonymized outage data for researchers and insurers
- [x] **White-label** — utilities get branded SMS sender ID and custom portal
- [x] **IVR voice calls** — 7-language TTS calls for users without SMS
- [x] **ATM / fuel station status** — crowdsourced operational status layer
- [x] **Prepaid meter integration** — low-balance alerts before predicted outages
- [x] **Grid topology model** — transformer→cell mapping for cascading risk
- [x] **Seasonal dashboard** — 24-month outage decomposition per cell
- [x] **Transfer learning** — new regions borrow from similar-climate regions
- [x] **Regulatory reporting** — monthly compliance reports per district
- [x] **Crew dispatch optimizer** — pre-position maintenance crews before high-risk windows
- [x] Migration chain extended to 0001→0021 (21 migrations, 30+ tables)

### Phase 3 — Scale & Polish
- [ ] Train XGBoost + Prophet on collected data
- [ ] Mapbox heatmap with H3 hexagon overlay
- [ ] PWA Service Worker + full offline mode (IndexedDB sync)
- [ ] ENTSO-E / EIA grid load integration (Europe + US grid data)
- [ ] Web Push notifications (VAPID)
- [ ] Stripe billing (Free / Pro / Business / Enterprise tiers)
- [ ] Public REST API for governments and NGOs
- [ ] GNN graph model for transformer-level cascade prediction

---

## Contributing

Pull requests are welcome. For major changes, open an issue first.

```bash
git checkout -b feature/your-feature-name
# make changes
git commit -m "feat: describe your change"
git push origin feature/your-feature-name
# open a PR
```

---

## License

MIT License — Copyright (c) 2026 AI Power Blackout Predictor Contributors

---

<div align="center">

Built for the world — from Osee to everywhere.

</div>
