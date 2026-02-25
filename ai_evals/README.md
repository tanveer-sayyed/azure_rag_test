# Generic GenAI Eval Suite

Local LLM judges, no cloud required.

## How it works

deepeval runs `LLMTestCase` objects against an Ollama-hosted judge model and scores
each response on metrics defined in `eval/eval_config.yaml`. pytest enforces minimum
thresholds so any test case that falls below the configured score fails the run.
A pre-push git hook blocks the push if pytest fails or if any metric regresses more
than 5% from the stored baseline.

## Prerequisites

- Python >= 3.11
- [uv](https://github.com/astral-sh/uv) (dependency manager)
- [Ollama](https://ollama.com) installed and running (`ollama serve`)
- Judge model pulled: `ollama pull llama3.2`

## Quickstart

```bash
# 1. Install the pre-push git hook
bash hooks/setup_hooks.sh

# 2. Pull the judge model (skip if already done)
ollama pull llama3.2

# 3. Edit eval/sut.py — replace run_system() with a call to your GenAI system

# 4. Edit eval/dataset.jsonl — add your test cases (see format below)

# 5. Run the eval suite and capture the first baseline
python -m pytest eval/ -v
python eval/baseline.py --update
```

After step 5, every subsequent `git push` will run the suite automatically and block
if regressions are detected.

## Repository layout

```
ai_evals/
├── eval/
│   ├── sut.py              # System Under Test — the only file you must implement
│   ├── dataset.jsonl       # Test cases (input / expected_output / retrieval_context)
│   ├── eval_config.yaml    # Judge model, metrics, thresholds
│   ├── test_eval.py        # pytest test file — reads dataset, calls sut, scores
│   ├── conftest.py         # pytest fixtures (loads config, sets up judge)
│   ├── baseline.py         # Local regression tracker (--check / --update)
│   └── README.md           # Detailed eval module docs
├── hooks/
│   ├── pre-push            # Git hook: Ollama check → pytest → baseline check
│   └── setup_hooks.sh      # Symlinks hooks/ into .git/hooks/
├── harness/
│   ├── metrics.py          # Metric helper wrappers
│   ├── accuracy.py         # Accuracy scoring utilities
│   ├── data_loader.py      # Dataset loading helpers
│   ├── reporter.py         # Report generation
│   ├── cost.py             # Token cost estimator
│   └── archive/            # Superseded harness code (see note at bottom)
├── datasets/
│   ├── rag_qa.jsonl        # Sample RAG QA dataset
│   └── chat_multiturn.json # Sample multi-turn chat dataset
├── ci/
│   ├── deepeval-ci.yaml    # CI pipeline definition for deepeval
│   └── deepeval_tests/     # Test files for CI use
├── otel/
│   └── tracer_setup.py     # OpenTelemetry tracer factory
├── reports/
│   └── latest/
│       ├── summary.json    # Latest eval run scores (read by baseline.py)
│       └── summary.csv     # Per-case slice data
├── rubrics/
│   ├── groundedness.yaml       # Custom rubric: groundedness
│   └── helpfulness_pairwise.yaml  # Custom rubric: pairwise helpfulness
├── pyproject.toml          # Project metadata and dependencies
└── uv.lock                 # Locked dependency versions
```

## The three files you always touch

| File | What it does | What to change |
|---|---|---|
| `eval/sut.py` | Defines `run_system(input)` — the entry point for your GenAI system | Replace the `raise NotImplementedError` body with your system call; return `{"output": ..., "retrieval_context": [...]}` |
| `eval/dataset.jsonl` | One JSON object per line: `id`, `input`, `expected_output`, `retrieval_context`, `expected_tools` | Add, edit, or remove test cases to match your system's domain |
| `eval/eval_config.yaml` | Judge model selection, per-metric enable/disable flags, score thresholds, regression delta | Change `judge.model` to swap models; flip `enabled: true/false` for metrics; adjust `threshold` per metric |

## Metrics reference

| Metric | When to enable | Config key |
|---|---|---|
| `answer_relevancy` | Always — measures how relevant the answer is to the question | `metrics.answer_relevancy.enabled` |
| `toxicity` | Always — flags harmful output (lower score = safer) | `metrics.toxicity.enabled` |
| `faithfulness` | RAG systems — checks answer is grounded in retrieved context | `metrics.faithfulness.enabled` |
| `contextual_precision` | RAG systems — checks retrieved chunks are relevant | `metrics.contextual_precision.enabled` |
| `contextual_recall` | RAG systems — checks all needed context was retrieved | `metrics.contextual_recall.enabled` |
| `tool_correctness` | Agent systems — checks correct tools were called (requires `expected_tools` in dataset) | `metrics.tool_correctness.enabled` |

## Regression workflow

Every `git push` runs three checks in sequence:

```
git push
  └─ pre-push hook
       ├─ [1] Ollama reachable?       → no  → BLOCKED (start Ollama first)
       │                              → yes → continue
       ├─ [2] python -m pytest eval/  → fail → BLOCKED (fix test failures)
       │                              → pass → continue
       └─ [3] python eval/baseline.py --check
                                      → regression > 5% → BLOCKED
                                      → no regression   → PUSH ALLOWED
```

**To update the baseline** after an intentional score change:

```bash
python -m pytest eval/ -v                      # run to generate fresh reports/latest/summary.json
python eval/baseline.py --update               # overwrite eval/baseline.json
git add eval/baseline.json
git commit -m "update eval baseline"
```

To bypass the hook in an emergency (discouraged): `git push --no-verify`

## Local dev dashboard (trulens-eval)

Install trulens-eval (`uv add trulens-eval`), then wrap your SUT for interactive
scoring in a browser dashboard:

```python
from trulens_eval import Tru, TruBasicApp
from eval.sut import run_system

tru = Tru()

tru_app = TruBasicApp(run_system, app_id="my-eval-app")

with tru_app as recording:
    run_system("Who founded PostgreSQL?")

tru.run_dashboard()   # opens http://localhost:8501
```

## OTel tracing

`otel/tracer_setup.py` provides a `setup_tracer()` factory backed by the
OpenTelemetry SDK. Import it in any eval step to add spans that print to stdout
via `ConsoleSpanExporter`. This is useful for tracing latency across multiple
pipeline stages (retrieval, generation, scoring) without any collector infrastructure.

```python
from otel.tracer_setup import setup_tracer

tracer = setup_tracer("my-eval-run")

with tracer.start_as_current_span("run_system"):
    result = run_system(input_text)
```

## Common commands

| Task | Command |
|---|---|
| Run full eval suite | `python -m pytest eval/ -v` |
| Run a single test | `python -m pytest eval/test_eval.py::test_answer_relevancy -v` |
| Capture / refresh baseline | `python eval/baseline.py --update` |
| Check regression manually | `python eval/baseline.py --check` |
| Install git hook | `bash hooks/setup_hooks.sh` |
| Push without hook | `git push --no-verify` |
| Swap judge model | Edit `judge.model` in `eval/eval_config.yaml`, then `ollama pull <model>` |
| Start Ollama | `ollama serve` |

## Archived code

The `harness/archive/` directory contains earlier pipeline implementations that have
been superseded. See [`harness/archive/README.md`](harness/archive/README.md) for
details.
