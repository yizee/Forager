"""Stage 4 sources: GitHub repositories and a balanced candidate mix (no network)."""

import json

from forager.digest import context_message, prepare_candidates
from forager.profile import DEFAULT_PROFILE
from forager.sources import github, load_snapshot, save_snapshot

TODAY = "2026-10-27"


def repo(name, stars, created="2026-10-23", **extra):
    return {"full_name": name, "html_url": f"https://github.com/{name}", "stargazers_count": stars,
            "created_at": f"{created}T10:00:00Z", "description": f"{name} does things.", "language": "Python",
            "topics": ["ai-agents", "llm"], **extra}


def test_readme_excerpt_is_plain_text():
    raw = ("# Title\n![build](https://img.shields.io/badge.svg) <img src='x.png'>\n"
           "> Agents for [video editing](https://example.com/docs).\n```bash\npip install x\n```\n"
           "- Fast | **simple**\n<!-- hidden -->")
    assert github.clean_readme(raw) == "Title Agents for video editing. Fast simple"
    assert len(github.clean_readme("word " * 500, limit=50)) == 50


def test_item_reports_growth_and_readme():
    item = github.to_item(repo("a/agent-kit", 249), "README text.", TODAY)
    assert item["type"] == "repo" and item["title"] == "a/agent-kit" and item["published"] == "2026-10-23"
    assert "249 stars in 4 days since it was created on 2026-10-23." in item["abstract"]
    assert "Topics: ai-agents, llm." in item["abstract"] and item["abstract"].endswith("README excerpt: README text.")
    same_day = github.to_item(repo("a/b", 3, created=TODAY), "", TODAY)
    assert "3 stars in 1 day since" in same_day["abstract"] and "README" not in same_day["abstract"]


def test_fetch_merges_topics_and_keeps_the_most_starred(monkeypatch):
    results = {"ai-agents": [repo("a/one", 50), repo("b/two", 200)], "llm": [repo("b/two", 200), repo("c/three", 90)]}
    readmes = []
    monkeypatch.setattr(github, "search", lambda topic, since, per_page: results.get(topic, []))
    monkeypatch.setattr(github, "readme", lambda name: readmes.append(name) or f"about {name}")
    items = github.fetch(["ai-agents", "llm"], limit=2, today=TODAY)
    assert [i["title"] for i in items] == ["b/two", "c/three"]
    assert readmes == ["b/two", "c/three"]                     # READMEs only for kept repositories


def test_candidates_interleave_source_types():
    raw = [{"type": "paper", "title": f"P{n}"} for n in range(5)] + [{"type": "repo", "title": f"R{n}"} for n in range(5)]
    ids = [c["id"] for c in prepare_candidates(raw, limit=6)]
    assert ids == ["p01", "r01", "p02", "r02", "p03", "r03"]
    papers_only = prepare_candidates(raw[:5], limit=3)
    assert [c["title"] for c in papers_only] == ["P0", "P1", "P2"]


def test_repo_topics_reach_the_writer():
    candidate = prepare_candidates([github.to_item(repo("a/b", 5), "", TODAY)])[0]
    shown = json.loads(context_message(DEFAULT_PROFILE, [candidate], None, TODAY))["candidates"][0]
    assert shown["id"] == "r01" and shown["type"] == "repo" and shown["categories"] == ["ai-agents", "llm"]


def test_snapshot_round_trip(tmp_path):
    items = [github.to_item(repo("a/b", 5), "", TODAY)]
    save_snapshot(items, tmp_path / "github.json")
    assert load_snapshot(tmp_path / "github.json") == items
