from __future__ import annotations

from pydantic import BaseModel, Field

from skills.tiktok_fetch import TikTokRecord


class TrendAnalysisInput(BaseModel):
    dataset_id: str
    records: list[TikTokRecord]
    metrics: list[str] = Field(default_factory=lambda: ["engagement_rate", "growth"])


class TrendAnalysisOutput(BaseModel):
    analysis_id: str
    summary: dict[str, float]
    insights: list[str]
    series: dict[str, list[float]]
    warnings: list[str] = Field(default_factory=list)


class TrendAnalysisSkill:
    name = "trend_analysis"
    description = "Analyze TikTok trend metrics and generate concise insights."

    async def run(self, inp: TrendAnalysisInput) -> TrendAnalysisOutput:
        if not inp.records:
            return TrendAnalysisOutput(
                analysis_id=f"trend_{inp.dataset_id}",
                summary={
                    "engagement_rate": 0.0,
                    "growth": 0.0,
                    "total_views": 0.0,
                    "total_engagement": 0.0,
                    "record_count": 0.0,
                },
                insights=["No records were available for trend analysis."],
                series={"views": [], "engagement": []},
                warnings=["Trend analysis received an empty record set."],
            )

        total_views = sum(record.views for record in inp.records)
        views_denominator = total_views or 1
        total_engagement = sum(record.engagement_count for record in inp.records)
        engagement_rate = round(total_engagement / views_denominator, 4)

        view_series = [float(record.views) for record in inp.records]
        engagement_series = [float(record.engagement_count) for record in inp.records]
        growth = 0.0
        if len(view_series) > 1 and view_series[0] > 0:
            growth = round((view_series[-1] - view_series[0]) / view_series[0], 4)

        strongest_record = max(inp.records, key=lambda record: record.engagement_count)
        trend_direction = "upward" if growth > 0 else "flat_or_downward"

        return TrendAnalysisOutput(
            analysis_id=f"trend_{inp.dataset_id}",
            summary={
                "engagement_rate": engagement_rate,
                "growth": growth,
                "total_views": float(total_views),
                "total_engagement": float(total_engagement),
                "record_count": float(len(inp.records)),
            },
            insights=[
                f"Trend direction is {trend_direction} based on first-to-last view change.",
                f"Highest engagement record is {strongest_record.id}.",
                "Engagement rate is computed as (likes + comments + shares) / views.",
            ],
            series={"views": view_series, "engagement": engagement_series},
        )
