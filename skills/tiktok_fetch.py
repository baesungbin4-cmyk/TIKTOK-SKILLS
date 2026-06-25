from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

ProviderName = Literal["mock", "fixture"]
SourceName = Literal["mock", "fixture", "live"]


class FetchInput(BaseModel):
    target_type: Literal["video", "account", "hashtag", "user"]
    target_id: str = Field(min_length=1)
    date_range: tuple[date, date] | None = None
    limit: int = Field(default=50, ge=1, le=200)
    cursor: str | None = None
    provider: ProviderName = "mock"


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
    source: SourceName = "mock"
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
        "Supports deterministic mock data and local JSON fixture data; add a live provider "
        "only after authentication, rate limits, and compliance boundaries are implemented."
    )

    async def run(self, inp: FetchInput) -> FetchOutput:
        trace_id = str(uuid4())
        start, end = inp.date_range or self._default_date_range()
        if inp.provider == "fixture":
            return self._from_fixture(inp, start, end, trace_id)
        return self._from_mock(inp, start, end, trace_id)

    def _from_mock(
        self,
        inp: FetchInput,
        start: date,
        end: date,
        trace_id: str,
    ) -> FetchOutput:
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

    def _from_fixture(
        self,
        inp: FetchInput,
        start: date,
        end: date,
        trace_id: str,
    ) -> FetchOutput:
        rows = self._load_fixture_rows()
        filtered = [
            row
            for row in rows
            if row["target_type"] == inp.target_type
            and row["target_id"] == inp.target_id
            and start <= date.fromisoformat(row["collected_date"]) <= end
        ]
        offset = self._cursor_to_offset(inp.cursor)
        page = filtered[offset : offset + inp.limit]
        next_offset = offset + len(page)
        cursor = str(next_offset) if next_offset < len(filtered) else None

        records = [
            TikTokRecord(
                id=row["id"],
                target_type=row["target_type"],
                target_id=row["target_id"],
                collected_date=date.fromisoformat(row["collected_date"]),
                views=int(row["views"]),
                likes=int(row["likes"]),
                comments=int(row["comments"]),
                shares=int(row["shares"]),
                collected_at=datetime.fromisoformat(row["collected_at"]),
            )
            for row in page
        ]

        warnings: list[str] = []
        if not records:
            warnings.append("Fixture provider returned no records for the requested filter.")

        return FetchOutput(
            dataset_id=f"fixture_{inp.target_type}_{inp.target_id}",
            records=records,
            cursor=cursor,
            source="fixture",
            is_live_data=False,
            warnings=warnings,
            trace_id=trace_id,
        )

    def _load_fixture_rows(self) -> list[dict[str, object]]:
        path = Path(__file__).resolve().parents[1] / "assets" / "sample_tiktok_records.json"
        with path.open(encoding="utf-8") as f:
            payload = json.load(f)
        rows = payload.get("records", [])
        if not isinstance(rows, list):
            raise ValueError("Fixture file must contain a top-level records list.")
        return rows

    def _cursor_to_offset(self, cursor: str | None) -> int:
        if cursor is None:
            return 0
        try:
            offset = int(cursor)
        except ValueError as exc:
            raise ValueError("Cursor must be an integer offset for fixture provider.") from exc
        return max(offset, 0)

    def _default_date_range(self) -> tuple[date, date]:
        end = date.today()
        return end - timedelta(days=7), end
