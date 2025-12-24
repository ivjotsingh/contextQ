"""Prompt and schema for query analysis and decomposition."""

# System prompt for the query analyzer
QUERY_ANALYSIS_SYSTEM_PROMPT = """You are a query analyzer for a document Q&A system.
Analyze user queries to determine if they need document lookup and if they span multiple documents."""

# User prompt template for query analysis
# Placeholders: {question}, {chat_history}, {max_sub_queries}
QUERY_ANALYSIS_PROMPT = """Analyze this user question for a document Q&A system.

User question: {question}

{chat_history_section}

Determine:
1. If this is a GENERAL question that doesn't need document lookup (skip_rag=true)
   - Greetings: "hello", "hi", "hey", "thanks"
   - Meta questions: "what can you do", "who are you", "help me"
   - General knowledge that wouldn't be in uploaded documents

2. If it requires information from MULTIPLE documents (needs_decomposition=true)
   Based on the question and chat history, detect:
   - Comparison: "compare", "difference", "vs", "between", "which one"
   - Synthesis: "combine", "together", "both", "all documents"
   - Overview: "summarize all", "overview of documents"
   - Cross-reference: mentions multiple document names or topics
   
   If decomposition needed, generate up to {max_sub_queries} sub-queries.
   Each sub-query should target a specific document or topic mentioned."""


# JSON schema for structured output via tool_use
QUERY_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "skip_rag": {
            "type": "boolean",
            "description": "True if question doesn't need document lookup (greetings, meta questions)",
        },
        "needs_decomposition": {
            "type": "boolean",
            "description": "True if question requires multiple document queries (comparison, cross-reference)",
        },
        "reasoning": {
            "type": "string",
            "description": "Brief explanation of the decision",
        },
        "sub_queries": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Sub-queries if decomposition is needed, empty otherwise",
        },
    },
    "required": ["skip_rag", "needs_decomposition", "reasoning", "sub_queries"],
}
