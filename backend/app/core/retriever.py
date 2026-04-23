import os
from langchain_community.embeddings import JinaEmbeddings
from langchain_pinecone import PineconeVectorStore

def get_context_retriever():
    embeddings = JinaEmbeddings(
        jina_api_key=os.getenv("JINA_API_KEY"),
        model_name="jina-embeddings-v3" 
    )
    

    embeddings.model_name = "jina-embeddings-v2-base-de" 
    
    index_name = os.getenv("PINECONE_INDEX_NAME")
    namespace = os.getenv("PINECONE_NAMESPACE")
    
    vectorstore = PineconeVectorStore(
        index_name=index_name, 
        embedding=embeddings,
        namespace=namespace if namespace else None
    )
    
    return vectorstore.as_retriever(search_kwargs={"k": 7})