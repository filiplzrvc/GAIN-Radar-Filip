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
- Unterstützt beliebige Sprachen via LLM-Übersetzung
"""
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from app.core.prompts import ANSWER_SYSTEM_PROMPT
from app.workflow.state import WorkflowState


answer_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)



# DETERMINISTISCHE ANTWORTEN (kein LLM nötig)
# DE + EN vordefiniert, andere Sprachen via _translate()

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

# Basis-Text für "passt nicht"-Übersetzung (immer Deutsch als Quelle)
_NO_MATCH_BASE_DE = (
    "Im verfügbaren Kursmaterial finde ich zu deiner Frage keine direkt passenden "
    "Informationen. Möchtest du die Frage in einem anderen Fach stellen oder "
    "dein Thema präzisieren?"
)



# HILFSFUNKTIONEN

def _get_response(responses: dict, language: str) -> str:
    """
    Wählt die Antwort in der passenden Sprache.
    DE/EN sind vordefiniert, andere Sprachen fallen auf EN zurück.
    Für vollständige Mehrsprachigkeit: _translate() nutzen.
    """
    return responses.get(language, responses.get("en", responses["de"]))


def _translate(text: str, target_language: str) -> str:
    """
    Übersetzt einen fixen Text in eine beliebige Zielsprache via LLM.
    Funktioniert für ALLE Sprachen (Serbisch, Chinesisch, Russisch, Türkisch, etc.)
    
    Bei Deutsch: direkte Rückgabe ohne LLM-Call.
    Bei Fehler: englischer Fallback.
    """
    if target_language == "de":
        return text  # Kein LLM-Call nötig
    
    try:
        translate_prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are a translator. Translate the given text into the target language. "
             "Output ONLY the translation, nothing else. No explanations, no comments."),
            ("human",
             f"Translate to language code '{target_language}':\n\n{{text}}")
        ])
        
        translate_chain = translate_prompt | answer_llm | StrOutputParser()
        translated = translate_chain.invoke({"text": text})
        return translated.strip()
    
    except Exception:
        # Fallback: englische Version
        return (
            "I couldn't find directly relevant information about your question "
            "in the available course material. Would you like to ask your question "
            "in a different subject or refine your topic?"
        )


def _format_history_for_prompt(history: list[dict]) -> str:
    """
    Formatiert den Konversations-Verlauf als String für das LLM.
    
    Beispiel-Output:
        Bisheriger Gesprächsverlauf:
        User: Was ist Overfitting?
        Assistent: Overfitting tritt auf, wenn ein Modell...
        User: Gib mir ein Beispiel
    """
    if not history:
        return ""
    
    lines = ["Bisheriger Gesprächsverlauf:"]
    for msg in history:
        role = "User" if msg.get("role") == "user" else "Assistent"
        text = msg.get("text", "").strip()
        lines.append(f"{role}: {text}")
    
    return "\n".join(lines)


def _format_sources(state: WorkflowState) -> list[str]:
    """Erstellt die Quellen-Liste aus den retrievten Dokumenten."""
    sources = set()
    for doc in state.retrieved_documents:
        sources.add(f"{doc.source_name} (S. {doc.page})")
    return sorted(list(sources))


def _has_no_match(answer: str) -> bool:
    """
    Prüft, ob die LLM-Antwort signalisiert, dass das Material nicht passt.
    Erkennt sowohl deutsche als auch englische Formulierungen.
    """
    if not answer:
        return False
    
    answer_lower = answer.lower()
    
    signals = [
        # Deutsch
        "finde ich zu deiner frage keine",
        "finde ich dazu keine",
        "keine direkt passenden informationen",
        "keine ausreichenden informationen",
        "nicht im kursmaterial",
        "im verfügbaren kursmaterial finde ich",
        # Englisch
        "i couldn't find",
        "i could not find",
        "i do not find",
        "no information about",
        "not covered in",
        "no directly relevant information",
        "do not find directly relevant",
        "cannot find any information",
        "in the available course material, i do not find",
    ]
    
    return any(signal in answer_lower for signal in signals)


def _generate_llm_answer(state: WorkflowState, with_warning: bool = False) -> str:
    """
    Ruft das LLM auf, um eine Antwort aus dem prepared_context zu erzeugen.
    
    Wählt je nach state.mode den passenden didaktischen Prompt:
    - quiz     → QUIZ_SYSTEM_PROMPT
    - flashcard → FLASHCARD_SYSTEM_PROMPT  
    - summary  → SUMMARY_SYSTEM_PROMPT
    - tutor    → ANSWER_SYSTEM_PROMPT (Standard)
    """
    from app.core.prompts import (
        QUIZ_SYSTEM_PROMPT,
        FLASHCARD_SYSTEM_PROMPT,
        SUMMARY_SYSTEM_PROMPT,
        ANSWER_SYSTEM_PROMPT
    )

    # Sprache dynamisch bestimmen
    language = state.language or "de"
    language_map = {"de": "German", "en": "English"}
    language_name = language_map.get(language, f"the language with ISO code '{language}'")

    # Sprach-Regel die vor jeden Prompt gesetzt wird
    language_rule = (
        f"CRITICAL LANGUAGE RULE: You MUST respond ONLY in {language_name}. "
        f"This is non-negotiable. Do NOT respond in any other language.\n\n"
    )

    # Richtigen Prompt je nach Modus wählen
    mode = state.mode or "tutor"

    if mode == "quiz":
        base_prompt = QUIZ_SYSTEM_PROMPT
        state.log("AntwortAgent", "Nutze Quiz-Prompt")
    elif mode == "flashcard":
        base_prompt = FLASHCARD_SYSTEM_PROMPT
        state.log("AntwortAgent", "Nutze Flashcard-Prompt")
    elif mode == "summary":
        base_prompt = SUMMARY_SYSTEM_PROMPT
        state.log("AntwortAgent", "Nutze Summary-Prompt")
    else:
        base_prompt = ANSWER_SYSTEM_PROMPT
        state.log("AntwortAgent", "Nutze Tutor-Prompt")

    dynamic_system = language_rule + base_prompt

    dynamic_prompt = ChatPromptTemplate.from_messages([
        ("system", dynamic_system),
        ("human", "{user_input}")
    ])

    chain = dynamic_prompt | answer_llm | StrOutputParser()

    # User-Input zusammenbauen
    user_input_parts = []

    # Konversations-Verlauf einfügen falls vorhanden
    history_text = _format_history_for_prompt(state.conversation_history)
    if history_text:
        user_input_parts.append(history_text)
        user_input_parts.append("")

    # Warnung bei insufficient Kontext
    if with_warning:
        user_input_parts.append(
            "[Hinweis: Der Kontext könnte unzureichend sein. "
            "Antworte nur, was wirklich belegbar ist, sonst sage es ehrlich.]"
        )
        user_input_parts.append("")

    # Aktuelle Frage mit Sprach-Erinnerung
    user_input_parts.append(
        f"Aktuelle Frage ({language_name} only!): {state.user_question}"
    )
    user_input_parts.append(
        f"[REMINDER: Your entire response MUST be in {language_name}. {language_name} only.]"
    )

    full_user_input = "\n".join(user_input_parts)

    return chain.invoke(
        {
            "context": state.prepared_context or "",
            "user_input": full_user_input
        },
        config={"run_name": f"3. Antwort-Generierung ({mode})"}
    )

def _handle_llm_answer(state: WorkflowState, with_warning: bool = False) -> None:
    """
    Generiert eine LLM-Antwort, prüft ob sie "passt nicht" bedeutet,
    und setzt final_answer + sources_used entsprechend.
    
    Bei "passt nicht": übersetzt die fixe Nachricht in die User-Sprache.
    Bei echter Antwort: Quellen werden angezeigt.
    """
    language = state.language or "de"
    
    llm_answer = _generate_llm_answer(state, with_warning=with_warning)
    
    if _has_no_match(llm_answer):
        # LLM sagt "passt nicht" → deterministische Antwort in User-Sprache
        state.final_answer = _translate(_NO_MATCH_BASE_DE, language)
        state.sources_used = []
        state.log("AntwortAgent", "Keine Quellen — 'passt nicht', Antwort übersetzt")
    else:
        # Echte Antwort aus dem Material
        state.final_answer = llm_answer
        state.sources_used = _format_sources(state)



# HAUPT-FUNKTION

def run_answer_agent(state: WorkflowState) -> WorkflowState:
    """
    Wählt die passende Antwortstrategie und füllt final_answer + sources_used.
    
    5 Strategien:
    1. Off-Topic    → deterministische Ablehnung (kein LLM)
    2. Clarification → deterministische Rückfrage (kein LLM)
    3. No Context   → deterministische "nichts gefunden" (kein LLM)
    4. Insufficient → LLM mit Vorsicht-Warnung
    5. Sufficient   → normale RAG-Antwort
    """
    state.log("AntwortAgent", "Wähle Antwortstrategie...")
    language = state.language or "de"
    
    # STRATEGIE 1: Off-Topic
    if state.decisions.off_topic:
        state.final_answer = _get_response(OFF_TOPIC_RESPONSES, language)
        state.sources_used = []
        state.log("AntwortAgent", "Strategie: Off-Topic-Ablehnung (kein LLM)")
        return state
    
    # STRATEGIE 2: Klärung nötig
    if state.decisions.clarification_needed:
        state.final_answer = _get_response(CLARIFICATION_RESPONSES, language)
        state.sources_used = []
        state.log("AntwortAgent", "Strategie: Rückfrage (kein LLM)")
        return state
    
    # STRATEGIE 3: Kein Kontext gefunden
    if state.context_quality == "none":
        state.final_answer = _get_response(NO_CONTEXT_RESPONSES, language)
        state.sources_used = []
        state.log("AntwortAgent", "Strategie: Kein Kontext (kein LLM)")
        return state
    
    # STRATEGIE 4: Wenig Kontext — LLM mit Warnung
    if state.context_quality == "insufficient":
        state.log("AntwortAgent", "Strategie: LLM mit Insufficient-Warnung")
        try:
            _handle_llm_answer(state, with_warning=True)
        except Exception as e:
            state.log("AntwortAgent", f"LLM-Fehler: {e}")
            state.final_answer = _get_response(NO_CONTEXT_RESPONSES, language)
            state.sources_used = []
        return state
    
    # STRATEGIE 5: Guter Kontext — normale RAG-Antwort
    state.log("AntwortAgent", "Strategie: Normale RAG-Antwort")
    try:
        _handle_llm_answer(state, with_warning=False)
    except Exception as e:
        state.log("AntwortAgent", f"LLM-Fehler: {e}")
        state.final_answer = (
            "Es ist ein Fehler bei der Antwort-Generierung aufgetreten. "
            "Bitte versuche es erneut."
        )
        state.sources_used = []
    
    return state