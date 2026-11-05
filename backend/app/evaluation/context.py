"""Evaluation context and TestCaseData schemas passed to evaluators and executors."""

from dataclasses import dataclass, field
from typing import Any
import uuid

from app.schemas.adapter import AssistantResponse


@dataclass
class TestCaseData:
    """Decoupled, session-independent representation of a TestCase."""

    id: uuid.UUID
    name: str
    input_data: dict[str, Any]
    expected_output: dict[str, Any] | None = None
    expected_behavior: str | None = None
    retrieval_context: list[Any] | dict[str, Any] | None = None
    ground_truth_context: list[Any] | dict[str, Any] | None = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    is_enabled: bool = True

    @classmethod
    def from_orm(cls, tc: Any) -> "TestCaseData":
        """Safely extract attributes from an ORM TestCase while its session is open."""
        return cls(
            id=tc.id,
            name=tc.name,
            input_data=dict(tc.input_data or {}),
            expected_output=tc.expected_output,
            expected_behavior=tc.expected_behavior,
            retrieval_context=tc.retrieval_context,
            ground_truth_context=getattr(tc, "ground_truth_context", None),
            tags=list(tc.tags) if isinstance(tc.tags, list) else [],
            metadata=dict(getattr(tc, "metadata_", {}) or {}),
            is_enabled=tc.is_enabled,
        )

    def to_snapshot(self) -> dict[str, Any]:
        """Produce an immutable JSON-serializable snapshot."""
        return {
            "id": str(self.id),
            "name": self.name,
            "input_data": self.input_data,
            "expected_output": self.expected_output,
            "expected_behavior": self.expected_behavior,
            "retrieval_context": self.retrieval_context,
            "ground_truth_context": self.ground_truth_context,
            "tags": self.tags,
            "metadata": self.metadata,
            "is_enabled": self.is_enabled,
        }


@dataclass
class EvaluationContext:
    """Standardized context passed to evaluators for computing metric results."""

    test_case_id: uuid.UUID
    test_case_name: str
    input_data: dict[str, Any]
    expected_output: dict[str, Any] | None = None
    expected_behavior: str | None = None
    retrieval_context: list[Any] | dict[str, Any] | None = None
    ground_truth_context: list[Any] | dict[str, Any] | None = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    actual_response: AssistantResponse | None = None
    error_message: str | None = None
    latency_ms: int = 0
    execution_info: dict[str, Any] = field(default_factory=dict)

    @property
    def output_text(self) -> str:
        """Helper to get actual output text cleanly."""
        if self.actual_response and self.actual_response.output:
            return self.actual_response.output
        return ""
