"""Pydantic schemas for datasets and bulk import/export."""

from datetime import datetime, timezone
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.test_case import TestCaseCreate, TestCaseResponse


class DatasetBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    description: str | None = None
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias="metadata_",
        description="Dataset metadata and domain details",
    )

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class DatasetCreate(DatasetBase):
    project_id: uuid.UUID | None = None


class DatasetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    metadata: dict[str, Any] | None = Field(default=None, validation_alias="metadata_")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class DatasetResponse(DatasetBase):
    id: uuid.UUID
    project_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    test_case_count: int = 0
    tags: list[str] = Field(default_factory=list)

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class DatasetImportRequest(BaseModel):
    """Payload to import multiple test cases into a dataset, or create a dataset with test cases."""

    name: str | None = None
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    test_cases: list[TestCaseCreate] = Field(default_factory=list)
    overwrite_existing: bool = False

    model_config = ConfigDict(extra="ignore")


class ImportResultResponse(BaseModel):
    dataset_id: uuid.UUID
    dataset_name: str
    imported_count: int
    skipped_count: int
    errors: list[dict[str, Any]] = Field(default_factory=list)
    created_test_case_ids: list[uuid.UUID] = Field(default_factory=list)


class DatasetExportResponse(BaseModel):
    dataset: DatasetResponse
    test_cases: list[TestCaseResponse]
    exported_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

