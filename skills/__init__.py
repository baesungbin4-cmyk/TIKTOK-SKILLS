"""Skill modules for the TikTok data analysis agent."""

from skills.anomaly_detection import (
    AnomalyDetectionInput,
    AnomalyDetectionOutput,
    AnomalyDetectionSkill,
    AnomalyPoint,
)
from skills.insight_gen import (
    InsightEvidence,
    InsightGenInput,
    InsightGenOutput,
    InsightGenSkill,
)
from skills.report_gen import ReportGenSkill, ReportInput, ReportOutput
from skills.tiktok_fetch import FetchInput, FetchOutput, TikTokFetchSkill, TikTokRecord
from skills.trend_analysis import TrendAnalysisInput, TrendAnalysisOutput, TrendAnalysisSkill
from skills.user_analysis import UserAnalysisInput, UserAnalysisOutput, UserAnalysisSkill

__all__ = [
    "AnomalyDetectionInput",
    "AnomalyDetectionOutput",
    "AnomalyDetectionSkill",
    "AnomalyPoint",
    "FetchInput",
    "FetchOutput",
    "InsightEvidence",
    "InsightGenInput",
    "InsightGenOutput",
    "InsightGenSkill",
    "ReportGenSkill",
    "ReportInput",
    "ReportOutput",
    "TikTokFetchSkill",
    "TikTokRecord",
    "TrendAnalysisInput",
    "TrendAnalysisOutput",
    "TrendAnalysisSkill",
    "UserAnalysisInput",
    "UserAnalysisOutput",
    "UserAnalysisSkill",
]
