# Contributing to AI Power Blackout Predictor

Thank you for your interest in contributing! This platform helps predict power outages for communities worldwide. Every contribution — code, documentation, translations, or bug reports — makes a real difference.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Ways to Contribute](#ways-to-contribute)
- [Development Setup](#development-setup)
- [Branch Strategy](#branch-strategy)
- [Commit Convention](#commit-convention)
- [Pull Request Process](#pull-request-process)
- [Good First Issues](#good-first-issues)
- [Architecture Overview](#architecture-overview)

---

## Code of Conduct

Be respectful. We are building infrastructure for underserved communities. Harassment of any kind will not be tolerated.

---

## Ways to Contribute

| Type | How |
|---|---|
| Bug fix | Open an issue first, then submit a PR |
| New feature | Discuss in an issue before coding |
| Translation | Add strings to `backend/app/services/sms_service.py` language maps |
| Documentation | Update `README.md` or add to `docs/` |
| New H3 cell data | Add to `data-pipeline/` scripts |
| ML model improvements | See `ml-engine/` — open a discussion first |

---

## Development Setup

### Prerequisites

- Python 3.12
- Docker + Docker Compose
- Node.js 20 (for frontend)

### One-command demo

```bash
docker compose -f docker-compose.demo.yml up
```

Open http://localhost:8000/docs for the API explorer.

### Manual backend setup

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env   # edit with your keys
alembic upgrade head
python scripts/seed_demo.py
uvicorn app.main:app --reload
```

### Running tests

```bash
cd backend
pytest tests/ -v --cov=app
```

All tests must pass with `--cov-fail-under=40` before a PR can merge.

---

## Branch Strategy

```
main          ← production-ready, protected
feature/xyz   ← new feature branches
fix/xyz       ← bug fix branches
docs/xyz      ← documentation only
```

Always branch from `main`. Keep branches focused — one feature per PR.

---

## Commit Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add carbon footprint endpoint
fix: correct MutableHeaders pop in security middleware
docs: update SMS gateway setup guide
chore: bump ruff to 0.4
test: add coverage for explain endpoint
```

**Never add `Co-Authored-By: Claude` or similar AI attribution lines.**

---

## Pull Request Process

1. Fork the repo and create your branch from `main`
2. Write tests for any new backend endpoint
3. Run `ruff check app/ --select E,F,W --ignore E501` — zero violations required
4. Run `pytest tests/ -v` — all tests must pass
5. Update `README.md` if you added a new feature area
6. Open the PR and fill in the template

CI checks (backend lint, tests, Docker build) must all be green before merge.

---

## Good First Issues

Look for issues labeled [`good first issue`](https://github.com/manziosee/AI-Power-Blackout-Predictor/labels/good%20first%20issue):

- Adding a new language to SMS templates
- Writing a test for an untested endpoint
- Improving OpenAPI descriptions
- Adding a new H3 cell import script for a country
- Documenting an environment variable

---

## Architecture Overview

```
backend/          FastAPI app (Python 3.12)
  app/
    api/v1/       REST endpoints + WebSocket
    core/         DB, security, rate limiting, WS manager
    models/       SQLAlchemy ORM (PostgreSQL + SQLite in tests)
    schemas/      Pydantic I/O schemas
    services/     Business logic
    tasks/        Celery async tasks
  migrations/     Alembic (0001 → latest)
  scripts/        seed_demo.py, bootstrap_supabase.sql, rls_policies.sql

ml-engine/        XGBoost + Prophet ML service (Python)
sms-gateway/      Jasmin SMPP bridge
data-pipeline/    Weather + grid data collectors
charts/           Helm chart for Kubernetes deployment
monitoring/       Prometheus + Grafana dashboard
sdk/python/       Official Python SDK (pip install blackout-predictor-sdk)
```

The backend uses `service_role` Postgres credentials that bypass Row Level Security — the RLS policies in `backend/scripts/rls_policies.sql` protect direct PostgREST access.

---

Questions? Email manziosee3@gmail.com.
