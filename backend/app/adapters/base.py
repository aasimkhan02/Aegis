"""Common base interface for all Aegis assistant adapters."""

from abc import ABC, abstractmethod

from app.schemas.adapter import AssistantResponse, ConversationRequest, Message


class BaseAssistantAdapter(ABC):
    """Abstract base class that all assistant adapters must implement."""

    provider_name: str = "base"

    def __init__(self, model: str | None = None) -> None:
        self.model = model or "default"

    @abstractmethod
    async def generate(self, request: ConversationRequest) -> AssistantResponse:
        """Asynchronously process a conversation request and return a standardized response.

        Args:
            request: Standardized ConversationRequest containing messages and options.

        Returns:
            AssistantResponse: Standardized response with output, usage, latency, etc.

        Raises:
            AdapterError: If an error occurs during invocation.
        """
        pass

    def _prepare_messages(self, request: ConversationRequest) -> list[Message]:
        """Combine optional system_prompt with request.messages if appropriate."""
        messages = list(request.messages)
        if request.system_prompt:
            # Check if there is already a system message at index 0
            if not messages or messages[0].role != "system":
                messages.insert(0, Message(role="system", content=request.system_prompt))
        return messages

