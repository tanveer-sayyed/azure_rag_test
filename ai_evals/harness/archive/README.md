# Archived Files

These files have been superseded by [deepeval](https://docs.confident-ai.com/) and are kept here for reference only. Do not import them.

| File | Superseded by |
|---|---|
| `faithfulness.py` | `deepeval.metrics.FaithfulnessMetric` |
| `safety.py` | `deepeval.metrics.ToxicityMetric` |
| `judges.py` | deepeval + OllamaModel (no OpenAI required) |
| `triad.py` | deepeval contextual metrics (trulens v0 API is broken) |
| `pipeline.py` | `eval/test_eval.py` |
| `runners.py` | `eval/sut.py` |

The active eval suite lives in `eval/`. See `eval/README.md` for usage.
