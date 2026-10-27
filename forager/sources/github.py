"""GitHub source: recently created repositories with the most stars, one search per topic.

Uses the public search API; no token is needed (GITHUB_TOKEN, if set, raises the rate
limits). A README excerpt becomes part of each item's source text, so the writer has
substance to summarize and the Critic has something to check claims against. Stars
gained since creation stand in for how fast a project is growing. README text is
untrusted web content: the agents are told to treat it as data.
"""

import html
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

API = "https://api.github.com"
DEFAULT_TOPICS = ("ai-agents", "llm", "image-generation", "video-generation", "generative-ai")
README_CHARS = 800


def _get(url: str, accept: str = "application/vnd.github+json", timeout: int = 30) -> str:
    headers = {"Accept": accept, "User-Agent": "Forager/0.1 (course project)", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def search(topic: str, since: str, per_page: int = 10) -> list[dict]:
    """Repositories with this topic created on or after `since`, most stars first."""
    params = urllib.parse.urlencode({"q": f"topic:{topic} created:>={since}", "sort": "stars", "order": "desc",
                                     "per_page": per_page})
    return json.loads(_get(f"{API}/search/repositories?{params}")).get("items", [])


def clean_readme(text: str, limit: int = README_CHARS) -> str:
    """Plain-text excerpt: no code blocks, HTML, images or badges; links keep their text."""
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"^\s*(#+|>|[-*+]|\d+\.)\s*", "", text, flags=re.M)
    text = re.sub(r"[|*_`]+", " ", text)
    return " ".join(html.unescape(text).split())[:limit]


def readme(full_name: str) -> str:
    try:
        return clean_readme(_get(f"{API}/repos/{full_name}/readme", accept="application/vnd.github.raw"))
    except (urllib.error.URLError, TimeoutError, OSError):
        return ""


def to_item(repo: dict, readme_text: str, today: str) -> dict:
    created = repo["created_at"][:10]
    days = max(1, (date.fromisoformat(today) - date.fromisoformat(created)).days)
    stars = repo.get("stargazers_count", 0)
    description = (repo.get("description") or "").strip()
    topics = repo.get("topics") or []
    parts = [description, f"{stars} stars in {days} day{'s' if days > 1 else ''} since it was created on {created}."]
    if repo.get("language"):
        parts.append(f"Main language: {repo['language']}.")
    if topics:
        parts.append("Topics: " + ", ".join(topics[:8]) + ".")
    if readme_text:
        parts.append("README excerpt: " + readme_text)
    return {"type": "repo", "source": "GitHub", "title": repo["full_name"], "url": repo["html_url"],
            "abstract": " ".join(p for p in parts if p), "stars": stars, "language": repo.get("language"),
            "topics": topics, "published": created}


def fetch(topics=DEFAULT_TOPICS, *, days: int = 7, per_topic: int = 10, limit: int = 15,
          with_readme: bool = True, today: str | None = None) -> list[dict]:
    """Merge the per-topic searches, keep the most-starred `limit` repositories."""
    today = today or date.today().isoformat()
    since = (date.fromisoformat(today) - timedelta(days=days)).isoformat()
    repos = {}
    for topic in topics:
        for repo in search(topic, since, per_topic):
            repos.setdefault(repo["full_name"], repo)
    ranked = sorted(repos.values(), key=lambda r: r.get("stargazers_count", 0), reverse=True)[:limit]
    return [to_item(r, readme(r["full_name"]) if with_readme else "", today) for r in ranked]
