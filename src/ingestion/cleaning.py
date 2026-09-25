from __future__ import annotations

from datetime import datetime

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records into a dataframe ready for embedding and quality checks."""
    rows: list[dict] = []

    for record in records:
        title = normalize_whitespace(record.title)
        summary = normalize_whitespace(record.summary)
        authors = [normalize_whitespace(author) for author in record.authors if normalize_whitespace(author)]
        categories = [normalize_whitespace(category) for category in record.categories if normalize_whitespace(category)]

        published = str(record.published or "")
        updated = str(record.updated or published)

        published_dt = pd.to_datetime(published, errors="coerce")

        age_days = 0
        if pd.notna(published_dt):
            age_days = (run_date.date() - published_dt.date()).days

        authors_joined = compact_join(authors)
        categories_joined = compact_join(categories)
        summary_chars = len(summary)

        text_for_embedding = (
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Published: {published}\n"
            f"Categories: {categories_joined}\n"
            f"Summary: {summary}"
        )

        if not title or not summary or not record.paper_id:
            continue

        rows.append(
            {
                "paper_id": record.paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": record.primary_category or (categories[0] if categories else ""),
                "published": published,
                "updated": updated,
                "abs_url": record.abs_url,
                "pdf_url": record.pdf_url,
                "comment": record.comment,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "age_days": int(age_days),
                "summary_chars": int(summary_chars),
                "text_for_embedding": text_for_embedding,
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        columns = [
            "paper_id",
            "title",
            "summary",
            "authors",
            "categories",
            "primary_category",
            "published",
            "updated",
            "abs_url",
            "pdf_url",
            "comment",
            "authors_joined",
            "categories_joined",
            "age_days",
            "summary_chars",
            "text_for_embedding",
        ]
        return pd.DataFrame(columns=columns)

    df = df.drop_duplicates(subset=["paper_id"], keep="first")
    df = df.sort_values(["published", "paper_id"], ascending=[False, True], kind="mergesort").reset_index(drop=True)
    return df
