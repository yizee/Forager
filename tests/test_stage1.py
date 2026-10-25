"""Stage 1 offline tests: scripted model replies, no key, no network, no spending.

Needs the lab package in lab/ (or FORAGER_LAB_DIR). Run: .venv/bin/python -m pytest
"""

import json
from pathlib import Path

import pytest

from forager import labkit
from forager.checks import check_digest, citation_stats
from forager.digest import context_message, generate_digest, prepare_candidates
from forager.jsonagent import parse_json
from forager.profile import DEFAULT_PROFILE
from forager.render import to_markdown
from forager.sources.arxiv import load_snapshot, parse_feed

SNAPSHOT = sorted((Path(__file__).parent.parent / "data" / "snapshot").glob("arxiv-*.json"))[-1]

try:
    labkit.ensure_importable()
    from lab_support.testing import offline_lab, scripted_reply
except RuntimeError as exc:  # lab/ not unzipped yet
    pytest.skip(str(exc), allow_module_level=True)


def raw_items():
    return load_snapshot(SNAPSHOT)


def good_digest(ids):
    return {
        "brief": {
            "points": [{"text": f"Point {n}.", "field": "AI agents" if n % 2 else "image generation",
                        "cites": [ids[n]]} for n in range(6)],
            "connections": [{"text": "A link across fields.", "cites": [ids[0], ids[1]]}],
            "changes": [{"text": "This is the first digest.", "cites": []}],
        },
        "items": [{"id": i, "summary": "Core contribution.", "topics": ["AI agents"],
                   "reason": {"kind": "interest" if n else "breadth", "interest_id": "i1" if n else None,
                              "text": "Matches your interest."}} for n, i in enumerate(ids[:8])],
    }


def test_snapshot_has_papers():
    papers = raw_items()
    assert len(papers) >= 20
    assert all(p["type"] == "paper" and p["url"].startswith("https://arxiv.org/abs/") for p in papers)


def test_parse_feed():
    xml = """<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
      <entry><id>http://arxiv.org/abs/2610.00001v1</id><title>A  Title</title>
      <summary>Some
      abstract.</summary><published>2026-10-20T00:00:00Z</published>
      <author><name>Ada</name></author><category term="cs.AI"/>
      <arxiv:primary_category term="cs.AI"/></entry></feed>"""
    [paper] = parse_feed(xml)
    assert paper["title"] == "A Title" and paper["abstract"] == "Some abstract."
    assert paper["url"] == "https://arxiv.org/abs/2610.00001v1" and paper["published"] == "2026-10-20"


def test_candidate_ids_and_context_size():
    candidates = prepare_candidates(raw_items())
    assert [c["id"] for c in candidates[:3]] == ["p01", "p02", "p03"]
    context = context_message(DEFAULT_PROFILE, candidates, None, "2026-10-25")
    assert len(context.encode()) < 60_000  # well under the lab's 160 KB request limit


def test_checks_catch_citation_problems():
    ids = [c["id"] for c in prepare_candidates(raw_items())]
    digest = good_digest(ids)
    assert check_digest(digest, set(ids)) == []
    digest["brief"]["points"][0]["cites"] = ["p99"]          # unknown ID
    digest["brief"]["points"][1]["cites"] = [ids[15]]        # real candidate, not in items
    digest["brief"]["points"][2]["cites"] = []               # no citation
    errors = check_digest(digest, set(ids))
    assert any("'p99', an unknown ID" in e for e in errors)
    assert any("not in items" in e for e in errors)
    assert any("must cite at least one" in e for e in errors)


def test_checks_enforce_point_count_and_reasons():
    ids = [c["id"] for c in prepare_candidates(raw_items())]
    digest = good_digest(ids)
    digest["brief"]["points"] = digest["brief"]["points"][:3]
    digest["items"][0]["reason"] = {"kind": "because", "text": "x"}
    errors = check_digest(digest, set(ids))
    assert any("5-8 points" in e for e in errors)
    assert any("reason.kind" in e for e in errors)


def test_parse_json_tolerates_fences():
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    with pytest.raises(ValueError):
        parse_json("no json here")


def test_pipeline_offline_passes_first_try():
    ids = [c["id"] for c in prepare_candidates(raw_items())]
    replies = [scripted_reply(json.dumps(good_digest(ids)))]
    with offline_lab(replies) as lab:
        outcome = generate_digest(lab, DEFAULT_PROFILE, raw_items(), today="2026-10-25")
        sent = lab.client.requests[0]["messages"]
    assert outcome["errors"] == [] and outcome["attempts"] == 1
    digest = outcome["digest"]
    assert citation_stats(digest) == {"points": 6, "points_with_valid_citations": 6}
    # Titles and links come from the source data, not from the model.
    assert digest["items"][0]["url"].startswith("https://arxiv.org/abs/")
    # The candidates reach the model as context, not through the short user message.
    assert any("Digest context" in str(m.get("content")) for m in sent)
    markdown = to_markdown(digest, DEFAULT_PROFILE)
    assert f'<a id="{ids[0]}"></a>' in markdown and f"[{ids[0]}](#{ids[0]})" in markdown
    assert "Interest match (AI agents)" in markdown and "Breadth:" in markdown


def test_pipeline_offline_repairs_bad_citation():
    ids = [c["id"] for c in prepare_candidates(raw_items())]
    bad = good_digest(ids)
    bad["brief"]["points"][0]["cites"] = ["p99"]
    replies = [scripted_reply(json.dumps(bad)), scripted_reply(json.dumps(good_digest(ids)))]
    with offline_lab(replies) as lab:
        outcome = generate_digest(lab, DEFAULT_PROFILE, raw_items(), today="2026-10-25")
        repair_request = lab.client.requests[1]["messages"][-1]["content"]
    assert outcome["errors"] == [] and outcome["attempts"] == 2
    assert "p99" in repair_request


def test_pipeline_offline_reports_unrepaired_failure():
    replies = [scripted_reply("not json"), scripted_reply("still not json")]
    with offline_lab(replies) as lab:
        outcome = generate_digest(lab, DEFAULT_PROFILE, raw_items(), today="2026-10-25")
    assert outcome["digest"] is None and outcome["attempts"] == 2
    assert "not valid JSON" in outcome["errors"][0]
