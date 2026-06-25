from __future__ import annotations

from statistics import median

from pydantic import BaseModel, Field

from skills.tiktok_fetch import TikTokRecord


class AnomalyDetectionInput(BaseModel):
    dataset_id: str
    records: list[TikTokRecord]
    metric: str = Field(default="views", pattern="^(views|engagement_count|engagement_rate)$")
    z_threshold: float = Field(default=3.5, ge=1.0, le=10.0)
    growth_threshold: float = Field(default=0.35, ge=0.0, le=10.0)


class AnomalyPoint(BaseModel):
    record_id: str
    collected_date: str
    metric_value: float
    baseline: float
    robust_z_score: float
    growth_rate: float | None
    severity: str
    reasons: list[str]


class AnomalyDetectionOutput(BaseModel):
    analysis_id: str
    metric: str
    baseline: float
    mad: float
    anomaly_count: int
    severity: str
    anomalies: list[AnomalyPoint]
    series: dict[str, list[float | str]]
    warnings: list[str] = Field(default_factory=list)


class AnomalyDetectionSkill:
    name = "anomaly_detection"
    description = (
        "Detect abnormal TikTok metric spikes using median/MAD robust z-score and "
        "period-over-period growth thresholds."
    )

    async def run(self, inp: AnomalyDetectionInput) -> AnomalyDetectionOutput:
        records = sorted(inp.records, key=lambda record: record.collected_date)
        if len(records) < 3:
            return AnomalyDetectionOutput(
                analysis_id=f"anomaly_{inp.dataset_id}",
                metric=inp.metric,
                baseline=0.0,
                mad=0.0,
                anomaly_count=0,
                severity="insufficient_data",
                anomalies=[],
                series={"dates": [], "values": [], "robust_z_scores": []},
                warnings=["At least three records are required for robust anomaly detection."],
            )

        values = [self._metric_value(record, inp.metric) for record in records]
        baseline = float(median(values))
        deviations = [abs(value - baseline) for value in values]
        mad = float(median(deviations))
        scale = 1.4826 * mad if mad > 0 else 1.0

        z_scores = [round((value - baseline) / scale, 4) for value in values]
        anomalies: list[AnomalyPoint] = []
        for idx, (record, value, z_score) in enumerate(zip(records, values, z_scores)):
            growth_rate = self._growth_rate(values[idx - 1], value) if idx > 0 else None
            reasons: list[str] = []
            if abs(z_score) >= inp.z_threshold:
                reasons.append("robust_z_score")
            if growth_rate is not None and growth_rate >= inp.growth_threshold:
                reasons.append("growth_spike")
            if not reasons:
                continue

            severity = self._severity(z_score, growth_rate)
            anomalies.append(
                AnomalyPoint(
                    record_id=record.id,
                    collected_date=record.collected_date.isoformat(),
                    metric_value=round(value, 4),
                    baseline=round(baseline, 4),
                    robust_z_score=z_score,
                    growth_rate=None if growth_rate is None else round(growth_rate, 4),
                    severity=severity,
                    reasons=reasons,
                )
            )

        return AnomalyDetectionOutput(
            analysis_id=f"anomaly_{inp.dataset_id}",
            metric=inp.metric,
            baseline=round(baseline, 4),
            mad=round(mad, 4),
            anomaly_count=len(anomalies),
            severity=self._overall_severity(anomalies),
            anomalies=anomalies,
            series={
                "dates": [record.collected_date.isoformat() for record in records],
                "values": [round(value, 4) for value in values],
                "robust_z_scores": z_scores,
            },
        )

    def _metric_value(self, record: TikTokRecord, metric: str) -> float:
        if metric == "engagement_count":
            return float(record.engagement_count)
        if metric == "engagement_rate":
            return round(record.engagement_count / max(record.views, 1), 6)
        return float(record.views)

    def _growth_rate(self, previous: float, current: float) -> float | None:
        if previous <= 0:
            return None
        return (current - previous) / previous

    def _severity(self, z_score: float, growth_rate: float | None) -> str:
        if abs(z_score) >= 6 or (growth_rate is not None and growth_rate >= 1.0):
            return "critical"
        if abs(z_score) >= 4.5 or (growth_rate is not None and growth_rate >= 0.6):
            return "high"
        return "medium"

    def _overall_severity(self, anomalies: list[AnomalyPoint]) -> str:
        if any(point.severity == "critical" for point in anomalies):
            return "critical"
        if any(point.severity == "high" for point in anomalies):
            return "high"
        if anomalies:
            return "medium"
        return "normal"
