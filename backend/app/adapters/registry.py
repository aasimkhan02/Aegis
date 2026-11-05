"""Lightweight adapter registry and factory for Aegis assistant adapters."""

from typing import Any, Callable, Type
from app.adapters.base import BaseAssistantAdapter
from app.adapters.exceptions import AdapterConfigError
from app.adapters.http_api import HttpApiAssistantAdapter
from app.adapters.mock import MockAssistantAdapter
from app.adapters.ollama import OllamaAssistantAdapter

_REGISTRY: dict[str, Type[BaseAssistantAdapter]] = {
    "mock": MockAssistantAdapter,
    "ollama": OllamaAssistantAdapter,
    "http": HttpApiAssistantAdapter,
}


def register_adapter(name: str, adapter_cls: Type[BaseAssistantAdapter]) -> None:
    """Register a custom assistant adapter class."""
    _REGISTRY[name.lower().strip()] = adapter_cls


def get_adapter(
    provider: str,
    base_url: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    **kwargs: Any,
) -> BaseAssistantAdapter:
    """Factory to instantiate an adapter based on provider name.

    Args:
        provider: Provider name ('mock', 'ollama', or 'http').
        base_url: Optional base endpoint URL.
        model: Optional model name.
        api_key: Optional API key (for HTTP API).
        **kwargs: Additional parameters passed to the adapter constructor.

    Returns:
        BaseAssistantAdapter: Initialized adapter instance.

    Raises:
        AdapterConfigError: If provider is unrecognized.
    """
    key = provider.lower().strip()
    adapter_cls = _REGISTRY.get(key)
    if not adapter_cls:
        available = ", ".join(sorted(_REGISTRY.keys()))
        raise AdapterConfigError(
            f"Unknown assistant provider {provider!r}. Available providers: {available}",
            provider=provider,
        )

    if key == "mock":
        return MockAssistantAdapter(model=model or "mock-gpt-v1", **kwargs)
    elif key == "ollama":
        return OllamaAssistantAdapter(base_url=base_url, model=model, **kwargs)
    elif key == "http":
        return HttpApiAssistantAdapter(
            base_url=base_url,
            api_key=api_key,
            model=model,
            **kwargs,
        )
    else:
        return adapter_cls(model=model, **kwargs)

