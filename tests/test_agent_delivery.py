from __future__ import annotations

import unittest

from agent.planner import TikTokAgent
from api.main import healthz, skills


class AgentDeliveryTest(unittest.IsolatedAsyncioTestCase):
    async def test_healthz_exposes_truthful_runtime_state(self) -> None:
        payload = await healthz()

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["data_source"], "mock")
        self.assertFalse(payload["is_live_tiktok_api_configured"])
        self.assertIn("metrics_enabled", payload)

    async def test_skill_schema_registry_is_complete(self) -> None:
        payload = await skills()
        names = {item["name"] for item in payload["skills"]}

        self.assertEqual(
            names,
            {"tiktok_fetch", "trend_analysis", "user_analysis", "report_gen"},
        )
        for item in payload["skills"]:
            self.assertIn("description", item)
            self.assertIn("parameters", item)

    async def test_account_query_runs_fetch_analysis_and_report(self) -> None:
        response = await TikTokAgent().run(
            "分析账号表现",
            target_type="account",
            target_id="demo",
            limit=5,
        )

        self.assertEqual(response.intent, "user_analysis")
        self.assertEqual(response.steps, ["tiktok_fetch", "user_analysis", "report_gen"])
        self.assertEqual(response.source, "mock")
        self.assertFalse(response.is_live_data)
        self.assertIn("mock", " ".join(response.warnings).lower())
        self.assertIn("summary", response.report)

    async def test_trend_query_runs_fetch_analysis_and_report(self) -> None:
        response = await TikTokAgent().run(
            "trending hashtags",
            target_type="hashtag",
            target_id="demo",
            limit=5,
        )

        self.assertEqual(response.intent, "trend_analysis")
        self.assertEqual(response.steps, ["tiktok_fetch", "trend_analysis", "report_gen"])
        self.assertGreater(response.result["summary"]["growth"], 0)
        self.assertEqual(response.report["source"], "mock")


if __name__ == "__main__":
    unittest.main()
