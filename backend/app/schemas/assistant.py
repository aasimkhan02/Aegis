"""Pydantic schemas for AssistantVersion management endpoints."""

from datetime import datetime
from typing import Any
import uuid
from pydantic import BaseModel, ConfigDict, Field


class AssistantVersionCreate(BaseModel):
    project_id: uuid.UUID = Field(..., description="Project UUID to associate assistant with")
    name: str = Field(..., max_length=150, description="Assistant name")
    version: str = Field(..., max_length=50, description="Semantic version string, e.g. 1.0.0")
    provider: str | None = Field(default="mock", description="Adapter provider: mock, bharathome, http, ollama")
    model_name: str | None = Field(default="mock-model", description="Model identifier")
    system_prompt: str | None = Field(default=None, description="System prompt instructions")
    config: dict[str, Any] = Field(default_factory=dict, description="Custom parameters or endpoint configuration")


class AssistantVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    project_name: str | None = None
    name: str
    version: str
    provider: str | None = None
    model_name: str | None = None
    system_prompt: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    runs_count: int = 0
    created_at: datetime


class AssistantVersionListResponse(BaseModel):
    items: list[AssistantVersionResponse]
    total: int

