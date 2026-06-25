from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Literal

from pydantic import BaseModel, Field

from skills.report_gen import ReportGenSkill, ReportInput
from skills.tiktok_fetch import FetchInput, ProviderName, TikTokFetchSkill
from skills.trend_analysis import TrendAnalysisInput, TrendAnalysisSkill
from skills.user_analysis import UserAnalysisInput, UserAnalysisSkill


class AgentRequest(BaseModel):
    query: str = Field(min_length=1)
    target_type: Literal["video", "account", "hashtag", "user"] = "hashtag"
    target_id: str = "demo"
    date_range: tuple[date, date] | None = None
    limit: int = Field(default=50, ge=1, le=200)
    provider: ProviderName = "mock"


class AgentResponse(BaseModel):
    intent: str
    dataset_id: str
    result: dict[str, Any]
    report: dict[str, Any]
    steps: list[str]
    source: str
    is_live_data: bool
    warnings: list[str] = Field(default_factory=list)
    trace_id: str


class TikTokAgent:
    def __init__(self) -> None:
        self.fetch_skill = TikTokFetchSkill()
        self.trend_skill = TrendAnalysisSkill()
        self.user_skill = UserAnalysisSkill()
        self.report_skill = ReportGenSkill()
        self.skills = {
            self.fetch_skill.name: self.fetch_skill,
            self.trend_skill.name: self.trend_skill,
            self.user_skill.name: self.user_skill,
            self.report_skill.name: self.report_skill,
        }

    async def run(self, query: str, **kwargs: Any) -> AgentResponse:
        request = AgentRequest(query=query, **kwargs)
        intent = self._plan(request)
        start, end = request.date_range or self._default_date_range()

        fetch_result = await self.fetch_skill.run(
            FetchInput(
                target_type=request.target_type,
                target_id=request.target_id,
                date_range=(start, end),
                limit=request.limit,
                provider=request.provider,
            )
        )

        if intent == "user_analysis":
            analysis = await self.user_skill.run(
                UserAnalysisInput(
                    dataset_id=fetch_result.dataset_id,
                    records=fetch_result.records,
                )
            )
        else:
            analysis = await self.trend_skill.run(
                TrendAnalysisInput(
                    dataset_id=fetch_result.dataset_id,
                    records=fetch_result.records,
                )
            )

        analysis_payload = analysis.model_dump()
        warnings = [
            *fetch_result.warnings,
            *analysis_payload.get("warnings", []),
        ]
        report = await self.report_skill.run(
            ReportInput(
                analysis_id=analysis_payload["analysis_id"],
                dataset_id=fetch_result.dataset_id,
                intent=intent,
                analysis_result=analysis_payload,
                source=fetch_result.source,
                is_live_data=fetch_result.is_live_data,
                warnings=warnings,
            )
        )

        return AgentResponse(
            intent=intent,
            dataset_id=fetch_result.dataset_id,
            result=analysis_payload,
            report=report.model_dump(),
            steps=[self.fetch_skill.name, intent, self.report_skill.name],
            source=fetch_result.source,
            is_live_data=fetch_result.is_live_data,
            warnings=report.warnings,
            trace_id=fetch_result.trace_id,
        )

    def _plan(self, request: AgentRequest) -> str:
        if request.target_type in {"account", "user"}:
            return "user_analysis"

        lowered = request.query.lower()
        user_keywords = (
            "user",
            "account",
            "profile",
            "creator",
            "账号",
            "账户",
            "用户",
            "达人",
            "创作者",
        )
        if any(keyword in lowered for keyword in user_keywords):
            return "user_analysis"
        return "trend_analysis"

    def _default_date_range(self) -> tuple[date, date]:
        end = date.today()
        return end - timedelta(days=7), end

    def tool_schemas(self) -> list[dict[str, Any]]:
        return [
            self._schema_for(self.fetch_skill.name, self.fetch_skill.description, FetchInput),
            self._schema_for(
                self.trend_skill.name,
                self.trend_skill.description,
                TrendAnalysisInput,
            ),
            self._schema_for(
                self.user_skill.name,
                self.user_skill.description,
                UserAnalysisInput,
            ),
            self._schema_for(
                self.report_skill.name,
                self.report_skill.description,
                ReportInput,
            ),
        ]

    def _schema_for(
        self,
        name: str,
        description: str,
        model: type[BaseModel],
    ) -> dict[str, Any]:
        return {
            "name": name,
            "description": description,
            "parameters": model.model_json_schema(),
        }
