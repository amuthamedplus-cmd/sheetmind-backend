"""
RAG (Retrieval Augmented Generation) system for large spreadsheets.

Enables semantic search across sheets with 500+ rows by:
1. Converting rows to vector embeddings
2. Storing in Chroma vector database
3. Retrieving only relevant rows for AI queries

Supports Google embeddings with OpenRouter API-based fallback.
"""

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from langchain_core.documents import Document

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy imports for embeddings (avoid import errors if not installed)
# ---------------------------------------------------------------------------

_google_embeddings = None
_local_embeddings = None
_chroma_client = None


def _get_google_embeddings():
    """Lazy load Google embeddings."""
    global _google_embeddings
    if _google_embeddings is None:
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            _google_embeddings = GoogleGenerativeAIEmbeddings(
                model="models/embedding-001",
                google_api_key=settings.GEMINI_API_KEY,
            )
            logger.info("Initialized Google embeddings")
        except Exception as e:
            logger.warning(f"Failed to initialize Google embeddings: {e}")
            return None
    return _google_embeddings


def _get_openrouter_embeddings():
    """Lazy load OpenAI-compatible embeddings via OpenRouter (fallback)."""
    global _local_embeddings
    if _local_embeddings is None:
        try:
            from langchain_openai import OpenAIEmbeddings
            _local_embeddings = OpenAIEmbeddings(
                model="openai/text-embedding-3-small",
                openai_api_key=settings.OPENROUTER_API_KEY,
                openai_api_base="https://openrouter.ai/api/v1",
            )
            logger.info("Initialized OpenRouter embeddings (text-embedding-3-small)")
        except Exception as e:
            logger.warning(f"Failed to initialize OpenRouter embeddings: {e}")
            return None
    return _local_embeddings


def _get_embeddings():
    """Get the best available embeddings model."""
    # Try Google first
    if settings.GEMINI_API_KEY:
        embeddings = _get_google_embeddings()
        if embeddings:
            return embeddings, "google"

    # Fall back to OpenRouter embeddings
    if settings.OPENROUTER_API_KEY:
        embeddings = _get_openrouter_embeddings()
        if embeddings:
            return embeddings, "openrouter"

    raise RuntimeError("No embedding model available. Provide GEMINI_API_KEY or OPENROUTER_API_KEY.")


# ---------------------------------------------------------------------------
# Chroma Directory Setup
# ---------------------------------------------------------------------------

CHROMA_DIR = Path(settings.CHROMA_PERSIST_DIR)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# SheetRAG Class
# ---------------------------------------------------------------------------

class SheetRAG:
    """RAG system for spreadsheet data."""

    # Maximum number of vectorstores to keep in memory
    MAX_CACHED = 10

    def __init__(self):
        """Initialize the RAG system."""
        self._vectorstores: Dict[str, any] = {}
        self._sheet_hashes: Dict[str, str] = {}  # sheet_name -> current hash
        self._embeddings = None
        self._embedding_type = None

    def _ensure_embeddings(self):
        """Ensure embeddings are loaded."""
        if self._embeddings is None:
            self._embeddings, self._embedding_type = _get_embeddings()
        return self._embeddings

    def _get_sheet_hash(self, cells: Dict) -> str:
        """Generate a hash of sheet data to detect changes."""
        content = json.dumps(cells, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def is_stale(self, cells: Dict, sheet_name: str) -> bool:
        """Check if the current index is outdated for this sheet data."""
        current_hash = self._get_sheet_hash(cells)
        stored_hash = self._sheet_hashes.get(sheet_name)
        return stored_hash is not None and stored_hash != current_hash

    def _cleanup_old_versions(self, sheet_name: str, keep_collection: str) -> None:
        """Remove old index versions for a sheet (memory + disk)."""
        prefix = sheet_name.replace(" ", "_") + "_"
        old_keys = [
            k for k in self._vectorstores
            if k.startswith(prefix) and k != keep_collection
        ]

        for key in old_keys:
            del self._vectorstores[key]
            # Remove Chroma directory from disk
            old_path = CHROMA_DIR / key
            if old_path.exists():
                import shutil
                try:
                    shutil.rmtree(old_path)
                    logger.info(f"Cleaned up old index: {key}")
                except Exception as e:
                    logger.warning(f"Failed to delete old index dir {key}: {e}")

    def _evict_if_needed(self) -> None:
        """Evict oldest vectorstores if we exceed MAX_CACHED."""
        while len(self._vectorstores) > self.MAX_CACHED:
            oldest_key = next(iter(self._vectorstores))
            del self._vectorstores[oldest_key]
            logger.info(f"Evicted cached vectorstore: {oldest_key}")

    def _cells_to_documents(self, cells: Dict, sheet_name: str) -> List[Document]:
        """
        Convert spreadsheet cells to LangChain documents.
        Each row becomes a document with metadata.
        """
        cell_pattern = re.compile(r"^([A-Z]+)(\d+)$")

        # Parse cells into rows and extract headers
        rows: Dict[int, Dict[str, str]] = {}
        headers: Dict[str, str] = {}

        for cell_ref, value in cells.items():
            match = cell_pattern.match(cell_ref)
            if not match:
                continue

            col = match.group(1)
            row_num = int(match.group(2))

            if row_num == 1:
                headers[col] = str(value)
            else:
                if row_num not in rows:
                    rows[row_num] = {}
                rows[row_num][col] = str(value)

        # Sort columns for consistent ordering
        sorted_cols = sorted(headers.keys(), key=lambda c: (len(c), c))

        # Create documents from rows
        documents = []
        for row_num, row_data in rows.items():
            # Create readable text representation
            parts = []
            for col in sorted_cols:
                header = headers.get(col, col)
                value = row_data.get(col, "")
                if value:
                    parts.append(f"{header}: {value}")

            if parts:
                text = f"Row {row_num}: " + " | ".join(parts)
                doc = Document(
                    page_content=text,
                    metadata={
                        "sheet": sheet_name,
                        "row": row_num,
                        "cells": json.dumps(row_data),
                    }
                )
                documents.append(doc)

        return documents

    def index_sheet(
        self,
        cells: Dict,
        sheet_name: str,
        force_reindex: bool = False
    ) -> Dict:
        """
        Index a sheet's data for semantic search.

        Args:
            cells: Dictionary of cell references to values
            sheet_name: Name of the sheet
            force_reindex: If True, reindex even if unchanged

        Returns:
            Status dict with indexed row count and embedding type
        """
        try:
            from langchain_community.vectorstores import Chroma
        except ImportError:
            return {"error": "chromadb not installed", "indexed": 0}

        sheet_hash = self._get_sheet_hash(cells)
        collection_name = f"{sheet_name}_{sheet_hash}".replace(" ", "_")

        # Check if already indexed with same data
        if collection_name in self._vectorstores and not force_reindex:
            return {
                "status": "already_indexed",
                "collection": collection_name,
                "embedding_type": self._embedding_type,
            }

        # Clean up old versions of this sheet's index before creating new one
        self._cleanup_old_versions(sheet_name, keep_collection=collection_name)

        # Convert to documents
        documents = self._cells_to_documents(cells, sheet_name)

        if not documents:
            return {"status": "no_data", "indexed": 0}

        # Get embeddings
        try:
            embeddings = self._ensure_embeddings()
        except RuntimeError as e:
            return {"error": str(e), "indexed": 0}

        # Create vector store
        try:
            persist_path = str(CHROMA_DIR / collection_name)
            vectorstore = Chroma.from_documents(
                documents=documents,
                embedding=embeddings,
                persist_directory=persist_path,
                collection_name=collection_name,
            )

            self._vectorstores[collection_name] = vectorstore
            self._sheet_hashes[sheet_name] = sheet_hash
            self._evict_if_needed()

            logger.info(f"Indexed {len(documents)} rows from '{sheet_name}' using {self._embedding_type} embeddings")

            return {
                "status": "indexed",
                "collection": collection_name,
                "indexed": len(documents),
                "embedding_type": self._embedding_type,
            }

        except Exception as e:
            logger.error(f"Failed to index sheet: {e}")
            return {"error": str(e), "indexed": 0}

    def search(
        self,
        query: str,
        sheet_name: str,
        cells: Dict,
        k: int = None,
    ) -> List[Dict]:
        """
        Semantic search for relevant rows.

        Args:
            query: Natural language search query
            sheet_name: Sheet to search in
            cells: Sheet data (for auto-indexing if needed)
            k: Number of results to return (default from settings)

        Returns:
            List of matching rows with scores
        """
        if k is None:
            k = settings.RAG_RESULTS_COUNT

        # Ensure indexed
        sheet_hash = self._get_sheet_hash(cells)
        collection_name = f"{sheet_name}_{sheet_hash}".replace(" ", "_")

        if collection_name not in self._vectorstores:
            result = self.index_sheet(cells, sheet_name)
            if "error" in result:
                logger.warning(f"RAG indexing failed: {result['error']}")
                return []

        vectorstore = self._vectorstores.get(collection_name)
        if not vectorstore:
            return []

        try:
            # Search with scores
            results = vectorstore.similarity_search_with_score(query, k=k)

            # Format results
            formatted = []
            for doc, score in results:
                try:
                    cell_data = json.loads(doc.metadata.get("cells", "{}"))
                except (json.JSONDecodeError, TypeError):
                    cell_data = {}
                formatted.append({
                    "row": doc.metadata.get("row"),
                    "content": doc.page_content,
                    "cells": cell_data,
                    "score": float(score),
                    "sheet": doc.metadata.get("sheet"),
                })

            return formatted

        except Exception as e:
            logger.error(f"RAG search failed: {e}")
            return []

    def search_multi_sheet(
        self,
        query: str,
        sheets: Dict[str, Dict],  # {sheet_name: cells}
        k: int = None,
    ) -> List[Dict]:
        """
        Search across multiple sheets.

        Args:
            query: Search query
            sheets: Dictionary mapping sheet names to their cells
            k: Results per sheet

        Returns:
            Combined results from all sheets, sorted by score
        """
        if k is None:
            k = settings.RAG_RESULTS_COUNT

        all_results = []

        for sheet_name, cells in sheets.items():
            results = self.search(query, sheet_name, cells, k=k)
            all_results.extend(results)

        # Sort by score (lower is better for Chroma) and return top results
        all_results.sort(key=lambda x: x["score"])
        return all_results[:k]

    def get_context_for_query(
        self,
        query: str,
        cells: Dict,
        sheet_name: str,
        max_rows: int = None,
    ) -> Tuple[str, List[int], bool]:
        """
        Get relevant context for an AI query.

        Instead of sending all rows, returns only semantically relevant rows
        for large sheets.

        Args:
            query: User's question
            cells: Sheet data
            sheet_name: Sheet name
            max_rows: Maximum rows to include

        Returns:
            (context_string, list_of_row_numbers, used_rag)
        """
        if max_rows is None:
            max_rows = settings.RAG_RESULTS_COUNT

        # Count rows
        row_count = len(set(
            int(re.match(r"[A-Z]+(\d+)", ref).group(1))
            for ref in cells.keys()
            if re.match(r"[A-Z]+(\d+)", ref)
        ))

        # For small sheets, return all data (no RAG needed)
        if row_count <= settings.RAG_THRESHOLD_ROWS:
            return self._format_all_cells(cells, sheet_name), [], False

        # For large sheets, detect stale index and log re-indexing
        if self.is_stale(cells, sheet_name):
            logger.info(f"Sheet '{sheet_name}' data changed — re-indexing for RAG")

        # For large sheets, use RAG (auto-indexes if needed via search → index_sheet)
        results = self.search(query, sheet_name, cells, k=max_rows)

        if not results:
            # RAG failed, fall back to all data with warning
            logger.warning(f"RAG search returned no results, using full context")
            return self._format_all_cells(cells, sheet_name), [], False

        # Build context from relevant rows
        lines = [
            f"Relevant rows from '{sheet_name}' (semantic search - {len(results)} most relevant of {row_count} total):",
            ""
        ]
        row_numbers = []

        for r in results:
            lines.append(r["content"])
            row_numbers.append(r["row"])

        lines.append("")
        lines.append(f"Note: Showing {len(results)} most relevant rows via RAG semantic search.")

        return "\n".join(lines), row_numbers, True

    def _format_all_cells(self, cells: Dict, sheet_name: str) -> str:
        """Format all cells as context string (for small sheets)."""
        docs = self._cells_to_documents(cells, sheet_name)

        # Limit to reasonable size
        max_docs = min(len(docs), 200)

        lines = [f"All data from '{sheet_name}' ({len(docs)} rows):"]
        for doc in docs[:max_docs]:
            lines.append(doc.page_content)

        if len(docs) > max_docs:
            lines.append(f"... and {len(docs) - max_docs} more rows")

        return "\n".join(lines)

    def clear_index(self, sheet_name: str = None):
        """
        Clear indexed data (memory + disk).

        Args:
            sheet_name: If provided, clear only this sheet's index.
                       If None, clear all indexes.
        """
        import shutil

        if sheet_name:
            prefix = sheet_name.replace(" ", "_") + "_"
            keys_to_remove = [k for k in self._vectorstores if k.startswith(prefix)]
            for key in keys_to_remove:
                del self._vectorstores[key]
                old_path = CHROMA_DIR / key
                if old_path.exists():
                    try:
                        shutil.rmtree(old_path)
                    except Exception:
                        pass
                logger.info(f"Cleared index for {key}")
            self._sheet_hashes.pop(sheet_name, None)
        else:
            # Clear all
            for key in list(self._vectorstores.keys()):
                old_path = CHROMA_DIR / key
                if old_path.exists():
                    try:
                        shutil.rmtree(old_path)
                    except Exception:
                        pass
            self._vectorstores.clear()
            self._sheet_hashes.clear()
            logger.info("Cleared all RAG indexes")


# ---------------------------------------------------------------------------
# RAG Tools for LangChain Agent
# ---------------------------------------------------------------------------

# Singleton instance
_rag_instance: Optional[SheetRAG] = None


def get_rag() -> SheetRAG:
    """Get or create the RAG singleton."""
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = SheetRAG()
    return _rag_instance


# Import tools module to add RAG tools
def _create_rag_tools():
    """Create RAG tools and add them to langchain_tools."""
    from langchain.tools import tool
    from app.services import langchain_tools

    @tool
    def semantic_search(query: str, max_results: int = 30) -> str:
        """
        Search the spreadsheet using natural language.
        Finds rows that are semantically similar to your query,
        even if they don't contain the exact words.

        Examples:
            - "unhappy customers" finds "disappointed", "frustrated", "angry"
            - "delivery problems" finds "shipping delayed", "package lost"
            - "high value orders" finds orders with large amounts

        Args:
            query: Natural language description of what you're looking for
            max_results: Maximum number of rows to return (default 30)

        Returns:
            JSON array of matching rows with relevance scores
        """
        context = langchain_tools.get_sheet_context()
        if not context or "cells" not in context:
            return '{"error": "No sheet data available for RAG search"}'

        sheet_name = context.get("sheetName", "Sheet1")
        cells = context["cells"]

        rag = get_rag()
        results = rag.search(query, sheet_name, cells, k=max_results)

        if not results:
            return '{"results": [], "message": "No matching rows found"}'

        return json.dumps({
            "results": results,
            "count": len(results),
            "query": query,
        }, indent=2)

    @tool
    def find_similar_rows(row_number: int, max_results: int = 10) -> str:
        """
        Find rows similar to a specific row.
        Useful for finding duplicates or related entries.

        Args:
            row_number: The row to find similar entries to
            max_results: Maximum number of similar rows to return

        Returns:
            JSON array of similar rows (excluding the source row)
        """
        context = langchain_tools.get_sheet_context()
        if not context or "cells" not in context:
            return '{"error": "No sheet data available"}'

        cells = context["cells"]
        sheet_name = context.get("sheetName", "Sheet1")

        # Build the row content
        row_content = []
        cell_pattern = re.compile(r"^([A-Z]+)(\d+)$")

        for cell_ref, value in cells.items():
            match = cell_pattern.match(cell_ref)
            if match and int(match.group(2)) == row_number:
                row_content.append(str(value))

        if not row_content:
            return f'{{"error": "Row {row_number} not found"}}'

        query = " ".join(row_content)

        rag = get_rag()
        results = rag.search(query, sheet_name, cells, k=max_results + 1)

        # Remove the source row itself
        results = [r for r in results if r["row"] != row_number]

        return json.dumps({
            "similar_to_row": row_number,
            "results": results[:max_results],
            "count": len(results[:max_results]),
        }, indent=2)

    # Add to langchain_tools
    langchain_tools.RAG_TOOLS.extend([semantic_search, find_similar_rows])
    langchain_tools.ALL_TOOLS = langchain_tools.SHEET_TOOLS + langchain_tools.RAG_TOOLS

    return [semantic_search, find_similar_rows]


# Initialize RAG tools when this module is imported
try:
    _rag_tools = _create_rag_tools()
except Exception as e:
    logger.warning(f"Failed to create RAG tools: {e}")
    _rag_tools = []
