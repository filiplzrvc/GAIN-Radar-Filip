'''
Test für den Anfrageanalyse-Agenten.
Testet verschiedene Arten von Fragen, um das Verhalten zu prüfen.
'''

from dotenv import load_dotenv
load_dotenv()

from app.workflow.state import WorkflowState
from app.workflow.analysis_agent import run_analysis_agent


# Verschiedene Testfälle 
test_cases = [
    # Normale Fachfrage
    "Šta je overfitting u mašinskom učenju?",
    
    # Englische Fachfrage
    "Objasni gradijentni spust u neuronskim mrežama.",
    
    # OFF-TOPIC
    "Sta da jedem danas za rucak?",
    
    # Zu vage
    "Pomozi mi",
    
    # Kontext-nah aber informell
    "Daj mi kratak pregled režima učenja kod gradient boostinga."
]


for question in test_cases:
    print("\n" + "=" * 70)
    print(f" Frage: {question}")
    print("=" * 70)
    
    # State erstellen
    state = WorkflowState(user_question=question, mode="tutor")
    
    # Agent laufen lassen
    state = run_analysis_agent(state)
    
    # Ergebnisse anzeigen
    print(f"\n Ergebnis:")
    print(f"   Sprache:            {state.language}")
    print(f"   Themen:             {state.topics}")
    print(f"   Intent:             {state.intent}")
    print(f"   Off-Topic:          {state.decisions.off_topic}")
    print(f"   Rückfrage nötig:    {state.decisions.clarification_needed}")