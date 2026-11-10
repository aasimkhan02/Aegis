"""Promptfoo Custom Python Provider for Aegis Assistant Adapters.

Enables Promptfoo to evaluate Aegis assistant versions (BharatHome v1, v2,
or any registered assistant version in PostgreSQL) directly using the existing adapter system.
"""

import asyncio
import os
from pathlib import Path
import sys
from typing import Any
import uuid

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.adapters.base import BaseAssistantAdapter
from app.db.session import SessionLocal
from app.demo.orchestrator import DemoAssistantOrchestrator
from app.evaluation.executor import resolve_assistant_adapter
from app.models.assistant_version import AssistantVersion
from app.schemas.adapter import ConversationRequest, Message


def _resolve_adapter(options: dict[str, Any] | None, context: dict[str, Any] | None) -> BaseAssistantAdapter:
    """Resolve an assistant adapter instance based on options, context, or environment."""
    cfg = (options or {}).get("config") or {}
    ctx_vars = (context or {}).get("vars") or {}

    # 1. Target by UUID if provided
    raw_version_id = (
        cfg.get("assistant_version_id")
        or ctx_vars.get("assistant_version_id")
        or os.environ.get("AEGIS_ASSISTANT_VERSION_ID")
    )
    if raw_version_id:
        try:
            target_uuid = uuid.UUID(str(raw_version_id).strip())
            db = SessionLocal()
            try:
                av = db.get(AssistantVersion, target_uuid)
                if av is not None:
                    return resolve_assistant_adapter(av)
            finally:
                db.close()
        except Exception:
            pass

    # 2. Target by version name ('v1' good or 'v2' broken)
    version = (
        cfg.get("version")
        or ctx_vars.get("assistant_version")
        or os.environ.get("AEGIS_ASSISTANT_VERSION", "v1")
    )
    provider_type = (
        cfg.get("provider")
        or os.environ.get("AEGIS_ASSISTANT_PROVIDER", "mock")
    )
    return DemoAssistantOrchestrator(assistant_version=str(version), provider=str(provider_type))


def call_api(
    prompt: str,
    options: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Promptfoo custom provider entrypoint invoked by the Promptfoo CLI."""
    try:
        adapter = _resolve_adapter(options, context)
        request = ConversationRequest(
            messages=[Message(role="user", content=prompt)]
        )

        # Run async generate safely across existing or fresh event loops
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import nest_asyncio

                nest_asyncio.apply()
                resp = loop.run_until_complete(adapter.generate(request))
            else:
                resp = loop.run_until_complete(adapter.generate(request))
        except RuntimeError:
            resp = asyncio.run(adapter.generate(request))

        return {
            "output": resp.output,
            "tokenUsage": {
                "total": resp.token_usage.total_tokens if resp.token_usage else 0,
                "prompt": resp.token_usage.prompt_tokens if resp.token_usage else 0,
                "completion": resp.token_usage.completion_tokens if resp.token_usage else 0,
            },
            "latencyMs": resp.latency_ms,
            "metadata": resp.metadata,
        }
    except Exception as e:
        return {
            "error": str(e),
            "output": f"Error executing assistant: {e}",
        }

