from __future__ import annotations

import json
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


IntentName = Literal["trend_analysis", "user_analysis", "anomaly_detection"]
InsightAudience = Literal["operator", "analyst", "executive"]
InsightLanguage = Literal["en", "zh"]


class InsightEvidence(BaseModel):
    metric: str
    value: float | str
    interpretation: str


class InsightGenInput(BaseModel):
    dataset_id: str
    intent: IntentName
    analysis_result: dict[str, Any]
    source: str
    is_live_data: bool
    warnings: list[str] = Field(default_factory=list)
    audience: InsightAudience = "operator"
    language: InsightLanguage = "en"


class InsightGenOutput(BaseModel):
    insight_id: str
    narrative: str
    evidence: list[InsightEvidence]
    recommended_actions: list[str]
    risk_flags: list[str]
    confidence: float
    llm_prompt: str
    warnings: list[str] = Field(default_factory=list)


class InsightGenSkill:
    name = "insight_gen"
    description = (
        "Transform structured TikTok analysis outputs into business-oriented narrative "
        "insights, evidence, risk flags, recommended actions, and an LLM-ready prompt."
    )

    async def run(self, inp: InsightGenInput) -> InsightGenOutput:
        if inp.intent == "anomaly_detection":
            narrative, evidence, actions, risks = self._from_anomaly(inp.analysis_result)
        elif inp.intent == "user_analysis":
            narrative, evidence, actions, risks = self._from_user(inp.analysis_result)
        else:
            narrative, evidence, actions, risks = self._from_trend(inp.analysis_result)

        warnings = list(inp.warnings)
        if not inp.is_live_data:
            warnings.append(
                f"Insight is generated from {inp.source} data and should not be treated as live TikTok intelligence."
            )

        return InsightGenOutput(
            insight_id=f"ins_{uuid4().hex[:10]}",
            narrative=narrative,
            evidence=evidence,
            recommended_actions=actions,
            risk_flags=risks,
            confidence=self._confidence(inp.source, evidence, risks),
            llm_prompt=self._build_llm_prompt(inp, narrative, evidence, actions, risks),
            warnings=warnings,
        )

    def _from_trend(
        self,
        result: dict[str, Any],
    ) -> tuple[str, list[InsightEvidence], list[str], list[str]]:
        summary = result.get("summary", {})
        growth = float(summary.get("growth", 0.0))
        engagement_rate = float(summary.get("engagement_rate", 0.0))
        total_views = float(summary.get("total_views", 0.0))

        direction = "growing" if growth > 0 else "flat or declining"
        narrative = (
            f"The tracked trend is {direction}: views changed by {growth:.2%} "
            f"with engagement rate at {engagement_rate:.2%} across {total_views:g} views."
        )
        evidence = [
            InsightEvidence(
                metric="growth",
                value=round(growth, 4),
                interpretation="First-to-last view change across the fetched record series.",
            ),
            InsightEvidence(
                metric="engagement_rate",
                value=round(engagement_rate, 4),
                interpretation="Likes, comments, and shares divided by total views.",
            ),
        ]
        actions = [
            "Compare high-engagement records with posting time, topic, and format.",
            "Prioritize creative patterns from the strongest records before scaling distribution.",
        ]
        risks = [] if growth > 0 else ["Trend momentum is weak under the current window."]
        return narrative, evidence, actions, risks

    def _from_user(
        self,
        result: dict[str, Any],
    ) -> tuple[str, list[InsightEvidence], list[str], list[str]]:
        profile = result.get("profile", {})
        health = str(profile.get("health", "unknown"))
        engagement_rate = float(profile.get("engagement_rate", 0.0))
        avg_likes = float(profile.get("avg_likes", 0.0))

        narrative = (
            f"Account health is {health}. Engagement rate is {engagement_rate:.2%}, "
            f"with average likes at {avg_likes:g} per record."
        )
        evidence = [
            InsightEvidence(
                metric="health",
                value=health,
                interpretation="Rule-based health label derived from likes and engagement rate.",
            ),
            InsightEvidence(
                metric="engagement_rate",
                value=round(engagement_rate, 4),
                interpretation="Overall account engagement across fetched records.",
            ),
        ]
        actions = list(result.get("recommendations", [])) or [
            "Collect more account records before making a content decision."
        ]
        risks = [] if health == "active" else ["Account needs attention under current thresholds."]
        return narrative, evidence, actions, risks

    def _from_anomaly(
        self,
        result: dict[str, Any],
    ) -> tuple[str, list[InsightEvidence], list[str], list[str]]:
        metric = str(result.get("metric", "views"))
        severity = str(result.get("severity", "normal"))
        anomaly_count = int(result.get("anomaly_count", 0))
        anomalies = list(result.get("anomalies", []))
        top = anomalies[0] if anomalies else {}

        if anomaly_count:
            narrative = (
                f"{anomaly_count} abnormal {metric} point(s) were detected. "
                f"Overall severity is {severity}; the strongest point is "
                f"{top.get('record_id', 'unknown')} on {top.get('collected_date', 'unknown')}."
            )
        else:
            narrative = f"No abnormal {metric} spike was detected under the current thresholds."

        evidence = [
            InsightEvidence(
                metric="baseline",
                value=float(result.get("baseline", 0.0)),
                interpretation="Median baseline used for robust anomaly scoring.",
            ),
            InsightEvidence(
                metric="mad",
                value=float(result.get("mad", 0.0)),
                interpretation="Median absolute deviation used to resist outlier distortion.",
            ),
            InsightEvidence(
                metric="severity",
                value=severity,
                interpretation="Overall severity derived from robust z-score and growth spike checks.",
            ),
        ]
        actions = (
            [
                "Check campaign calendar, paid traffic, content format, and posting time around the anomaly point.",
                "Compare anomaly records with comments, shares, and external events before changing strategy.",
            ]
            if anomaly_count
            else ["Keep monitoring the same metric over a longer window before escalating."]
        )
        risks = [] if severity == "normal" else [f"{metric} anomaly severity is {severity}."]
        return narrative, evidence, actions, risks

    def _confidence(
        self,
        source: str,
        evidence: list[InsightEvidence],
        risks: list[str],
    ) -> float:
        base = 0.78 if source == "fixture" else 0.7
        if source == "live":
            base = 0.88
        if not evidence:
            base -= 0.2
        if risks:
            base -= 0.05
        return round(max(min(base, 0.95), 0.3), 2)

    def _build_llm_prompt(
        self,
        inp: InsightGenInput,
        narrative: str,
        evidence: list[InsightEvidence],
        actions: list[str],
        risks: list[str],
    ) -> str:
        payload = {
            "dataset_id": inp.dataset_id,
            "intent": inp.intent,
            "source": inp.source,
            "is_live_data": inp.is_live_data,
            "audience": inp.audience,
            "language": inp.language,
            "analysis_result": inp.analysis_result,
            "draft": {
                "narrative": narrative,
                "evidence": [item.model_dump() for item in evidence],
                "recommended_actions": actions,
                "risk_flags": risks,
            },
            "warnings": inp.warnings,
        }
        return (
            "You are a TikTok analytics strategist. Turn the JSON analysis into a concise "
            "business insight. Do not claim the data is live unless is_live_data is true. "
            "Return: executive summary, evidence, risks, and next actions.\n\n"
            + json.dumps(payload, ensure_ascii=False, indent=2)
        )
