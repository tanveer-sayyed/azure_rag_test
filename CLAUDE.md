# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Code Conventions (from RULES.md)

- No supportive comments (no inline explanations of obvious code).
- Minimal modular design with clear separation of concerns.
- Each method or class has only a one-liner docstring.
- All variables named descriptively.
- File size < 200 lines.
- Manage token economy carefully (avoid verbose output).

## Architecture

This is a "Mr. Bawn" Mystery RAG application. The system has two independent deployable units running on **local services** (Ollama + Weaviate + sentence-transformers), deployable to Azure Web App with the same stack as sidecars.

### Local service stack

| Role | Service | Notes |
|---|---|---|
| LLM | Ollama (`llama3.1:8b`) | Local; swap model via `OLLAMA_MODEL` env var |
| Embeddings | sentence-transformers `all-MiniLM-L6-v2` | 384-dim, runs in-process |
| Vector DB | Weaviate (Docker) | Collection `BawnMystery`, no built-in vectorizer |

### 1. Ingestion Pipeline (`src/ingestion/`)

Azure Function triggered by Event Grid on `Microsoft.Storage.BlobCreated` events:

```
Azure Blob Storage → Event Grid → Azure Function (IngestBlob) → DocumentIndexer
                                                                       ↓
                                                                  Weaviate
                                                          (collection: BawnMystery)
```

`function_app.py` handles the Event Grid trigger; `DocumentIndexer` in `indexer.py` downloads the blob from Azure Blob Storage (still uses `DefaultAzureCredential`), splits on `\n\n`, generates embeddings via sentence-transformers, and batch-uploads to Weaviate using deterministic UUIDs for idempotent re-ingestion.

### 2. Web App (`src/webapp/`)

FastAPI app serving a chat UI:

```
User → POST /chat → RagEngine.ask_question()
                         ├── encode question (sentence-transformers all-MiniLM-L6-v2)
                         ├── near-vector search Weaviate (top-3, distance < 0.5)
                         └── Ollama chat completion (llama3.1:8b)
```

`app.py` is the FastAPI entrypoint; `rag_engine.py` owns all service client logic.

### Identity model

Azure Blob Storage access uses `DefaultAzureCredential` (Managed Identity in production). Weaviate and Ollama are accessed by URL — no credentials required for local/sidecar deployments.

Required environment variables:

| Variable | Used by | Default |
|---|---|---|
| `WEAVIATE_URL` | Both webapp and ingestion | `http://localhost:8080` |
| `OLLAMA_MODEL` | Webapp only | `llama3.1:8b` |
| `STORAGE_ACCOUNT_NAME` | Ingestion only | — |

### Azure Web App deployment note

Deploy Weaviate and Ollama as sidecar containers alongside the FastAPI app on the same Azure Web App (multi-container) or Azure Container Apps. Set `WEAVIATE_URL` and `OLLAMA_MODEL` in Application Settings. The ingestion Function App needs `WEAVIATE_URL` and `STORAGE_ACCOUNT_NAME` in its configuration.

### 3. Eval Suite (`ai_evals/`)

deepeval-based suite using a local Ollama judge (default: `llama3.2`). A pre-push git hook runs the suite and blocks pushes on failures or >5% metric regression.

The three files to edit when adapting the suite:

| File | Purpose |
|---|---|
| `eval/sut.py` | Implement `run_system(input) -> {"output": ..., "retrieval_context": [...]}` |
| `eval/dataset.jsonl` | Test cases (`id`, `input`, `expected_output`, `retrieval_context`) |
| `eval/eval_config.yaml` | Judge model, per-metric enable/threshold, regression delta |

## Commands

All `ai_evals/` commands must be run from the `ai_evals/` directory.

### Prerequisites (local services)
```bash
# Weaviate
docker run -d -p 8080:8080 -p 50051:50051 \
  -e QUERY_DEFAULTS_VECTORIZER=none \
  cr.weaviate.io/semitechnologies/weaviate:latest

# Ollama (if not already running)
ollama serve
ollama pull llama3.1:8b

# Webapp deps
pip install -r src/webapp/requirements.txt
```

### Web app (local)
```bash
cd src/webapp && uvicorn app:app --reload
```

### Ingestion function (local testing)
The ingestion function runs in Azure; it still reads blobs from Azure Blob Storage via `DefaultAzureCredential` but writes to Weaviate. Set `WEAVIATE_URL` and `STORAGE_ACCOUNT_NAME` before running locally with Azure Functions Core Tools.

### Eval suite
```bash
# Prerequisites
ollama serve
ollama pull llama3.2

# Run full suite
cd ai_evals && python -m pytest eval/ -v

# Run a single test
python -m pytest eval/test_eval.py::test_answer_relevancy -v

# Capture / refresh baseline after intentional score changes
python eval/baseline.py --update
git add eval/baseline.json && git commit -m "update eval baseline"

# Check regression manually
python eval/baseline.py --check

# Install the pre-push git hook (once per clone)
bash hooks/setup_hooks.sh
```

### Dependencies (uv)
```bash
# Root project
uv sync

# Eval suite
cd ai_evals && uv sync
```

---

## Improvement Plan: WAF + Inference Economics

Ordered by impact. Each item names the file(s) to change.

### P0 — Inference Economics (highest token cost reduction)

**Batch embeddings during ingestion** (`indexer.py`)
- Currently: one `embeddings.create()` call per chunk inside the loop (`indexer.py:96`).
- Fix: collect all chunk strings, call `embeddings.create(input=chunk_list)` once, zip results back.
- Impact: N-1 round-trips eliminated per blob; meaningful at any volume.

**Cache question embeddings in the webapp** (`rag_engine.py`)
- Currently: every `/chat` POST re-embeds the question unconditionally.
- Fix: add an `lru_cache` or plain `dict` keyed on the question string inside `RagEngine`.
- Impact: zero embedding cost on repeated identical queries (demos, health probes, retries).

**Filter low-score retrieval context** (`rag_engine.py`)
- Currently: top-3 chunks always forwarded verbatim to the chat completion prompt.
- Fix: read `@search.score` from each result; drop chunks below a threshold (e.g. 0.5).
- Impact: reduces prompt tokens when search returns weak matches; also improves answer quality.

### P1 — Reliability

**Move index creation out of the hot path** (`indexer.py`, `function_app.py`)
- Currently: `ensure_search_index_exists()` runs inside `process_blob_document()` on every event (`indexer.py:87`).
- Fix: call it once in `DocumentIndexer.__init__()` (cold start) or promote to a one-time deployment step.
- Impact: eliminates a list-indexes API call per event; removes race condition on concurrent events.

**Real health check** (`app.py`)
- Currently: `/health` always returns `{"status": "ok"}` regardless of service state.
- Fix: attempt a lightweight search client call (e.g. `get_index`) and return `503` on failure.
- Impact: load balancer / container orchestrator can actually detect a broken instance.

**Surface startup failures** (`app.py`)
- Currently: `RagEngine()` failure is silently swallowed into `rag_engine_instance = None`; subsequent requests return a plain error string with no trace.
- Fix: log the exception at startup; set a flag so `/health` returns `503` instead of `200`.

### P2 — Operational Excellence

**Add logging to the webapp module** (`rag_engine.py`, `app.py`)
- Currently: zero `logging` calls in either file; errors only surface via exception strings in the HTML response.
- Fix: add `import logging` and `logger = logging.getLogger(__name__)`; log question, retrieval count, and any exceptions.

**Implement `eval/sut.py`** (`ai_evals/eval/sut.py`)
- Currently: `run_system()` raises `NotImplementedError`, so the pre-push hook blocks every push.
- Fix: wire `run_system()` to `RagEngine.ask_question()`; return `{"output": answer, "retrieval_context": [chunks]}`.
- Dependency: requires the webapp to be importable from the eval directory (add `src/webapp` to path or extract shared logic).

### P3 — Security / Correctness

**Validate question length** (`app.py`)
- Currently: unbounded `question` form field passed directly to embedding and chat APIs.
- Fix: reject or truncate inputs over a reasonable limit (e.g. 2000 chars) with a 400 response.

**Update `api_version`** (`rag_engine.py:26`, `indexer.py:42`)
- Currently: `"2023-05-15"` in both clients.
- Fix: bump to a current stable version (e.g. `"2024-02-01"`) to stay within supported lifecycle.
