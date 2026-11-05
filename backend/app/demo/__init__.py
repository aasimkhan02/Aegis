"""Demo customer-support assistant package for BharatHome Appliances."""

from app.demo.assistants import (
    BHARATHOME_V1_CONFIG,
    BHARATHOME_V1_MODEL,
    BHARATHOME_V1_NAME,
    BHARATHOME_V1_PROVIDER,
    BHARATHOME_V1_SYSTEM_PROMPT,
    BHARATHOME_V1_VERSION,
    BHARATHOME_V2_CONFIG,
    BHARATHOME_V2_MODEL,
    BHARATHOME_V2_NAME,
    BHARATHOME_V2_PROVIDER,
    BHARATHOME_V2_SYSTEM_PROMPT,
    BHARATHOME_V2_VERSION,
)
from app.demo.knowledge_base import (
    BHARATHOME_KNOWLEDGE_BASE,
    search_knowledge_base,
)
from app.demo.orchestrator import DemoAssistantOrchestrator
from app.demo.tools import (
    AVAILABLE_TOOLS,
    TOOL_SCHEMAS,
    create_service_request,
    execute_tool,
    product_lookup,
    troubleshooting_lookup,
    warranty_lookup,
)

__all__ = [
    "BHARATHOME_KNOWLEDGE_BASE",
    "search_knowledge_base",
    "AVAILABLE_TOOLS",
    "TOOL_SCHEMAS",
    "product_lookup",
    "warranty_lookup",
    "troubleshooting_lookup",
    "create_service_request",
    "execute_tool",
    "BHARATHOME_V1_NAME",
    "BHARATHOME_V1_VERSION",
    "BHARATHOME_V1_MODEL",
    "BHARATHOME_V1_PROVIDER",
    "BHARATHOME_V1_SYSTEM_PROMPT",
    "BHARATHOME_V1_CONFIG",
    "BHARATHOME_V2_NAME",
    "BHARATHOME_V2_VERSION",
    "BHARATHOME_V2_MODEL",
    "BHARATHOME_V2_PROVIDER",
    "BHARATHOME_V2_SYSTEM_PROMPT",
    "BHARATHOME_V2_CONFIG",
    "DemoAssistantOrchestrator",
]

