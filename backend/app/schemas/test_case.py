"""Pydantic schemas for test cases."""

from datetime import datetime
from typing import Any, Union
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TestCaseBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    input_data: Union[dict[str, Any], list[Any], str] = Field(
        default_factory=dict,
        description="Prompt, multi-turn messages, or variables",
    )
    expected_output: Union[dict[str, Any], list[Any], str, None] = None
    expected_behavior: str | None = None
    retrieval_context: Union[list[Any], dict[str, Any], str, None] = Field(
        default_factory=list,
        description="Relevant retrieval passages or documents",
    )
    ground_truth_context: Union[list[Any], dict[str, Any], str, None] = Field(
        default_factory=list,
        description="Curated, trusted ground-truth reference information",
    )
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias="metadata_",
        description="Arbitrary test case metadata",
    )
    is_enabled: bool = True

    @field_validator("input_data", mode="before")
    @classmethod
    def normalize_input_data(cls, v: Any) -> Any:
        if isinstance(v, str):
            # Normalizes plain string prompt into standard message format if needed
            return {"prompt": v}
        return v if v is not None else {}

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, v: Any) -> list[str]:
        if isinstance(v, list):
            return [str(item).strip() for item in v if str(item).strip()]
        elif isinstance(v, str):
            return [t.strip() for t in v.split(",") if t.strip()]
        return []

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class TestCaseCreate(TestCaseBase):
    dataset_id: uuid.UUID | None = None


class TestCaseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    input_data: Union[dict[str, Any], list[Any], str, None] = None
    expected_output: Union[dict[str, Any], list[Any], str, None] = None
    expected_behavior: str | None = None
    retrieval_context: Union[list[Any], dict[str, Any], str, None] = None
    ground_truth_context: Union[list[Any], dict[str, Any], str, None] = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = Field(default=None, validation_alias="metadata_")
    is_enabled: bool | None = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class TestCaseResponse(TestCaseBase):
    id: uuid.UUID
    dataset_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    has_evaluations: bool = False

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

