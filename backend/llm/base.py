"""Base LLM service interface.

Defines the contract that all LLM providers must implement.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator


class LLMError(Exception):
    """Raised when LLM generation fails."""


class BaseLLMService(ABC):
    """Abstract base class for LLM services.

    All LLM providers (Anthropic, OpenAI, etc.) must implement these methods.
    """

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system: str,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Generate a single response.

        Args:
            prompt: User message.
            system: System instructions.
            temperature: Sampling temperature (0-1).
            max_tokens: Maximum tokens to generate.

        Returns:
            Generated text.
        """

    @abstractmethod
    async def stream(
        self,
        prompt: str,
        system: str,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream a response.

        Args:
            prompt: User message.
            system: System instructions.
            temperature: Sampling temperature (0-1).
            max_tokens: Maximum tokens to generate.

        Yields:
            Text chunks as they are generated.
        """

    @abstractmethod
    async def generate_structured_output(
        self,
        prompt: str,
        system: str,
        tool_name: str,
        tool_schema: dict,
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict:
        """Generate structured JSON output using tool/function calling.

        Args:
            prompt: User message.
            system: System instructions.
            tool_name: Name of the tool.
            tool_schema: JSON schema for the output.
            model: Override model name.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens.

        Returns:
            Parsed JSON matching the schema.
        """
