"""Prompt and schema for query analysis and decomposition."""

# System prompt for the query analyzer
QUERY_ANALYSIS_SYSTEM_PROMPT = "You are a query analyzer for a document Q&A system."

# User prompt template for query analysis
# Placeholders: {doc_names_str}, {question}, {max_sub_queries}
QUERY_ANALYSIS_PROMPT = """Analyze this user question for a document Q&A system.

Available documents: {doc_names_str}
User question: {question}

Determine:
1. If this is a GENERAL question that doesn't need document lookup (skip_rag=true)
   - Greetings: "hello", "hi", "hey"
   - Meta questions: "what can you do", "who are you", "help me"
   - General knowledge that wouldn't be in uploaded documents

2. If it requires information from multiple documents (needs_decomposition=true)
   - Comparison: "compare", "difference", "vs", "between", "which one"
   - Synthesis: "combine", "together", "both", "all documents"
   - Overview: "what are the documents about", "summarize all", "overview"
   - Cross-reference: "based on X, what about Y"
   - If yes, generate up to {max_sub_queries} sub-queries targeting specific documents
   - For overview questions, generate ONE sub-query per document"""


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
            "description": "True if question requires multiple document queries (comparison, overview)",
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
