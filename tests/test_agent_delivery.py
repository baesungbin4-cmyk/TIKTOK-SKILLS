from __future__ import annotations

from datetime import date
import unittest

from agent.planner import TikTokAgent
from api.main import healthz, skills
from skills.anomaly_detection import AnomalyDetectionInput, AnomalyDetectionSkill
from skills.insight_gen import InsightGenInput, InsightGenSkill
from skills.tiktok_fetch import FetchInput, TikTokFetchSkill


class AgentDeliveryTest(unittest.IsolatedAsyncioTestCase):
    async def test_healthz_exposes_truthful_runtime_state(self) -> None:
        payload = await healthz()

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["data_source"], "mock")
        self.assertEqual(payload["supported_providers"], ["mock", "fixture"])
        self.assertFalse(payload["is_live_tiktok_api_configured"])
        self.assertIn("metrics_enabled", payload)

    async def test_skill_schema_registry_is_complete(self) -> None:
        payload = await skills()
        names = {item["name"] for item in payload["skills"]}

        self.assertEqual(
            names,
            {
                "tiktok_fetch",
                "anomaly_detection",
                "insight_gen",
                "trend_analysis",
                "user_analysis",
                "report_gen",
            },
        )
        for item in payload["skills"]:
            self.assertIn("description", item)
            self.assertIn("parameters", item)
        fetch_schema = next(item for item in payload["skills"] if item["name"] == "tiktok_fetch")
        self.assertIn("provider", fetch_schema["parameters"]["properties"])

    async def test_account_query_runs_fetch_analysis_and_report(self) -> None:
        response = await TikTokAgent().run(
            "分析账号表现",
            target_type="account",
            target_id="demo",
            limit=5,
        )

        self.assertEqual(response.intent, "user_analysis")
        self.assertEqual(
            response.steps,
            ["tiktok_fetch", "user_analysis", "insight_gen", "report_gen"],
        )
        self.assertEqual(response.source, "mock")
        self.assertFalse(response.is_live_data)
        self.assertIn("mock", " ".join(response.warnings).lower())
        self.assertIn("summary", response.report)
        self.assertIn("narrative", response.insight)

    async def test_trend_query_runs_fetch_analysis_and_report(self) -> None:
        response = await TikTokAgent().run(
            "trending hashtags",
            target_type="hashtag",
            target_id="demo",
            limit=5,
        )

        self.assertEqual(response.intent, "trend_analysis")
        self.assertEqual(
            response.steps,
            ["tiktok_fetch", "trend_analysis", "insight_gen", "report_gen"],
        )
        self.assertGreater(response.result["summary"]["growth"], 0)
        self.assertEqual(response.report["source"], "mock")

    async def test_fixture_provider_filters_and_paginates_records(self) -> None:
        first_page = await TikTokFetchSkill().run(
            FetchInput(
                target_type="hashtag",
                target_id="demo",
                provider="fixture",
                date_range=(date(2026, 6, 19), date(2026, 6, 23)),
                limit=2,
            )
        )
        second_page = await TikTokFetchSkill().run(
            FetchInput(
                target_type="hashtag",
                target_id="demo",
                provider="fixture",
                date_range=(date(2026, 6, 19), date(2026, 6, 23)),
                limit=2,
                cursor=first_page.cursor,
            )
        )

        self.assertEqual(first_page.source, "fixture")
        self.assertFalse(first_page.is_live_data)
        self.assertEqual(len(first_page.records), 2)
        self.assertEqual(first_page.cursor, "2")
        self.assertEqual(len(second_page.records), 2)
        self.assertEqual(second_page.records[0].id, "hashtag_demo_2026-06-21")

    async def test_agent_can_run_against_fixture_provider(self) -> None:
        response = await TikTokAgent().run(
            "trending hashtags",
            target_type="hashtag",
            target_id="demo",
            provider="fixture",
            date_range=(date(2026, 6, 19), date(2026, 6, 24)),
            limit=6,
        )

        self.assertEqual(response.source, "fixture")
        self.assertFalse(response.is_live_data)
        self.assertEqual(response.result["summary"]["record_count"], 6.0)
        self.assertGreater(response.result["summary"]["growth"], 0)
        self.assertIn("evidence", response.insight)

    async def test_anomaly_skill_detects_fixture_spike(self) -> None:
        fetch = await TikTokFetchSkill().run(
            FetchInput(
                target_type="hashtag",
                target_id="demo",
                provider="fixture",
                date_range=(date(2026, 6, 19), date(2026, 6, 24)),
                limit=6,
            )
        )
        result = await AnomalyDetectionSkill().run(
            AnomalyDetectionInput(
                dataset_id=fetch.dataset_id,
                records=fetch.records,
                metric="views",
                growth_threshold=0.35,
            )
        )

        self.assertEqual(result.metric, "views")
        self.assertGreaterEqual(result.anomaly_count, 1)
        self.assertIn("hashtag_demo_2026-06-23", {item.record_id for item in result.anomalies})

    async def test_agent_routes_anomaly_queries_to_anomaly_detection(self) -> None:
        response = await TikTokAgent().run(
            "detect abnormal spike",
            target_type="hashtag",
            target_id="demo",
            provider="fixture",
            date_range=(date(2026, 6, 19), date(2026, 6, 24)),
            limit=6,
            anomaly_metric="views",
        )

        self.assertEqual(response.intent, "anomaly_detection")
        self.assertEqual(
            response.steps,
            ["tiktok_fetch", "anomaly_detection", "insight_gen", "report_gen"],
        )
        self.assertEqual(response.result["severity"], "critical")
        self.assertGreaterEqual(response.result["anomaly_count"], 1)
        self.assertIn("abnormal views", response.insight["narrative"])
        self.assertIn("TikTok analytics strategist", response.insight["llm_prompt"])
        self.assertIn("abnormal views", response.report["summary"])

    async def test_insight_skill_turns_analysis_into_actions(self) -> None:
        result = await InsightGenSkill().run(
            InsightGenInput(
                dataset_id="fixture_hashtag_demo",
                intent="anomaly_detection",
                analysis_result={
                    "metric": "views",
                    "severity": "high",
                    "anomaly_count": 1,
                    "baseline": 15000.0,
                    "mad": 1200.0,
                    "anomalies": [
                        {
                            "record_id": "hashtag_demo_2026-06-23",
                            "collected_date": "2026-06-23",
                        }
                    ],
                },
                source="fixture",
                is_live_data=False,
            )
        )

        self.assertGreaterEqual(result.confidence, 0.7)
        self.assertTrue(result.evidence)
        self.assertTrue(result.recommended_actions)
        self.assertIn("is_live_data", result.llm_prompt)


if __name__ == "__main__":
    unittest.main()
