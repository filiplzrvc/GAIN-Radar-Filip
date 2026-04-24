import os
from langchain_community.embeddings import JinaEmbeddings
from langchain_pinecone import PineconeVectorStore

EMBEDDING_MODEL = "jina-embeddings-v2-base-de"  # 768 Dimensionen, deutsches Modell
RETRIEVAL_TOP_K = 7  # Wie viele Dokumente pro Anfrage zurückgegeben werden


def get_context_retriever():
    """
    Erstellt einen Retriever, der semantisch ähnliche Dokumente aus 
    Pinecone zurückgibt.
    
    Das Embedding-Modell MUSS zum Modell passen, mit dem die Dokumente
    ursprünglich indexiert wurden (jina-embeddings-v2-base-de, 768 dim).
    """
    embeddings = JinaEmbeddings(
        jina_api_key=os.getenv("JINA_API_KEY"),
        model_name=EMBEDDING_MODEL
    )
    
    index_name = os.getenv("PINECONE_INDEX_NAME")
    namespace = os.getenv("PINECONE_NAMESPACE")  # leer/None ist OK
    
    vectorstore = PineconeVectorStore(
        index_name=index_name,
        embedding=embeddings,
        namespace=namespace if namespace else None
    )
    
    return vectorstore.as_retriever(search_kwargs={"k": RETRIEVAL_TOP_K})