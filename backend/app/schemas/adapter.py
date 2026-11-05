"""Pydantic schemas for the common assistant adapter system."""

from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ToolCall(BaseModel):
    """Standardized representation of a tool or function call."""

    model_config = ConfigDict(extra="allow")

    id: str | None = None
    type: str = "function"
    name: str
    arguments: dict[str, Any] | str = Field(default_factory=dict)


class Message(BaseModel):
    """A single message within a conversation."""

    model_config = ConfigDict(extra="allow")

    role: Literal["system", "user", "assistant", "tool"]
    content: str = ""
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)


class GenerationParameters(BaseModel):
    """Optional generation parameters controlling LLM inference."""

    model_config = ConfigDict(extra="allow")

    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    stop: list[str] | str | None = None
    tools: list[dict[str, Any]] | None = None
    timeout_seconds: float = 30.0
    extra: dict[str, Any] = Field(default_factory=dict)


class ConversationRequest(BaseModel):
    """Input request sent to any assistant adapter."""

    model_config = ConfigDict(extra="allow")

    messages: list[Message]
    parameters: GenerationParameters = Field(default_factory=GenerationParameters)
    model: str | None = None
    system_prompt: str | None = None


class TokenUsage(BaseModel):
    """Standardized token usage metadata."""

    model_config = ConfigDict(extra="allow")

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class AssistantResponse(BaseModel):
    """Standardized output returned by all assistant adapters."""

    model_config = ConfigDict(extra="allow")

    output: str
    provider: str
    model: str
    latency_ms: int
    token_usage: TokenUsage | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

