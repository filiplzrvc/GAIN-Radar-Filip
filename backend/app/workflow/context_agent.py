"""
Kontextaufbereitungs-Agent 

Aufgabe:
- Bekommt die retrievten Dokumente
- BEWERTET, ob der Kontext für die Frage ausreichend ist
- Filtert Müll-Chunks raus (zu kurz, doppelt, irrelevant)
- Baut einen strukturierten Context-String für das Antwort-LLM
- Setzt context_quality im State, die der Antwort-Agent nutzt
"""
from langsmith import traceable
from app.workflow.state import WorkflowState

COURSE_TOPIC_HINTS = {
    "aief": ["machine learning", "neural network", "ki", "künstliche intelligenz",
             "algorithmus", "training", "modell", "klassifikation", "deep learning",
             "overfitting", "clustering", "regression", "backpropagation"],
    "swen": ["software", "design pattern", "mvc", "solid", "agile", "scrum",
             "refactoring", "testing", "continuous integration", "architektur",
             "objektorientiert", "clean code", "repository", "deployment"],
    "itsec": ["sicherheit", "security", "verschlüsselung", "angriff", "firewall",
              "authentifizierung", "kryptographie", "vulnerability", "phishing",
              "sql injection", "xss", "penetration", "zertifikat", "schlüssel",
              "cryptography", "encryption", "certificate", "public key", "pki"],
}

# Schwellwerte für Qualitätsbewertung
MIN_CHUNK_LENGTH = 30
MIN_DOCS_FOR_GOOD_CONTEXT = 2
MIN_TOTAL_CONTEXT_LENGTH = 300


def _is_course_relevant(state: WorkflowState) -> bool:
    """Prüft ob die Frage thematisch zum Kurs passt."""
    course = state.course
    if course not in COURSE_TOPIC_HINTS:
        return True

    question_lower = state.user_question.lower()
    topics_lower = [t.lower() for t in (state.topics or [])]
    combined = question_lower + " " + " ".join(topics_lower)

    return any(kw in combined for kw in COURSE_TOPIC_HINTS[course])


@traceable(name="Kontext-Filter")
def prepare_context(state: WorkflowState) -> WorkflowState:
    """
    Filtert und bewertet den Kontext, bereitet ihn für den Antwort-Agent vor.
    """
    if state.decisions.off_topic or state.decisions.clarification_needed:
        state.log("ContextAgent", "Übersprungen: nicht anwendbar")
        state.context_quality = "none"
        state.decisions.context_sufficient = False
        return state

    docs = state.retrieved_documents

    # Filter 1: Zu kurze Chunks raus
    filtered = [d for d in docs if len(d.content.strip()) >= MIN_CHUNK_LENGTH]
    removed_short = len(docs) - len(filtered)

    # Filter 2: Duplikate raus (gleiche Quelle + Seite)
    seen = set()
    deduplicated = []
    for d in filtered:
        key = (d.source_name, d.page)
        if key not in seen:
            seen.add(key)
            deduplicated.append(d)
    removed_dupes = len(filtered) - len(deduplicated)

    # Qualitätsbewertung
    total_length = sum(len(d.content) for d in deduplicated)

    if len(deduplicated) == 0:
        quality = "none"
        reason = "Keine verwertbaren Dokumente nach Filterung"
        state.decisions.context_sufficient = False
    elif len(deduplicated) < MIN_DOCS_FOR_GOOD_CONTEXT or total_length < MIN_TOTAL_CONTEXT_LENGTH:
        quality = "insufficient"
        reason = f"Nur {len(deduplicated)} Dokumente / {total_length} Zeichen"
        state.decisions.context_sufficient = False
    else:
        quality = "sufficient"
        reason = f"{len(deduplicated)} Dokumente / {total_length} Zeichen"
        state.decisions.context_sufficient = True

    # Kurs-Relevanz prüfen — auch wenn Chunks gefunden wurden
    if quality == "sufficient" and not _is_course_relevant(state):
        quality = "none"
        reason = "Thema passt nicht zum Kurs"
        state.decisions.context_sufficient = False
        state.log("ContextAgent", "Thema passt nicht zum Kurs → Qualität auf 'none' gesetzt")

    # Strukturierten Kontext-Text bauen
    context_parts = []
    for i, doc in enumerate(deduplicated, 1):
        header = f"[Quelle {i}: {doc.source_name}, Seite {doc.page}]"
        context_parts.append(f"{header}\n{doc.content.strip()}")

    prepared_context = "\n\n---\n\n".join(context_parts)

    state.prepared_context = prepared_context
    state.context_quality = quality
    state.retrieved_documents = deduplicated

    state.log(
        "ContextAgent",
        f"Qualität: {quality}. {reason}. Entfernt: {removed_short} kurz, {removed_dupes} Duplikate."
    )

    return state