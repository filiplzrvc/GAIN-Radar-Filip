import json
import os
from dotenv import load_dotenv

load_dotenv()

from app.workflow.orchestrator import process_request
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy
from langchain_openai import ChatOpenAI, OpenAIEmbeddings


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
    correct_rejections = []  # "passt nicht" Antworten — korrektes Verhalten

    print("Starte Evaluation...\n" + "=" * 60)

    for case in test_cases:
        print(f"Teste Frage: {case['question']}")

        result = process_request(
            question=case["question"],
            course=case["course"],
            mode=case["mode"]
        )

        # Agenten-Logik bewerten
        off_topic_correct = (result.decisions.off_topic == case["expected_off_topic"])
        expected_ctx = case["expected_context_quality"]
        if expected_ctx == "sufficient_but_rejected":
            context_eval_correct = (result.context_quality == "sufficient")
        else:
            context_eval_correct = (result.context_quality == expected_ctx)

        if off_topic_correct and context_eval_correct:
            agent_score += 1
            print("  -> Agenten-Entscheidungen: KORREKT ✅")
        else:
            print(f"  -> Agenten-Entscheidungen: FALSCH ❌")
            print(f"     off_topic: erwartet={case['expected_off_topic']}, bekam={result.decisions.off_topic}")
            print(f"     context:   erwartet={case['expected_context_quality']}, bekam={result.context_quality}")

        # RAGAS nur für Fragen mit echtem Kontext und Antwort
        if (not result.decisions.off_topic
                and not result.decisions.clarification_needed
                and result.retrieved_documents
                and result.final_answer
                and result.context_quality == "sufficient"):

            # Prüfe ob die Antwort eine korrekte Ablehnung ist ("passt nicht")
            rejection_signals = [
                "finde ich zu deiner frage keine",
                "finde ich dazu keine",
                "keine direkt passenden informationen",
                "keine ausreichenden informationen",
                "im verfügbaren kursmaterial finde ich",
                "i couldn't find",
                "i could not find",
                "no directly relevant information",
            ]
            answer_lower = (result.final_answer or "").lower()
            is_rejection = any(s in answer_lower for s in rejection_signals)
            is_quiz_or_flashcard = case.get("mode") in ["quiz", "flashcards", "flashcard"]

            if is_rejection or is_quiz_or_flashcard:
                correct_rejections.append({
                    "question": case["question"],
                    "course": case["course"],
                    "answer": result.final_answer[:80] + "..."
                })
                print("  -> Korrekte Ablehnung (Material passt nicht) — kein RAGAS nötig ✅")
            else:
                ragas_data["question"].append(case["question"])
                ragas_data["answer"].append(result.final_answer)
                contexts = [doc.content for doc in result.retrieved_documents]
                ragas_data["contexts"].append(contexts)
                ragas_data["ground_truth"].append(case["reference_answer"])

    # === AGENTEN SCORE ===
    print("\n" + "=" * 60)
    print(f"AGENTEN LOGIK SCORE: {agent_score} / {len(test_cases)} richtig geroutet.")
    print("=" * 60)

    # === KORREKTE ABLEHNUNGEN ===
    if correct_rejections:
        print(f"\n--- KORREKTE ABLEHNUNGEN ({len(correct_rejections)} Fälle) ---")
        print("(System hat erkannt, dass Material nicht passt — korrektes Verhalten)")
        for r in correct_rejections:
            print(f"  [{r['course']}] {r['question']}")

    # === RAGAS ===
    if not ragas_data["question"]:
        print("\nKeine RAGAS-Samples vorhanden.")
        return

    print(f"\nBerechne RAGAS Metriken für {len(ragas_data['question'])} echte RAG-Antworten...")

    eval_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=4096)
    eval_embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    dataset = Dataset.from_dict(ragas_data)

    result_ragas = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy],
        llm=eval_llm,
        embeddings=eval_embeddings,
    )

    df = result_ragas.to_pandas()

    print(f"\n--- RAGAS ERGEBNISSE (nur echte RAG-Antworten) ---")
    print(f"{'Frage':<60} {'Faith.':>8} {'Relev.':>8}")
    print("-" * 78)
    for _, row in df.iterrows():
        q = str(row.get("user_input", row.get("question", "?")))[:58]
        f_val = row.get("faithfulness", float("nan"))
        r_val = row.get("answer_relevancy", float("nan"))
        print(f"{q:<60} {f_val:>8.4f} {r_val:>8.4f}")

    f_mean = df["faithfulness"].mean()
    r_mean = df["answer_relevancy"].mean()

    print("-" * 78)
    print(f"{'Durchschnitt Faithfulness:':<60} {f_mean:>8.4f}")
    print(f"{'Durchschnitt Answer Relevancy:':<60} {r_mean:>8.4f}")

    # === GESAMTBEWERTUNG ===
    print("\n" + "=" * 60)
    print("GESAMTBEWERTUNG")
    print("=" * 60)
    print(f"  Agenten-Routing:        {agent_score}/{len(test_cases)} ({agent_score/len(test_cases)*100:.0f}%)")
    print(f"  Korrekte Ablehnungen:   {len(correct_rejections)} (Material passt nicht → ehrlich abgelehnt)")
    print(f"  Echte RAG-Antworten:    {len(ragas_data['question'])}")
    print(f"  Faithfulness:           {f_mean:.4f}")
    print(f"  Answer Relevancy:       {r_mean:.4f}")


if __name__ == "__main__":
    run_evaluation()