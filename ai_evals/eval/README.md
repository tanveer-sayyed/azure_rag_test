# eval/ — Generic GenAI Eval Suite

A copy-paste eval template powered by [deepeval](https://docs.confident-ai.com/) with local Ollama judges.
Runs as a pre-push git hook: **no cloud, no API keys, no dashboard subscription.**

---

## Quickstart

```bash
# 1. Install the pre-push hook (once per clone)
bash hooks/setup_hooks.sh

# 2. Pull the default judge model
ollama pull llama3.2

# 3. Fill in your system under test
$EDITOR eval/sut.py

# 4. Add your test cases
$EDITOR eval/dataset.jsonl

# 5. Run evals manually
python -m pytest eval/ -v

# 6. Establish a baseline
python eval/baseline.py --update
```

After that, `git push` will automatically run the eval suite and block the push if:
- any pytest assertion fails, or
- any metric drops more than 5% from the baseline.

Use `git push --no-verify` to bypass the hook (use sparingly).

---

## File Map

| File | Purpose |
|---|---|
| `eval_config.yaml` | Metric selection, thresholds, judge model |
| `conftest.py` | Wires OllamaModel into deepeval (auto-loaded by pytest) |
| `test_eval.py` | Data-driven pytest runner — do not edit |
| `sut.py` | **Edit this** — wrap your GenAI system |
| `dataset.jsonl` | **Edit this** — add your test cases |
| `baseline.py` | Local regression tracker |
| `baseline.json` | Auto-generated; commit after `--update` |

---

## Dataset Format

Each line is a JSON object:

```jsonl
{"id":"q1","input":"Who founded PostgreSQL?","expected_output":"Michael Stonebraker","retrieval_context":["Berkeley POSTGRES project..."],"expected_tools":[]}
```

| Field | Required | Notes |
|---|---|---|
| `id` | yes | unique string |
| `input` | yes | user query |
| `expected_output` | yes | ground-truth answer |
| `retrieval_context` | if RAG | chunks the LLM should use |
| `expected_tools` | if agent | placeholder (not scored yet) |

---

## Enabling Metrics

Edit `eval_config.yaml`:

```yaml
faithfulness:
  enabled: true   # ← flip this
  threshold: 0.7
```

Available metrics:

| Metric | When to enable |
|---|---|
| `answer_relevancy` | always (default on) |
| `toxicity` | always (default on) |
| `faithfulness` | RAG — response grounded in retrieved chunks |
| `contextual_precision` | RAG — retrieved chunks are relevant |
| `contextual_recall` | RAG — all needed chunks were retrieved |
| `tool_correctness` | Agent — requires `expected_tools` in dataset |

**Agent trajectory evaluation** is an open problem with no standardised ground-truth format.
Until a standard emerges, log tool calls to `reports/` manually and review them there.

---

## Local Dev Dashboard (trulens-eval)

trulens-eval is **not** used in the CI hook, but it's great for interactive development.
Wrap your SUT to get a trace dashboard:

```python
from trulens_eval import TruBasicApp, Tru

tru = Tru()

def my_app(question: str) -> str:
    from eval.sut import run_system
    return run_system(question)["output"]

tru_app = TruBasicApp(my_app, app_id="my-app-v1")

with tru_app as recording:
    my_app("Who founded PostgreSQL?")

tru.run_dashboard()  # opens Streamlit at http://localhost:8501
```

---

## Regression Workflow

```
pytest pass → python eval/baseline.py --check
                 ↓ no regression       ↓ regression detected
              push allowed         push blocked
                                   fix or --update to accept
```

```bash
# Accept improved scores as the new baseline
python eval/baseline.py --update
git add eval/baseline.json
git commit -m "update eval baseline"
```
