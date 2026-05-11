"""
Retrieval-Agent 

Aufgabe:
- Bekommt den State mit der Nutzerfrage und dem Fach
- Holt relevante Dokumente aus Pinecone (über den bestehenden Retriever)
- Schreibt die gefundenen Dokumente in den State
- Loggt die Aktion für die Trace
"""
from app.workflow.state import WorkflowState, RetrievedDocument
from app.core.retriever import get_context_retriever


def retrieve_documents(state: WorkflowState) -> WorkflowState:
    # Defensive Checks
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
        # Retriever für das richtige Fach holen 
        retriever = get_context_retriever(course_code=state.course)
        
        # Such-Query bauen: bei Folgefragen die Topics aus der Anfrageanalyse
        # mit der Original-Frage kombinieren, damit Pinecone den richtigen Kontext findet.
        # Beispiel: "Gib mir ein Beispiel" + Topics ["Overfitting"] 
        #        → "Gib mir ein Beispiel Overfitting"
        if state.conversation_history and state.topics:
            search_query = state.user_question + " " + " ".join(state.topics)
            state.log("RetrievalAgent", f"Folgefrage: erweitere Query mit Topics → '{search_query[:80]}'")
        else:
            search_query = state.user_question
        
        # Suche durchführen
        docs = retriever.invoke(search_query)
        
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