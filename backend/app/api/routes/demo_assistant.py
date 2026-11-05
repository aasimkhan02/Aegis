"""FastAPI routes for interacting with BharatHome Demo Assistants (v1 and v2)."""

from typing import Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.demo.assistants import (
    BHARATHOME_V1_CONFIG,
    BHARATHOME_V1_MODEL,
    BHARATHOME_V1_NAME,
    BHARATHOME_V1_SYSTEM_PROMPT,
    BHARATHOME_V1_VERSION,
    BHARATHOME_V2_CONFIG,
    BHARATHOME_V2_MODEL,
    BHARATHOME_V2_NAME,
    BHARATHOME_V2_SYSTEM_PROMPT,
    BHARATHOME_V2_VERSION,
)
from app.demo.knowledge_base import BHARATHOME_KNOWLEDGE_BASE, search_knowledge_base
from app.demo.orchestrator import DemoAssistantOrchestrator
from app.demo.tools import AVAILABLE_TOOLS, TOOL_SCHEMAS, execute_tool
from app.schemas.adapter import AssistantResponse, ConversationRequest, Message

router = APIRouter()


class ChatQueryPayload(BaseModel):
    version: str = Field(default="v1", description="'v1' (good) or 'v2' (broken)")
    message: str = Field(..., min_length=1, description="User message to assistant")
    provider: str = Field(default="mock", description="Adapter provider: mock or ollama")


class ToolExecutionPayload(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


@router.get("/assistants")
def get_demo_assistants() -> dict[str, Any]:
    """Retrieve metadata and configurations for BharatHome Assistants v1 and v2."""
    return {
        "assistants": [
            {
                "name": BHARATHOME_V1_NAME,
                "version": BHARATHOME_V1_VERSION,
                "model": BHARATHOME_V1_MODEL,
                "type": "good_production",
                "system_prompt": BHARATHOME_V1_SYSTEM_PROMPT,
                "config": BHARATHOME_V1_CONFIG,
            },
            {
                "name": BHARATHOME_V2_NAME,
                "version": BHARATHOME_V2_VERSION,
                "model": BHARATHOME_V2_MODEL,
                "type": "broken_test_only",
                "system_prompt": BHARATHOME_V2_SYSTEM_PROMPT,
                "config": BHARATHOME_V2_CONFIG,
            },
        ],
        "available_tools": TOOL_SCHEMAS,
    }


@router.post("/chat", response_model=AssistantResponse)
async def chat_with_demo_assistant(payload: ChatQueryPayload) -> AssistantResponse:
    """Send a user message to BharatHome Assistant v1 or v2."""
    orchestrator = DemoAssistantOrchestrator(
        assistant_version=payload.version,
        provider=payload.provider,
    )
    request = ConversationRequest(
        messages=[Message(role="user", content=payload.message)],
    )
    return await orchestrator.generate(request)


@router.post("/generate", response_model=AssistantResponse)
async def generate_with_demo_assistant(
    request: ConversationRequest,
    version: str = Query(default="v1", description="'v1' or 'v2'"),
    provider: str = Query(default="mock", description="'mock' or 'ollama'"),
) -> AssistantResponse:
    """Process a full ConversationRequest with BharatHome Assistant."""
    orchestrator = DemoAssistantOrchestrator(
        assistant_version=version,
        provider=provider,
    )
    return await orchestrator.generate(request)


@router.post("/tools/execute")
def execute_demo_tool(payload: ToolExecutionPayload) -> dict[str, Any]:
    """Directly test or execute a BharatHome demo tool."""
    if payload.tool_name not in AVAILABLE_TOOLS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown tool '{payload.tool_name}'. Available: {list(AVAILABLE_TOOLS.keys())}",
        )
    return execute_tool(payload.tool_name, payload.arguments)


@router.get("/knowledge-base")
def query_knowledge_base(
    q: str | None = Query(default=None, description="Search query terms"),
    limit: int = Query(default=5, ge=1, le=20),
) -> dict[str, Any]:
    """Browse or search the BharatHome knowledge base."""
    if q:
        results = search_knowledge_base(q, top_k=limit)
    else:
        results = BHARATHOME_KNOWLEDGE_BASE[:limit]

    return {
        "total_articles": len(BHARATHOME_KNOWLEDGE_BASE),
        "returned": len(results),
        "articles": results,
    }

