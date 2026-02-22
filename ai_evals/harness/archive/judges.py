"""
Capture nuanced qualities like helpfulness or safety.
"""
import json
from typing import List, Dict
from .runner import run_item
from .metrics import exact_match, soft_contains, aggregate
from .reporters import write_report

def eval_rag(dataset_path: str) -> Dict:
    rows = []
    with open(dataset_path) as f:
        for line in f:
            item = json.loads(line)
            out = run_item(item)
            em = exact_match(out["prediction"], item.get("reference",""))
            soft = soft_contains(out["prediction"], item.get("reference",""))
            rows.append({**item, **out, "em": em, "soft": soft})
    write_report(rows)
    em_stats = aggregate([r["em"] for r in rows])
    soft_stats = aggregate([r["soft"] for r in rows])
    return {"exact_match": em_stats, "soft_contains": soft_stats}

def load_rubric(path: str) -> Dict: 
    with open(path, 'r') as f: 
        return yaml.safe_load(f) 

def llm_judge(pred: str, rubric: Dict) -> float: 
    prompt = rubric["instructions"].format(answer=pred) 
    response = client.chat.completions.create( 
        model="gpt-4o-mini", 
        messages=[{"role":"system","content":prompt}] 
    ) 
    score = float(response.choices[0].message.content.strip()) 
    return max(rubric["scale"]["min"], min(rubric["scale"]["max"], score)) 

if __name__ == "__main__":
    print(eval_rag("datasets/rag_qa.jsonl"))
    # Usage
    rubric = load_rubric("rubrics/groundedness.yaml") 
    score = llm_judge("The capital of France is Paris.", rubric) 
    print(f"Groundedness score: {score}")