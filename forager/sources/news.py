"""News source: recent AI stories from a few tech-news RSS and Atom feeds.

Each story's source text is the longest text its feed carries (full content when the
feed includes it, otherwise the summary), stripped of HTML and prefixed with the outlet.
Feed text is untrusted web content: the agents are told to treat it as data. A feed
that fails is skipped, so one unreachable outlet does not stop the digest.
"""

import html
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from email.utils import parsedate_to_datetime

FEEDS = {
    "TechCrunch": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "The Verge": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "MIT Technology Review": "https://www.technologyreview.com/topic/artificial-intelligence/feed",
    "Ars Technica": "https://arstechnica.com/ai/feed/",
    "The Decoder": "https://the-decoder.com/feed/",
}
TEXT_CHARS = 800          # a short excerpt: snapshots are committed to a public repository
ATOM = "{http://www.w3.org/2005/Atom}"
CONTENT = "{http://purl.org/rss/1.0/modules/content/}encoded"


def _get(url: str, timeout: int = 20) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "Forager/0.1 (course project)"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def plain(text: str | None) -> str:
    """Feed HTML to plain text: no scripts, styles or tags; entities decoded."""
    text = re.sub(r"<(script|style)\b.*?</\1>", " ", text or "", flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(html.unescape(text).split())


def _day(value: str | None) -> str:
    """RSS (RFC 822) or Atom (ISO 8601) date to YYYY-MM-DD; empty if unreadable."""
    value = (value or "").strip()
    for parse in (parsedate_to_datetime, lambda v: datetime.fromisoformat(v.replace("Z", "+00:00"))):
        try:
            return parse(value).date().isoformat()
        except (TypeError, ValueError, IndexError):
            continue
    return ""


def _story(outlet: str, title, url, texts, published, categories) -> dict:
    text = max((plain(t) for t in texts if t), key=len, default="")
    topics = {}
    for category in categories:
        if category and category.strip():
            topics.setdefault(category.strip().casefold(), category.strip())   # "Apple" and "apple" once
    topics = list(topics.values())[:6]
    return {"type": "news", "source": outlet, "title": plain(title), "url": (url or "").strip(),
            "abstract": f"[{outlet}] {text[:TEXT_CHARS]}".strip(), "published": _day(published), "topics": topics}


def parse_feed(xml_text: str, outlet: str) -> list[dict]:
    """Parse an RSS 2.0 or Atom feed into raw story records (no Forager IDs yet)."""
    root = ET.fromstring(xml_text)
    stories = []
    if root.tag == ATOM + "feed":
        for entry in root.findall(ATOM + "entry"):
            link = next((l.get("href") for l in entry.findall(ATOM + "link")
                         if l.get("rel", "alternate") == "alternate"), "")
            stories.append(_story(outlet, entry.findtext(ATOM + "title"), link,
                                  [entry.findtext(ATOM + "content"), entry.findtext(ATOM + "summary")],
                                  entry.findtext(ATOM + "published") or entry.findtext(ATOM + "updated"),
                                  [c.get("term") for c in entry.findall(ATOM + "category")]))
    else:
        for item in root.iter("item"):
            stories.append(_story(outlet, item.findtext("title"), item.findtext("link"),
                                  [item.findtext(CONTENT), item.findtext("description")], item.findtext("pubDate"),
                                  [c.text for c in item.findall("category")]))
    return [s for s in stories if s["title"] and s["url"]]


def fetch(feeds=None, *, days: int = 3, limit: int = 15, today: str | None = None) -> list[dict]:
    """Stories from the last `days` days, newest first per outlet, taken one outlet at a
    time so no single outlet fills the list."""
    today = today or date.today().isoformat()
    since = (date.fromisoformat(today) - timedelta(days=days)).isoformat()
    queues = []
    for outlet, url in (feeds or FEEDS).items():
        try:
            stories = parse_feed(_get(url), outlet)
        except (urllib.error.URLError, TimeoutError, OSError, ET.ParseError):
            continue
        queues.append(sorted((s for s in stories if s["published"] >= since),
                             key=lambda s: s["published"], reverse=True))
    merged, seen = [], set()
    while len(merged) < limit and any(queues):
        for queue in queues:
            if queue and len(merged) < limit:
                story = queue.pop(0)
                if story["url"] not in seen:
                    seen.add(story["url"])
                    merged.append(story)
    return merged
