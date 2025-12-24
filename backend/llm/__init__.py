"""LLM module - unified interface for language model interactions.

Usage:
    from llm import LLMService, LLMError

    llm = LLMService()
    response = await llm.generate(prompt, system)

    async for chunk in llm.stream(prompt, system):
        print(chunk, end="")

Structure:
    - base.py: Abstract interface (BaseLLMService)
    - anthropic.py: Claude implementation (AnthropicService)
    - service.py: Alias to current provider (LLMService = AnthropicService)
"""

from llm.anthropic import AnthropicService
from llm.base import BaseLLMService, LLMError
from llm.prompts import (
    ASSISTANT_SYSTEM_PROMPT,
    DOCUMENT_QA_SYSTEM_PROMPT,
    QUERY_ANALYSIS_PROMPT,
)

# Default provider - can be swapped by changing this alias
LLMService = AnthropicService

__all__ = [
    "BaseLLMService",
    "LLMService",
    "LLMError",
    "AnthropicService",
    "DOCUMENT_QA_SYSTEM_PROMPT",
    "ASSISTANT_SYSTEM_PROMPT",
    "QUERY_ANALYSIS_PROMPT",
]
