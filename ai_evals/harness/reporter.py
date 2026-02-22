import csv, json, os
from typing import List, Dict


def write_report(rows: List[Dict], out_dir="reports/latest"):
    """Write summary.json and summary.csv to out_dir."""
    if rows:
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "summary.json"), "w") as f:
            json.dump(rows, f, indent=2)
        with open(os.path.join(out_dir, "summary.csv"), "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
    return os.path.join(out_dir, "summary.json")