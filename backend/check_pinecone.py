# backend/check_pinecone.py
"""
Inventur des Pinecone-Index mit echtem Embedding.
"""
import os
from collections import Counter
from dotenv import load_dotenv
from pinecone import Pinecone
from langchain_community.embeddings import JinaEmbeddings

load_dotenv()

# Echtes Embedding einer typischen Frage erstellen
print("🔧 Erstelle Embedding für Test-Query...")
embeddings = JinaEmbeddings(
    jina_api_key=os.getenv("JINA_API_KEY"),
    model_name="jina-embeddings-v2-base-de"
)
query_vector = embeddings.embed_query("Was ist Machine Learning?")

# Pinecone abfragen
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))

# 1. Statistiken
print("\n" + "=" * 60)
print("📊 INDEX-STATISTIKEN")
print("=" * 60)
stats = index.describe_index_stats()
print(f"Dimension:         {stats.get('dimension')}")
print(f"Total Vektoren:    {stats.get('total_vector_count')}")

# 2. Echte Suche mit dem Embedding
print("\n" + "=" * 60)
print("📁 ECHTE SUCHE: 'Was ist Machine Learning?'")
print("=" * 60)
results = index.query(
    vector=query_vector,
    top_k=10,
    include_metadata=True,
    include_values=False
)

print(f"\n{len(results.get('matches', []))} Treffer gefunden\n")

for i, match in enumerate(results.get('matches', []), 1):
    print(f"--- Treffer {i} (Score: {match.get('score'):.3f}) ---")
    print(f"  ID: {match.get('id')}")
    metadata = match.get('metadata', {})
    if metadata:
        for key, value in metadata.items():
            # Lange Texte abschneiden
            value_str = str(value)
            if len(value_str) > 100:
                value_str = value_str[:100] + "..."
            print(f"  {key}: {value_str}")
    else:
        print("  ⚠️ KEINE Metadaten!")
    print()

# 3. Alle vorkommenden Metadaten-Felder zählen
all_keys = set()
sources = Counter()
for match in results.get('matches', []):
    md = match.get('metadata', {})
    all_keys.update(md.keys())
    src = md.get('source_name') or md.get('source') or md.get('file_name') or 'UNKNOWN'
    sources[src] += 1

print("=" * 60)
print("📋 ZUSAMMENFASSUNG")
print("=" * 60)
print(f"Vorhandene Metadaten-Felder: {sorted(all_keys)}")
print(f"\nQuellen-Verteilung:")
for src, count in sources.most_common():
    print(f"  - {src}: {count}x")