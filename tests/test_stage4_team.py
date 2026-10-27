"""Stage 4 offline tests (Idea 3): the news source, the Manager and its three source
specialists, the code checks on the Manager, and the digest-modes runner.

Scripted model replies; no key, network or spending. Run: .venv/bin/python -m pytest
"""

import asyncio
import importlib.util
import json
import urllib.error
from pathlib import Path
from types import SimpleNamespace

import pytest

from forager import labkit
from forager.digest import generate_digest, merge_items, prepare_candidates
from forager.profile import DEFAULT_PROFILE
from forager.render import to_markdown
from forager.sources import news
from forager.team import SPECIALISTS, Team, reader_view
from forager.ui_runtime import event_line

try:
    labkit.ensure_importable()
    from lab_support.testing import offline_lab, scripted_reply
except RuntimeError as exc:  # lab/ not unzipped yet
    pytest.skip(str(exc), allow_module_level=True)

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("run_digest_modes", ROOT / "eval" / "run_digest_modes.py")
modes_runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(modes_runner)

TODAY = "2026-10-27"
RAW = ([{"type": "paper", "source": "arXiv", "title": f"Paper {n}", "url": f"https://arxiv.org/abs/2610.0000{n}",
         "abstract": f"Paper {n} abstract: a planner for tool-using agents.", "categories": ["cs.AI"],
         "published": "2026-10-26"} for n in range(1, 5)]
       + [{"type": "repo", "source": "GitHub", "title": f"org/repo{n}", "url": f"https://github.com/org/repo{n}",
           "abstract": f"Repo {n} README excerpt.", "stars": 100 * n, "language": "Python", "topics": ["llm"],
           "published": "2026-10-23"} for n in range(1, 5)]
       + [{"type": "news", "source": "Outlet", "title": f"Story {n}", "url": f"https://example.com/story-{n}",
           "abstract": f"[Outlet] Story {n} text.", "topics": ["AI"], "published": "2026-10-26"} for n in range(1, 5)])
CANDIDATES = prepare_candidates(RAW)
FITS = {"p01": "i1", "p02": "i3", "p03": None, "r01": "i1", "r02": "i2", "r03": None,
        "n01": "i1", "n02": "i2", "n03": "i3"}


def reply(data):
    return scripted_reply(json.dumps(data))


def item(item_id, interest):
    return {"id": item_id, "summary": f"Summary of {item_id}.", "topics": ["t"],
            "reason": {"kind": "interest", "interest_id": interest, "text": "match"} if interest
            else {"kind": "breadth", "interest_id": None, "text": "nearby"}}


def digest(fits=FITS):
    ids = list(fits)
    return {"brief": {"points": [{"text": f"Point {n}.", "field": "f", "cites": [ids[n]]} for n in range(5)],
                      "connections": [], "changes": [{"text": "First digest.", "cites": []}]},
            "items": [item(i, f) for i, f in fits.items()]}


def notes(kind, fits=FITS):
    return {"items": [{"id": i, "summary": f"Summary of {i}.", "topics": ["t"], "fit": "interest" if f else "breadth",
                       "interest_id": f, "why": "Worth a look."} for i, f in fits.items() if i[0] == kind[0]],
            "overview": f"Today's {kind}."}


def team_replies(final, fits=FITS):
    """The Manager asks all three specialists at once; each reads its source and reports."""
    replies = [scripted_reply(calls=[(SPECIALISTS[k]["tool"], {"input": f"What matters in today's {k}?"})
                                     for k in SPECIALISTS])]
    for kind, spec_ in SPECIALISTS.items():
        replies += [scripted_reply(calls=[(spec_["reader"], {})]), reply(notes(kind, fits))]
    return replies + [reply(final)]


def run(mode, replies, **extra):
    events = []
    with offline_lab(replies) as lab:
        outcome = generate_digest(lab, DEFAULT_PROFILE, RAW, mode=mode, today=TODAY, on_event=events.append, **extra)
        return outcome, lab.client.requests, events


# ---- news source ----

RSS = """<?xml version="1.0"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel><title>X</title>
<item><title>Lab ships &amp; video model</title><link>https://example.com/a</link>
<pubDate>Mon, 26 Oct 2026 20:04:16 +0000</pubDate><category>AI</category><category>Video</category><category>ai</category>
<description><![CDATA[<p>Short summary.</p>]]></description>
<content:encoded><![CDATA[<p>The lab released a <b>video</b> model.</p><script>alert(1)</script><p>It is fast.</p>]]></content:encoded>
</item><item><title>No link</title></item></channel></rss>"""

ATOM = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>V</title>
<entry><title type="html">Agents arrive</title><link rel="alternate" type="text/html" href="https://example.org/b"/>
<published>2026-10-26T19:34:58-04:00</published><category term="AI"/>
<summary type="html">&lt;p&gt;Agents arrive in apps.&lt;/p&gt;</summary></entry></feed>"""


def test_news_parser_reads_rss_and_atom():
    [story] = news.parse_feed(RSS, "TechCrunch")                       # the item without a link is dropped
    assert story == {"type": "news", "source": "TechCrunch", "title": "Lab ships & video model",
                     "url": "https://example.com/a", "published": "2026-10-26", "topics": ["AI", "Video"],
                     "abstract": "[TechCrunch] The lab released a video model. It is fast."}
    [entry] = news.parse_feed(ATOM, "The Verge")
    assert (entry["url"], entry["published"], entry["abstract"]) == (
        "https://example.org/b", "2026-10-26", "[The Verge] Agents arrive in apps.")


def test_news_fetch_keeps_recent_stories_rotates_outlets_and_skips_failures(monkeypatch):
    def feed(*stories):
        return "<rss><channel>" + "".join(
            f"<item><title>{t}</title><link>https://e.com/{t}</link><pubDate>{d}</pubDate></item>" for t, d in stories
        ) + "</channel></rss>"
    feeds = {"A": feed(("a1", "Tue, 27 Oct 2026 08:00:00 +0000"), ("a2", "Mon, 26 Oct 2026 08:00:00 +0000"),
                       ("old", "Tue, 20 Oct 2026 08:00:00 +0000")),
             "B": feed(("b1", "Tue, 27 Oct 2026 09:00:00 +0000"))}

    def get(url, timeout=20):
        if url == "down":
            raise urllib.error.URLError("unreachable")
        return feeds[url]
    monkeypatch.setattr(news, "_get", get)
    stories = news.fetch({"A": "A", "Down": "down", "B": "B"}, days=3, limit=10, today=TODAY)
    assert [s["title"] for s in stories] == ["a1", "b1", "a2"]


# ---- the Manager and its specialists ----

def test_reader_views_show_one_source_with_growth():
    by_id = {c["id"]: c for c in CANDIDATES}
    assert reader_view(by_id["p01"], TODAY)["categories"] == ["cs.AI"]
    repo = reader_view(by_id["r04"], TODAY)
    assert (repo["stars"], repo["age_days"], repo["stars_per_day"]) == (400, 4, 100.0)
    assert reader_view(by_id["n02"], TODAY)["outlet"] == "Outlet"


def test_manager_delegates_and_each_specialist_reads_only_its_source():
    outcome, requests, events = run("critic", team_replies(digest()) + [reply({"verdict": "PASS", "issues": []})])
    assert outcome["errors"] == [] and outcome["writer"] == "team" and len(requests) == 9

    manager_view = requests[0]["messages"][1]["content"]
    assert "Digest context" in manager_view and "Story 1" in manager_view
    assert "abstract" not in manager_view and "README excerpt" not in manager_view   # the Manager sees no texts
    for index, kind in ((2, "paper"), (4, "repo"), (6, "news")):
        system = requests[index]["messages"][0]["content"]
        assert system.startswith(f"You are Forager's {SPECIALISTS[kind]['name']}") and '"label": "AI agents"' in system
        shown = [v["id"] for v in json.loads(requests[index]["messages"][-1]["content"])]
        assert shown == [c["id"] for c in CANDIDATES if c["type"] == kind]
    final = requests[7]["messages"]
    assert any("Summary of n03." in str(m.get("content")) for m in final)     # the notes reach the Manager
    assert "[Outlet] Story 1 text." in requests[8]["messages"][1]["content"]   # the Critic reads the sources

    team = outcome["digest"]["checks"]["team"]
    assert [(t["specialist"], t["candidates"], len(t["reported"]), len(t["used"])) for t in team] == [
        ("Paper researcher", 4, 3, 3), ("Open-source researcher", 4, 3, 3), ("News researcher", 4, 3, 3)]
    assert team[2]["questions"] == ["What matters in today's news?"]
    assert "Written by the Manager from its specialists' notes: Paper researcher reported 3 of 4 papers" \
        in to_markdown(outcome["digest"], DEFAULT_PROFILE)
    assert [e["tool"] for e in events if e["type"] == "tool_started"] == [
        "ask_paper_researcher", "read_papers", "ask_open_source_researcher", "read_repos",
        "ask_news_researcher", "read_news"]


def test_manager_that_skips_the_specialists_is_sent_back():
    outcome, requests, _ = run("rules", [reply(digest()), reply(digest())])
    assert len(requests) == 2 and outcome["errors"]
    repair = requests[1]["messages"][-1]["content"]
    assert "You have not asked the News researcher; call ask_news_researcher" in repair
    assert "Item p01 was not reported by the Paper researcher" in repair


def test_unreported_items_and_unsupported_interest_labels_need_a_repair():
    bad = digest({**FITS, "p03": "i3", "p04": None})              # p03 was noted as breadth; p04 never reported
    outcome, requests, _ = run("rules", team_replies(bad) + [reply(digest())])
    assert outcome["errors"] == [] and len(requests) == 9
    repair = requests[8]["messages"][-1]["content"]
    assert "Item p04 was not reported by the Paper researcher" in repair
    assert "Item p03 is marked as matching i3, but the Paper researcher, who read it, marked it as breadth" in repair
    [first, second] = outcome["check_log"]
    assert first["stage"] == "draft" and len(first["problems"]) == 2 and second["problems"] == []


def test_critic_adjust_goes_back_to_the_manager_with_its_notes():
    flagged = {"type": "irrelevant_exploration", "refs": ["r03"], "explanation": "Unrelated.", "fix": "Drop it."}
    revised = digest({k: v for k, v in FITS.items() if k != "r03"})
    replies = team_replies(digest()) + [reply({"verdict": "ADJUST", "issues": [flagged]}), reply(revised)]
    outcome, requests, _ = run("critic", replies)
    assert outcome["revised"] and outcome["errors"] == [] and len(requests) == 10
    revision = requests[9]["messages"]
    assert "independent reviewer" in revision[-1]["content"]
    assert any("Summary of r03." in str(m.get("content")) for m in revision)  # same Manager session, notes kept
    assert "r03" not in {i["id"] for i in outcome["digest"]["items"]}
    assert "1 issue(s); the Manager revised the digest once" in to_markdown(outcome["digest"], DEFAULT_PROFILE)
    reviewed = outcome["reviewed_draft"]                                        # what the Critic saw
    assert "r03" in {i["id"] for i in reviewed["items"]} and "checks" not in reviewed


def test_an_interest_heading_over_unmatched_items_needs_a_repair():
    bad = digest()
    bad["brief"]["points"][2]["field"] = "Video editing"          # cites p03, which its specialist marked as breadth
    outcome, requests, _ = run("rules", team_replies(bad) + [reply(digest())])
    assert outcome["errors"] == [] and len(requests) == 9
    assert "brief.points[2] is under the heading 'Video editing'" in requests[8]["messages"][-1]["content"]
    assert [len(entry["problems"]) for entry in outcome["check_log"]] == [1, 0]
    outcome, requests, _ = run("rules", [reply(bad)], writer="single")   # other writers: measured, not enforced
    assert outcome["errors"] == [] and len(requests) == 1


def test_manager_names_items_and_code_copies_the_specialists_notes():
    final = {**digest(), "items": [{"id": i} for i in FITS]}
    final["items"][0] = {"id": "p01", "reason": {"kind": "breadth", "interest_id": None, "text": "Shown as breadth."}}
    final["items"][6] = {"id": "n01", "summary": "The Manager's own words."}
    outcome, requests, _ = run("rules", team_replies(final))
    assert outcome["errors"] == [] and len(requests) == 8
    items = {i["id"]: i for i in outcome["digest"]["items"]}
    assert (items["r01"]["summary"], items["r01"]["topics"]) == ("Summary of r01.", ["t"])
    assert items["r01"]["reason"] == {"kind": "interest", "interest_id": "i1", "text": "Worth a look."}
    assert items["n01"]["summary"] == "Summary of n01."        # summaries come from the specialist that read it
    assert items["p01"]["reason"]["text"] == "Shown as breadth."   # the Manager may show a match as breadth


def truncated(data):
    """A reply cut off at the output limit, as the lab reports it."""
    response = reply(data)
    response["choices"][0]["finish_reason"] = "length"
    return response


def test_a_lost_manager_answer_is_rewritten_from_the_notes_once():
    final = {**digest(), "items": [{"id": i} for i in FITS]}
    replies = team_replies(digest())[:-1] + [truncated(digest()), reply(final), reply({"verdict": "PASS", "issues": []})]
    outcome, requests, _ = run("critic", replies)
    assert outcome["errors"] == [] and outcome["rewritten"] and len(requests) == 10
    rewrite = requests[8]
    assert rewrite["messages"][0]["content"].startswith("You are the Manager") and not rewrite.get("tools")
    context = rewrite["messages"][1]["content"]
    assert "specialist_notes" in context and "Summary of n03." in context and "abstract" not in context
    assert [e["stage"] for e in outcome["check_log"]] == ["draft", "rewrite"]
    assert "Model output was truncated" in outcome["check_log"][0]["problems"][0]
    assert "wrote the digest again from the same notes" in to_markdown(outcome["digest"], DEFAULT_PROFILE)
    assert outcome["reviewed_draft"]["items"] == outcome["digest"]["items"]      # PASS: nothing was revised

    outcome, requests, _ = run("rules", [truncated(digest())])   # cut off before asking anyone: nothing to reuse
    assert not outcome["rewritten"] and outcome["digest"] is None and len(requests) == 1


def test_single_mode_keeps_the_single_writer():
    outcome, requests, _ = run("single", [reply(digest())])
    assert outcome["writer"] == "single" and len(requests) == 1 and outcome["team_calls"] == []
    assert "abstract" in requests[0]["messages"][1]["content"]
    assert "Written by a single agent" in to_markdown(outcome["digest"], DEFAULT_PROFILE)


def test_specialist_answers_are_checked_in_code():
    team = Team(DEFAULT_PROFILE, CANDIDATES, TODAY)
    extract = team._extractor("paper")

    def answer(text, read=True):
        if read:
            team._read.add("paper")                      # what calling read_papers does
        return json.loads(asyncio.run(extract(SimpleNamespace(input="Q?", final_output=text))))
    data = {"items": [{"id": "p01", "summary": "S.", "fit": "interest", "interest_id": "i9"},
                      {"id": "r01", "summary": "Not a paper.", "fit": "breadth"},
                      {"id": "p01", "summary": "Again."},
                      {"id": "p02", "summary": "S.", "fit": "Interest", "interest_id": "Video Editing"}], "overview": "O."}
    sent = answer(json.dumps(data))
    assert [(n["id"], n["fit"], n["interest_id"]) for n in sent["items"]] == [("p01", "breadth", None),
                                                                            ("p02", "interest", "i2")]
    assert sent["problems"] == ["p01: interest 'i9' is not in the profile; treated as breadth.",
                                "Ignored 'r01': not one of today's papers."]
    broken = answer("I could not read them.")
    assert broken["items"] == [] and broken["problems"] == ["The Paper researcher's answer was not valid JSON."]
    unread = answer(json.dumps(data), read=False)       # a valid answer, but it never read its source
    assert unread["items"] == [] and "answered without calling read_papers" in unread["problems"][0]
    assert [c["question"] for c in team.calls] == ["Q?", "Q?", "Q?"] and team.notes().keys() == {"p01", "p02"}


def test_event_lines_describe_the_delegation():
    asked = {"type": "tool_started", "agent": "Manager", "tool": "ask_news_researcher",
             "arguments": json.dumps({"input": "Any  agent\nnews?"})}
    assert event_line(asked) == "Manager asks the News researcher: Any agent news?"
    assert event_line({"type": "tool_completed", "agent": "Manager", "tool": "ask_news_researcher",
                       "result": {"items": [{}, {}]}}) == "News researcher reported 2 items."
    assert event_line({"type": "tool_completed", "agent": "Paper researcher", "tool": "read_papers",
                       "result": [{}, {}, {}]}) == "Paper researcher: read 3 papers."


# ---- the digest-modes runner ----

def test_digest_modes_runner_offline():
    replies = [reply(digest())] + team_replies(digest())
    with offline_lab(replies) as lab:
        records = modes_runner.run_modes(lab, DEFAULT_PROFILE, RAW, ["single", "rules"], today=TODAY)
    single, rules = records
    assert (single["writer"], single["requests"], rules["writer"], rules["requests"]) == ("single", 1, "team", 8)
    crowded = merge_items(digest({k: "i1" for k in FITS}), CANDIDATES, TODAY)
    crowded = modes_runner.metrics(crowded, DEFAULT_PROFILE, CANDIDATES, (), TODAY)
    assert (crowded["rule_problems"], crowded["uncovered"]) == (1, 2)      # single mode is measured the same way
    assert rules["metrics"] == {
        "items": 9, "by_type": {"paper": 3, "repo": 3, "news": 3},
        "by_bucket": {"AI agents": 3, "image generation": 2, "Breadth": 2, "video editing": 2},
        "largest_bucket": "AI agents", "largest_share": 0.33, "breadth_share": 0.22, "rule_problems": 0,
        "heading_problems": 0, "uncovered": 0, "points": 5, "points_with_valid_citations": 5, "critic_verdict": None,
        "critic_issues": 0, "revised": False}
    assert rules["reviewed_draft"] is None and rules["profile"] == DEFAULT_PROFILE     # the judges need no runtime/
    table = modes_runner.summary_table(records)
    assert "| 1 | rules | team | PASS | 9 | news 3, paper 3, repo 3 | AI agents 33% | 22% | 0 |" in table
    text = modes_runner.report(records, DEFAULT_PROFILE, ["news-2026-10-27.json"], "test")
    assert "Manager asked the news specialist: What matters in today's news?" in text and "#### Full items" in text


def test_digest_modes_runner_stops_at_the_cost_cap():
    with offline_lab([reply(digest()), reply(digest())]) as lab:
        spend = lambda record: lab.ledger.data.update(cost=lab.ledger.data["cost"] + 0.01)    # stands in for a paid run
        records = modes_runner.run_modes(lab, DEFAULT_PROFILE, RAW, ["single"], 3, today=TODAY, on_record=spend,
                                         max_cost=0.015)
    assert len(records) == 2                    # the third run would have started after $0.02


def test_digest_modes_runner_keeps_the_reviewed_draft():
    flagged = {"type": "irrelevant_exploration", "refs": ["r03"], "explanation": "Unrelated.", "fix": "Drop it."}
    revised = digest({k: v for k, v in FITS.items() if k != "r03"})
    revised["brief"]["points"][0]["text"] = "Point 0, narrower."
    replies = team_replies(digest()) + [reply({"verdict": "ADJUST", "issues": [flagged]}), reply(revised)]
    with offline_lab(replies) as lab:
        [record] = modes_runner.run_modes(lab, DEFAULT_PROFILE, RAW, ["critic"], today=TODAY)
    assert "r03" in {i["id"] for i in record["reviewed_draft"]["items"]} and record["metrics"]["revised"]
    json.dumps({k: v for k, v in record.items() if k != "outcome"})       # what the runner saves
    text = modes_runner.report([record], DEFAULT_PROFILE, ["news-2026-10-27.json"], "test")
    assert "#### What the revision changed" in text and "- Items dropped: r03" in text
    assert "- Draft points[0], rewritten or dropped: Point 0." in text
