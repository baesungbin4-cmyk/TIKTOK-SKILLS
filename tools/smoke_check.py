from __future__ import annotations

import asyncio
import json
import sys
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.planner import TikTokAgent
from api.main import healthz, skills


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


async def check_runtime_contract() -> None:
    health = await healthz()
    assert_true(health["status"] == "ok", "healthz status is not ok")
    assert_true(health["data_source"] == "mock", "data source must be explicit")
    assert_true(
        health["supported_providers"] == ["mock", "fixture"],
        "supported providers are not exposed",
    )
    assert_true(
        health["is_live_tiktok_api_configured"] is False,
        "live TikTok API state must be explicit",
    )

    skill_payload = await skills()
    skill_names = {item["name"] for item in skill_payload["skills"]}
    assert_true(
        skill_names
        == {
            "tiktok_fetch",
            "anomaly_detection",
            "trend_analysis",
            "user_analysis",
            "report_gen",
        },
        f"unexpected skill registry: {sorted(skill_names)}",
    )
    fetch_schema = next(item for item in skill_payload["skills"] if item["name"] == "tiktok_fetch")
    assert_true(
        "provider" in fetch_schema["parameters"]["properties"],
        "fetch schema is missing provider",
    )

    agent = TikTokAgent()
    user_response = await agent.run(
        "分析账号表现",
        target_type="account",
        target_id="demo",
        limit=5,
    )
    assert_true(user_response.intent == "user_analysis", "account query routed incorrectly")
    assert_true(user_response.is_live_data is False, "mock data must not be marked live")
    assert_true(user_response.report["source"] == "mock", "report source mismatch")

    trend_response = await agent.run(
        "trending hashtags",
        target_type="hashtag",
        target_id="demo",
        limit=5,
    )
    assert_true(trend_response.intent == "trend_analysis", "trend query routed incorrectly")
    assert_true(
        trend_response.steps == ["tiktok_fetch", "trend_analysis", "report_gen"],
        f"unexpected trend execution steps: {trend_response.steps}",
    )

    fixture_response = await agent.run(
        "trending hashtags",
        target_type="hashtag",
        target_id="demo",
        provider="fixture",
        date_range=(date(2026, 6, 19), date(2026, 6, 24)),
        limit=6,
    )
    assert_true(fixture_response.source == "fixture", "fixture provider was not used")
    assert_true(
        fixture_response.result["summary"]["record_count"] == 6.0,
        "fixture analysis should use six sample records",
    )

    anomaly_response = await agent.run(
        "detect abnormal spike",
        target_type="hashtag",
        target_id="demo",
        provider="fixture",
        date_range=(date(2026, 6, 19), date(2026, 6, 24)),
        limit=6,
        anomaly_metric="views",
    )
    assert_true(
        anomaly_response.intent == "anomaly_detection",
        "anomaly query routed incorrectly",
    )
    assert_true(
        anomaly_response.result["anomaly_count"] >= 1,
        "fixture spike should be detected",
    )


def check_static_delivery_files() -> None:
    dashboard_path = ROOT / "docker" / "grafana" / "dashboards" / "fastapi-overview.json"
    json.loads(dashboard_path.read_text(encoding="utf-8"))

    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert_true("ENABLE_METRICS" in compose, "app metrics env var is missing")
    assert_true(
        "GRAFANA_ADMIN_PASSWORD:?" in compose,
        "Grafana admin password should be required, not defaulted",
    )
    assert_true("nginx-exporter" not in compose, "compose references missing nginx exporter")
    assert_true('"80:80"' in compose, "nginx HTTP port mapping is missing")
    assert_true(
        '"127.0.0.1:3000:3000"' in compose,
        "Grafana should bind to localhost only",
    )
    assert_true('"9090:9090"' not in compose, "Prometheus should not be public")

    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert_true("COPY assets ./assets" in dockerfile, "Docker image must include fixtures")

    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    assert_true("\ndocker/\n" not in dockerignore, ".dockerignore must not exclude compose images")

    prometheus = (ROOT / "docker" / "prometheus" / "prom-config.yml").read_text(
        encoding="utf-8"
    )
    assert_true("app:8000" in prometheus, "Prometheus is not scraping the app")
    assert_true("nginx-exporter" not in prometheus, "Prometheus references missing exporter")

    nginx = (ROOT / "docker" / "nginx" / "default.conf").read_text(encoding="utf-8")
    assert_true(
        nginx.index("log_format") < nginx.index("server {"),
        "Nginx log_format must be in the http context",
    )
    assert_true("limit_req_zone" in nginx, "Nginx request rate limit is missing")
    assert_true("client_max_body_size 8m;" in nginx, "Nginx body limit is missing")
    assert_true("proxy_pass http://fastapi_backend;" in nginx, "Nginx app proxy is missing")


async def main() -> None:
    check_static_delivery_files()
    await check_runtime_contract()
    print("smoke_check: ok")


if __name__ == "__main__":
    asyncio.run(main())
