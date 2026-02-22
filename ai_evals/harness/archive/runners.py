from typing import Dict, List

def answer_rag(question: str, contexts: List[str]) -> str:
    # Your real pipeline goes here. This stub mimics a call.
    return "Michael Stonebraker" if "PostgreSQL" in question else "Atomicity, Consistency, Isolation, Durability"

def run_item(item: Dict) -> Dict:
    pred = answer_rag(item["question"], item.get("contexts", []))
    return {"id": item["id"], "prediction": pred}