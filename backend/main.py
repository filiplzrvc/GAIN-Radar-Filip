"""FastAPI-Hauptanwendung des GAIN-Radar Backends."""
# WICHTIG: load_dotenv() muss VOR allen App-Imports stehen,
# damit OPENAI_API_KEY beim Import von analysis_agent verfügbar ist.
from dotenv import load_dotenv
load_dotenv()

import json
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# IMPORTS FÜR DEN TURBO-CACHE
from langchain_core.globals import set_llm_cache
from langchain_community.cache import InMemoryCache


from app.models.schema import (
    ChatRequest, ChatResponse,
    CourseInfo, CoursesResponse
)
from app.workflow.orchestrator import process_request


app = FastAPI(title="GAIN-Radar Backend API", version="0.3.0")

# PERFORMANCE OPTIMIERUNG: Globaler LLM-Cache
# Merkt sich bereits generierte Antworten im Arbeitsspeicher.
# Wenn dieselbe Frage nochmal kommt, sinkt die Wartezeit auf 0,01 Sekunden!
set_llm_cache(InMemoryCache())

# CORS für Angular-Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_courses() -> list[dict]:
    """Lädt config/courses.json."""
    config_path = Path(__file__).parent / "config" / "courses.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)["courses"]


@app.get("/api/courses", response_model=CoursesResponse)
async def get_courses():
    """Gibt eine Liste aller verfügbaren Fächer zurück."""
    try:
        courses_data = load_courses()
        courses = [CourseInfo(**c) for c in courses_data]
        return CoursesResponse(courses=courses)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="courses.json nicht gefunden")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fehler beim Laden: {e}")


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Verarbeitet eine Chat-Anfrage über den agentischen Workflow.
    """
    # Validierung: Existiert das Fach?
    valid_codes = [c["code"] for c in load_courses()]
    if request.course not in valid_codes:
        raise HTTPException(
            status_code=400,
            detail=f"Fach '{request.course}' nicht verfügbar. Gültig: {valid_codes}"
        )
    
    try:
        # Statt direktem tutor_agent → Orchestrator mit allen 4 Agenten
        state = process_request(
            question=request.text,
            course=request.course,
            mode=request.mode,
            session_id=request.session_id
        )
        
        return ChatResponse(
            reply=state.final_answer or "Es ist ein Fehler aufgetreten.",
            sources=state.sources_used,
            session_id=state.session_id,
            mode_used=state.mode,
            course_used=state.course
        )
    except Exception as e:
        print(f"Fehler in /api/chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    """Health-Check mit Versions- und Workflow-Info."""
    return {
        "status": "ok",
        "version": "0.3.0",
        "workflow": "agentic"
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)