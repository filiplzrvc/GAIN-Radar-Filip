"""
Aufgabe:
- Zentrale Stelle, die die Agenten in der richtigen Reihenfolge aufruft
- Lädt Konversations-Verlauf am Anfang
- Speichert das neue Q&A-Paar am Ende
"""
from langsmith import traceable
from typing import Optional
from app.workflow.state import WorkflowState
from app.workflow.analysis_agent import run_analysis_agent
from app.workflow.retrieval_agent import retrieve_documents
from app.workflow.context_agent import prepare_context
from app.workflow.answer_agent import run_answer_agent
from app.workflow.memory_manager import get_history_for_llm, append_to_session

@traceable(name="GAIN-Radar Orchestrator")
def process_request(
    question: str,
    course: str,
    mode: str = "tutor",
    session_id: Optional[str] = None
) -> WorkflowState:
    """
    Führt die komplette agentische Pipeline aus, mit Session-Memory.
    """
    # State initialisieren
    state = WorkflowState(
        user_question=question,
        course=course,
        mode=mode
    )
    
    if session_id:
        state.session_id = session_id

    state.conversation_history = get_history_for_llm(state.session_id)
    
    if state.conversation_history:
        state.log(
            "Orchestrator",
            f"Folgefrage erkannt: {len(state.conversation_history)} vorherige Nachrichten geladen"
        )
    else:
        state.log("Orchestrator", f"Neue Session '{state.session_id}'")
    
    state.log("Orchestrator", f"Pipeline gestartet für Fach '{course}', Modus '{mode}'")
    
    # === Pipeline ausführen ===
    state = run_analysis_agent(state)
    state = retrieve_documents(state)
    state = prepare_context(state)
    state = run_answer_agent(state)
    
    state.log("Orchestrator", "Pipeline abgeschlossen")
    
    # Antwort speichern (außer bei Off-Topic ohne echten Inhalt)
    # Wir speichern auch off-topic Antworten, damit der User den Verlauf komplett sieht.
    if state.final_answer:
        append_to_session(
            session_id=state.session_id,
            course=state.course,
            user_question=state.user_question,
            bot_answer=state.final_answer,
            sources=state.sources_used
        )
        state.log("Orchestrator", "Q&A in Session gespeichert")
    
    return state