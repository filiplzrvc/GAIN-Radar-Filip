"""
Retrieval-Agent (Phase 3).
PDF-Referenz: Kap. 5.4 - Retrieval-Agent

Aufgabe:
- Bekommt den State mit der Nutzerfrage und dem Fach-Code
- Holt relevante Dokumente aus Pinecone (über den bestehenden Retriever)
- Schreibt die gefundenen Dokumente in den State
- Loggt die Aktion für die Trace
"""
from app.workflow.state import WorkflowState, RetrievedDocument
from app.core.retriever import get_context_retriever


def retrieve_documents(state: WorkflowState) -> WorkflowState:
    """
    Holt relevante Dokumente aus dem Vektorstore basierend auf der Nutzerfrage.
    
    Args:
        state: Workflow-State mit user_question und course
    
    Returns:
        Aktualisierter State mit retrieved_documents
    """
    
    # Defensive Checks: Gibt es überhaupt was zu retrieven?
    if state.decisions.off_topic:
        state.log("RetrievalAgent", "Übersprungen: Frage ist off-topic")
        return state
    
    if state.decisions.clarification_needed:
        state.log("RetrievalAgent", "Übersprungen: Klärung nötig")
        return state
    
    if not state.course:
        state.log("RetrievalAgent", "FEHLER: Kein Fach-Code im State")
        return state
    
    try:
        # Retriever für das richtige Fach holen (Namespace-Filter wirkt hier!)
        retriever = get_context_retriever(course_code=state.course)
        
        # Suche durchführen
        # Wir nehmen die Original-Frage. Alternative: state.topics als Query.
        docs = retriever.invoke(state.user_question)
        
        # LangChain-Documents in unsere RetrievedDocument-Struktur konvertieren
        retrieved = []
        for doc in docs:
            retrieved.append(RetrievedDocument(
                content=doc.page_content,
                source_name=doc.metadata.get("source_name", "Unbekannt"),
                page=doc.metadata.get("page_label", "?"),
                score=doc.metadata.get("score", None)
            ))
        
        state.retrieved_documents = retrieved
        state.log(
            "RetrievalAgent",
            f"{len(retrieved)} Dokumente aus Namespace '{state.course}' geholt"
        )
        
    except Exception as e:
        state.log("RetrievalAgent", f"FEHLER: {str(e)}")
        state.retrieved_documents = []
    
    return state