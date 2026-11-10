"""Pydantic schemas for Project management endpoints."""

from datetime import datetime
import uuid
from pydantic import BaseModel, ConfigDict, Field


class ProjectBase(BaseModel):
    name: str = Field(..., max_length=150, description="Project name")
    description: str | None = Field(default=None, description="Optional description")


class ProjectCreate(ProjectBase):
    slug: str | None = Field(default=None, max_length=150, description="URL-friendly slug (auto-generated if omitted)")


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=150)
    description: str | None = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    description: str | None = None
    assistants_count: int = 0
    datasets_count: int = 0
    runs_count: int = 0
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int

