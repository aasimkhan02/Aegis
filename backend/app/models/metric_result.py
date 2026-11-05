from datetime import datetime, timezone
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.case_result import CaseResult


class MetricResult(Base):
    __tablename__ = "metric_results"
    __table_args__ = (
        UniqueConstraint(
            "case_result_id",
            "metric_name",
            name="uq_metric_results_case_metric",
        ),
        CheckConstraint(
            "score >= 0.0 AND score <= 1.0",
            name="ck_metric_results_score_range",
        ),
        CheckConstraint(
            "threshold IS NULL OR (threshold >= 0.0 AND threshold <= 1.0)",
            name="ck_metric_results_threshold_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    case_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("case_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    details: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    # Relationships
    case_result: Mapped["CaseResult"] = relationship(
        "CaseResult",
        back_populates="metric_results",
    )

    def __repr__(self) -> str:
        return f"<MetricResult id={self.id} metric={self.metric_name!r} score={self.score}>"

