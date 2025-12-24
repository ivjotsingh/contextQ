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
