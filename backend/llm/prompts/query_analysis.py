"""Prompt for query analysis and decomposition."""

QUERY_ANALYSIS_PROMPT = """You are a query analyzer for a document Q&A system. Analyze the user's question and determine:
1. If it's a GENERAL question that doesn't need document lookup (skip_rag=true)
2. If it requires information from multiple documents (needs_decomposition=true)

SKIP RAG (skip_rag=true) for:
- Questions about the assistant's capabilities: "what can you do", "how do you work", "help me"
- Greetings: "hello", "hi", "hey"
- Meta questions: "who are you", "what are you"
- General knowledge that wouldn't be in uploaded documents
- Conversational follow-ups that don't need document context

DECOMPOSITION RULES (only if skip_rag=false):
1. Only decompose if the question REQUIRES comparing, contrasting, or synthesizing information across multiple documents
2. Generate at most {max_sub_queries} sub-queries
3. Each sub-query should target specific information from a specific document type
4. Keep sub-queries simple and focused

SIGNALS THAT NEED DECOMPOSITION (needs_decomposition=true):
- Comparison questions: "compare", "difference", "vs", "between", "which one"
- Gap analysis: "missing", "lack", "don't have", "not in", "gaps"
- Synthesis: "combine", "together", "both", "all documents"
- Cross-reference: "based on X, what about Y", "according to A, does B"
- **OVERVIEW/SUMMARY requests**: "what are the documents about", "summarize all", "overview of documents", "what do I have", "list the documents", "content of all/X documents"
  - For overview questions, generate ONE sub-query per document like: "What is [document_name] about? Summarize its main content."

Available documents: {document_names}

User question: {question}

Respond with a JSON object:
{{
    "skip_rag": true/false,
    "needs_decomposition": true/false,
    "reasoning": "brief explanation of your decision",
    "sub_queries": ["sub-query 1", "sub-query 2"] // empty array if no decomposition needed or skip_rag is true. For overview questions, include one query per document.
}}

IMPORTANT: For questions asking about "all documents", "what are my documents about", "summarize everything", etc., you MUST set needs_decomposition=true and generate a sub-query for EACH document to ensure all are retrieved.

Only output the JSON, nothing else."""

