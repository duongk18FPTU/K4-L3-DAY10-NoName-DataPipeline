from __future__ import annotations

import json
import re
from pathlib import Path

import requests

from core.config import Settings
from core.utils import PaperRecord, ensure_parent, normalize_whitespace, write_json


def _strip_html(value: str) -> str:
    text = value or ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_title(raw_title) -> str:
    if isinstance(raw_title, list) and raw_title:
        return normalize_whitespace(str(raw_title[0]))
    if isinstance(raw_title, str):
        return normalize_whitespace(raw_title)
    return ""


def _extract_authors(raw_authors) -> list[str]:
    authors: list[str] = []
    for item in raw_authors or []:
        if not isinstance(item, dict):
            name = str(item).strip()
            if name:
                authors.append(name)
            continue
        given = str(item.get("given") or "").strip()
        family = str(item.get("family") or "").strip()
        name = " ".join(part for part in [given, family] if part)
        if name:
            authors.append(name)
    return authors


def _extract_categories(raw_subjects) -> list[str]:
    categories: list[str] = []
    for item in raw_subjects or []:
        value = normalize_whitespace(str(item))
        if value:
            categories.append(value)
    return categories


def _extract_date(raw_date) -> str:
    if not raw_date:
        return ""
    if isinstance(raw_date, str):
        return raw_date[:10]
    if isinstance(raw_date, dict):
        if "date-time" in raw_date and raw_date["date-time"]:
            return str(raw_date["date-time"])[:10]
        if "date-parts" in raw_date and raw_date["date-parts"]:
            parts = raw_date["date-parts"][0]
            if len(parts) >= 3:
                year, month, day = parts[:3]
                return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
            if len(parts) >= 2:
                year, month = parts[:2]
                return f"{int(year):04d}-{int(month):02d}-01"
            if len(parts) >= 1:
                year = parts[0]
                return f"{int(year):04d}-01-01"
    return ""


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload into a list of PaperRecord objects."""
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        if not isinstance(item, dict):
            continue

        doi = str(item.get("DOI") or "").strip()
        title = _extract_title(item.get("title"))
        summary = _strip_html(item.get("abstract") or "")
        authors = _extract_authors(item.get("author"))
        categories = _extract_categories(item.get("subject"))
        primary_category = categories[0] if categories else ""
        published = (
            _extract_date(item.get("published-print"))
            or _extract_date(item.get("published-online"))
            or _extract_date(item.get("published"))
        )
        updated = _extract_date(item.get("deposited")) or published
        abs_url = str(item.get("URL") or "").strip()

        pdf_url = ""
        for link in item.get("link") or []:
            if not isinstance(link, dict):
                continue
            href = str(link.get("URL") or "").strip()
            content_type = str(link.get("content-type") or "").lower()
            if "pdf" in content_type or href.lower().endswith(".pdf"):
                pdf_url = href
                break

        comment = ""
        container = item.get("container-title") or []
        if isinstance(container, list) and container:
            comment = normalize_whitespace(str(container[0]))

        if not doi or not title or not summary:
            continue

        records.append(
            PaperRecord(
                paper_id=doi,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=comment,
            )
        )

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch source records from Crossref or load local snapshot fallback."""
    params = {
        "query.title": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
        "select": "DOI,title,abstract,author,subject,published-print,published-online,published,deposited,URL,link,container-title",
    }
    raw_path = settings.paths.raw_api_response
    fallback_payload = None

    if raw_path.exists():
        fallback_payload = json.loads(raw_path.read_text(encoding="utf-8"))

    try:
        for attempt in range(3):
            response = requests.get("https://api.crossref.org/works", params=params, timeout=30)
            if response.status_code in {429, 503} and attempt < 2:
                continue
            response.raise_for_status()
            payload = response.json()
            if not payload.get("message", {}).get("items"):
                raise ValueError("Crossref API returned no items.")
            break
    except (requests.RequestException, ValueError):
        if fallback_payload is None:
            raise
        payload = fallback_payload

    ensure_parent(raw_path)
    raw_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

    records = parse_crossref_payload(payload)
    write_json(settings.paths.raw_records_json, [record.__dict__ for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load raw JSON snapshot and map it back into PaperRecord objects."""
    payload = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(payload, dict):
        items = payload.get("items") or payload.get("message", {}).get("items", [])
    else:
        items = payload

    records: list[PaperRecord] = []
    for item in items:
        if isinstance(item, PaperRecord):
            records.append(item)
            continue
        if not isinstance(item, dict):
            continue

        authors = item.get("authors")
        categories = item.get("categories")
        published = item.get("published") or ""
        updated = item.get("updated") or published
        primary_category = item.get("primary_category") or (categories[0] if isinstance(categories, list) and categories else "")

        records.append(
            PaperRecord(
                paper_id=str(item.get("paper_id") or item.get("DOI") or "").strip(),
                title=normalize_whitespace(str(item.get("title") or "")),
                summary=normalize_whitespace(str(item.get("summary") or "")),
                authors=authors if isinstance(authors, list) else [str(authors)] if authors else [],
                categories=categories if isinstance(categories, list) else [str(categories)] if categories else [],
                primary_category=str(primary_category or "").strip(),
                published=str(published),
                updated=str(updated),
                abs_url=str(item.get("abs_url") or "").strip(),
                pdf_url=str(item.get("pdf_url") or "").strip(),
                comment=str(item.get("comment") or "").strip(),
            )
        )

    return [record for record in records if record.paper_id and record.title and record.summary]
