"""Kleiner Test ob der WorkflowState funktioniert."""
from app.workflow.state import WorkflowState, RetrievedDocument

# State wie vom Frontend kommend erstellen
state = WorkflowState(
    user_question="Was ist Overfitting?",
    mode="tutor"
)

# Ein Agent loggt seine Aktivität
state.log("AnfrageanalyseAgent", "Sprache erkannt: Deutsch")

# Ein anderer Agent füllt Felder
state.topics = ["Machine Learning", "Overfitting"]
state.language = "de"

# Noch ein Agent fügt ein Dokument hinzu
state.retrieved_documents.append(
    RetrievedDocument(
        content="Overfitting tritt auf, wenn...",
        source_name="AIEF_Modul3.pdf",
        page="12"
    )
)

# Finales Ergebnis anzeigen
import json
print("\n📦 Finaler State als JSON:\n")
print(json.dumps(state.to_dict(), indent=2, ensure_ascii=False))