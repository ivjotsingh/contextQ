"""Query analyzer service for intelligent query decomposition.

Detects when queries require cross-document reasoning and decomposes
them into targeted sub-queries for better retrieval.
"""

import asyncio
import logging
import json
from dataclasses import dataclass

from anthropic import AsyncAnthropic, APITimeoutError

from app.config import get_settings

# Timeout for query analysis (seconds)
ANALYSIS_TIMEOUT = 10.0

logger = logging.getLogger(__name__)


@dataclass
class QueryAnalysis:
    """Result of query analysis."""

    needs_decomposition: bool
    sub_queries: list[str]
    reasoning: str | None = None
    skip_rag: bool = False  # If True, this is a general question that doesn't need RAG


# Prompt for query analysis and decomposition
ANALYSIS_PROMPT = """You are a query analyzer for a document Q&A system. Analyze the user's question and determine:
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


class QueryAnalyzer:
    """Service for analyzing and decomposing complex queries."""

    def __init__(self) -> None:
        """Initialize query analyzer."""
        self.settings = get_settings()
        self.client = AsyncAnthropic(api_key=self.settings.anthropic_api_key)
        self.max_sub_queries = self.settings.max_sub_queries

    async def analyze(
        self,
        question: str,
        doc_count: int,
        document_names: list[str] | None = None,
    ) -> QueryAnalysis:
        """Analyze a query and determine if decomposition is needed.

        Args:
            question: User's question
            doc_count: Number of documents in the session
            document_names: Optional list of document filenames for context

        Returns:
            QueryAnalysis with decomposition decision and sub-queries
        """
        # Fast path: single document doesn't need decomposition
        if doc_count <= 1:
            logger.debug("Skipping decomposition: single document")
            return QueryAnalysis(
                needs_decomposition=False,
                sub_queries=[],
                reasoning="Single document - no cross-document reasoning needed",
            )

        # Fast path: very short questions are usually simple lookups
        if len(question.split()) < 4:
            logger.debug("Skipping decomposition: short question")
            return QueryAnalysis(
                needs_decomposition=False,
                sub_queries=[],
                reasoning="Short question - likely simple lookup",
            )

        # Use LLM to analyze the query (with timeout)
        try:
            doc_names_str = ", ".join(document_names) if document_names else f"{doc_count} documents"
            
            prompt = ANALYSIS_PROMPT.format(
                max_sub_queries=self.max_sub_queries,
                document_names=doc_names_str,
                question=question,
            )

            # Wrap in timeout to prevent hanging
            response = await asyncio.wait_for(
                self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=500,
                    temperature=0,
                    messages=[{"role": "user", "content": prompt}],
                ),
                timeout=ANALYSIS_TIMEOUT,
            )

            result_text = response.content[0].text.strip()
            
            # Parse JSON response
            # Handle potential markdown code blocks
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
                result_text = result_text.strip()

            result = json.loads(result_text)

            skip_rag = result.get("skip_rag", False)
            needs_decomposition = result.get("needs_decomposition", False)
            sub_queries = result.get("sub_queries", [])
            reasoning = result.get("reasoning", "")
            
            # If skip_rag is true, don't decompose
            if skip_rag:
                logger.info("Query classified as general (skip RAG): %s", reasoning[:100] if reasoning else "")
                return QueryAnalysis(
                    needs_decomposition=False,
                    sub_queries=[],
                    reasoning=reasoning,
                    skip_rag=True,
                )

            # SAFETY GUARDS
            # 1. Enforce max sub-queries limit
            if len(sub_queries) > self.max_sub_queries:
                logger.warning(
                    "Truncating sub-queries from %d to %d",
                    len(sub_queries),
                    self.max_sub_queries,
                )
                sub_queries = sub_queries[: self.max_sub_queries]

            # 2. Validate sub-queries are strings and not empty
            sub_queries = [
                sq.strip() for sq in sub_queries
                if isinstance(sq, str) and sq.strip()
            ]

            # 3. Limit sub-query length to prevent prompt injection
            max_subquery_length = 500
            sub_queries = [
                sq[:max_subquery_length] for sq in sub_queries
            ]

            # 4. If decomposition requested but no valid sub-queries, fall back
            if needs_decomposition and not sub_queries:
                logger.warning("Decomposition requested but no valid sub-queries, falling back")
                needs_decomposition = False

            # 5. Sanity check: sub-queries should be different from original
            # (prevents infinite loops or redundant queries)

            # Log the analysis result with sub-queries
            if needs_decomposition and sub_queries:
                logger.info(
                    "Query decomposition triggered: %d sub-queries generated",
                    len(sub_queries),
                )
                for i, sq in enumerate(sub_queries, 1):
                    logger.info("  Sub-query %d: %s", i, sq)
                logger.info("  Reasoning: %s", reasoning[:150] if reasoning else "none")
            else:
                logger.info(
                    "Query decomposition skipped: %s",
                    reasoning[:100] if reasoning else "standard retrieval",
                )

            return QueryAnalysis(
                needs_decomposition=needs_decomposition,
                sub_queries=sub_queries,
                reasoning=reasoning,
            )

        except json.JSONDecodeError as e:
            logger.warning("Failed to parse query analysis response: %s", e)
            return QueryAnalysis(
                needs_decomposition=False,
                sub_queries=[],
                reasoning=f"Parse error: {e}",
            )

        except asyncio.TimeoutError:
            logger.warning("Query analysis timed out after %.1fs, using standard retrieval", ANALYSIS_TIMEOUT)
            return QueryAnalysis(
                needs_decomposition=False,
                sub_queries=[],
                reasoning="Analysis timed out",
            )

        except APITimeoutError as e:
            logger.warning("Anthropic API timeout: %s", e)
            return QueryAnalysis(
                needs_decomposition=False,
                sub_queries=[],
                reasoning="API timeout",
            )

        except Exception as e:
            logger.warning("Query analysis failed, falling back to standard retrieval: %s", e)
            return QueryAnalysis(
                needs_decomposition=False,
                sub_queries=[],
                reasoning=f"Analysis error: {e}",
            )

