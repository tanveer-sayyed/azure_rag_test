"""System Under Test — calls the live RAG engine and returns a result dict."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src/webapp"))

from rag_engine import RagEngine

_engine: RagEngine | None = None


def run_system(input: str) -> dict:
    """Call the RAG engine and return output with retrieval context."""
    global _engine
    if _engine is None:
        _engine = RagEngine()
    answer, combined_context = _engine.ask_question(input)
    chunks = [c for c in combined_context.split("\n\n") if c.strip()]
    return {"output": answer, "retrieval_context": chunks}
