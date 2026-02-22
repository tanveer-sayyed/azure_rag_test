import json
from typing import List, Dict

def load_dataset(path: str) -> List[Dict]:
    """ Reads a JSONL file and returns a list of example dicts. Each dict must include 'id', 'input', and optional 'contexts' or 'reference'. """
    examples = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            examples.append(json.loads(line))
    return examples

# Usage
dataset = load_dataset("datasets/rag_qa.jsonl")
print(f"Loaded {len(dataset)} examples.")