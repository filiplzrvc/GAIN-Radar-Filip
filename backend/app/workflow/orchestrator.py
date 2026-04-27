"""
Aufgabe:
- Zentrale Stelle, die die Agenten in der richtigen Reihenfolge aufruft
- Versteckt die Pipeline-Komplexität hinter einer einfachen Funktion
- Wird von FastAPI (main.py) und von Tests gleichermaßen genutzt
"""
from typing import Optional
from app.workflow.state import WorkflowState
from app.workflow.analysis_agent import run_analysis_agent
from app.workflow.retrieval_agent import retrieve_documents
from app.workflow.context_agent import prepare_context
from app.workflow.answer_agent import run_answer_agent


def process_request(
    question: str,
    course: str,
    mode: str = "tutor",
    session_id: Optional[str] = None
) -> WorkflowState:
    """
    Führt die komplette agentische Pipeline aus.
    
    Args:
        question: Die Nutzerfrage
        course: Fach-Code (z.B. "aief", "itsec", "swen")
        mode: Lernmodus (vorerst nur "tutor", später quiz/flashcards/summary)
        session_id: Optional - für spätere Session-Memory
    
    Returns:
        WorkflowState mit final_answer und sources_used
    """
    # State initialisieren
    state = WorkflowState(
        user_question=question,
        course=course,
        mode=mode
    )
    
    # Wenn session_id mitgegeben, übernehmen (sonst behält State seine generierte ID)
    if session_id:
        state.session_id = session_id
    
    state.log("Orchestrator", f"Pipeline gestartet für Fach '{course}', Modus '{mode}'")
    
    # === Pipeline ausführen ===
    state = run_analysis_agent(state)
    state = retrieve_documents(state)
    state = prepare_context(state)
    state = run_answer_agent(state)
    
    state.log("Orchestrator", "Pipeline abgeschlossen")
    
    return state