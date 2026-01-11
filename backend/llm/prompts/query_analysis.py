"""Prompt and schema for query analysis with query expansion."""

from pydantic import BaseModel, Field


class QueryAnalysisResult(BaseModel):
    """Structured output for query analysis."""

    skip_rag: bool = Field(
        description="True if question doesn't need document lookup (greetings, meta questions about assistant)"
    )
    expanded_query: str = Field(
        description="Self-contained query with context expanded. Used for vector search and LLM context."
    )
    reasoning: str = Field(description="Brief explanation of the decision")


# System prompt for the query analyzer
QUERY_ANALYSIS_SYSTEM_PROMPT = """You are a query analyzer for a document Q&A system.
Your job is to:
1. Determine if a question needs document lookup (skip_rag)
2. If needed, expand context-dependent questions into self-contained queries

The expanded query is used for both vector similarity search and LLM context."""

# User prompt template for query analysis
QUERY_ANALYSIS_PROMPT = """Analyze this user question for a document Q&A system.

User question: {question}

{chat_history_section}

Determine:

1. skip_rag (true/false)
   Set skip_rag=true for:
   - Simple greetings: "hi", "hello", "thanks"
   - Questions about the assistant itself: "what can you do", "who are you"
   - System meta questions: "how many documents uploaded", "list my documents", "what files do I have"
     (These are about the SYSTEM, not about document CONTENT - they should be answered by the assistant)
   
   Set skip_rag=false for:
   - Questions about document CONTENT: "what does the resume say", "summarize the report"
   - Any question that needs to search INSIDE documents
   - Follow-up questions about document content
   
   KEY DISTINCTION:
   - "How many documents?" → skip_rag=true (system info)
   - "What is in the documents?" → skip_rag=false (content search)
   
   When in doubt, set skip_rag=false.

2. expanded_query (string)
   Create a self-contained query by expanding any context-dependent references.
   
   IMPORTANT: The expanded_query must be self-contained - it should NOT rely on conversation context.
   
   Rules:
   - If the question is context-dependent (pronouns, references, follow-ups), EXPAND it to be self-contained
   - Use conversation context to resolve vague references
   - Keep it concise but complete (aim for 10-50 words)
   - If the question is already clear and self-contained, keep it as is
   
   Examples:
   - "now?" after discussing document count → "How many documents are currently uploaded?"
   - "what about that?" after discussing pricing → "What is the pricing information?"
   - "compare A and B" → "Comparison of pricing, features, and differences between A and B"
   - "tell me about the resume" → Keep as is (already clear)
   - "what are his skills?" → "What are the skills and qualifications listed in the resume?"
   - "thanks for that!" → "Thank you for that information" (expanded for context)"""


# JSON schema for structured output via tool_use (generated from Pydantic model)
QUERY_ANALYSIS_SCHEMA = QueryAnalysisResult.model_json_schema()
