"""Prompt and schema for query analysis and decomposition."""

from pydantic import BaseModel, Field


class QueryAnalysisResult(BaseModel):
    """Structured output for query analysis."""

    skip_rag: bool = Field(
        description="True if question doesn't need document lookup (greetings, meta questions)"
    )
    needs_decomposition: bool = Field(
        description="True if question requires multiple document queries (comparison, cross-reference)"
    )
    reasoning: str = Field(description="Brief explanation of the decision")
    sub_queries: list[str] = Field(
        default_factory=list,
        description="Sub-queries if decomposition is needed, empty otherwise",
    )


# System prompt for the query analyzer
QUERY_ANALYSIS_SYSTEM_PROMPT = """You are a query analyzer for a document Q&A system.
Analyze user queries to determine if they need document lookup and if they span multiple documents."""

# User prompt template for query analysis
# Placeholders: {question}, {chat_history}, {max_sub_queries}
QUERY_ANALYSIS_PROMPT = """Analyze this user question for a document Q&A system.

User question: {question}

{chat_history_section}

Determine:
1. skip_rag (true/false)
   Set skip_rag=true ONLY for:
   - Simple greetings: "hi", "hello", "thanks"
   - Questions about the assistant itself: "what can you do", "who are you"
   
   Set skip_rag=false for EVERYTHING ELSE, including:
   - Any question about documents or their content
   - Any question that might be answered using uploaded documents
   - Questions about "how many", "what", "summarize", etc.
   
   When in doubt, set skip_rag=false.

2. needs_decomposition (true/false)
   Set true if the question spans MULTIPLE documents:
   - Comparisons: "compare", "difference", "vs"
   - Synthesis: "combine", "all documents", "both"
   - Cross-reference: mentions multiple document names
   
   If true, generate up to {max_sub_queries} sub-queries targeting specific documents."""


# JSON schema for structured output via tool_use (generated from Pydantic model)
QUERY_ANALYSIS_SCHEMA = QueryAnalysisResult.model_json_schema()
