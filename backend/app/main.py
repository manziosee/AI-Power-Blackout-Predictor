from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.v1.endpoints.ws import router as ws_router
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.security_headers import SecurityHeadersMiddleware
from app.models import *  # noqa: F401,F403 — ensure all models are registered

_DESCRIPTION = """
## AI Power Blackout Predictor API

A global platform that predicts power outages before they happen, using machine learning,
crowd-sourced reports, weather data, and grid topology analysis.

### Authentication

| Method | Header | Used by |
|---|---|---|
| **Bearer JWT** | `Authorization: Bearer <token>` | End-user endpoints (`/users`, `/outages`, `/alerts`, …) |
| **Utility API Key** | `X-Utility-API-Key: <key>` | Utility-company portal (`/utility/portal/…`) |
| **Public API Key** | `X-API-Key: <key>` | Third-party / NGO data access (`/public/…`) |
| **Admin JWT** | `Authorization: Bearer <admin-token>` | Admin panel (`/admin/…`) |

### Rate Limiting (Public API)

Public API keys are subject to sliding-window rate limits.
Exceeded limits return **HTTP 429** with a `Retry-After` header.
Current headroom is visible on `GET /public/me/analytics`.

### Real-Time Feed

Connect to `ws://<host>/ws/outages/live` (WebSocket) to receive live JSON events
whenever a new outage is reported or a report reaches verified status.

### Observability

Prometheus metrics are available at `GET /metrics`.
OpenTelemetry tracing can be enabled with `OTEL_ENABLED=true`.

### Key Feature Areas

- **Predictions** — H3-cell-level outage probability forecasts (ML + GNN)
- **Outage Reports** — crowd-sourced verification with trust-weighted scoring
- **Alerts** — SMS / WhatsApp / Telegram / Push with quiet-hours and risk-override
- **Incidents** — automatic spatial clustering of concurrent outage reports
- **Planned Outages** — utility-scheduled maintenance with iCal feed
- **Resilience Scores** — per-cell reliability grades
- **Insurance** — auto-initiated claims on verified long outages
- **Prepaid Meters** — low-balance alerts cross-referenced with outage predictions
- **Utility Portal** — planned outage management and MTTR benchmarking
- **Public API** — rate-limited read-only access for NGOs and researchers
"""

_TAGS_METADATA = [
    {"name": "Health", "description": "Service liveness check."},
    {"name": "Auth / Users", "description": "Registration, login, profile, locations, and subscription tier."},
    {"name": "Predictions", "description": "ML outage probability forecasts per H3 cell."},
    {"name": "GNN Predictions", "description": "Graph Neural Network cascade-risk predictions."},
    {"name": "Outage Reports", "description": "Crowd-sourced outage reporting and verification."},
    {"name": "Incidents", "description": "Automatic spatial clustering of concurrent outage reports into named incidents."},
    {"name": "Alerts", "description": "Alert subscriptions, SMS/push/channel delivery, quiet-hours, and risk-override."},
    {"name": "Planned Outages", "description": "Utility-scheduled maintenance windows. Includes iCal feed generation."},
    {"name": "Restoration", "description": "Crew dispatch tracking and restoration ETA updates."},
    {"name": "Neighborhoods", "description": "Per-cell reliability statistics and leaderboards."},
    {"name": "Analytics", "description": "Utility response-time benchmarks, weather correlation, and platform KPIs."},
    {"name": "Community", "description": "Points, badges, leaderboards, and neighbourhood notes."},
    {"name": "Resilience", "description": "Composite reliability grades per H3 cell."},
    {"name": "Insurance", "description": "Parametric insurance policies and auto-claim processing."},
    {"name": "Prepaid", "description": "Prepaid meter balance tracking and prediction-aware topup reminders."},
    {"name": "Utility Portal", "description": "Utility-company dashboard: planned outages, MTTR, response benchmarks."},
    {"name": "Grid Topology", "description": "Transformer registry, cell coverage, and GNN graph data."},
    {"name": "Grid Load", "description": "Real-time and historical grid load snapshots."},
    {"name": "Maintenance", "description": "Transformer maintenance risk scoring and scheduling recommendations."},
    {"name": "Dispatch", "description": "Crew dispatch recommendations based on risk forecasts."},
    {"name": "POI", "description": "Points-of-interest (hospitals, fuel stations, etc.) and their power status."},
    {"name": "Medical Priority", "description": "Registered medically-dependent users who receive priority early alerts."},
    {"name": "Seasonal", "description": "Month-by-month historical outage statistics per cell."},
    {"name": "Transfer Learning", "description": "Cross-region similarity scores for cold-start prediction."},
    {"name": "Regulatory", "description": "Automated regulatory report generation."},
    {"name": "Billing", "description": "Subscription plans, Stripe payment integration, and usage limits."},
    {"name": "Public API", "description": "Rate-limited read-only API for NGOs, researchers, and utilities. Requires `X-API-Key`."},
    {"name": "Webhooks", "description": "Event-driven webhooks for predictions and confirmed outages."},
    {"name": "WhatsApp", "description": "WhatsApp alert opt-in management and delivery."},
    {"name": "Telegram", "description": "Telegram bot subscription management and delivery."},
    {"name": "IVR", "description": "Voice-call alerts for feature-phone users."},
    {"name": "USSD", "description": "USSD session handler for network-agnostic feature-phone access."},
    {"name": "SMS Inbound", "description": "Inbound SMS command processing (REPORT, STATUS, STOP, …)."},
    {"name": "Push Notifications", "description": "Web Push subscription management and delivery."},
    {"name": "Email Alerts", "description": "Email digest subscription management."},
    {"name": "Reports", "description": "User-facing outage history and personal report feed."},
    {"name": "Feedback", "description": "Prediction feedback loop for model retraining."},
    {"name": "Business", "description": "Business impact profiles — revenue loss estimates and B2B features."},
    {"name": "Data Marketplace", "description": "Anonymised bulk data export requests and downloads."},
    {"name": "White Label", "description": "Per-utility branding configuration (logo, colours, sender ID)."},
    {"name": "Insights", "description": "AI-generated outage trend summaries and actionable insights."},
    {"name": "Admin", "description": "Internal admin panel — platform stats, user management, fraud flags, model drift. Requires admin JWT."},
    {"name": "WebSocket", "description": "Real-time WebSocket event stream for live outage feed."},
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.OTEL_ENABLED:
        from opentelemetry import trace
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
        provider = TracerProvider()
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor().instrument_app(app)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description=_DESCRIPTION,
    contact={
        "name": "AI Power Blackout Predictor",
        "email": "manziosee3@gmail.com",
    },
    license_info={
        "name": "MIT",
    },
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=_TAGS_METADATA,
    lifespan=lifespan,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.METRICS_ENABLED:
    Instrumentator().instrument(app).expose(app, include_in_schema=False)

app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(ws_router)


@app.get("/health", tags=["Health"], summary="Service liveness check")
async def health():
    from app.core.ws_manager import manager
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "ws_connections": manager.connection_count,
    }
