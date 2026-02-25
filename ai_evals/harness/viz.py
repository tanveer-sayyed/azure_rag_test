"""Visualization helpers: rich terminal table, static HTML report, and metrics chart."""
import io
import os
import base64
from datetime import date
from typing import List, Dict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from rich.console import Console
from rich.table import Table
import pandas as pd


def print_table(rows: List[Dict]) -> None:
    """Print a coloured pass/fail table to the terminal."""
    t = Table(title="Eval Results", show_lines=True)
    for col in ("id", "metric", "score", "threshold", "passed", "num_chunks"):
        t.add_column(col)
    for r in rows:
        style = "green" if r.get("passed") else "red"
        t.add_row(
            str(r.get("id", "")),
            str(r.get("metric", "")),
            f"{r.get('score', 0):.3f}" if r.get("score") is not None else "ERR",
            f"{r.get('threshold', 0):.3f}",
            str(r.get("passed", "")),
            str(r.get("num_chunks", 0)),
            style=style,
        )
    total = len(rows)
    passed_count = sum(1 for r in rows if r.get("passed"))
    Console().print(t)
    Console().print(f"[bold]{passed_count}/{total} passed[/bold]")


def _build_chart_html(rows: List[Dict]) -> str:
    """Return an HTML <img> of per-metric bar charts, one subplot per metric."""
    df = pd.DataFrame(rows)
    metrics = list(df["metric"].unique())
    questions = sorted(df["id"].unique())

    _LABEL = {
        "AnswerRelevancyMetric": "Answer Relevancy",
        "ToxicityMetric": "Toxicity",
        "FaithfulnessMetric": "Faithfulness",
        "ContextualPrecisionMetric": "Contextual Precision",
        "ContextualRecallMetric": "Contextual Recall",
    }

    n = len(metrics)
    fig, axes = plt.subplots(n, 1, figsize=(max(12, len(questions) * 0.7), n * 2.4), sharex=True)
    if n == 1:
        axes = [axes]

    for ax, metric in zip(axes, metrics):
        mdf = df[df["metric"] == metric].set_index("id").reindex(questions)
        scores = mdf["score"].fillna(0).tolist()
        passed = mdf["passed"].fillna(False).tolist()
        threshold = mdf["threshold"].dropna().iloc[0] if not mdf["threshold"].dropna().empty else 0.5

        colors = ["#2ecc71" if p else "#e74c3c" for p in passed]
        ax.bar(questions, scores, color=colors, width=0.6, zorder=2)
        ax.axhline(threshold, color="#2c3e50", linestyle="--", linewidth=1.2, zorder=3)
        ax.set_ylim(0, 1.1)
        ax.set_ylabel("Score", fontsize=8)
        ax.set_title(_LABEL.get(metric, metric), fontsize=9, fontweight="bold", loc="left", pad=4)
        ax.tick_params(axis="x", labelsize=7, rotation=45)
        ax.tick_params(axis="y", labelsize=7)
        ax.yaxis.grid(True, linestyle=":", alpha=0.5, zorder=1)
        ax.set_axisbelow(True)
        ax.text(len(questions) - 0.5, threshold + 0.03, f"threshold {threshold:.2f}",
                fontsize=7, color="#2c3e50", ha="right")

    axes[-1].set_xlabel("Question ID", fontsize=9)

    legend_handles = [
        mpatches.Patch(color="#2ecc71", label="Pass"),
        mpatches.Patch(color="#e74c3c", label="Fail"),
    ]
    fig.legend(handles=legend_handles, loc="upper right", fontsize=8, framealpha=0.9)
    fig.suptitle("Eval Metrics by Question", fontsize=12, fontweight="bold", y=1.01)
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode()
    return f'<img src="data:image/png;base64,{b64}" style="max-width:100%;margin-top:2em;display:block;" />'


_HTML_COLUMNS = [
    "id", "input", "expected_output", "actual_output", "num_chunks", "chunk_sources",
    "chunk_distances", "retrieval_context_len", "metric", "score",
    "threshold", "passed", "reason",
]


def _row_colour(row: "pd.Series") -> List[str]:
    """Return background-colour CSS for each cell based on passed column."""
    colour = "background-color: #d4edda" if row.get("passed") else "background-color: #f8d7da"
    return [colour] * len(row)


def write_html(rows: List[Dict], out_dir: str = "reports/latest") -> str:
    """Write a styled HTML report with metrics chart to out_dir/report.html."""
    os.makedirs(out_dir, exist_ok=True)
    df = pd.DataFrame(rows, columns=_HTML_COLUMNS)
    styled = (
        df.style
        .apply(_row_colour, axis=1)
        .format({"score": lambda v: f"{v:.3f}" if v is not None else "ERR", "threshold": "{:.3f}"})
        .set_caption(f"Eval Report — {date.today()}")
    )
    html_table = styled.to_html()
    chart_html = _build_chart_html(rows)
    html = (
        f"<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>Eval Report {date.today()}</title></head>"
        f"<body>{html_table}{chart_html}</body></html>"
    )
    out_path = os.path.join(out_dir, "report.html")
    with open(out_path, "w") as f:
        f.write(html)
    return out_path
