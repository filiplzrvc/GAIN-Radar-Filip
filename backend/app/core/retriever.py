"""
Retriever - holt Dokumente aus Pinecone mit Namespace-Support.
"""
import os
from functools import lru_cache
from langchain_community.embeddings import JinaEmbeddings
from langchain_pinecone import PineconeVectorStore

EMBEDDING_MODEL = "jina-embeddings-v2-base-de"
RETRIEVAL_TOP_K = 5


@lru_cache(maxsize=1)
def _get_embeddings():
    """Embeddings-Instanz wird nur einmal erstellt (gecached)."""
    print("🔧 Initialisiere Jina Embeddings (einmalig)...")
    return JinaEmbeddings(
        jina_api_key=os.getenv("JINA_API_KEY"),
        model_name=EMBEDDING_MODEL
    )


@lru_cache(maxsize=10)
def _get_vectorstore_for_namespace(namespace: str):
    """VectorStore pro Namespace gecached."""
    print(f"🔧 Initialisiere VectorStore für Namespace '{namespace}' (einmalig)...")
    return PineconeVectorStore(
        index_name=os.getenv("PINECONE_INDEX_NAME"),
        embedding=_get_embeddings(),
        namespace=namespace
    )


def get_context_retriever(course_code: str, top_k: int = RETRIEVAL_TOP_K):
    """
    Gibt einen Retriever zurück, der nur im Namespace eines Fachs sucht.
    
    Args:
        course_code: Der Fach-Code (z.B. "aief", "itsec", "swen")
        top_k: Wie viele Dokumente max. zurückgegeben werden sollen
    
    Raises:
        ValueError: Wenn course_code leer ist
    """
    if not course_code or not course_code.strip():
        raise ValueError(
            "course_code darf nicht leer sein. "
            "Gültige Werte: 'aief', 'itsec', 'swen'"
        )
    
    vectorstore = _get_vectorstore_for_namespace(course_code)
    return vectorstore.as_retriever(search_kwargs={"k": top_k})