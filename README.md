# TikTok Data Analysis Agent

FastAPI-based TikTok data analysis agent prototype with modular skills, typed Pydantic contracts, Docker Compose deployment, Nginx reverse proxy, Prometheus metrics, and Grafana dashboard provisioning.

## Delivery Status

This project is deliverable as a deployable local-data analysis agent. It does not connect to TikTok OpenAPI yet. The runtime response explicitly returns `source`, `is_live_data=false`, and warnings where appropriate so downstream users cannot mistake demo or fixture data for live TikTok data.

Implemented skills:

- `tiktok_fetch`: returns normalized deterministic mock records or local JSON fixture records.
- `anomaly_detection`: detects abnormal spikes using median/MAD robust z-score and period-over-period growth thresholds.
- `trend_analysis`: computes engagement, growth, series, and insights.
- `user_analysis`: computes account health metrics and recommendations.
- `insight_gen`: converts structured analysis outputs into narrative insight, evidence, risk flags, actions, and an LLM-ready prompt.
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

Use the local fixture provider for a repeatable sample-data run:

```bash
curl -X POST http://127.0.0.1:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"query":"trending hashtags","target_type":"hashtag","target_id":"demo","provider":"fixture","date_range":["2026-06-19","2026-06-23"],"limit":5}'
```

Run anomaly detection against the same fixture dataset:

```bash
curl -X POST http://127.0.0.1:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"query":"detect abnormal spike","target_type":"hashtag","target_id":"demo","provider":"fixture","date_range":["2026-06-19","2026-06-24"],"limit":6,"anomaly_metric":"views"}'
```

Provider behavior:

- `mock`: generates deterministic records in code for fast smoke testing.
- `fixture`: reads `assets/sample_tiktok_records.json`, filters by target/date, and supports cursor pagination.
- `live`: not implemented; add authentication, provider contracts, rate limits, retry policy, and compliance checks before enabling it.

Anomaly detection uses robust statistics instead of a simple average threshold:

- baseline: median of the selected metric.
- dispersion: median absolute deviation (MAD), scaled by `1.4826`.
- detection reasons: robust z-score breach and/or period-over-period growth spike.
- severity: medium/high/critical based on z-score and growth magnitude.

The agent also runs `insight_gen` after each analysis step. This keeps the runtime usable without an external LLM while producing a prompt that can be handed to an LLM provider later:

- narrative: concise business interpretation of the metric result.
- evidence: metric/value/interpretation tuples for auditability.
- risk flags: explicit caveats and abnormal conditions.
- recommended actions: operator-facing next steps.
- `llm_prompt`: a provider-agnostic prompt payload that preserves `source` and `is_live_data`.

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

To deliver live TikTok analytics, add a compliant TikTok OpenAPI or licensed data provider integration behind the existing provider boundary. Add OAuth2/API-key authentication, rate limits, exponential backoff, persistent task storage, and report file storage before exposing this to untrusted users. If LLM-generated strategy text is enabled, keep `source`, `is_live_data`, and evidence fields in the prompt to avoid overstating data provenance.
