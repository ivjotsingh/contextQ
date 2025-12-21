"""LLM Service - unified interface for language model interactions.

Provides a model-agnostic interface for LLM operations. Currently supports Claude,
with architecture ready for multi-provider support.

Usage:
    from llm import LLMService

    # Current usage with Claude (default)
    llm = LLMService(model="claude-sonnet-4-20250514")
    response = await llm.generate(prompt, system)

    # Or later with different model (future)
    # llm = LLMService(model="gpt-4")  # Would use OpenAI client
"""

import logging
from typing import AsyncGenerator

from anthropic import APIError, AsyncAnthropic, RateLimitError

from config import get_settings

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Raised when LLM generation fails."""

    pass


class LLMService:
    """Unified LLM service supporting multiple providers.

    Currently implements Claude via Anthropic API. Architecture supports
    future expansion to other providers (OpenAI, etc.) based on model name.

    Args:
        model: Model identifier. Currently supports Claude models.
               Future: "gpt-4" would route to OpenAI client.
    """

    def __init__(self, model: str | None = None) -> None:
        """Initialize LLM service.

        Args:
            model: Model name to use. Defaults to settings.llm_model.
        """
        self.settings = get_settings()
        self.model = model or self.settings.llm_model

        # Route to appropriate provider based on model name
        # Currently only Claude is supported
        # Future: Add OpenAI, Gemini, etc. based on model prefix
        if self._is_claude_model(self.model):
            self._client = AsyncAnthropic(api_key=self.settings.anthropic_api_key)
            self._provider = "anthropic"
        else:
            # For now, default to Claude for unknown models
            # Future: raise ValueError or route to other providers
            logger.warning(
                "Unknown model '%s', defaulting to Anthropic client", self.model
            )
            self._client = AsyncAnthropic(api_key=self.settings.anthropic_api_key)
            self._provider = "anthropic"

    def _is_claude_model(self, model: str) -> bool:
        """Check if model is a Claude model."""
        return model.startswith("claude")

    async def generate(
        self,
        prompt: str,
        system: str,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Generate a response from the LLM.

        Args:
            prompt: User message/prompt.
            system: System instructions.
            temperature: Sampling temperature (0-1). Defaults to settings.
            max_tokens: Maximum tokens to generate. Defaults to settings.

        Returns:
            Generated text response.

        Raises:
            LLMError: If generation fails.
        """
        if self._provider == "anthropic":
            return await self._generate_anthropic(
                prompt, system, temperature, max_tokens
            )
        else:
            raise LLMError(f"Unsupported provider: {self._provider}")

    async def stream(
        self,
        prompt: str,
        system: str,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream a response from the LLM.

        Args:
            prompt: User message/prompt.
            system: System instructions.
            temperature: Sampling temperature (0-1). Defaults to settings.
            max_tokens: Maximum tokens to generate. Defaults to settings.

        Yields:
            Text chunks as they are generated.

        Raises:
            LLMError: If streaming fails.
        """
        if self._provider == "anthropic":
            async for chunk in self._stream_anthropic(
                prompt, system, temperature, max_tokens
            ):
                yield chunk
        else:
            raise LLMError(f"Unsupported provider: {self._provider}")

    async def _generate_anthropic(
        self,
        prompt: str,
        system: str,
        temperature: float | None,
        max_tokens: int | None,
    ) -> str:
        """Generate using Anthropic Claude API."""
        try:
            response = await self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens or self.settings.llm_max_tokens,
                temperature=(
                    temperature
                    if temperature is not None
                    else self.settings.llm_temperature
                ),
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except RateLimitError as e:
            logger.warning("Claude rate limit hit: %s", e)
            raise LLMError("Rate limit exceeded. Please try again in a moment.") from e
        except APIError as e:
            logger.error("Claude API error: %s", e)
            raise LLMError(f"LLM service error: {e}") from e
        except Exception as e:
            logger.error("Unexpected error during LLM generation: %s", e)
            raise LLMError(f"Failed to generate answer: {e}") from e

    async def _stream_anthropic(
        self,
        prompt: str,
        system: str,
        temperature: float | None,
        max_tokens: int | None,
    ) -> AsyncGenerator[str, None]:
        """Stream using Anthropic Claude API."""
        try:
            async with self._client.messages.stream(
                model=self.model,
                max_tokens=max_tokens or self.settings.llm_max_tokens,
                temperature=(
                    temperature
                    if temperature is not None
                    else self.settings.llm_temperature
                ),
                system=system,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except RateLimitError as e:
            logger.warning("Claude rate limit hit during streaming: %s", e)
            raise LLMError("Rate limit exceeded. Please try again.") from e
        except Exception as e:
            logger.error("Streaming generation failed: %s", e)
            raise LLMError(f"Streaming failed: {e}") from e

