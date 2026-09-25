"""TV3: real MiniLM/Chroma smoke checks; no LLM calls unless --agent-question is set."""
from __future__ import annotations

import argparse
import hashlib
from dataclasses import replace
from pathlib import Path
import sys
from time import perf_counter
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd
import numpy as np

from core.config import load_settings, require_llm_credentials
from core.utils import first_sentence, now_utc, write_csv, write_json
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import load_raw_records
from ingestion.corruption import corrupt_clean_dataframe
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-question", help="Optional live Agent question; requires configured LLM")
    parser.add_argument("--expected-documents", type=int, default=24,
                        help="CP2 snapshot size (default: 24); change for a different corpus")
    args = parser.parse_args()
    settings = load_settings()
    # Each run has a separate database: build() deletes its target collection.
    output = settings.paths.project_dir / "data" / "tv3" / uuid4().hex
    paths = replace(settings.paths, chroma_dir=output / "chroma",
                    embeddings_json=output / "baseline.json",
                    corrupted_embeddings_json=output / "corrupted.json",
                    repaired_embeddings_json=output / "repaired.json")
    settings = replace(settings, paths=paths)
    run_date = now_utc()
    records = load_raw_records(paths.raw_records_json)
    baseline = build_clean_dataframe(records, run_date)
    require(not baseline.empty, "TV2 clean data is empty")
    require(len(baseline) == args.expected_documents, "Clean document count differs from CP2 expectation")
    require(baseline.paper_id.is_unique, "Duplicate paper_id in baseline")
    required = ["paper_id", "title", "text_for_embedding", "published", "authors_joined",
                "categories_joined", "summary", "abs_url", "pdf_url"]
    require(set(required).issubset(baseline.columns), "Missing retrieval columns")
    require(not baseline[required].isna().any().any(), "Null Chroma metadata")
    for field in ("paper_id", "title", "text_for_embedding"):
        require(baseline[field].str.strip().ne("").all(), f"Blank {field}")
    write_csv(baseline, output / "papers_clean.csv")
    corrupted = corrupt_clean_dataframe(baseline, output / "corruption_log.json")
    repaired = build_clean_dataframe(load_raw_records(paths.raw_records_json), run_date)
    pd.testing.assert_frame_equal(baseline, repaired)

    # All papers, four field checks each. This is a TV3 smoke suite, not TV4's test set.
    cases = []
    for row in baseline.to_dict("records"):
        title = row["title"]
        for question, expected in (
            (f"What is the summary of the paper '{title}'?", first_sentence(row["summary"])),
            (f"Who authored the paper '{title}'?", row["authors_joined"]),
            (f"When was the paper '{title}' published?", row["published"]),
            (f"What categories does the paper '{title}' belong to?", row["categories_joined"]),
        ):
            cases.append((row["paper_id"], question, expected))

    report = {"run_date": run_date.isoformat(), "embedding_model": settings.embedding_model,
              "output": str(output.relative_to(paths.project_dir)),
              "raw_sha256": hashlib.sha256(paths.raw_records_json.read_bytes()).hexdigest(),
              "top_k": settings.top_k, "states": {}, "agent": "not requested"}
    for name, df, manifest in (
        ("baseline", baseline, paths.embeddings_json),
        ("corrupted", corrupted, paths.corrupted_embeddings_json),
        ("repaired", repaired, paths.repaired_embeddings_json),
    ):
        start = perf_counter()
        index = LocalEmbeddingIndex.build(df, settings, manifest)
        duration = perf_counter() - start
        require(index.collection.count() == len(df), f"{name}: document count mismatch")
        stored = index.collection.get(include=["embeddings", "metadatas", "documents"])
        vectors = np.asarray(stored["embeddings"])
        require(vectors.shape == (len(df), 384), f"{name}: unexpected MiniLM vector shape")
        require(np.isfinite(vectors).all(), f"{name}: non-finite embeddings")
        require(np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-5),
                f"{name}: embeddings are not normalized")
        expected = {f"{row['paper_id']}::{i}": row for i, row in enumerate(df.to_dict("records"))}
        for record_id, metadata, content in zip(stored["ids"], stored["metadatas"], stored["documents"]):
            row = expected[record_id]
            require(content == row["text_for_embedding"], "Persisted content mismatch")
            require(all(metadata[key] == row[key] for key in required if key != "text_for_embedding"),
                    "Persisted metadata mismatch")
        rebuild_start = perf_counter()
        index = LocalEmbeddingIndex.build(df, settings, manifest)
        rebuild_duration = perf_counter() - rebuild_start
        require(index.collection.count() == len(df), f"{name}: rebuild duplicated documents")
        index = LocalEmbeddingIndex.load(settings, manifest)
        require(index.collection.count() == len(df), f"{name}: reload mismatch")
        for row in df.to_dict("records"):
            require(index.lookup(row["paper_id"]) is not None, "DOI lookup failed")
            require(index.lookup(row["title"]) is not None, "Title lookup failed")
        require(index.lookup("__tv3_nonexistent_paper__") is None, "Unknown lookup failed")
        # Titles queried directly through search(), without QA's exact-title shortcut.
        hits = sum(row["paper_id"] in [r.paper_id for r in index.search(row["title"])]
                   for row in baseline.to_dict("records"))
        answers = []
        for paper_id, question, expected in cases:
            answer = answer_question(question, settings, index)
            answers.append({"paper_id": paper_id, "question": question, "expected": expected,
                            "answer": answer.answer, "correct": answer.answer == expected,
                            "retrieved_doc_ids": answer.retrieved_doc_ids})
        result = {"documents": len(df), "index_seconds": round(duration, 3),
                  "rebuild_seconds": round(rebuild_duration, 3),
                  "vector_metadata_rebuild": "passed",
                  "title_search_hit_rate_at_4": hits / len(baseline),
                  "qa_exact_match": sum(a["correct"] for a in answers) / len(answers),
                  "qa_cases": len(answers), "count_reload_lookup": "passed"}
        report["states"][name] = result
        write_json(output / f"{name}_answers.json", answers)
        print(name, result, flush=True)
        if name == "baseline" and args.agent_question:
            from retrieval.agent import build_agent, run_agent_question
            require_llm_credentials(settings)
            report["agent"] = run_agent_question(build_agent(settings, index), args.agent_question)
    write_json(output / "results.json", report)
    require(report["states"]["baseline"]["qa_exact_match"] == 1, "Baseline QA mismatch; inspect answers")
    for metric in ("documents", "qa_exact_match", "title_search_hit_rate_at_4"):
        require(report["states"]["baseline"][metric] == report["states"]["repaired"][metric],
                f"Repair did not restore {metric}")
    write_json(paths.project_dir / "report" / "TV3_results.json", report)
    print(f"PASS: TV3 retrieval checks. Evidence: {output / 'results.json'}")


if __name__ == "__main__":
    main()
