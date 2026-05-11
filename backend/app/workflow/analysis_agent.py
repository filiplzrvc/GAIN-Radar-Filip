"""
Analysiert eine eingehende Nutzerfrage und füllt im WorkflowState:
- language: Erkannte Sprache
- topics: Extrahierte Themen
- intent: Nutzerintention
- decisions.off_topic: Ist die Frage themenfremd?
- decisions.clarification_needed: Muss nachgefragt werden?

ERLAUBTE AKTIONEN
- Sprache, Themen, Intent klassifizieren
- Off-Topic-Entscheidung treffen
- Konversations-Verlauf berücksichtigen für Folgefragen

NICHT ERLAUBT:
- Dokumente abrufen (das macht der Retrieval-Agent)
- Antworten generieren (das macht der Antwort-Agent)
"""

import json
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from app.core.prompts import analysis_prompt
from app.workflow.state import WorkflowState


# Separates LLM für den Analyse-Agenten.
# Temperature=0 → immer gleiche Antworten bei gleicher Frage (wichtig für Klassifikation)
analysis_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


def _format_history_for_analysis(history: list[dict]) -> str:
    """
    Formatiert den Konversations-Verlauf als String für den Analyse-Prompt.
    Kürzer als beim Antwort-Agent - der Analyse-Agent braucht nur die Topics zu kennen.
    """
    if not history:
        return ""
    
    lines = ["Bisheriger Gesprächsverlauf:"]
    for msg in history:
        role = "User" if msg.get("role") == "user" else "Assistent"
        text = msg.get("text", "").strip()
        # Bot-Antworten kürzen, damit der Prompt nicht explodiert
        if role == "Assistent" and len(text) > 200:
            text = text[:200] + "..."
        lines.append(f"{role}: {text}")
    
    return "\n".join(lines)


def run_analysis_agent(state: WorkflowState) -> WorkflowState:
    """
    Führt die Anfrageanalyse durch und aktualisiert den State.
    
    Args:
        state: Der eingehende WorkflowState mit user_question
    
    Returns:
        Der gleiche State, angereichert mit Analyseergebnissen
    """
    state.log("AnfrageanalyseAgent", f"Analysiere Frage: '{state.user_question[:60]}...'")
    
    # Konversations-Verlauf in den User-Input einbauen
    history_text = _format_history_for_analysis(state.conversation_history)
    if history_text:
        full_input = f"{history_text}\n\nAktuelle Frage: {state.user_question}"
        state.log("AnfrageanalyseAgent", f"Nutze Verlauf mit {len(state.conversation_history)} Nachrichten")
    else:
        full_input = state.user_question
    
    # LLM-Chain bauen: Prompt → LLM → String
    chain = analysis_prompt | analysis_llm | StrOutputParser()
    
    try:
        # LLM aufrufen mit der erweiterten Eingabe
        raw_response = chain.invoke({"user_input": full_input})
        
        # Markdown-Codeblöcke ggf. wegstrippen
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1])
        
        # JSON parsen
        result = json.loads(cleaned)
        
        # State mit den Ergebnissen füllen
        state.language = result.get("language", "de")
        state.topics = result.get("topics", [])
        state.intent = result.get("intent", "other")
        state.decisions.off_topic = result.get("off_topic", False)
        state.decisions.clarification_needed = result.get("clarification_needed", False)
        
        state.log("AnfrageanalyseAgent",
                  f"Sprache={state.language}, Themen={state.topics}, Intent={state.intent}")
        
        if state.decisions.off_topic:
            state.log("AnfrageanalyseAgent",
                      f"OFF-TOPIC erkannt. Grund: {result.get('reasoning', 'keine Begründung')}")
        
        if state.decisions.clarification_needed:
            state.log("AnfrageanalyseAgent",
                      f"Anfrage zu unklar, Rückfrage nötig. Grund: {result.get('reasoning', '')}")
    
    except json.JSONDecodeError as e:
        state.log("AnfrageanalyseAgent",
                  f"JSON-Parse-Fehler: {e}. Rohausgabe: {raw_response[:200]}")
        state.language = "de"
        state.decisions.off_topic = False
        state.decisions.clarification_needed = False
    
    except Exception as e:
        state.log("AnfrageanalyseAgent", f"Unerwarteter Fehler: {e}")
        state.language = "de"
    
    return state