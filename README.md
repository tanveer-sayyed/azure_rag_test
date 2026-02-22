# azure_rag_test
azure rag test

## Commands

All commands run from the repo root using the single `uv` environment.

```bash
# Install / sync dependencies
uv sync

# Ingest local docs into Weaviate
uv run python ingest_local.py docs

# Run the web app
uv run python -m uvicorn src.webapp.app:app --reload

# Run the eval suite
uv run python -m pytest

# Run a single eval test
uv run python -m pytest ai_evals/eval/test_eval.py::test_case[q01] -v

# Refresh eval baseline after intentional score changes
uv run python ai_evals/eval/baseline.py --update
git add ai_evals/eval/baseline.json && git commit -m "update eval baseline"

# Check regression manually
uv run python ai_evals/eval/baseline.py --check

# Install the pre-push git hook (once per clone)
bash ai_evals/hooks/setup_hooks.sh
```
