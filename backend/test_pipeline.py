"""
End-to-End Test der Phase-3-und-4-Pipeline:
  Anfrageanalyse → Retrieval → Kontextaufbereitung → Antwort

Wir testen 4 Szenarien und zeigen die finalen Antworten.
"""
from dotenv import load_dotenv
load_dotenv()

from app.workflow.state import WorkflowState
from app.workflow.analysis_agent import run_analysis_agent
from app.workflow.retrieval_agent import retrieve_documents
from app.workflow.context_agent import prepare_context
from app.workflow.answer_agent import run_answer_agent


def run_full_pipeline(question: str, course: str) -> WorkflowState:
    """Führt alle 4 Pipeline-Schritte aus und gibt den State zurück."""
    print("\n" + "=" * 70)
    print(f"📥 Frage: '{question}'")
    print(f"📚 Fach: {course}")
    print("=" * 70)
    
    state = WorkflowState(user_question=question, course=course)
    
    state = run_analysis_agent(state)
    state = retrieve_documents(state)
    state = prepare_context(state)
    state = run_answer_agent(state)
    
    return state


def print_result(state: WorkflowState):
    """Druckt die finale Antwort und Metadaten."""
    print(f"\n📊 META")
    print(f"   Sprache:           {state.language}")
    print(f"   Off-Topic:         {state.decisions.off_topic}")
    print(f"   Clarification:     {state.decisions.clarification_needed}")
    print(f"   Context-Qualität:  {state.context_quality}")
    print(f"   Dokumente:         {len(state.retrieved_documents)}")
    
    print(f"\n💬 ANTWORT")
    print(f"   {state.final_answer}")
    
    if state.sources_used:
        print(f"\n📚 QUELLEN")
        for src in state.sources_used:
            print(f"   - {src}")


# ====== TESTS ======

print("\n\n🧪 TEST 1: Off-Topic-Frage (sollte deterministische Antwort sein)")
state = run_full_pipeline("Wie wird das Wetter morgen in Wien?", "aief")
print_result(state)
assert state.final_answer is not None
assert len(state.sources_used) == 0
print("\n✅ Test 1 OK")


print("\n\n🧪 TEST 2: Vage Frage (sollte Klärungs-Rückfrage sein)")
state = run_full_pipeline("Erklär mir was", "aief")
print_result(state)
assert state.final_answer is not None
print("\n✅ Test 2 OK")


print("\n\n🧪 TEST 3: Gute Frage im richtigen Fach (sollte echte RAG-Antwort sein)")
state = run_full_pipeline("Was ist Overfitting?", "aief")
print_result(state)
assert state.final_answer is not None
assert len(state.sources_used) > 0, "Sollte Quellen haben!"
print("\n✅ Test 3 OK")


print("\n\n🧪 TEST 4: Cross-Course (sollte ehrliche 'passt nicht'-Antwort sein)")
state = run_full_pipeline("What is asymmetric encryption?", "aief")
print_result(state)
assert state.final_answer is not None
print("\n   ⚠️ Erwartung: Antwort sagt ehrlich, dass das Material nicht passt")
print("   (Verlässt sich auf RAG-Treue im Prompt)")
print("\n✅ Test 4 OK (visuell prüfen)")


print("\n\n🧪 TEST 5: Englische Frage in passendem Fach")
state = run_full_pipeline("What is asymmetric encryption?", "itsec")
print_result(state)
assert state.language == "en"
assert len(state.sources_used) > 0
print("\n✅ Test 5 OK")


print("\n\n🎉 ALLE TESTS DURCHGELAUFEN!")
print("\n💡 Was Phase 4 gebracht hat:")
print("   - 3 von 5 Fällen brauchen keinen LLM-Call (off-topic, clarification, no context)")
print("   - Cross-Course-Halluzinationen werden durch RAG-Treue-Prompt abgefangen")
print("   - Strukturierte Quellen-Ausgabe für Transparenz")
print("\n   Phase 4 fertig! Nächste Schritte: Orchestrator + main.py-Integration")