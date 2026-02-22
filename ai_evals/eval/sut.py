"""System Under Test — calls the live RAG engine and returns a result dict."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src/webapp"))

from rag_engine import RagEngine

_engine: RagEngine | None = None


def run_system(input: str) -> dict:
    """Call the RAG engine and return output with retrieval context and chunk metadata."""
    global _engine
    if _engine is None:
        _engine = RagEngine()
    answer, retrieved_objects = _engine.ask_question(input)
    chunks = [f"Source: {o['source']}\nContent: {o['content']}" for o in retrieved_objects]
    return {
        "output": answer,
        "retrieval_context": chunks,
        "chunk_sources": [o["source"] for o in retrieved_objects],
        "chunk_distances": [round(o["distance"], 4) for o in retrieved_objects],
        "num_chunks": len(retrieved_objects),
        "retrieval_context_len": sum(len(c) for c in chunks),
    }
