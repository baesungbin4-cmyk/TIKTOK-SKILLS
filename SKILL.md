---
name: tiktok-skills
description: Build, inspect, run, test, or extend a TikTok data analysis AI agent with modular Python skills for mock TikTok data fetching, trend analysis, user/account analysis, report generation, FastAPI endpoints, Docker Compose deployment, Prometheus metrics, and Grafana dashboards. Use when working on TikTok analytics agent workflows, tool schemas, mock data boundaries, or deployment hardening for this repository.
---

# TikTok Skills

Use this skill to work on the TikTok Data Analysis Agent in this repository.

## Project Map

- `skills/`: Python skill modules and Pydantic input/output contracts, including trend, user, anomaly detection, insight generation, and report skills.
- `assets/sample_tiktok_records.json`: Local fixture dataset for repeatable analysis runs.
- `agent/planner.py`: Orchestrates fetch, analysis, and report steps.
- `api/main.py`: FastAPI app exposing `/healthz`, `/skills`, `/analyze`, and optional `/metrics`.
- `docker/` and `docker-compose.yml`: Nginx, Prometheus, and Grafana deployment stack.
- `tests/` and `tools/smoke_check.py`: Runtime contract and delivery checks.

## Operating Rules

- Keep the live-data boundary explicit: current TikTok records are deterministic mock or local fixture data, not real TikTok OpenAPI responses.
- Preserve response fields that prevent misuse: `source`, `is_live_data`, `warnings`, and `trace_id`.
- Keep each module contract typed with Pydantic models before wiring it into the planner or API.
- Prefer adding new data providers behind the `tiktok_fetch` provider boundary instead of mixing provider-specific code into analysis modules.
- For abnormal-spike requests, route through `anomaly_detection` and preserve the robust baseline, MAD, z-score, growth rate, severity, and reason fields.
- After structured analysis, run `insight_gen` to produce narrative insight, evidence, recommended actions, risk flags, and an LLM-ready prompt without claiming live data.
- Update `/skills` schema output when adding or changing a callable skill.
- Avoid committing local secrets, `.env`, Docker CLI state, caches, or Baidu upload sidecar files.

## Common Workflows

### Add Or Change A Skill Module

1. Add or update the relevant module under `skills/`.
2. Define explicit input and output Pydantic models.
3. Add the class `name`, `description`, and async `run` method.
4. Register the module in `skills/__init__.py`.
5. Wire orchestration logic in `agent/planner.py` if the skill participates in `/analyze`.
6. Extend `tests/test_agent_delivery.py` and `tools/smoke_check.py`.

### Validate Changes

Run these commands from the repository root:

```bash
python -m compileall agent api skills tools tests
python -m unittest discover -s tests
python tools/smoke_check.py
```

For deployment changes, also run:

```bash
GRAFANA_ADMIN_PASSWORD=dummy-password-for-config-check docker compose config
```

For analytics changes, verify trend analysis, anomaly detection, and insight generation against the fixture provider.

### Prepare For Live TikTok Data

When replacing the mock provider, keep the mock mode available for tests. Add authentication, rate limits, retry policy, provider-specific error mapping, and compliance notes before marking `is_live_data=true`.

## User-Facing Boundaries

- Say "mock data" plainly in generated reports unless a real provider is configured and tested.
- Do not claim the system accesses private TikTok data, production TikTok OpenAPI, or live trend data unless the provider integration exists in the repository.
- Prefer small, testable changes over broad rewrites of the agent, API, and deployment stack at the same time.
