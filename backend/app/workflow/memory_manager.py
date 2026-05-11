"""
Aufgabe:
- Sessions als JSON-Files in backend/sessions/ verwalten
- Laden: bei Folgefragen den Verlauf einer Session abrufen
- Speichern: nach jeder Antwort den Verlauf aktualisieren
- Sliding-Window: nur die letzten N Q&A-Paare ans LLM senden
  (User sieht alle, aber Prompt bleibt klein und schnell)
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

# Konfiguration
SESSIONS_DIR = Path(__file__).parent.parent.parent / "sessions"
LLM_HISTORY_LIMIT = 12  # Letzte 6 Q&A-Paare = 12 Nachrichten an das LLM


def _ensure_sessions_dir():
    """Stellt sicher, dass der sessions-Ordner existiert."""
    SESSIONS_DIR.mkdir(exist_ok=True)


def _session_path(session_id: str) -> Path:
    """Gibt den Datei-Pfad für eine Session-ID zurück."""
    # Sicherheits-Check: keine Path-Traversal-Angriffe wie "../../etc/passwd"
    safe_id = session_id.replace("/", "").replace("\\", "").replace("..", "")
    return SESSIONS_DIR / f"{safe_id}.json"


def load_session(session_id: str) -> Optional[dict]:
    """
    Lädt eine Session aus dem JSON-File.
    Returns:
        Dict mit Session-Daten oder None falls nicht vorhanden.
    """
    _ensure_sessions_dir()
    path = _session_path(session_id)
    
    if not path.exists():
        return None
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Fehler beim Laden von Session {session_id}: {e}")
        return None


def get_history_for_llm(session_id: str) -> list[dict]:
    """
    Lädt nur die letzten N Nachrichten einer Session für das LLM.
    
    User sieht alle Nachrichten, aber das LLM bekommt nur ein Sliding Window
    der letzten 6 Q&A-Paare (12 Nachrichten). Das hält den Prompt schnell und günstig.
    """
    session = load_session(session_id)
    if not session:
        return []
    
    messages = session.get("messages", [])
    return messages[-LLM_HISTORY_LIMIT:]


def append_to_session(
    session_id: str,
    course: str,
    user_question: str,
    bot_answer: str,
    sources: list[str]
) -> None:
    """
    Hängt ein neues Q&A-Paar an die Session-Datei.
    Erstellt die Session, falls sie noch nicht existiert.
    """
    _ensure_sessions_dir()
    path = _session_path(session_id)
    now = datetime.utcnow().isoformat() + "Z"
    
    # Existierende Session laden oder neue erstellen
    session = load_session(session_id) or {
        "session_id": session_id,
        "created_at": now,
        "course": course,
        "messages": []
    }
    
    # Neue Nachrichten anhängen
    session["messages"].append({
        "role": "user",
        "text": user_question,
        "timestamp": now
    })
    session["messages"].append({
        "role": "bot",
        "text": bot_answer,
        "sources": sources,
        "timestamp": now
    })
    session["last_updated"] = now
    
    # Speichern
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(session, f, ensure_ascii=False, indent=2)
    except IOError as e:
        print(f"Fehler beim Speichern von Session {session_id}: {e}")