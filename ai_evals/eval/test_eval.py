"""
Data-driven deepeval pytest runner.
Reads eval_config.yaml and dataset.jsonl, calls sut.run_system() for each case,
then asserts all enabled metrics meet their thresholds.
"""
import json
import os
import pathlib
import yaml
import pytest

from deepeval.metrics import (
    AnswerRelevancyMetric,
    ToxicityMetric,
    FaithfulnessMetric,
    ContextualPrecisionMetric,
    ContextualRecallMetric,
    ToolCorrectnessMetric,
)
from deepeval.test_case import LLMTestCase

from eval.conftest import judge_model
from eval import sut

_here = pathlib.Path(__file__).parent
_cfg_path = _here / "eval_config.yaml"
_dataset_path = _here / "dataset.jsonl"

with open(_cfg_path) as _f:
    _cfg = yaml.safe_load(_f)

_metric_cfg = _cfg["metrics"]


def _build_metrics() -> list:
    metrics = []

    if _metric_cfg.get("answer_relevancy", {}).get("enabled"):
        metrics.append(
            AnswerRelevancyMetric(
                threshold=_metric_cfg["answer_relevancy"]["threshold"],
                model=judge_model,
            )
        )

    if _metric_cfg.get("toxicity", {}).get("enabled"):
        metrics.append(
            ToxicityMetric(
                threshold=_metric_cfg["toxicity"]["threshold"],
                model=judge_model,
            )
        )

    if _metric_cfg.get("faithfulness", {}).get("enabled"):
        metrics.append(
            FaithfulnessMetric(
                threshold=_metric_cfg["faithfulness"]["threshold"],
                model=judge_model,
            )
        )

    if _metric_cfg.get("contextual_precision", {}).get("enabled"):
        metrics.append(
            ContextualPrecisionMetric(
                threshold=_metric_cfg["contextual_precision"]["threshold"],
                model=judge_model,
            )
        )

    if _metric_cfg.get("contextual_recall", {}).get("enabled"):
        metrics.append(
            ContextualRecallMetric(
                threshold=_metric_cfg["contextual_recall"]["threshold"],
                model=judge_model,
            )
        )

    if _metric_cfg.get("tool_correctness", {}).get("enabled"):
        metrics.append(ToolCorrectnessMetric())

    return metrics


def _load_cases() -> list[dict]:
    cases = []
    with open(_dataset_path) as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


_cases = _load_cases()
_metrics = _build_metrics()


@pytest.mark.parametrize("case", _cases, ids=[c["id"] for c in _cases])
def test_case(case: dict, report_collector):
    result = sut.run_system(case["input"])

    tc = LLMTestCase(
        input=case["input"],
        actual_output=result["output"],
        expected_output=case.get("expected_output", ""),
        retrieval_context=result.get("retrieval_context", case.get("retrieval_context", [])),
        expected_tools=case.get("expected_tools", []),
    )

    failures = []
    for m in _metrics:
        m.measure(tc)
        report_collector.append({
            "id": case["id"],
            "input": case["input"],
            "expected_output": case.get("expected_output", ""),
            "actual_output": result["output"],
            "num_chunks": result.get("num_chunks", 0),
            "chunk_sources": result.get("chunk_sources", []),
            "chunk_distances": result.get("chunk_distances", []),
            "retrieval_context_len": result.get("retrieval_context_len", 0),
            "metric": m.__class__.__name__,
            "score": m.score,
            "threshold": m.threshold,
            "passed": m.success,
            "reason": getattr(m, "reason", ""),
        })
        if not m.success:
            failures.append(
                f"{m.__class__.__name__} (score: {m.score}, threshold: {m.threshold}, reason: {m.reason})"
            )
    if failures:
        raise AssertionError("Metrics: " + ", ".join(failures) + " failed.")
