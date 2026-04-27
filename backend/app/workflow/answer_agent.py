"""
Antwort-Agent 

Aufgabe:
- Bekommt einen vollständig analysierten und vorbereiteten WorkflowState
- Wählt eine von 5 Antwort-Strategien:
    1. off_topic           → Höfliche Ablehnung (kein LLM)
    2. clarification       → Rückfrage (kein LLM)
    3. context none        → "Nichts gefunden" (kein LLM)
    4. context insufficient → LLM-Antwort mit Warnung
    5. context sufficient  → Normale LLM-Antwort

- Schreibt final_answer und sources_used in den State
"""
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from app.core.prompts import answer_prompt
from app.workflow.state import WorkflowState


answer_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)


# Deterministische Antworten (kein LLM nötig)

OFF_TOPIC_RESPONSES = {
    "de": (
        "Diese Frage liegt außerhalb der Studieninhalte. "
        "GAIN-Radar hilft dir bei Fragen zu deinen Kursen. "
        "Möchtest du etwas zu einem deiner Fächer wissen?"
    ),
    "en": (
        "This question is outside the scope of your course content. "
        "GAIN-Radar helps you with questions about your courses. "
        "Would you like to ask something about one of your subjects?"
    ),
}

CLARIFICATION_RESPONSES = {
    "de": (
        "Deine Frage ist mir noch zu unklar. Kannst du sie etwas konkreter formulieren? "
        "Zum Beispiel: Welches Thema interessiert dich, oder zu welchem Konzept möchtest du mehr wissen?"
    ),
    "en": (
        "Your question is still a bit unclear to me. Could you be more specific? "
        "For example: which topic are you interested in, or which concept would you like to know more about?"
    ),
}

NO_CONTEXT_RESPONSES = {
    "de": (
        "Im Kursmaterial finde ich zu deiner Frage leider keine Informationen. "
        "Vielleicht passt sie nicht zu diesem Fach – möchtest du sie in einem anderen Fach stellen?"
    ),
    "en": (
        "I couldn't find any information about your question in the course material. "
        "Maybe it doesn't fit this subject – would you like to ask in a different course?"
    ),
}


def _get_response(responses: dict, language: str) -> str:
    """Wählt die Antwort in der passenden Sprache mit DE als Fallback."""
    return responses.get(language, responses["de"])


def _generate_llm_answer(state: WorkflowState, with_warning: bool = False) -> str:
    """Ruft das LLM auf, um eine Antwort aus dem prepared_context zu erzeugen."""
    chain = answer_prompt | answer_llm | StrOutputParser()
    
    # Bei "insufficient" Kontext: dem LLM einen Hinweis im Frage-Block mitgeben
    user_input = state.user_question
    if with_warning:
        warning = (
            "[Hinweis: Der Kontext könnte unzureichend sein. "
            "Antworte nur, was wirklich belegbar ist, sonst sage es ehrlich.]\n\n"
        )
        user_input = warning + state.user_question
    
    return chain.invoke({
        "context": state.prepared_context or "",
        "user_input": user_input
    })


def _format_sources(state: WorkflowState) -> list[str]:
    """Erstellt die Quellen-Liste aus den retrievten Dokumenten."""
    sources = set()
    for doc in state.retrieved_documents:
        sources.add(f"{doc.source_name} (S. {doc.page})")
    return sorted(list(sources))


def run_answer_agent(state: WorkflowState) -> WorkflowState:
    """
    Wählt die passende Antwortstrategie und füllt final_answer + sources_used.
    """
    state.log("AntwortAgent", "Wähle Antwortstrategie...")
    
    # STRATEGIE 1: Off-Topic
    if state.decisions.off_topic:
        state.final_answer = _get_response(OFF_TOPIC_RESPONSES, state.language or "de")
        state.sources_used = []
        state.log("AntwortAgent", "Strategie: Off-Topic-Ablehnung (kein LLM)")
        return state
    
    # STRATEGIE 2: Klärung nötig 
    if state.decisions.clarification_needed:
        state.final_answer = _get_response(CLARIFICATION_RESPONSES, state.language or "de")
        state.sources_used = []
        state.log("AntwortAgent", "Strategie: Rückfrage (kein LLM)")
        return state
    
    # STRATEGIE 3: Kein Kontext gefunden 
    if state.context_quality == "none":
        state.final_answer = _get_response(NO_CONTEXT_RESPONSES, state.language or "de")
        state.sources_used = []
        state.log("AntwortAgent", "Strategie: Kein Kontext (kein LLM)")
        return state
    
    # STRATEGIE 4: Wenig Kontext - LLM mit Warnung
    if state.context_quality == "insufficient":
        state.log("AntwortAgent", "Strategie: LLM mit Insufficient-Warnung")
        try:
            state.final_answer = _generate_llm_answer(state, with_warning=True)
            state.sources_used = _format_sources(state)
        except Exception as e:
            state.log("AntwortAgent", f"❌ LLM-Fehler: {e}")
            state.final_answer = _get_response(NO_CONTEXT_RESPONSES, state.language or "de")
            state.sources_used = []
        return state
    
    # STRATEGIE 5: Guter Kontext - normale RAG-Antwort
    state.log("AntwortAgent", "Strategie: Normale RAG-Antwort")
    try:
        state.final_answer = _generate_llm_answer(state, with_warning=False)
        state.sources_used = _format_sources(state)
    except Exception as e:
        state.log("AntwortAgent", f"❌ LLM-Fehler: {e}")
        state.final_answer = (
            "Es ist ein Fehler bei der Antwort-Generierung aufgetreten. "
            "Bitte versuche es erneut."
        )
        state.sources_used = []
    
    return state