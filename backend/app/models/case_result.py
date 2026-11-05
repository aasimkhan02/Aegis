from datetime import datetime, timezone
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.evaluation_run import EvaluationRun
    from app.models.test_case import TestCase
    from app.models.metric_result import MetricResult


class CaseResult(Base):
    __tablename__ = "case_results"
    __table_args__ = (
        UniqueConstraint(
            "evaluation_run_id",
            "test_case_id",
            name="uq_case_results_run_case",
        ),
        CheckConstraint(
            "status IN ('passed', 'failed', 'error', 'skipped')",
            name="ck_case_results_status",
        ),
        CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0",
            name="ck_case_results_latency_ms_non_negative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # RESTRICT deletion protects historical test run records
    evaluation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evaluation_runs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    test_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("test_cases.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # test_case_snapshot preserves the original test case input and expected behavior,
    # ensuring evaluation integrity even if the test case is later updated or removed.
    test_case_snapshot: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )
    actual_output: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    # Relationships
    evaluation_run: Mapped["EvaluationRun"] = relationship(
        "EvaluationRun",
        back_populates="case_results",
    )
    test_case: Mapped["TestCase"] = relationship(
        "TestCase",
        back_populates="case_results",
    )
    metric_results: Mapped[list["MetricResult"]] = relationship(
        "MetricResult",
        back_populates="case_result",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<CaseResult id={self.id} status={self.status!r}>"

