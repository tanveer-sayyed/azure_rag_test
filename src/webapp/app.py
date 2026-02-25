import os
import logging
import pathlib
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates
from .rag_engine import RagEngine

app = FastAPI()
templates = Jinja2Templates(directory=pathlib.Path(__file__).parent / "templates")
logger = logging.getLogger(__name__)

_startup_error: Exception | None = None
try:
    rag_engine_instance = RagEngine()
except Exception as initialization_error:
    rag_engine_instance = None
    _startup_error = initialization_error
    logger.error("RagEngine initialization failed: %s", initialization_error)

@app.get("/", response_class=HTMLResponse)
async def read_root_page(request: Request):
    """Render the landing page."""
    return templates.TemplateResponse("index.html", {"request": request, "answer": None})

@app.get("/health")
async def health_check_endpoint():
    """Return 200 if all services are reachable, 503 otherwise."""
    if rag_engine_instance is None:
        return JSONResponse({"status": "unavailable", "detail": str(_startup_error)}, status_code=503)
    try:
        rag_engine_instance.health_check()
        return {"status": "ok"}
    except Exception as health_error:
        return JSONResponse({"status": "unavailable", "detail": str(health_error)}, status_code=503)

_MAX_QUESTION_LEN = 2000

@app.post("/chat", response_class=HTMLResponse)
async def chat_endpoint(request: Request, question: str = Form(...)):
    """Handle chat interactions and RAG retrieval."""
    if len(question) > _MAX_QUESTION_LEN:
        return Response(content="Question exceeds 2000 character limit.", status_code=400)
    if not rag_engine_instance:
        return templates.TemplateResponse("index.html", {
            "request": request, 
            "answer": "Error: RAG Engine not initialized.",
            "question": question
        })
    
    try:
        generated_answer, retrieved_context = rag_engine_instance.ask_question(question)
        return templates.TemplateResponse("index.html", {
            "request": request, 
            "answer": generated_answer, 
            "context": retrieved_context,
            "question": question
        })
    except Exception as processing_error:
        logger.error("chat error question=%r: %s", question, processing_error)
        return templates.TemplateResponse("index.html", {
            "request": request,
            "answer": f"Error occurred: {str(processing_error)}",
            "question": question
        })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
