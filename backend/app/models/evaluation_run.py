from datetime import datetime, timezone
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.assistant_version import AssistantVersion
    from app.models.dataset import Dataset
    from app.models.case_result import CaseResult


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', 'cancelled')",
            name="ck_evaluation_runs_status",
        ),
        CheckConstraint(
            "total_cases >= 0",
            name="ck_evaluation_runs_total_cases_non_negative",
        ),
        CheckConstraint(
            "passed_cases >= 0",
            name="ck_evaluation_runs_passed_cases_non_negative",
        ),
        CheckConstraint(
            "failed_cases >= 0",
            name="ck_evaluation_runs_failed_cases_non_negative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # RESTRICT deletion protects completed evaluation history
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    assistant_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assistant_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
    )
    config: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    total_cases: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    passed_cases: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    failed_cases: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="evaluation_runs",
    )
    assistant_version: Mapped["AssistantVersion"] = relationship(
        "AssistantVersion",
        back_populates="evaluation_runs",
    )
    dataset: Mapped["Dataset"] = relationship(
        "Dataset",
        back_populates="evaluation_runs",
    )
    case_results: Mapped[list["CaseResult"]] = relationship(
        "CaseResult",
        back_populates="evaluation_run",
    )

    def __repr__(self) -> str:
        return f"<EvaluationRun id={self.id} status={self.status!r}>"

