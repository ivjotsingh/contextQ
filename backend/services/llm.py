"""LLM service re-exports for services module.

This module re-exports from the llm/ package for convenience within services.
The primary LLM module is at llm/.
"""

# Re-export from llm package
from llm.service import LLMService as LLMClient, LLMError

__all__ = ["LLMClient", "LLMError"]

