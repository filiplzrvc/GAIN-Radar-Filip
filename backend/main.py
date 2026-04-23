import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.models.schema import ChatRequest, ChatResponse
from app.agents.tutor_agent import get_tutor_response

# Lade Umgebungsvariablen (.env)
load_dotenv()

app = FastAPI(title="GAIN-Radar Backend API")

# CORS konfigurieren (Schnittstelle zu Angular)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        # Hier rufen wir jetzt unseren Agenten auf
        result = get_tutor_response(request.text)
        
        # result ist jetzt {"reply": "...", "sources": [...]}
        return ChatResponse(
            reply=result["reply"],
            sources=result["sources"]
        )
    except Exception as e:
        print(f"Fehler: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)