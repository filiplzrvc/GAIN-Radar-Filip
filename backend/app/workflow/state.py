"""WorkflowState: Der zentrale State, der durch alle Agenten wandert.
Dieses Objekt wird durch ALLE Agenten gereicht und sammelt auf dem Weg
alle Informationen: Nutzerfrage, erkannter Modus, geholte Dokumente,
Entscheidungen der Agenten, finale Antwort, etc.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid


@dataclass
class RetrievedDocument:
    """Ein einzelnes Dokument-Chunk, das vom Retrieval-Agent geholt wurde."""
    content: str                    # Der eigentliche Text
    source_name: str                # z.B. "AIEF_Modul1_Grundlagen.pdf"
    page: Optional[str] = None      # z.B. "13" oder "Kapitel 4.2"
    score: Optional[float] = None   # Ähnlichkeits-Score von Pinecone


@dataclass
class AgentDecisions:
    """
    Sammelt alle Entscheidungen, die Agenten während des Workflows treffen.
    """
    off_topic: bool = False              # Ist die Frage themenfremd?
    clarification_needed: bool = False   # Muss Nutzer nachgefragt werden?
    mode_applied: Optional[str] = None   # Welcher Lernmodus wurde verwendet?
    context_sufficient: bool = True      # Reicht der Kontext für eine Antwort?


@dataclass
class WorkflowState:
    """
    Der zentrale State, der durch alle Agenten wandert.
    
    Die Reihenfolge der Felder spiegelt den typischen Workflow wider:
    1. Eingabe vom User
    2. Anfrageanalyse-Agent füllt: topics, language, intent
    3. Retrieval-Agent füllt: retrieved_documents
    4. Kontextaufbereitungs-Agent füllt: prepared_context
    5. Didaktischer Agent beeinflusst: Antwortstruktur
    6. Antwort-Agent füllt: final_answer
    7. Session-Memory-Agent speichert alles
    """
    
    # 1. EINGABE 
    user_question: str                                       # Die Frage des Studierenden
    course: str = ""                                         # Fach-Code (z.B. "aief", "itsec", "swen")
    mode: str = "tutor"                                      # tutor, quiz, flashcards, summary
    session_id: str = field(default_factory=lambda: f"sess_{uuid.uuid4().hex[:8]}")
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    
    # 2. ANFRAGEANALYSE 
    language: Optional[str] = None                           # "de", "en", ...
    topics: list[str] = field(default_factory=list)          # ["Machine Learning", "Overfitting"]
    intent: Optional[str] = None                             # "definition", "explanation", ...
    
    # 3. RETRIEVAL 
    retrieved_documents: list[RetrievedDocument] = field(default_factory=list)
    
    # 4. KONTEXTAUFBEREITUNG 
    prepared_context: Optional[str] = None                   # Zusammengeführter, gefilterter Kontext
    context_quality: str = "unknown"                         # "sufficient", "insufficient", "none"
    
    # 5. ENTSCHEIDUNGEN (werden von verschiedenen Agenten gefüllt) 
    decisions: AgentDecisions = field(default_factory=AgentDecisions)
    
    # 6. FINALE ANTWORT 
    final_answer: Optional[str] = None
    sources_used: list[str] = field(default_factory=list)    # Formatierte Quellen-Strings
    
    # 7. DEBUG / LOGGING
    # Jeder Agent kann hier reinschreiben, was er gemacht hat - für Nachvollziehbarkeit
    trace: list[str] = field(default_factory=list)
    
    
    def log(self, agent_name: str, message: str) -> None:
        """
        Hilfsmethode für Agenten, um ihre Aktivitäten zu dokumentieren.
        """
        entry = f"[{agent_name}] {message}"
        self.trace.append(entry)
        print(f"{entry}")  # Live-Ausgabe in die Konsole zum Debuggen
    
    
    def to_dict(self) -> dict:
        """
        Konvertiert den State in ein Dictionary - wird später für die
        JSON-Speicherung im Session-Memory gebraucht
        """
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "user_question": self.user_question,
            "course": self.course,
            "mode": self.mode,
            "language": self.language,
            "topics": self.topics,
            "intent": self.intent,
            "retrieved_documents": [
                {
                    "source_name": doc.source_name,
                    "page": doc.page,
                    "score": doc.score
                }
                for doc in self.retrieved_documents
            ],
            "context_quality": self.context_quality,
            "agent_decisions": {
                "off_topic": self.decisions.off_topic,
                "clarification_needed": self.decisions.clarification_needed,
                "mode_applied": self.decisions.mode_applied,
                "context_sufficient": self.decisions.context_sufficient,
            },
            "final_answer": self.final_answer,
            "sources_used": self.sources_used,
            "trace": self.trace,
        }