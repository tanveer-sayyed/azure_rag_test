"""
Compute fast, deterministic metrics, exact match, token overlap, retrieval scores, on each
example.
"""

from typing import Dict
import numpy as np

def exact_match(pred: str, ref: str) -> float:
    return float(pred.strip().lower() == ref.strip().lower())

def soft_contains(pred: str, ref: str) -> float:
    return float(ref.lower() in pred.lower())

def aggregate(scores):
    arr = np.array(scores, dtype=float)
    return {"mean": float(arr.mean()), "n": len(arr)}

def token_overlap(pred: str, context: str) -> float:
    pred_tokens = pred.lower().split()
    ctx_tokens = set(context.lower().split())
    if not pred_tokens:
        return 0.0
    overlap = sum(1 for t in pred_tokens if t in ctx_tokens)
    return overlap / len(pred_tokens)