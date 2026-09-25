from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import write_json


def build_test_set(df: pd.DataFrame, output_path: Path) -> list[dict[str, Any]]:
    """Tao bo evaluation set tu cleaned dataframe.

    Sinh 10 cau hoi chia deu 4 loai:
    - summary: "What is the summary of the paper '<Title>'?"
    - authors: "Who authored the paper '<Title>'?"
    - date:    "When was the paper '<Title>' published?"
    - categories: "What categories does the paper '<Title>' belong to?"

    Moi row co: id, question_type, question, ground_truth, ground_truth_doc_ids.
    """
    if len(df) < 3:
        raise ValueError(f"Can khoa 3 paper, chi co {len(df)} records.")

    # Chon toi da 5 paper dai dien (tranh trung lap, uu tien paper co summary dai)
    sample_df = df.copy()
    if "summary_chars" in sample_df.columns:
        sample_df = sample_df.sort_values("summary_chars", ascending=False)
    sample_size = min(5, len(sample_df))
    papers = sample_df.head(sample_size).reset_index(drop=True)

    question_types = ["summary", "authors", "date", "categories"]
    test_set: list[dict[str, Any]] = []
    q_id = 0

    # Sinh du 10 cau hoi bang cach lap vong qua cac loai cau hoi
    for i in range(10):
        paper = papers.iloc[i % len(papers)]
        qtype = question_types[i % len(question_types)]
        title = str(paper["title"]).strip()
        paper_id = str(paper["paper_id"]).strip()

        if qtype == "summary":
            question = f"What is the summary of the paper '{title}'?"
            ground_truth = str(paper.get("summary", "")).strip()
        elif qtype == "authors":
            question = f"Who authored the paper '{title}'?"
            authors = paper.get("authors_joined") or paper.get("authors", "")
            ground_truth = str(authors).strip() if authors else "Unknown"
        elif qtype == "date":
            question = f"When was the paper '{title}' published?"
            ground_truth = str(paper.get("published", "")).strip()
        else:  # categories
            question = f"What categories does the paper '{title}' belong to?"
            cats = paper.get("categories_joined") or paper.get("categories", "")
            ground_truth = str(cats).strip() if cats else "Unknown"

        test_set.append({
            "id": f"q{q_id:03d}",
            "question_type": qtype,
            "question": question,
            "ground_truth": ground_truth,
            "ground_truth_doc_ids": [paper_id],
        })
        q_id += 1

    write_json(Path(output_path), test_set)
    print(f"  [TestSet] Sinh {len(test_set)} cau hoi -> {output_path}")
    return test_set
