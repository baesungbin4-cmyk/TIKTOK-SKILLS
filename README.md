# TikTok Data Analysis Agent

FastAPI-based TikTok data analysis agent prototype with modular skills, typed Pydantic contracts, Docker Compose deployment, Nginx reverse proxy, Prometheus metrics, and Grafana dashboard provisioning.

## Delivery Status

This project is deliverable as a deployable mock-data analysis agent. It does not connect to TikTok OpenAPI yet. The runtime response explicitly returns `source="mock"`, `is_live_data=false`, and warnings so downstream users cannot mistake demo data for live TikTok data.

Implemented skills:

- `tiktok_fetch`: returns normalized deterministic mock records.
- `trend_analysis`: computes engagement, growth, series, and insights.
- `user_analysis`: computes account health metrics and recommendations.
- `report_gen`: creates an inline structured report and chart specs.

## Local Validation

```bash
python -m compileall agent api skills tools tests
python -m unittest discover -s tests
python tools/smoke_check.py
```

## Local API Run

```bash
pip install -r requirements.txt
uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Then call:

```bash
curl http://127.0.0.1:8000/healthz
curl http://127.0.0.1:8000/skills
curl -X POST http://127.0.0.1:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"query":"分析账号表现","target_type":"account","target_id":"demo","limit":5}'
```

## Docker Deployment

```bash
cp .env.example .env
# Edit .env and set a strong GRAFANA_ADMIN_PASSWORD.
docker compose build
docker compose up -d
docker compose ps
```

Compose builds small local images for Nginx, Prometheus, and Grafana so their configuration is baked into containers instead of depending on host bind mounts.

Public HTTP entrypoint:

- `GET /healthz`
- `GET /skills`
- `POST /analyze`

Grafana is bound to `127.0.0.1:3000` on the server. Access it through an SSH tunnel:

```bash
ssh -L 3000:localhost:3000 user@server
```

## Production Gaps

To deliver live TikTok analytics, replace the mock provider in `skills/tiktok_fetch.py` with a compliant TikTok OpenAPI or licensed data provider integration. Add API authentication, rate limits per tenant, persistent task storage, and report file storage before exposing this to untrusted users.
