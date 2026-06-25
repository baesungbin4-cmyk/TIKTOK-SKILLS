from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class FetchInput(BaseModel):
    target_type: Literal["video", "account", "hashtag", "user"]
    target_id: str = Field(min_length=1)
    date_range: tuple[date, date] | None = None
    limit: int = Field(default=50, ge=1, le=200)
    cursor: str | None = None


class TikTokRecord(BaseModel):
    id: str
    target_type: str
    target_id: str
    collected_date: date
    views: int
    likes: int
    comments: int
    shares: int
    collected_at: datetime

    @property
    def engagement_count(self) -> int:
        return self.likes + self.comments + self.shares


class FetchOutput(BaseModel):
    dataset_id: str
    records: list[TikTokRecord]
    cursor: str | None = None
    source: Literal["mock"] = "mock"
    is_live_data: bool = False
    warnings: list[str] = Field(
        default_factory=lambda: [
            "TikTok OpenAPI is not configured in this project; records are deterministic mock data."
        ]
    )
    trace_id: str


class TikTokFetchSkill:
    name = "tiktok_fetch"
    description = (
        "Fetch and normalize TikTok video/account/hashtag/user data. "
        "Current implementation returns deterministic mock data unless a real provider is added."
    )

    async def run(self, inp: FetchInput) -> FetchOutput:
        trace_id = str(uuid4())
        start, end = inp.date_range or self._default_date_range()
        window_days = max((end - start).days, 1)
        record_count = min(inp.limit, 10)

        records = [
            TikTokRecord(
                id=f"{inp.target_type}_{inp.target_id}_{idx}",
                target_type=inp.target_type,
                target_id=inp.target_id,
                collected_date=start + timedelta(days=min(idx, window_days)),
                views=10_000 + idx * 850,
                likes=900 + idx * 70,
                comments=80 + idx * 8,
                shares=45 + idx * 6,
                collected_at=datetime.now(timezone.utc),
            )
            for idx in range(record_count)
        ]

        return FetchOutput(
            dataset_id=f"ds_{uuid4().hex[:10]}",
            records=records,
            cursor=None,
            trace_id=trace_id,
        )

    def _default_date_range(self) -> tuple[date, date]:
        end = date.today()
        return end - timedelta(days=7), end
