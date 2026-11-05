"""SQLAlchemy models registry for Aegis."""

from app.models.project import Project
from app.models.assistant_version import AssistantVersion
from app.models.dataset import Dataset
from app.models.test_case import TestCase
from app.models.evaluation_run import EvaluationRun
from app.models.case_result import CaseResult
from app.models.metric_result import MetricResult

__all__ = [
    "Project",
    "AssistantVersion",
    "Dataset",
    "TestCase",
    "EvaluationRun",
    "CaseResult",
    "MetricResult",
]

