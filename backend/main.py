"""FastAPI-Hauptanwendung des GAIN-Radar Backends."""
import json
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.models.schema import (
    ChatRequest, ChatResponse,
    CourseInfo, CoursesResponse
)
from app.agents.tutor_agent import get_tutor_response

load_dotenv()

app = FastAPI(title="GAIN-Radar Backend API", version="0.2.0")

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
    """Verarbeitet eine Chat-Anfrage."""
    valid_codes = [c["code"] for c in load_courses()]
    if request.course not in valid_codes:
        raise HTTPException(
            status_code=400,
            detail=f"Fach '{request.course}' nicht verfügbar. Gültig: {valid_codes}"
        )
    
    try:
        result = get_tutor_response(request.text, course_code=request.course)
        return ChatResponse(
            reply=result["reply"],
            sources=result["sources"],
            mode_used=request.mode,
            course_used=request.course,
            session_id=request.session_id
        )
    except Exception as e:
        print(f"❌ Fehler in /api/chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "0.2.0"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)