"""
Local regression tracking — no cloud required.

Modes:
  --check   Read reports/latest/summary.json, compare to eval/baseline.json.
            Exit 1 if any metric drops > regression_delta from baseline.
            On first run (no baseline.json), creates it and exits 0.
  --update  Save current results as new baseline (run this intentionally
            after verifying a score change is acceptable).

Usage:
  python eval/baseline.py --check
  python eval/baseline.py --update
"""
import argparse
import json
import pathlib
import sys

import yaml

_here = pathlib.Path(__file__).parent
_cfg_path = _here / "eval_config.yaml"
_baseline_path = _here / "baseline.json"
_summary_path = pathlib.Path("reports/latest/summary.json")

with open(_cfg_path) as _f:
    _cfg = yaml.safe_load(_f)

REGRESSION_DELTA = _cfg["thresholds"]["regression_delta"]


def _load_json(path: pathlib.Path) -> dict:
    with open(path) as f:
        return json.load(f)


def _save_json(path: pathlib.Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved: {path}")


def _extract_scores(summary: list | dict) -> dict[str, float]:
    """Extract per-metric mean scores from deepeval summary.json format."""
    scores: dict[str, float] = {}
    if isinstance(summary, list):
        # deepeval writes a list of test results; aggregate by metric name
        metric_buckets: dict[str, list[float]] = {}
        for result in summary:
            for metric_data in result.get("metrics_data", []):
                name = metric_data.get("name", "unknown")
                score = metric_data.get("score")
                if score is not None:
                    metric_buckets.setdefault(name, []).append(float(score))
        for name, vals in metric_buckets.items():
            scores[name] = sum(vals) / len(vals)
    elif isinstance(summary, dict):
        # Flat dict fallback
        for k, v in summary.items():
            if isinstance(v, (int, float)):
                scores[k] = float(v)
            elif isinstance(v, dict) and "mean" in v:
                scores[k] = float(v["mean"])
    return scores


def check() -> None:
    if not _summary_path.exists():
        print(f"ERROR: {_summary_path} not found. Run pytest first.", file=sys.stderr)
        sys.exit(1)

    current_scores = _extract_scores(_load_json(_summary_path))

    if not _baseline_path.exists():
        print("No baseline.json found — creating it from current results.")
        _save_json(_baseline_path, current_scores)
        print("Baseline established. Re-run after your next eval to check regression.")
        sys.exit(0)

    baseline_scores = _load_json(_baseline_path)
    regressions = []

    for metric, baseline_val in baseline_scores.items():
        current_val = current_scores.get(metric)
        if current_val is None:
            print(f"  WARN: metric '{metric}' missing from current results — skipped.")
            continue
        drop = baseline_val - current_val
        status = "OK" if drop <= REGRESSION_DELTA else "REGRESSION"
        print(f"  {metric}: baseline={baseline_val:.3f}  current={current_val:.3f}  drop={drop:+.3f}  [{status}]")
        if drop > REGRESSION_DELTA:
            regressions.append(metric)

    if regressions:
        print(f"\nFAIL: regression detected in: {', '.join(regressions)}")
        print("Fix the regressions or run `python eval/baseline.py --update` to accept new scores.")
        sys.exit(1)
    else:
        print("\nPASS: no regression detected.")


def update() -> None:
    if not _summary_path.exists():
        print(f"ERROR: {_summary_path} not found. Run pytest first.", file=sys.stderr)
        sys.exit(1)

    current_scores = _extract_scores(_load_json(_summary_path))
    _save_json(_baseline_path, current_scores)
    print("Baseline updated.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Local eval baseline tracker")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="Check for regression")
    group.add_argument("--update", action="store_true", help="Accept current scores as new baseline")
    args = parser.parse_args()

    if args.check:
        check()
    else:
        update()
