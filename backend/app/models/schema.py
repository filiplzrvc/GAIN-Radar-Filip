from pydantic import BaseModel
from typing import List

class ChatRequest(BaseModel):
    text: str
    mode: str = "tutor"
    # Später können wir hier session_id hinzufügen

class ChatResponse(BaseModel):
    reply: str
    sources: List[str] = []