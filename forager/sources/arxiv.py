"""arXiv source: recent papers from selected categories via the public Atom API."""

import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

API = "https://export.arxiv.org/api/query"
ATOM = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
DEFAULT_CATEGORIES = ("cs.AI", "cs.CL", "cs.CV")


def _text(node, path):
    found = node.find(path, ATOM)
    return " ".join(found.text.split()) if found is not None and found.text else ""


def parse_feed(xml_text: str) -> list[dict]:
    """Parse an arXiv Atom feed into raw paper records (no Forager IDs yet)."""
    root = ET.fromstring(xml_text)
    papers = []
    for entry in root.findall("a:entry", ATOM):
        primary = entry.find("arxiv:primary_category", ATOM)
        papers.append({
            "type": "paper",
            "source": "arXiv",
            "arxiv_id": _text(entry, "a:id").rsplit("/abs/", 1)[-1],
            "title": _text(entry, "a:title"),
            "url": _text(entry, "a:id").replace("http://", "https://"),
            "abstract": _text(entry, "a:summary"),
            "authors": [_text(a, "a:name") for a in entry.findall("a:author", ATOM)][:5],
            "categories": [c.get("term") for c in entry.findall("a:category", ATOM)],
            "primary_category": primary.get("term") if primary is not None else "",
            "published": _text(entry, "a:published")[:10],
        })
    return papers


def fetch(categories=DEFAULT_CATEGORIES, max_results=30, timeout=30) -> list[dict]:
    """Fetch the most recently submitted papers across the given categories."""
    query = " OR ".join(f"cat:{c}" for c in categories)
    params = urllib.parse.urlencode({
        "search_query": query, "sortBy": "submittedDate", "sortOrder": "descending",
        "start": 0, "max_results": max_results,
    })
    request = urllib.request.Request(f"{API}?{params}", headers={"User-Agent": "Forager/0.1 (course project)"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return parse_feed(response.read().decode("utf-8"))


def save_snapshot(papers: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(papers, ensure_ascii=False, indent=2) + "\n")


def load_snapshot(path: Path) -> list[dict]:
    return json.loads(Path(path).read_text())
