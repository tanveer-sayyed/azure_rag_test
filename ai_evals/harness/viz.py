"""Visualization helpers: rich terminal table and static HTML report."""
import os
from datetime import date
from typing import List, Dict

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
            f"{r.get('score', 0):.3f}",
            f"{r.get('threshold', 0):.3f}",
            str(r.get("passed", "")),
            str(r.get("num_chunks", 0)),
            style=style,
        )
    total = len(rows)
    passed_count = sum(1 for r in rows if r.get("passed"))
    Console().print(t)
    Console().print(f"[bold]{passed_count}/{total} passed[/bold]")


_HTML_COLUMNS = [
    "id", "input", "actual_output", "num_chunks", "chunk_sources",
    "chunk_distances", "retrieval_context_len", "metric", "score",
    "threshold", "passed", "reason",
]


def _row_colour(row: "pd.Series") -> List[str]:
    """Return background-colour CSS for each cell based on passed column."""
    colour = "background-color: #d4edda" if row.get("passed") else "background-color: #f8d7da"
    return [colour] * len(row)


def write_html(rows: List[Dict], out_dir: str = "reports/latest") -> str:
    """Write a styled HTML report to out_dir/report.html."""
    os.makedirs(out_dir, exist_ok=True)
    df = pd.DataFrame(rows, columns=_HTML_COLUMNS)
    styled = (
        df.style
        .apply(_row_colour, axis=1)
        .format({"score": "{:.3f}", "threshold": "{:.3f}"})
        .set_caption(f"Eval Report — {date.today()}")
    )
    html_table = styled.to_html()
    html = f"<!DOCTYPE html><html><head><meta charset='utf-8'>"
    html += f"<title>Eval Report {date.today()}</title></head>"
    html += f"<body>{html_table}</body></html>"
    out_path = os.path.join(out_dir, "report.html")
    with open(out_path, "w") as f:
        f.write(html)
    return out_path
