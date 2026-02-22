"""
Accuracy answers the basic question: did we get the right answer?
"""


def exact_match(prediction: str, reference: str) -> float:
    """ Returns 1.0 if prediction exactly equals reference (case-insensitive), else 0.0. """
    return float(prediction.strip().lower() == reference.strip().lower())

# Example
print(exact_match("Michael Stonebraker", "michael stonebraker"))  # → 1.0
print(exact_match("Postgres founder", "Michael Stonebraker"))  # → 0.0