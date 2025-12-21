"""LLM module - unified interface for language model interactions.

Usage:
    from llm import LLMService, LLMError

    # Create service with specific model
    llm = LLMService(model="claude-sonnet-4-20250514")

    # Generate response
    response = await llm.generate(prompt, system)

    # Stream response
    async for chunk in llm.stream(prompt, system):
        print(chunk, end="")

    # Or later with different model (future)
    # llm = LLMService(model="gpt-4")  # Would use OpenAI client
"""

from llm.service import LLMService, LLMError
from llm.prompts import (
    DOCUMENT_QA_SYSTEM_PROMPT,
    ASSISTANT_SYSTEM_PROMPT,
    QUERY_ANALYSIS_PROMPT,
)

__all__ = [
    "LLMService",
    "LLMError",
    "DOCUMENT_QA_SYSTEM_PROMPT",
    "ASSISTANT_SYSTEM_PROMPT",
    "QUERY_ANALYSIS_PROMPT",
]

