#Tutor-Agent 
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from app.core.prompts import tutor_prompt
from app.core.retriever import get_context_retriever

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)


def get_tutor_response(user_input: str, course_code: str) -> dict:
    """
    Generiert eine Tutor-Antwort basierend auf dem ausgewählten Fach.
    
    Args:
        user_input: Die Frage des Studierenden
        course_code: Der Fach-Namespace (z.B. "aief")
    """
    retriever = get_context_retriever(course_code=course_code)
    docs = retriever.invoke(user_input)
    
    source_list = []
    for doc in docs:
        name = doc.metadata.get("source_name", "Unbekanntes Skript")
        page = doc.metadata.get("page_label", "?")
        source_list.append(f"{name} (S. {page})")
    
    unique_sources = list(set(source_list))
    
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)
    
    chain = (
        {"context": lambda x: format_docs(docs), "user_input": RunnablePassthrough()}
        | tutor_prompt
        | llm
        | StrOutputParser()
    )
    
    response_text = chain.invoke(user_input)
    
    return {
        "reply": response_text,
        "sources": unique_sources
    }