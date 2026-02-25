from deepeval.metrics import GEval
from deepeval.models import OllamaModel
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

_judge = OllamaModel(model="llama3.2", base_url="http://localhost:11434/v1")

def test_answer_relevance():
    metric = GEval(
        name="relevance",
        criteria="Answer must directly address the question with info from context.",
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
        model=_judge,
    )
    case = LLMTestCase(
        input="Who founded PostgreSQL?",
        actual_output="Michael Stonebraker",
    )
    metric.measure(case)
    assert metric.score >= 0.8, f"Low relevance: {metric.score}"
