<div align="center">

# ⚡ AI Power Blackout Predictor

**Predict electricity outages before they happen — anywhere in the world.**

AI-powered platform that combines crowdsourced outage reports, real-time weather data, and machine learning to predict power blackouts at the neighborhood level. Sends SMS alerts via your own SMPP gateway, renders live heatmaps, and works offline.

<br/>

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=for-the-badge)](https://github.com/your-org/ai-power-blackout-predictor/pulls)
[![Made with Love](https://img.shields.io/badge/Made%20with-Love-red.svg?style=for-the-badge)](#)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Services](#-services)
- [Getting Started](#-getting-started)
- [Environment Variables](#-environment-variables)
- [SMS Gateway](#-sms-gateway--jasmin--smpp)
- [ML Engine](#-ml-engine)
- [Supported Languages](#-supported-languages)
- [Build Phases](#-build-phases)
- [License](#-license)

---

## 🌍 Overview

Electricity outages are one of the most disruptive daily challenges across Africa, Asia, Latin America, and developing regions worldwide. This platform uses **AI + crowdsourcing** to predict outages hours before they happen and warn residents via SMS — even on feature phones with no internet.

It is built to scale globally, with per-region ML models, multi-language SMS alerts, and a fully offline-capable Progressive Web App.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 🤖 **AI Predictions** | XGBoost + Prophet ensemble predicts outage probability per neighborhood cell |
| 📡 **Your Own SMS Gateway** | Jasmin + SMPP connects directly to telecom operators — no Twilio fees |
| 🗺️ **Neighborhood Heatmaps** | Uber H3 hexagonal grid renders real-time risk maps worldwide |
| 📴 **Offline Support** | PWA with Service Workers + IndexedDB — works without internet |
| 👥 **Crowdsourced Reports** | Users confirm outages via app or SMS — feeds the ML model |
| 🌐 **7 Languages** | English, French, Swahili, Kinyarwanda, Arabic, Spanish, Portuguese |
| ⏰ **4-Hour Predictions** | Runs every 4 hours, checks weather + history + grid patterns |
| 🔔 **Multi-channel Alerts** | SMS, push notifications, and email — user-configurable thresholds |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND (PWA)                       │
│          React · Mapbox Heatmap · Offline-first             │
└───────────────────────┬─────────────────────────────────────┘
                        │ REST API
┌───────────────────────▼─────────────────────────────────────┐
│                    BACKEND (FastAPI)                         │
│     Users · Predictions · Outages · Alerts · H3 Cells       │
│                  Celery Tasks (every 4h)                     │
└──────┬──────────────────────┬──────────────────────┬────────┘
       │                      │                      │
┌──────▼──────┐   ┌───────────▼──────────┐  ┌──────▼────────┐
│  ML ENGINE  │   │     DATA PIPELINE    │  │  SMS GATEWAY  │
│  XGBoost    │   │  Weather · ENTSO-E   │  │ Jasmin + SMPP │
│  Prophet    │   │  EIA · Crowdsource   │  │  Per-country  │
│  Ensemble   │   │  H3 Mapper · Cron    │  │  connectors   │
└─────────────┘   └──────────────────────┘  └───────────────┘
       │                      │                      │
┌──────▼──────────────────────▼──────────────────────▼────────┐
│           PostgreSQL + PostGIS · Redis · RabbitMQ            │
└─────────────────────────────────────────────────────────────┘
```

**Data flow:**
1. **OpenWeatherMap** → Weather snapshots stored per H3 cell hourly
2. **Users** → Report outages via app / SMS → verified by 3-report consensus
3. **Celery** → Runs predictions every 4h per cell → stores probability + risk level
4. **Alert checker** → Matches predictions against user subscriptions → fires SMS / push
5. **Frontend** → Reads predictions → renders heatmap → shows risk for user's location

---

## 🛠️ Tech Stack

### Backend

![Python](https://img.shields.io/badge/Python_3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?style=for-the-badge&logo=python&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-37814A?style=for-the-badge&logo=celery&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-E92063?style=for-the-badge&logo=pydantic&logoColor=white)

---

### Database & Cache

![PostgreSQL](https://img.shields.io/badge/PostgreSQL_15-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![PostGIS](https://img.shields.io/badge/PostGIS-336791?style=for-the-badge&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis_7-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![RabbitMQ](https://img.shields.io/badge/RabbitMQ-FF6600?style=for-the-badge&logo=rabbitmq&logoColor=white)

---

### Machine Learning

![XGBoost](https://img.shields.io/badge/XGBoost-189ABC?style=for-the-badge&logo=python&logoColor=white)
![Prophet](https://img.shields.io/badge/Facebook_Prophet-1877F2?style=for-the-badge&logo=meta&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=for-the-badge&logo=scikitlearn&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-013243?style=for-the-badge&logo=numpy&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)

---

### SMS & Messaging

![Jasmin](https://img.shields.io/badge/Jasmin_SMS_Gateway-FF6B35?style=for-the-badge&logo=message&logoColor=white)
![SMPP](https://img.shields.io/badge/SMPP_v3.4-2C3E50?style=for-the-badge&logoColor=white)

---

### Frontend

![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![React](https://img.shields.io/badge/React_18-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![Vite](https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)
![Mapbox](https://img.shields.io/badge/Mapbox_GL_JS-000000?style=for-the-badge&logo=mapbox&logoColor=white)
![Zustand](https://img.shields.io/badge/Zustand-443E38?style=for-the-badge&logo=react&logoColor=white)
![i18next](https://img.shields.io/badge/i18next-26A69A?style=for-the-badge&logo=i18next&logoColor=white)

---

### Geospatial

![Uber H3](https://img.shields.io/badge/Uber_H3-000000?style=for-the-badge&logo=uber&logoColor=white)

> **H3** is Uber's hexagonal hierarchical geospatial indexing system. Every neighborhood in the world is mapped to a hexagonal cell — resolution 8 gives ~460m cells, perfect for neighborhood-level predictions.

---

### Infrastructure

![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Nginx](https://img.shields.io/badge/Nginx-009639?style=for-the-badge&logo=nginx&logoColor=white)
![PWA](https://img.shields.io/badge/PWA-5A0FC8?style=for-the-badge&logo=pwa&logoColor=white)

---

### External APIs

![OpenWeatherMap](https://img.shields.io/badge/OpenWeatherMap-EB6E4B?style=for-the-badge&logo=openweathermap&logoColor=white)
![ENTSO-E](https://img.shields.io/badge/ENTSO--E_(Europe_Grid)-003DA5?style=for-the-badge&logoColor=white)
![EIA](https://img.shields.io/badge/EIA_(US_Grid)-004990?style=for-the-badge&logoColor=white)

---

## 📦 Services

The project is composed of **5 containerized microservices** + supporting infrastructure:

```
ai-power-blackout-predictor/
│
├── backend/           → FastAPI REST API                  (port 8000)
├── sms-gateway/       → Jasmin SMS wrapper API            (port 8001)
├── ml-engine/         → ML inference + training server    (port 8002)
├── frontend/          → React PWA                         (port 5173)
├── data-pipeline/     → Weather + crowdsource ETL cron
│
└── infrastructure/
    ├── postgres/      → PostgreSQL + PostGIS init SQL
    ├── nginx/         → Reverse proxy config
    └── redis/         → Redis config
```

| Service | Port | Description |
|---|---|---|
| Backend API | `8000` | FastAPI — predictions, users, alerts, outage reports |
| SMS Gateway | `8001` | Your own SMS microservice wrapping Jasmin |
| ML Engine | `8002` | XGBoost + Prophet prediction API |
| Frontend | `5173` | React PWA — heatmaps, offline, 7 languages |
| PostgreSQL | `5432` | Main database with PostGIS extension |
| Redis | `6379` | Cache + Celery task broker |
| RabbitMQ | `5672` | Jasmin message queue |
| RabbitMQ UI | `15672` | RabbitMQ management dashboard |
| Jasmin HTTP | `8080` | Jasmin internal HTTP API |
| Nginx | `80` | Reverse proxy (production) |

---

## 🚀 Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- [Git](https://git-scm.com/)
- An [OpenWeatherMap API key](https://openweathermap.org/api) (free tier works)

### 1 — Clone & configure

```bash
git clone https://github.com/your-org/ai-power-blackout-predictor.git
cd ai-power-blackout-predictor

# Copy and edit environment variables
cp .env.example .env
```

Open `.env` and set at minimum:
```env
OPENWEATHERMAP_API_KEY=your-key-here
SECRET_KEY=your-random-64-char-secret
VITE_MAPBOX_TOKEN=your-mapbox-token
```

### 2 — Start all services

```bash
docker-compose up -d
```

### 3 — Seed neighborhood cells

```bash
# Seeds H3 cells for 12 major cities worldwide
docker-compose exec data-pipeline python processors/h3_mapper.py
```

### 4 — Open the app

| URL | Description |
|---|---|
| `http://localhost:5173` | React frontend |
| `http://localhost:8000/docs` | Swagger API docs |
| `http://localhost:15672` | RabbitMQ dashboard (`guest/guest`) |

### Local development (without Docker)

```bash
# Backend
cd backend
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# SMS Gateway
cd sms-gateway
pip install -r requirements.txt
uvicorn api.main:app --port 8001 --reload

# ML Engine
cd ml-engine
pip install -r requirements.txt
uvicorn inference.predictor:app --port 8002 --reload
```

---

## 🔧 Environment Variables

| Variable | Description | Example |
|---|---|---|
| `SECRET_KEY` | JWT signing secret | `64-char-random-string` |
| `DATABASE_URL` | Async PostgreSQL URL | `postgresql+asyncpg://...` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `OPENWEATHERMAP_API_KEY` | OWM API key (free tier, global) | `abc123...` |
| `ML_ENGINE_URL` | ML engine microservice URL | `http://ml-engine:8002` |
| `JASMIN_HOST` | Jasmin container hostname | `jasmin` |
| `SMPP_HOST` | Your SMPP aggregator endpoint | `smpp.your-aggregator.com` |
| `SMPP_USERNAME` | SMPP username | `your-username` |
| `JASMIN_CONNECTOR_DEFAULT` | Default Jasmin connector ID | `default` |
| `USSD_SHORT_CODE` | USSD short code digits | `384` |

See [`.env.example`](.env.example) for the full list.

---

## 📲 SMS Gateway — Jasmin + SMPP

Instead of paying per-SMS to Twilio or Africa's Talking, this project runs its **own SMS infrastructure** using [Jasmin](https://docs.jasminsms.com/), an open-source Python SMS gateway that speaks SMPP — the protocol used by every telecom operator worldwide.

```
Your App
   ↓  POST /sms/send  { to, country, lang, template, vars }
SMS Gateway API  (port 8001)
   ↓  Routes via JASMIN_CONNECTOR_{CC} env var
Jasmin Gateway  (port 8080)
   ↓  SMPP v3.4 protocol  (operator-agnostic)
Any SMPP aggregator worldwide  (Sinch, Infobip, Vonage, AT, direct operator…)
   ↓
User's Phone  (any country, any network)
```

### Cost comparison

| Provider | Cost per SMS | 100k SMS/month |
|---|---|---|
| Twilio | ~$0.05–0.08 | ~$6,500 |
| Africa's Talking | ~$0.01–0.03 | ~$2,000 |
| **Your own (SMPP direct)** | **~$0.003–0.008** | **~$500** |

### Adding a new country/operator

No code changes needed. Just set environment variables:

1. Get SMPP credentials from your aggregator (Sinch, Infobip, Vonage, etc.) or directly from the local telecom
2. Set `SMPP_HOST`, `SMPP_USERNAME`, `SMPP_PASSWORD` in `.env`
3. Optionally set `JASMIN_CONNECTOR_{CC}` for per-country routing (e.g. `JASMIN_CONNECTOR_NG=ng_connector`)
4. Configure the connector in Jasmin via CLI or `sms-gateway/jasmin/connectors.cfg`

The single [`JasminConnector`](sms-gateway/connectors/jasmin.py) handles all countries.

---

## 🤖 ML Engine

### Prediction pipeline (runs every 4 hours via Celery)

```
1. FETCH      OpenWeatherMap forecast → next 24h per tracked H3 cell
2. FEATURES   Weather + temporal + historical outage + grid type
3. PREDICT    XGBoost  → P(outage in 4h)  [weight: 70%]
              Prophet  → 7-day trend       [weight: 30%]
              Ensemble → final probability
4. STORE      PostgreSQL predictions table
5. ALERT      Celery checks subscriptions → SMS + push if threshold crossed
```

### Feature set

| Category | Features |
|---|---|
| Weather | `rainfall_mm`, `temperature_c`, `wind_speed_ms`, `humidity_pct`, `is_storm`, `is_heavy_rain` |
| Temporal | `hour`, `day_of_week`, `month`, `is_weekend`, `is_peak_hour`, `is_holiday` |
| Historical | `outages_last_7d`, `outages_last_30d`, `avg_duration_minutes`, `outage_frequency_per_week` |
| Grid | `grid_type` (hydro/coal/gas/nuclear/mixed), `center_lat`, `center_lng` |

### Train models for a region

```bash
cd ml-engine

# Train all regions
python training/train.py --region all

# Train a specific region
python training/train.py --region africa_east
```

Available regions: `africa_east`, `africa_west`, `europe_central`, `north_america_east`, `latin_america`, `asia_south`

### Risk levels

| Level | Probability | Color |
|---|---|---|
| 🟢 Low | < 40% | Green |
| 🟡 Medium | 40–64% | Amber |
| 🔴 High | 65–84% | Red |
| 🟣 Critical | ≥ 85% | Purple |

---

## 🌐 Supported Languages

| Code | Language | Primary Regions |
|---|---|---|
| `en` | English | Global default |
| `fr` | French | Francophone Africa, Europe |
| `sw` | Swahili | East Africa (KE, TZ, UG) |
| `rw` | Kinyarwanda | Rwanda |
| `ar` | Arabic | Middle East, North Africa |
| `es` | Spanish | Latin America, Spain |
| `pt` | Portuguese | Brazil, Angola, Mozambique |

SMS messages are sent in the user's registered language. Kinyarwanda example:

> *"IMBARAGA: Amashanyarazi azima mu gace kawe saa 18:00 (82%). Shaza ibikoresho byawe nonaha."*

---

## 🗓️ Build Phases

### ✅ Phase 1 — Foundation (Weeks 1–3)
- [x] PostgreSQL schema + PostGIS + H3 cell seeder
- [x] FastAPI backend (users, outage reports, H3 lookup)
- [x] OpenWeatherMap integration
- [x] Jasmin SMS gateway Docker setup + SMPP connectors
- [x] React PWA (home, report outage, basic map, dashboard)
- [x] Celery tasks (weather fetch + rule-based prediction + alert dispatch)
- [x] 7-language SMS templates

### 🔄 Phase 2 — Intelligence (Weeks 4–6)
- [ ] Train XGBoost + Prophet on collected data
- [ ] Replace rule-based predictor with ML ensemble
- [ ] Mapbox heatmap with H3 hexagon overlay
- [ ] Alert subscription system + quiet hours
- [ ] ENTSO-E / EIA grid load integration

### 🔮 Phase 3 — Scale & Polish (Weeks 7–9)
- [ ] PWA Service Worker + full offline mode
- [ ] USSD fallback for feature phones
- [ ] Web Push notifications (Firebase FCM)
- [ ] Public REST API for utilities and governments
- [ ] Stripe billing (Free / Pro / Business / Enterprise tiers)
- [ ] White-label for utility companies

---

## 🤝 Contributing

Pull requests are welcome. For major changes, open an issue first to discuss what you would like to change.

```bash
# Fork → clone → branch
git checkout -b feature/your-feature-name

# Make changes, then
git commit -m "feat: describe your change"
git push origin feature/your-feature-name
# Open a PR
```

---

## 📄 License

```
MIT License

Copyright (c) 2026 AI Power Blackout Predictor Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

<div align="center">

Built with ⚡ for the world — from Osee to everywhere.

</div>
