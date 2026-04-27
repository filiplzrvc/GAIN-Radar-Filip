#Pydantic-Schemas für API-Anfragen und -Antworten
from pydantic import BaseModel, Field
from typing import List, Optional


class ChatRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Die Frage des Studierenden")
    mode: str = Field(default="tutor", description="tutor, quiz, flashcards, summary")
    course: str = Field(..., description="Fach-Code aus courses.json (z.B. 'aief')")
    session_id: Optional[str] = Field(default=None, description="Session-ID für Folge-Anfragen")


class ChatResponse(BaseModel):
    reply: str
    sources: List[str] = []
    session_id: Optional[str] = None
    mode_used: Optional[str] = None
    course_used: Optional[str] = None


class CourseInfo(BaseModel):
    code: str
    name: str
    description: str
    language: str


class CoursesResponse(BaseModel):
    courses: List[CourseInfo]