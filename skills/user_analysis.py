from __future__ import annotations

from pydantic import BaseModel, Field

from skills.tiktok_fetch import TikTokRecord


class UserAnalysisInput(BaseModel):
    dataset_id: str
    records: list[TikTokRecord]


class UserAnalysisOutput(BaseModel):
    analysis_id: str
    profile: dict[str, float | str]
    recommendations: list[str]
    warnings: list[str] = Field(default_factory=list)


class UserAnalysisSkill:
    name = "user_analysis"
    description = "Analyze account/user performance and produce operation advice."

    async def run(self, inp: UserAnalysisInput) -> UserAnalysisOutput:
        if not inp.records:
            return UserAnalysisOutput(
                analysis_id=f"user_{inp.dataset_id}",
                profile={
                    "total_views": 0.0,
                    "avg_likes": 0.0,
                    "comment_rate": 0.0,
                    "health": "unknown",
                },
                recommendations=["Collect account records before making operation decisions."],
                warnings=["User analysis received an empty record set."],
            )

        total_views = sum(record.views for record in inp.records)
        views_denominator = total_views or 1
        avg_likes = sum(record.likes for record in inp.records) / max(len(inp.records), 1)
        avg_comments = sum(record.comments for record in inp.records) / max(
            len(inp.records), 1
        )
        comment_rate = avg_comments / views_denominator
        engagement_rate = (
            sum(record.engagement_count for record in inp.records) / views_denominator
        )

        return UserAnalysisOutput(
            analysis_id=f"user_{inp.dataset_id}",
            profile={
                "total_views": float(total_views),
                "avg_likes": round(avg_likes, 2),
                "comment_rate": round(comment_rate, 6),
                "engagement_rate": round(engagement_rate, 4),
                "health": "active"
                if avg_likes > 500 and engagement_rate > 0.05
                else "needs_attention",
            },
            recommendations=[
                "Prioritize formats with high like velocity.",
                "Use comment prompts when comment rate is below benchmark.",
            ],
        )
