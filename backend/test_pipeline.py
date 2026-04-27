'''
Testing der Phase-3-und-4-Pipeline:
  Anfrageanalyse → Retrieval → Kontextaufbereitung → Antwort
'''

from dotenv import load_dotenv
load_dotenv()

from app.workflow.state import WorkflowState
from app.workflow.orchestrator import process_request


def run_full_pipeline(question: str, course: str) -> WorkflowState:
    """Führt die gesamte Pipeline über den Orchestrator aus."""
    print("\n" + "=" * 70)
    print(f"Frage: '{question}'")
    print(f"Fach: {course}")
    print("=" * 70)
    
    return process_request(question=question, course=course)


def print_result(state: WorkflowState):
    #Finale Antwort und Metadaten
    print(f"\n META")
    print(f"   Sprache:           {state.language}")
    print(f"   Off-Topic:         {state.decisions.off_topic}")
    print(f"   Clarification:     {state.decisions.clarification_needed}")
    print(f"   Context-Qualität:  {state.context_quality}")
    print(f"   Dokumente:         {len(state.retrieved_documents)}")
    
    print(f"\n ANTWORT")
    print(f"   {state.final_answer}")
    
    if state.sources_used:
        print(f"\n QUELLEN")
        for src in state.sources_used:
            print(f"   - {src}")


#TESTS 

print("\n\n TEST 1: Off-Topic-Frage ")
state = run_full_pipeline("Wie wird das Wetter morgen in Wien?", "aief")
print_result(state)
assert state.final_answer is not None
assert len(state.sources_used) == 0
print("\n Test 1 OK")


print("\n\n TEST 2: Vage Frage ")
state = run_full_pipeline("Erklär mir was", "aief")
print_result(state)
assert state.final_answer is not None
print("\n Test 2 OK")


print("\n\n TEST 3: Gute Frage im richtigen Fach ")
state = run_full_pipeline("Was ist Overfitting?", "aief")
print_result(state)
assert state.final_answer is not None
assert len(state.sources_used) > 0, "Sollte Quellen haben!"
print("\n Test 3 OK")


print("\n\n TEST 4: Cross-Course ")
state = run_full_pipeline("What is asymmetric encryption?", "aief")
print_result(state)
assert state.final_answer is not None
print("\n  Erwartung: Antwort sagt ehrlich, dass das Material nicht passt")
print("   (Verlässt sich auf RAG-Treue im Prompt)")
print("\n Test 4 OK ")


print("\n\n TEST 5: Englische Frage in passendem Fach")
state = run_full_pipeline("What is asymmetric encryption?", "itsec")
print_result(state)
assert state.language == "en"
assert len(state.sources_used) > 0
print("\n Test 5 OK")