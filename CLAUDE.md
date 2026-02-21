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

This is a "Mr. Bawn" Mystery RAG application deployed on Azure at toy scale. The system has two independent deployable units:

### 1. Ingestion Pipeline (`src/ingestion/`)

Azure Function triggered by Event Grid on `Microsoft.Storage.BlobCreated` events:

```
Azure Blob Storage → Event Grid → Azure Function (IngestBlob) → DocumentIndexer
                                                                       ↓
                                                              Azure AI Search
                                                          (index: bawn-mystery-index)
```

`function_app.py` handles the Event Grid trigger; `DocumentIndexer` in `indexer.py` downloads the blob, splits on `\n\n`, generates embeddings via `text-embedding-ada-002`, and batch-uploads to the vector index.

### 2. Web App (`src/webapp/`)

FastAPI app serving a chat UI:

```
User → POST /chat → RagEngine.ask_question()
                         ├── embed question (text-embedding-ada-002)
                         ├── hybrid search Azure AI Search (top-3 chunks)
                         └── Azure OpenAI chat completion (gpt-35-turbo)
```

`app.py` is the FastAPI entrypoint; `rag_engine.py` owns all Azure client logic.

### Identity model

All Azure service access uses `DefaultAzureCredential` (Managed Identity in production — no connection strings or API keys in code). Required environment variables:

| Variable | Used by |
|---|---|
| `AZURE_SEARCH_ENDPOINT` | Both webapp and ingestion |
| `AZURE_OPENAI_ENDPOINT` | Both webapp and ingestion |
| `STORAGE_ACCOUNT_NAME` | Ingestion only |

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

### Web app (local)
```bash
cd src/webapp && uvicorn app:app --reload
```

### Ingestion function (local testing)
The ingestion function runs in Azure; local testing requires the Azure Functions Core Tools and the Azure SDK emulator or a real Azure subscription.

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
