"""
Faithfulness (or groundedness) ensures the model doesn’t hallucinate beyond
provided contexts.
"""

import re

def token_overlap(prediction: str, contexts: str) -> float:
    """Computes the fraction of prediction tokens that appear in contexts."""
    # normalize and split
    pred_tokens = re.findall(r"\w+", prediction.lower())
    context_tokens = set(re.findall(r"\w+", contexts.lower()))
    if not pred_tokens:
        return 0.0
    overlap_count = sum(1 for t in pred_tokens if t in context_tokens)
    return overlap_count / len(pred_tokens)

# Example
ctx = "Michael Stonebraker led the Berkeley POSTGRES project."
ans = "Michael Stonebraker was the lead of the POSTGRES project."
print(token_overlap(ans, ctx))  # → e.g. 0.75