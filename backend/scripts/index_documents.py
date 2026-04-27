"""
Re-Indexierung: Liest PDFs aus data/<course_code>/ und legt sie 
mit Embeddings in den passenden Pinecone-Namespace.

  python scripts/index_documents.py              # alle Fächer aus courses.json
  python scripts/index_documents.py --course aief   # nur ein Fach
  python scripts/index_documents.py --dry-run    # nur anzeigen, nichts hochladen
"""
import os
import sys
import json
import argparse
import time
from pathlib import Path
from dotenv import load_dotenv


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import JinaEmbeddings
from langchain_pinecone import PineconeVectorStore

load_dotenv()

#Konfiguration
EMBEDDING_MODEL = "jina-embeddings-v2-base-de"
CHUNK_SIZE = 1000           # Zeichen pro Chunk
CHUNK_OVERLAP = 200         # Überlappung zwischen Chunks
BATCH_SIZE = 50             # Wie viele Chunks gleichzeitig hochladen


def load_courses_config():
    #Lädt die Fach-Konfiguration aus config/courses.json.
    config_path = Path(__file__).parent.parent / "config" / "courses.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)["courses"]


def index_course(course_code: str, course_name: str, dry_run: bool = False):
    #Indexiert alle PDFs eines Fachs in den entsprechenden Namespace.
    
    data_dir = Path(__file__).parent.parent / "data" / course_code
    
    if not data_dir.exists():
        print(f"Ordner {data_dir} existiert nicht. Skip.")
        return
    
    # PDFs finden
    pdf_files = sorted(data_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"Keine PDFs in {data_dir} gefunden. Skip.")
        return
    
    print(f"\n{'=' * 70}")
    print(f"{course_name} ({course_code})")
    print(f"{'=' * 70}")
    print(f"   {len(pdf_files)} PDFs gefunden")
    
    # Text-Splitter konfigurieren
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    
    # Alle Dokumente sammeln
    all_chunks = []
    for pdf_path in pdf_files:
        print(f"\n {pdf_path.name}")
        
        # PDF laden
        loader = PyPDFLoader(str(pdf_path))
        pages = loader.load()
        print(f"      {len(pages)} Seiten geladen")
        
        # Modul-Name aus Dateiname ableiten
        stem = pdf_path.stem
        # Zahlen + Underscore entfernen
        module_name = stem
        if "_" in stem and stem.split("_")[0].rstrip("ab c").isdigit():
            module_name = "_".join(stem.split("_")[1:])
        
        # Chunks mit Metadaten anreichern
        for page_doc in pages:
            chunks = splitter.split_text(page_doc.page_content)
            page_num = page_doc.metadata.get("page", 0)
            
            for chunk_idx, chunk_text in enumerate(chunks):
                all_chunks.append({
                    "text": chunk_text,
                    "metadata": {
                        # Standard-Metadaten
                        "source_name": pdf_path.name,
                        "source_stem": stem,
                        "page": float(page_num),
                        "page_label": str(page_num + 1),  # 1-basiert
                        # Neue Metadaten für Filter
                        "course_code": course_code,
                        "course_name": course_name,
                        "module": module_name,
                        "chunk_index": chunk_idx,
                        # Inhalt selbst (für Retrieval-Display)
                        "text": chunk_text[:1000],  # gekürzt aufgrund Pinecone Limit
                    }
                })
        
        print(f" {sum(1 for c in all_chunks if c['metadata']['source_name'] == pdf_path.name)} Chunks erstellt")
    
    print(f"\n Gesamt: {len(all_chunks)} Chunks in {course_code}")
    
    if dry_run:
        print(f" DRY-RUN: Nichts wird hochgeladen.")
        return
    
    # Embeddings + Pinecone Setup
    print(f"\n Initialisiere Embeddings & Pinecone...")
    embeddings = JinaEmbeddings(
        jina_api_key=os.getenv("JINA_API_KEY"),
        model_name=EMBEDDING_MODEL
    )
    
    # Texte und Metadaten extrahieren
    texts = [c["text"] for c in all_chunks]
    metadatas = [c["metadata"] for c in all_chunks]
    
    # Hochladen in Batches 
    print(f" Lade {len(texts)} Chunks in Namespace '{course_code}' hoch...")
    
    vectorstore = PineconeVectorStore(
        index_name=os.getenv("PINECONE_INDEX_NAME"),
        embedding=embeddings,
        namespace=course_code
    )
    
    total_uploaded = 0
    for i in range(0, len(texts), BATCH_SIZE):
        batch_texts = texts[i:i + BATCH_SIZE]
        batch_meta = metadatas[i:i + BATCH_SIZE]
        
        try:
            vectorstore.add_texts(texts=batch_texts, metadatas=batch_meta)
            total_uploaded += len(batch_texts)
            print(f"Batch {i // BATCH_SIZE + 1}: {total_uploaded}/{len(texts)} hochgeladen")
            time.sleep(1)  # Rate-Limiting
        except Exception as e:
            print(f" Fehler bei Batch {i // BATCH_SIZE + 1}: {e}")
            print(f" Versuche weiter mit nächstem Batch...")
    
    print(f" Fertig: {total_uploaded}/{len(texts)} Chunks in '{course_code}'")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--course", help="Nur ein bestimmtes Fach indexieren (course_code)")
    parser.add_argument("--dry-run", action="store_true", help="Nichts hochladen, nur anzeigen")
    args = parser.parse_args()
    
    courses = load_courses_config()
    
    if args.course:
        courses = [c for c in courses if c["code"] == args.course]
        if not courses:
            print(f"Fach '{args.course}' nicht in courses.json gefunden")
            return
    
    print(f"Indexierung startet ({len(courses)} Fach/Fächer)")
    if args.dry_run:
        print("DRY-RUN-Modus: Es wird nichts hochgeladen.\n")
    
    for course in courses:
        index_course(course["code"], course["name"], dry_run=args.dry_run)
    
    print("\n" + "=" * 70)
    print("Alles erledigt!")


if __name__ == "__main__":
    main()