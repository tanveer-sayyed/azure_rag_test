from trulens_eval import TruBasicApp
from trulens_eval.feedback import Groundedness, AnswerRelevance, ContextRelevance

# Replace with your actual callable
def rag_app(question, contexts):
    return "Michael Stonebraker"

app = TruBasicApp(rag_app)
triad = [
    ContextRelevance(),
    Groundedness(),
    AnswerRelevance()
]
question = "Who founded PostgreSQL?"
contexts = ["Berkeley POSTGRES project led by Michael Stonebraker"]
result = app.run(question, contexts)
scores = {fb.name: fb(result=result, context=contexts) for fb in triad}
print(scores)

