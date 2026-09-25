"""TV3 integration probes; separate from the team's official evaluation pipelines.

Run: python script/verify_tv3.py
Artifacts: data/tv3/, summary: report/tv3_verification.json.
Uses real MiniLM/Chroma, no LLM and no live Crossref requests.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import fields, replace
from datetime import datetime
from importlib.metadata import version
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from core.config import load_settings  # noqa: E402
from core.utils import first_sentence, now_utc, write_json  # noqa: E402
from ingestion.cleaning import build_clean_dataframe  # noqa: E402
from ingestion.corruption import corrupt_clean_dataframe  # noqa: E402
from ingestion.crossref import load_raw_records  # noqa: E402
from retrieval.index import LocalEmbeddingIndex  # noqa: E402
from retrieval.qa import answer_question  # noqa: E402


def probe_set(df):
    """Freeze 4 questions/paper from baseline once; never regenerate from corrupted data."""
    templates = [
        ("summary", "What is the summary of the paper '{title}'?", "summary"),
        ("authors", "Who authored the paper '{title}'?", "authors_joined"),
        ("date", "When was the paper '{title}' published?", "published"),
        (
            "categories",
            "What categories does the paper '{title}' belong to?",
            "categories_joined",
        ),
    ]
    return [
        {
            "paper_id": row["paper_id"],
            "kind": kind,
            "question": template.format(title=row["title"]),
            "reference": first_sentence(row[column])
            if kind == "summary"
            else row[column],
        }
        for row in df.to_dict("records")
        for kind, template, column in templates
    ]


def token_f1(reference, prediction):
    """Set-based token F1, same definition as the supplied metrics module; no judge."""
    expected, actual = set(reference.lower().split()), set(prediction.lower().split())
    overlap = len(expected & actual)
    return 2 * overlap / (len(expected) + len(actual)) if expected and actual else 0.0


def isolated_settings(settings, destination):
    """Preserve input paths; move all generated artifacts into the TV3 sandbox."""
    original = settings.paths
    data_root = ROOT / "data"
    overrides = {}
    for entry in fields(original):
        if entry.name in {
            "project_dir",
            "workspace_dir",
            "raw_records_json",
            "raw_api_response",
        }:
            continue
        overrides[entry.name] = destination / getattr(original, entry.name).relative_to(
            data_root
        )
    return replace(settings, paths=replace(original, **overrides))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-date", help="Timezone-aware ISO timestamp for reproducible age_days"
    )
    args = parser.parse_args()
    run_date = datetime.fromisoformat(args.run_date) if args.run_date else now_utc()
    if run_date.tzinfo is None:
        parser.error("--run-date must include timezone")
    settings = isolated_settings(load_settings(ROOT), ROOT / "data/tv3")
    checks = []

    def check(name, condition):
        checks.append({"name": name, "passed": bool(condition)})
        if not condition:
            raise AssertionError(name)

    raw = settings.paths.raw_records_json
    records = load_raw_records(raw)
    clean = build_clean_dataframe(records, run_date)
    check("clean_has_24_papers", len(clean) == 24)
    check("clean_ids_unique", clean.paper_id.is_unique)
    required = {
        "paper_id",
        "title",
        "summary",
        "authors_joined",
        "categories_joined",
        "published",
        "updated",
        "abs_url",
        "pdf_url",
        "text_for_embedding",
        "age_days",
        "summary_chars",
    }
    check("clean_contract", required <= set(clean.columns))
    check(
        "embedding_text_matches_metadata",
        all(
            row.text_for_embedding
            == (
                f"Title: {row.title}\nAuthors: {row.authors_joined}\nPublished: {row.published}\n"
                f"Categories: {row.categories_joined}\nSummary: {row.summary}"
            )
            for row in clean.itertuples()
        ),
    )
    original = clean.copy(deep=True)
    corrupt = corrupt_clean_dataframe(clean, settings.paths.corruption_log)
    check("corruption_does_not_mutate_baseline", original.equals(clean))
    repaired = build_clean_dataframe(load_raw_records(raw), run_date)
    check("repair_equals_baseline", repaired.equals(clean))
    check(
        "repair_idempotent",
        repaired.equals(build_clean_dataframe(load_raw_records(raw), run_date)),
    )
    write_json(
        ROOT / "report/tv3_preflight.json",
        {
            "scope": "TV3 data contract checks, not official quality/freshness report",
            "run_date": run_date.isoformat(),
            "raw_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
            "baseline_rows": len(clean),
            "corrupted_rows": len(corrupt),
            "repaired_rows": len(repaired),
            "checks": list(checks),
        },
    )
    probes = probe_set(clean)
    write_json(ROOT / "data/tv3/probes.json", probes)
    results, indexes = {}, {}
    for stage, df, manifest in [
        ("baseline", clean, settings.paths.embeddings_json),
        ("corrupted", corrupt, settings.paths.corrupted_embeddings_json),
        ("repaired", repaired, settings.paths.repaired_embeddings_json),
    ]:
        print(f"Building {stage}: {len(df)} rows", flush=True)
        index = LocalEmbeddingIndex.build(df, settings, manifest)
        indexes[stage] = index
        check(f"{stage}_collection_count", index.collection.count() == len(df))
        for row in df.itertuples():
            check(
                f"{stage}_lookup_id:{row.paper_id}",
                index.lookup(row.paper_id) is not None,
            )
            check(
                f"{stage}_lookup_title:{row.paper_id}",
                index.lookup(row.title) is not None,
            )
        check(
            f"{stage}_missing_lookup", index.lookup("TV3_NONEXISTENT_PAPER_000") is None
        )
        stored = index.collection.get(include=["embeddings"])["embeddings"]
        check(f"{stage}_embedding_384", all(len(v) == 384 for v in stored))
        check(
            f"{stage}_embedding_normalized",
            all(abs(sum(float(x) ** 2 for x in v) - 1) < 1e-4 for v in stored),
        )
        loaded = LocalEmbeddingIndex.load(settings, manifest)
        check(f"{stage}_load_count", loaded.collection.count() == len(df))
        rows = []
        for probe in probes:
            semantic = loaded.search(probe["question"])
            check(
                f"{stage}_top_k:{probe['paper_id']}:{probe['kind']}",
                0 < len(semantic) <= settings.top_k,
            )
            scores = [r.score for r in semantic]
            check(
                f"{stage}_score_order:{probe['paper_id']}:{probe['kind']}",
                scores == sorted(scores, reverse=True),
            )
            answer = answer_question(probe["question"], settings, loaded)
            rows.append(
                {
                    **probe,
                    "answer": answer.answer,
                    "semantic_ids": [r.paper_id for r in semantic],
                    "qa_ids": answer.retrieved_doc_ids,
                    "semantic_hit": probe["paper_id"] in [r.paper_id for r in semantic],
                    "qa_hit": probe["paper_id"] in answer.retrieved_doc_ids,
                    "token_f1": token_f1(probe["reference"], answer.answer),
                }
            )
        write_json(ROOT / f"data/tv3/{stage}_probe_answers.json", rows)
        results[stage] = {
            "rows": len(df),
            "unique_papers": int(df.paper_id.nunique()),
            "collection": index.collection_name,
            "samples": len(probes),
            "semantic_hit_at_4": mean(r["semantic_hit"] for r in rows),
            "qa_hit_at_4": mean(r["qa_hit"] for r in rows),
            "qa_token_f1": mean(r["token_f1"] for r in rows),
            "empty_reference_count": sum(not r["reference"].strip() for r in rows),
            "qa_token_f1_nonempty": mean(
                r["token_f1"] for r in rows if r["reference"].strip()
            ),
            "by_question_type": {
                kind: {
                    "samples": sum(r["kind"] == kind for r in rows),
                    "token_f1": mean(r["token_f1"] for r in rows if r["kind"] == kind),
                }
                for kind in ("summary", "authors", "date", "categories")
            },
            "blank_summaries": int(df.summary.eq("").sum()),
            "duplicate_paper_rows": int(df.paper_id.duplicated().sum()),
        }
        print(stage, json.dumps(results[stage]), flush=True)
    before = (
        indexes["corrupted"].collection.count(),
        indexes["repaired"].collection.count(),
    )
    rebuilt = LocalEmbeddingIndex.build(clean, settings)
    check("baseline_rebuild_no_duplicates", rebuilt.collection.count() == len(clean))
    check(
        "collection_isolation",
        before
        == (
            indexes["corrupted"].collection.count(),
            indexes["repaired"].collection.count(),
        ),
    )
    for metric in ("semantic_hit_at_4", "qa_hit_at_4", "qa_token_f1"):
        check(
            f"repair_restores_{metric}",
            results["baseline"][metric] == results["repaired"][metric],
        )
    unknown = answer_question(
        "Who authored the paper 'TV3_NONEXISTENT_PAPER_000'?", settings, rebuilt
    )
    finding = {
        "unknown_exact_title_answer": unknown.answer,
        "unknown_exact_title_returned_ids": unknown.retrieved_doc_ids,
        "note": "QA falls back to nearest paper even when the exact title is absent.",
    }
    summary = {
        "scope": "TV3 integration probes; not official phase1/corruption pipeline metrics",
        "run_date": run_date.isoformat(),
        "raw_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
        "embedding_model": settings.embedding_model,
        "versions": {
            p: version(p)
            for p in ("chromadb", "sentence-transformers", "pandas", "langchain")
        },
        "probe_count": len(probes),
        "checks_passed": len(checks),
        "stages": results,
        "corrupted_minus_baseline": {
            m: results["corrupted"][m] - results["baseline"][m]
            for m in ("semantic_hit_at_4", "qa_hit_at_4", "qa_token_f1")
        },
        "findings": [finding],
        "not_run": [
            "LLM judge",
            "Ragas",
            "TV4 quality/freshness",
            "TV1 official pipelines",
        ],
    }
    write_json(ROOT / "data/tv3/checks.json", checks)
    write_json(ROOT / "report/tv3_verification.json", summary)
    print(
        f"PASS: {len(checks)} checks. Summary: report/tv3_verification.json", flush=True
    )


if __name__ == "__main__":
    main()
