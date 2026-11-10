"""Pydantic schemas for Promptfoo prompt and adversarial evaluation."""

from datetime import datetime
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field


class PromptfooEvaluationRequest(BaseModel):
    """Payload to initiate a Promptfoo prompt & adversarial test run."""

    assistant_version_id: uuid.UUID | None = Field(
        default=None,
        description="Target AssistantVersion UUID in PostgreSQL (optional if using version flag)",
    )
    version: str = Field(
        default="v1",
        description="Assistant version identifier: 'v1' (good production) or 'v2' (intentionally broken)",
    )
    provider: str = Field(
        default="mock",
        description="Underlying provider: 'mock', 'ollama', or 'http'",
    )
    timeout_seconds: int = Field(
        default=120,
        ge=10,
        le=300,
        description="Subprocess execution timeout in seconds (default: 120s)",
    )


class PromptfooAssertionResult(BaseModel):
    """Assertion outcome within an individual Promptfoo test case."""

    model_config = ConfigDict(from_attributes=True)

    type: str = Field(..., description="Assertion type (contains, not-contains, icontains, etc.)")
    value: str | None = Field(default=None, description="Assertion target value or pattern")
    passed: bool = Field(..., description="Whether the assertion succeeded")
    reason: str | None = Field(default=None, description="Diagnostic explanation")


class PromptfooTestResultItem(BaseModel):
    """Outcome of a single Promptfoo test case."""

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., description="Descriptive name of the test case")
    prompt: str = Field(..., description="Input prompt evaluated")
    passed: bool = Field(..., description="Whether all assertions in this test passed")
    score: float = Field(..., description="Computed score between 0.0 and 1.0")
    reason: str | None = Field(default=None, description="Diagnostic summary")
    latency_ms: int | None = Field(default=None, description="Test execution latency in milliseconds")
    output: str | None = Field(default=None, description="Actual assistant response output")
    assertions: list[PromptfooAssertionResult] = Field(
        default_factory=list,
        description="Detailed assertion outcomes",
    )


class PromptfooEvaluationResponse(BaseModel):
    """Structured response returned by the Promptfoo evaluation API."""

    model_config = ConfigDict(from_attributes=True)

    status: str = Field(
        ...,
        description="Execution status: 'completed', 'failed', 'timeout', 'cli_not_found', or 'error'",
    )
    total_tests: int = Field(default=0, description="Total number of evaluated test cases")
    passed: int = Field(default=0, description="Count of test cases passing all assertions")
    failed: int = Field(default=0, description="Count of test cases with failed assertions")
    results: list[PromptfooTestResultItem] = Field(
        default_factory=list,
        description="Detailed per-case results",
    )
    duration_seconds: float = Field(default=0.0, description="Total execution duration in seconds")
    assistant_name: str | None = Field(default=None, description="Name of the evaluated assistant")
    assistant_version: str | None = Field(default=None, description="Version string of the evaluated assistant")
    error: str | None = Field(default=None, description="Error message if execution failed or timed out")

