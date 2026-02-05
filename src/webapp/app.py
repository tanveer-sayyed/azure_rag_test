import os
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from rag_engine import RagEngine

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Initialize RAG Engine
# In production, might want to lazy load or handle failures gracefully
try:
    rag = RagEngine()
    print("RAG Engine initialized.")
except Exception as e:
    print(f"Warning: RAG Engine failed to initialize (likely missing env vars locally): {e}")
    rag = None

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "answer": None})

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/chat", response_class=HTMLResponse)
async def chat(request: Request, question: str = Form(...)):
    if not rag:
        return templates.TemplateResponse("index.html", {
            "request": request, 
            "answer": "Error: RAG Engine not initialized (Check configuration).",
            "question": question
        })
    
    try:
        answer, context = rag.ask(question)
        return templates.TemplateResponse("index.html", {
            "request": request, 
            "answer": answer, 
            "context": context,
            "question": question
        })
    except Exception as e:
        return templates.TemplateResponse("index.html", {
            "request": request, 
            "answer": f"Error occurred: {str(e)}",
            "question": question
        })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
