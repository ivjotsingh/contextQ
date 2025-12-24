"""Anthropic Claude LLM implementation."""

import logging
from collections.abc import AsyncGenerator

import httpx
from anthropic import APIError, AsyncAnthropic, RateLimitError

from config import get_settings

from .base import BaseLLMService, LLMError

logger = logging.getLogger(__name__)


class AnthropicService(BaseLLMService):
    """Claude LLM service via Anthropic API."""

    def __init__(self, model: str | None = None) -> None:
        settings = get_settings()
        self.model = model or settings.llm_model
        self.settings = settings

        self._client = AsyncAnthropic(
            api_key=settings.anthropic_api_key,
            timeout=httpx.Timeout(timeout=60.0, connect=10.0),
        )

    async def generate(
        self,
        prompt: str,
        system: str,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Generate a response using Claude."""
        try:
            response = await self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens or self.settings.llm_max_tokens,
                temperature=temperature
                if temperature is not None
                else self.settings.llm_temperature,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text

        except RateLimitError as e:
            logger.warning("Rate limit: %s", e)
            raise LLMError("Rate limit exceeded. Please try again.") from e
        except APIError as e:
            logger.error("API error: %s", e)
            raise LLMError(f"LLM error: {e}") from e

    async def stream(
        self,
        prompt: str,
        system: str,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream a response using Claude."""
        try:
            async with self._client.messages.stream(
                model=self.model,
                max_tokens=max_tokens or self.settings.llm_max_tokens,
                temperature=temperature
                if temperature is not None
                else self.settings.llm_temperature,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                async for text in stream.text_stream:
                    yield text

        except RateLimitError as e:
            logger.warning("Rate limit during streaming: %s", e)
            raise LLMError("Rate limit exceeded.") from e
        except Exception as e:
            logger.error("Streaming failed: %s", e)
            raise LLMError(f"Streaming failed: {e}") from e

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
        """Generate structured JSON using Claude's tool_use."""
        try:
            response = await self._client.messages.create(
                model=model or self.settings.query_analysis_model,
                max_tokens=max_tokens or 1024,
                temperature=temperature if temperature is not None else 0,
                system=system,
                messages=[{"role": "user", "content": prompt}],
                tools=[
                    {
                        "name": tool_name,
                        "description": f"Structured output for {tool_name}",
                        "input_schema": tool_schema,
                    }
                ],
                tool_choice={"type": "tool", "name": tool_name},
            )

            for block in response.content:
                if block.type == "tool_use" and block.name == tool_name:
                    return block.input

            raise LLMError(f"Tool '{tool_name}' was not called")

        except RateLimitError as e:
            logger.warning("Rate limit: %s", e)
            raise LLMError("Rate limit exceeded.") from e
        except APIError as e:
            logger.error("API error: %s", e)
            raise LLMError(f"LLM error: {e}") from e
