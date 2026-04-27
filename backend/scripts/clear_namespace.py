"""
Löscht alle Vektoren in einem Pinecone-Namespace.
  python scripts/clear_namespace.py              # löscht default-Namespace
  python scripts/clear_namespace.py --ns aief    # löscht aief-Namespace
  python scripts/clear_namespace.py --all        # löscht ALLE Namespaces
"""
import os
import sys
import argparse
from dotenv import load_dotenv
from pinecone import Pinecone

#Skript aus jedem Verzeichnis startbar
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()


def clear_namespace(namespace: str = ""):
    #Löscht alle Vektoren in einem Namespace.
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))
    
    # Statistiken vorher
    stats = index.describe_index_stats()
    namespaces = stats.get("namespaces", {})
    
    display_name = namespace if namespace else "(default/leer)"
    
    if namespace not in namespaces and namespace != "":
        print(f"Namespace '{display_name}' existiert nicht.")
        print(f"Existierende Namespaces: {list(namespaces.keys())}")
        return
    
    count = namespaces.get(namespace, {}).get("vector_count", 0)
    
    if count == 0:
        print(f"Namespace '{display_name}' ist bereits leer.")
        return
    
    # Sicherheitsabfrage
    print(f"Du wirst {count} Vektoren aus Namespace '{display_name}' löschen.")
    confirm = input("Wirklich fortfahren? Tippe 'ja' zum Bestätigen: ")
    if confirm.lower() != "ja":
        print("Abgebrochen.")
        return
    
    # Löschen
    print(f"Lösche Namespace '{display_name}'...")
    if namespace:
        index.delete(delete_all=True, namespace=namespace)
    else:
        index.delete(delete_all=True)
    
    print(f"Namespace '{display_name}' geleert.")


def clear_all():
    #Löscht alle Namespaces im Index
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))
    
    stats = index.describe_index_stats()
    namespaces = stats.get("namespaces", {})
    
    if not namespaces:
        print("Index ist bereits leer.")
        return
    
    total = sum(ns.get("vector_count", 0) for ns in namespaces.values())
    print(f"Du wirst {total} Vektoren aus {len(namespaces)} Namespaces löschen:")
    for ns, data in namespaces.items():
        display = ns if ns else "(default)"
        print(f"   - {display}: {data.get('vector_count')} Vektoren")
    
    confirm = input("\n Wirklich ALLES löschen? Tippe 'ja' zum Bestätigen: ")
    if confirm.lower() != "ja":
        print("Abgebrochen.")
        return
    
    for ns in namespaces.keys():
        if ns:
            index.delete(delete_all=True, namespace=ns)
        else:
            index.delete(delete_all=True)
        display = ns if ns else "(default)"
        print(f"'{display}' geleert")
    
    print("\n Index ist jetzt leer.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ns", default="", help="Namespace zum Löschen")
    parser.add_argument("--all", action="store_true", help="Alle Namespaces löschen")
    args = parser.parse_args()
    
    if args.all:
        clear_all()
    else:
        clear_namespace(args.ns)