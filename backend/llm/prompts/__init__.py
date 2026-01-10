"""LLM prompts for various use cases."""

from llm.prompts.assistant import ASSISTANT_SYSTEM_PROMPT
from llm.prompts.document_qa import DOCUMENT_QA_SYSTEM_PROMPT
from llm.prompts.query_analysis import (
    QUERY_ANALYSIS_PROMPT,
    QUERY_ANALYSIS_SCHEMA,
    QUERY_ANALYSIS_SYSTEM_PROMPT,
    QueryAnalysisResult,
)

__all__ = [
    "DOCUMENT_QA_SYSTEM_PROMPT",
    "ASSISTANT_SYSTEM_PROMPT",
    "QUERY_ANALYSIS_PROMPT",
    "QUERY_ANALYSIS_SCHEMA",
    "QUERY_ANALYSIS_SYSTEM_PROMPT",
    "QueryAnalysisResult",
]
