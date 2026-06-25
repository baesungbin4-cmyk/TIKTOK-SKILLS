from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class ReportInput(BaseModel):
    analysis_id: str
    dataset_id: str
    intent: Literal["trend_analysis", "user_analysis"]
    analysis_result: dict[str, Any]
    source: str
    is_live_data: bool
    warnings: list[str] = Field(default_factory=list)
    format: Literal["json", "markdown"] = "json"


class ReportOutput(BaseModel):
    report_id: str
    format: Literal["json", "markdown"]
    summary: str
    charts: list[dict[str, Any]]
    recommendations: list[str]
    report_url: str | None = None
    source: str
    is_live_data: bool
    warnings: list[str] = Field(default_factory=list)


class ReportGenSkill:
    name = "report_gen"
    description = (
        "Generate a structured analysis report from a completed trend or user analysis. "
        "This implementation returns inline JSON/markdown-ready content and does not persist files."
    )

    async def run(self, inp: ReportInput) -> ReportOutput:
        if inp.intent == "user_analysis":
            summary = self._user_summary(inp.analysis_result)
            charts = self._user_charts(inp.analysis_result)
            recommendations = list(inp.analysis_result.get("recommendations", []))
        else:
            summary = self._trend_summary(inp.analysis_result)
            charts = self._trend_charts(inp.analysis_result)
            recommendations = list(inp.analysis_result.get("insights", []))

        warnings = list(inp.warnings)
        if inp.source == "mock":
            warnings.append(
                "Report is generated from mock source data; do not treat it as a live TikTok report."
            )

        return ReportOutput(
            report_id=f"rpt_{uuid4().hex[:10]}",
            format=inp.format,
            summary=summary,
            charts=charts,
            recommendations=recommendations,
            source=inp.source,
            is_live_data=inp.is_live_data,
            warnings=warnings,
        )

    def _trend_summary(self, result: dict[str, Any]) -> str:
        summary = result.get("summary", {})
        total_views = summary.get("total_views", 0)
        engagement_rate = summary.get("engagement_rate", 0)
        growth = summary.get("growth", 0)
        return (
            f"Trend analysis covers {total_views:g} views with engagement rate "
            f"{engagement_rate:.2%} and growth {growth:.2%}."
        )

    def _trend_charts(self, result: dict[str, Any]) -> list[dict[str, Any]]:
        series = result.get("series", {})
        return [
            {
                "type": "line",
                "title": "Views by collected record",
                "series": {"views": series.get("views", [])},
            },
            {
                "type": "line",
                "title": "Engagement by collected record",
                "series": {"engagement": series.get("engagement", [])},
            },
        ]

    def _user_summary(self, result: dict[str, Any]) -> str:
        profile = result.get("profile", {})
        total_views = profile.get("total_views", 0)
        engagement_rate = profile.get("engagement_rate", 0)
        health = profile.get("health", "unknown")
        return (
            f"Account analysis covers {total_views:g} views. "
            f"Health is {health}; engagement rate is {engagement_rate:.2%}."
        )

    def _user_charts(self, result: dict[str, Any]) -> list[dict[str, Any]]:
        profile = result.get("profile", {})
        return [
            {
                "type": "metric",
                "title": "Account health snapshot",
                "series": {
                    "avg_likes": [profile.get("avg_likes", 0)],
                    "comment_rate": [profile.get("comment_rate", 0)],
                    "engagement_rate": [profile.get("engagement_rate", 0)],
                },
            }
        ]
