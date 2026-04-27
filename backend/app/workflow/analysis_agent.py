"""
Anfrageanalyse-Agent

Analysiert eine eingehende Nutzerfrage und füllt im WorkflowState:
- language: Erkannte Sprache
- topics: Extrahierte Themen
- intent: Nutzerintention
- decisions.off_topic: Ist die Frage themenfremd?
- decisions.clarification_needed: Muss nachgefragt werden?

ERLAUBTE AKTIONEN:
- Sprache, Themen, Intent klassifizieren
- Off-Topic-Entscheidung treffen

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


def run_analysis_agent(state: WorkflowState) -> WorkflowState:
    """
    Führt die Anfrageanalyse durch und aktualisiert den State.
    
    Args:
        state: Der eingehende WorkflowState mit user_question
    
    Returns:
        Der gleiche State, angereichert mit Analyseergebnissen
    """
    state.log("AnfrageanalyseAgent", f"Analysiere Frage: '{state.user_question[:60]}...'")
    
    # LLM-Chain bauen: Prompt → LLM → String
    chain = analysis_prompt | analysis_llm | StrOutputParser()
    
    try:
        # LLM aufrufen
        raw_response = chain.invoke({"user_input": state.user_question})
        
        # Manchmal gibt das LLM Markdown-Codeblöcke zurück: ```json ... ```
        # Die strippen wir raus, damit json.loads klappt
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            # Erste und letzte Zeile (die ```) entfernen
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
        
        # Logging - so sieht man in der Konsole genau, was der Agent entschieden hat
        state.log("AnfrageanalyseAgent", 
                  f"Sprache={state.language}, Themen={state.topics}, Intent={state.intent}")
        
        if state.decisions.off_topic:
            state.log("AnfrageanalyseAgent", 
                      f"⚠️ OFF-TOPIC erkannt. Grund: {result.get('reasoning', 'keine Begründung')}")
        
        if state.decisions.clarification_needed:
            state.log("AnfrageanalyseAgent",
                      f"⚠️ Anfrage zu unklar, Rückfrage nötig. Grund: {result.get('reasoning', '')}")
    
    except json.JSONDecodeError as e:
        # Falls das LLM kein gültiges JSON zurückgibt → defensiv fallbacken
        state.log("AnfrageanalyseAgent", 
                  f"JSON-Parse-Fehler: {e}. Rohausgabe: {raw_response[:200]}")
        # Fallback: Annehmen, dass es eine normale, topic-relevante Frage ist
        state.language = "de"
        state.decisions.off_topic = False
        state.decisions.clarification_needed = False
    
    except Exception as e:
        state.log("AnfrageanalyseAgent", f"Unerwarteter Fehler: {e}")
        # Defensives Fallback - lieber weitermachen als abbrechen
        state.language = "de"
    
    return state