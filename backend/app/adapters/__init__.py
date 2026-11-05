"""Assistant adapters package for Aegis."""

from app.adapters.base import BaseAssistantAdapter
from app.adapters.exceptions import (
    AdapterConfigError,
    AdapterConnectionError,
    AdapterError,
    AdapterResponseError,
)
from app.adapters.http_api import HttpApiAssistantAdapter
from app.adapters.mock import MockAssistantAdapter
from app.adapters.ollama import OllamaAssistantAdapter
from app.adapters.registry import get_adapter, register_adapter

__all__ = [
    "BaseAssistantAdapter",
    "MockAssistantAdapter",
    "OllamaAssistantAdapter",
    "HttpApiAssistantAdapter",
    "get_adapter",
    "register_adapter",
    "AdapterError",
    "AdapterConnectionError",
    "AdapterResponseError",
    "AdapterConfigError",
]

