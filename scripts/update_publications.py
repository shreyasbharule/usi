#!/usr/bin/env python3
"""Refresh the USI scholarly feed from ORCID, Crossref and Google Scholar.\n\n# Manual refresh trigger: 2026-10-16

Sources:
- ORCID: authoritative identity / public works list
- Crossref: canonical DOI metadata
- Google Scholar via SerpApi: citation counts, profile metrics and Scholar-only records

No third-party Python packages required.
"""
from __future__ import annotations

import json
import os
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ORCID = os.environ.get("ORCID_ID", "0000-0002-9507-1279")
SCHOLAR_ID = os.environ.get("GOOGLE_SCHOLAR_ID", "cvEv8M4AAAAJ")
SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "").strip()
OUT = Path(__file__).resolve().parents[1] / "publications.json"
UA = "USI-Urban-Systems-Intelligence/2.0 (mailto:sbharule@arp.iitkgp.ac.in)"


def get_json(url: str, accept: str = "application/json") -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    with urllib.request.urlopen(req, timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))


def normalise_title(value: str | None) -> str:
    if not value:
        return ""
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def orcid_works() -> list[dict]:
    data = get_json(
        f"https://pub.orcid.org/v3.0/{ORCID}/works",
        "application/vnd.orcid+json",
    )
    rows = []
    for group in data.get("group", []):
        summaries = group.get("work-summary") or []
        if not summaries:
            continue
        summary = summaries[0]
        ext = []
        for ei in group.get("external-ids", {}).get("external-id", []):
            typ = (ei.get("external-id-type") or "").lower()
            val = ei.get("external-id-value")
            if typ and val:
                ext.append((typ, val))
        title = ((summary.get("title") or {}).get("title") or {}).get("value")
        year = (((summary.get("publication-date") or {}).get("year") or {}).get("value"))
        typ = summary.get("type")
        url = ((summary.get("url") or {}).get("value"))
        rows.append(
            {
                "title": title,
                "year": year,
                "type": typ,
                "url": url,
                "external_ids": ext,
            }
        )
    return rows


def crossref(doi: str) -> dict | None:
    try:
        encoded = urllib.parse.quote(doi, safe="")
        msg = get_json(f"https://api.crossref.org/works/{encoded}")["message"]
    except Exception as exc:
        print(f"Crossref lookup failed for {doi}: {exc}")
        return None

    title = (msg.get("title") or [None])[0]
    authors = []
    for author in msg.get("author", []) or []:
        name = " ".join(
            part for part in [author.get("given"), author.get("family")] if part
        )
        if name:
            authors.append(name)

    year = None
    for key in ("published-print", "published-online", "issued", "created"):
        date_parts = ((msg.get(key) or {}).get("date-parts") or [])
        if date_parts and date_parts[0]:
            year = date_parts[0][0]
            break

    venue = (msg.get("container-title") or [None])[0] or msg.get("publisher")
    return {
        "title": title,
        "authors": authors,
        "year": year,
        "venue": venue,
        "type": msg.get("type"),
        "doi": msg.get("DOI") or doi,
        "url": msg.get("URL") or f"https://doi.org/{doi}",
        "source": "ORCID + Crossref",
    }


def _all_metric(row: dict) -> int | None:
    for value in row.values():
        if isinstance(value, dict) and value.get("all") is not None:
            try:
                return int(value["all"])
            except (TypeError, ValueError):
                pass
    return None


def scholar_profile() -> tuple[list[dict], dict]:
    if not SERPAPI_KEY:
        print("SERPAPI_KEY is not set; continuing without Google Scholar enrichment.")
        return [], {}

    params = {
        "engine": "google_scholar_author",
        "author_id": SCHOLAR_ID,
        "hl": "en",
        "sort": "pubdate",
        "num": "100",
        "api_key": SERPAPI_KEY,
        "output": "json",
    }
    url = "https://serpapi.com/search?" + urllib.parse.urlencode(params)
    data = get_json(url)

    if data.get("error"):
        raise RuntimeError(f"SerpApi error: {data['error']}")

    articles = []
    for article in data.get("articles", []) or []:
        cited = (article.get("cited_by") or {}).get("value")
        try:
            cited = int(cited) if cited is not None else 0
        except (TypeError, ValueError):
            cited = 0
        articles.append(
            {
                "title": article.get("title"),
                "authors": [article.get("authors")] if article.get("authors") else [],
                "year": article.get("year"),
                "venue": article.get("publication"),
                "type": "scholar-record",
                "doi": None,
                "url": article.get("link"),
                "scholar_url": article.get("link"),
                "scholar_citations": cited,
                "scholar_cited_by_url": (article.get("cited_by") or {}).get("link"),
                "citation_id": article.get("citation_id"),
                "source": "Google Scholar",
            }
        )

    metrics = {
        "author_id": SCHOLAR_ID,
        "profile_url": f"https://scholar.google.com/citations?user={SCHOLAR_ID}",
        "total_citations": None,
        "h_index": None,
        "i10_index": None,
    }

    table = (data.get("cited_by") or {}).get("table") or []
    if len(table) > 0:
        metrics["total_citations"] = _all_metric(table[0])
    if len(table) > 1:
        metrics["h_index"] = _all_metric(table[1])
    if len(table) > 2:
        metrics["i10_index"] = _all_metric(table[2])

    return articles, metrics


def canonical_orcid_records() -> list[dict]:
    records = []
    for work in orcid_works():
        ids = dict(work["external_ids"])
        doi = ids.get("doi")
        enriched = crossref(doi) if doi else None
        if enriched:
            item = enriched
        else:
            item = {
                "title": work["title"],
                "authors": [],
                "year": work["year"],
                "venue": None,
                "type": work["type"],
                "doi": doi,
                "url": work["url"] or (f"https://doi.org/{doi}" if doi else None),
                "source": "ORCID",
            }
        records.append(item)
        time.sleep(0.08)
    return records


def merge_records(orcid_records: list[dict], scholar_records: list[dict]) -> list[dict]:
    scholar_by_title = {
        normalise_title(item.get("title")): item
        for item in scholar_records
        if normalise_title(item.get("title"))
    }

    merged = []
    seen_titles = set()

    for item in orcid_records:
        key = normalise_title(item.get("title"))
        scholar = scholar_by_title.get(key)
        if scholar:
            item["scholar_url"] = scholar.get("scholar_url")
            item["scholar_citations"] = scholar.get("scholar_citations", 0)
            item["scholar_cited_by_url"] = scholar.get("scholar_cited_by_url")
            item["citation_id"] = scholar.get("citation_id")
            item["source"] = "ORCID + Crossref + Google Scholar" if item.get("doi") else "ORCID + Google Scholar"
        else:
            item["scholar_citations"] = 0
        if key:
            seen_titles.add(key)
        merged.append(item)

    # Google Scholar sometimes contains works that are absent from ORCID.
    # Include them, while keeping ORCID/Crossref metadata canonical when a title matches.
    for scholar in scholar_records:
        key = normalise_title(scholar.get("title"))
        if key and key not in seen_titles:
            merged.append(scholar)
            seen_titles.add(key)

    # DOI first for deduplication, then normalised title.
    deduped = []
    seen = set()
    for item in merged:
        key = (item.get("doi") or normalise_title(item.get("title")) or "").lower()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    def sort_key(item: dict):
        try:
            year = int(item.get("year") or 0)
        except (TypeError, ValueError):
            year = 0
        return (year, normalise_title(item.get("title")))

    deduped.sort(key=sort_key, reverse=True)
    return deduped


def main() -> None:
    orcid_records = canonical_orcid_records()
    scholar_records, scholar_metrics = scholar_profile()
    publications = merge_records(orcid_records, scholar_records)

    payload = {
        "source": "ORCID + Crossref + Google Scholar",
        "orcid": ORCID,
        "google_scholar_id": SCHOLAR_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(publications),
        "scholar_metrics": scholar_metrics,
        "publications": publications,
    }
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Wrote {len(publications)} works to {OUT} "
        f"(Scholar records: {len(scholar_records)})"
    )


if __name__ == "__main__":
    main()
