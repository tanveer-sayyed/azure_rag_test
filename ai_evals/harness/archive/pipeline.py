from typing import Dict
from judges import load_rubric, llm_judge
from reporter import write_report
from data_loader import load_dataset
from metrics import exact_match, token_overlap, aggregate


def run_pipeline(dataset_path: str) -> Dict:
    """
    Runs the evaluation pipeline.
    """
    dataset = load_dataset(dataset_path)
    results = []
    rubric = load_rubric("rubrics/groundedness.yaml")
    for ex in dataset:
        pred = your_system_under_test(ex) # replace with actual call
        em = exact_match(pred, ex.get("reference", ""))
        overlap = token_overlap(pred, " ".join(ex.get("contexts", [])))
        grounded = llm_judge(pred, rubric)
        results.append({
            "id": ex["id"],
            "prediction": pred,
            "reference": ex.get("reference", ""),
            "exact_match": em,
            "token_overlap": overlap,
            "groundedness": grounded
        })
    write_report(results)
    metrics = {
        "exact_match": aggregate([r["exact_match"] for r in results]),
        "token_overlap": aggregate([r["token_overlap"] for r in results]),
        "groundedness": aggregate([r["groundedness"] for r in results])
    }
    print(metrics)
    return metrics

if __name__ == "__main__":
    run_pipeline("datasets/rag_qa.jsonl")