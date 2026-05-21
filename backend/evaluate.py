import json
import os
from dotenv import load_dotenv

load_dotenv()
os.environ["LANGCHAIN_TRACING_V2"] = "true"

from app.workflow.orchestrator import process_request
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy



def run_evaluation():
    # Goldenes Set laden
    with open("eval_data.json", "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    ragas_data = {
        "question": [],
        "answer": [],
        "contexts": [],
        "ground_truth": []
    }

    agent_score = 0

    print("Starte Evaluation...\n" + "="*40)

    # Testfälle durch den Orchestrator jagen
    for case in test_cases:
        print(f"Teste Frage: {case['question']}")
        
        # Orchestrator aufrufen
        state = process_request(
            question=case["question"],
            course=case["course"],
            mode=case["mode"]
        )

        # Agenten-Mehrwert Evaluieren
        # Hat der Agent richtig gedacht?
        off_topic_correct = (state.decisions.off_topic == case["expected_off_topic"])
        context_eval_correct = (state.context_quality == case["expected_context_quality"])
        
        if off_topic_correct and context_eval_correct:
            agent_score += 1
            print("  -> Agenten-Entscheidungen: KORREKT ✅")
        else:
            print("  -> Agenten-Entscheidungen: FALSCH ❌")

        # RAGAS Daten Sammeln
        # Nur für Fragen, die nicht Off-Topic sind
        if not state.decisions.off_topic:
            ragas_data["question"].append(case["question"])
            ragas_data["answer"].append(state.final_answer)
            # braucht eine Liste von Strings als Kontext
            contexts = [doc.content for doc in state.retrieved_documents] if state.retrieved_documents else ["Kein Kontext"]
            ragas_data["contexts"].append(contexts)
            ragas_data["ground_truth"].append(case["reference_answer"])

    print("="*40)
    print(f"AGENTEN LOGIK SCORE: {agent_score} / {len(test_cases)} richtig geroutet.")
    print("="*40)

    # RAGAS Metriken berechnen (Faktentreue & Relevanz)
    print("Berechne RAGAS Metriken (Faithfulness, Relevancy)...")
    dataset = Dataset.from_dict(ragas_data)
    
    # Evaluiert die Antworten mittels GPT
    result = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy],
    )
    
    print("\n--- RAGAS ERGEBNISSE ---")
    print(result)

if __name__ == "__main__":
    run_evaluation()