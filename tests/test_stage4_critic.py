"""Stage 4 offline tests (Idea 3): the Critic, the three pipeline modes, and the case-set scorer.

Scripted model replies; no key, network or spending. Run: .venv/bin/python -m pytest
"""

import copy
import importlib.util
import json
from pathlib import Path

import pytest

from forager import labkit
from forager.critic import MAX_ISSUES, SOURCE_CHARS, check_review, critic_input, critique
from forager.digest import COVERAGE_HINT, generate_digest, prepare_candidates
from forager.profile import DEFAULT_PROFILE
from forager.render import to_markdown
from forager.sources.arxiv import load_snapshot

try:
    labkit.ensure_importable()
    from lab_support.testing import offline_lab, scripted_reply
except RuntimeError as exc:  # lab/ not unzipped yet
    pytest.skip(str(exc), allow_module_level=True)

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("run_critic_cases", ROOT / "eval" / "run_critic_cases.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

CASES = {case["id"]: case for case in runner.load_cases()}
RAW = load_snapshot(ROOT / "data" / "snapshot" / "arxiv-2026-10-25.json")
IDS = [c["id"] for c in prepare_candidates(RAW)]
TODAY = "2026-10-25"


def reply(data):
    return scripted_reply(json.dumps(data))


def issue(kind, refs, explanation="Clearly wrong.", fix="Fix it."):
    return {"type": kind, "refs": refs, "explanation": explanation, "fix": fix}


def adjust(*issues):
    return {"verdict": "ADJUST", "issues": list(issues)}


PASS = {"verdict": "PASS", "issues": []}


def perfect(case):
    """The ground truth written as a Critic answer."""
    problems = case["expected"]["problems"]
    return adjust(*[issue(p["type"], p["refs"], p["explanation"]) for p in problems]) if problems else PASS


# ---- the Critic's answer is checked in code ----

def test_ground_truth_of_every_case_is_a_valid_critic_answer():
    for case in CASES.values():
        assert check_review(perfect(case), case["digest"]) == [], case["id"]


def test_check_review_rejects_malformed_answers():
    digest = CASES["ie-01"]["digest"]
    bad = {
        "verdict must be PASS or ADJUST": {"verdict": "MAYBE", "issues": []},
        "issues must be a list": {"verdict": "PASS", "issues": None},
        "Use ADJUST with at least one issue": {"verdict": "ADJUST", "issues": []},
        "or PASS with an empty issues list": {"verdict": "PASS", "issues": [issue("near_duplicate", ["p09", "p08"])]},
        f"at most {MAX_ISSUES} issues": adjust(*[issue("unsupported_citation", ["points[0]"])] * (MAX_ISSUES + 1)),
        "type must be one of": adjust(issue("style", ["p30"])),
        "are not item IDs": adjust(issue("irrelevant_exploration", ["p99"])),
        "needs an explanation": adjust(issue("irrelevant_exploration", ["p30"], explanation=" ")),
        "names at least two items": adjust(issue("near_duplicate", ["n01"])),
        "irrelevant_exploration names breadth items": adjust(issue("irrelevant_exploration", ["p09"])),
        "mislabeled_interest names items marked": adjust(issue("mislabeled_interest", ["p01"])),
        "name the point": adjust(issue("unsupported_citation", ["p09"])),
        "name the connection": adjust(issue("overstated_connection", ["p01", "p14"])),
    }
    for expected, answer in bad.items():
        assert any(expected in error for error in check_review(answer, digest)), expected
    assert check_review(adjust(issue("irrelevant_exploration", ["p30"])), digest) == []


def test_critic_sees_sources_and_refs_but_no_ground_truth():
    case = CASES["ie-01"]
    view = json.loads(critic_input(case["profile"], case["digest"], case["today"]))
    p30 = next(i for i in view["items"] if i["id"] == "p30")
    assert p30["source_text"] == next(i for i in case["digest"]["items"] if i["id"] == "p30")["source_text"][:SOURCE_CHARS]
    assert view["brief"]["points"][0]["ref"] == "points[0]" and view["brief"]["connections"][0]["ref"] == "connections[0]"
    assert set(view) == {"today", "profile", "brief", "items"}
    assert {key for item in view["items"] for key in item} == {
        "id", "type", "title", "source_text", "digest_summary", "topics", "reason"}   # no url, no synthetic flag
    text = json.dumps(view)
    for case in CASES.values():                                     # no ground truth from any case
        for problem in case["expected"]["problems"]:
            assert problem["explanation"] not in text


def test_critique_offline_repairs_a_bad_ref():
    case = CASES["ie-01"]
    replies = [reply(adjust(issue("irrelevant_exploration", ["p31"]))),
               reply(adjust(issue("irrelevant_exploration", ["p30"])))]
    with offline_lab(replies) as lab:
        outcome = critique(lab, case["profile"], case["digest"], today=case["today"])
        repair = lab.client.requests[1]["messages"][-1]["content"]
    assert outcome["errors"] == [] and outcome["attempts"] == 2
    assert outcome["data"]["issues"][0]["refs"] == ["p30"] and "p31" in repair


# ---- pipeline modes (writer + rules + Critic) ----

def draft(ids=IDS, reasons=("i1", "i1", "i2", "i2", "i3", "i3", None, None)):
    items = [{"id": i, "summary": "Core contribution.", "topics": ["t"],
              "reason": {"kind": "interest", "interest_id": r, "text": "match"} if r
              else {"kind": "breadth", "interest_id": None, "text": "nearby"}} for i, r in zip(ids, reasons)]
    return {"brief": {"points": [{"text": f"Point {n}.", "field": "f", "cites": [ids[n]]} for n in range(5)],
                      "connections": [{"text": "Link.", "cites": [ids[0], ids[2]]}],
                      "changes": [{"text": "First digest.", "cites": []}]},
            "items": items}


CROWDED = draft(reasons=("i1",) * 6 + ("i2", "i3"))                     # i1: 6 of 8 items
REVISED = draft(ids=IDS[:6] + IDS[8:10])                                 # breadth p07 swapped for p09


def run(mode, replies, profile=DEFAULT_PROFILE):
    with offline_lab(replies) as lab:
        outcome = generate_digest(lab, profile, RAW, mode=mode, today=TODAY)
        return outcome, lab.client.requests


def test_single_mode_checks_structure_only():
    outcome, requests = run("single", [reply(CROWDED)])
    assert outcome["errors"] == [] and len(requests) == 1 and outcome["critic"] is None


def test_rules_mode_repairs_a_rule_violation_without_a_critic():
    outcome, requests = run("rules", [reply(CROWDED), reply(draft())])
    assert outcome["errors"] == [] and outcome["critic"] is None and len(requests) == 2
    assert "'i1' has 6 of 8 items" in requests[1]["messages"][-1]["content"]


def test_critic_pass_keeps_the_draft():
    outcome, requests = run("critic", [reply(draft()), reply(PASS)])
    assert len(requests) == 2 and outcome["critic"]["verdict"] == "PASS" and not outcome["revised"]
    critic_view = requests[1]["messages"][1]["content"]
    assert "Digest to review" in critic_view and RAW[0]["abstract"][:200] in critic_view   # sources reach the Critic
    assert "- Critic: no problems found." in to_markdown(outcome["digest"], DEFAULT_PROFILE)


def test_critic_adjust_leads_to_one_revision():
    flagged = issue("irrelevant_exploration", [IDS[6]], "Unrelated to the profile.", "Drop it.")
    outcome, requests = run("critic", [reply(draft()), reply(adjust(flagged)), reply(REVISED)])
    assert len(requests) == 3 and outcome["revised"] and outcome["errors"] == []
    assert IDS[6] not in {i["id"] for i in outcome["digest"]["items"]}
    revision = requests[2]["messages"][-1]["content"]
    assert "independent reviewer" in revision and "Unrelated to the profile." in revision
    markdown = to_markdown(outcome["digest"], DEFAULT_PROFILE)
    assert "1 issue(s); the writer revised the digest once" in markdown and f"irrelevant exploration ({IDS[6]})" in markdown


def test_revision_that_breaks_a_rule_falls_back_to_the_checked_draft():
    flagged = issue("irrelevant_exploration", [IDS[6]])
    outcome, requests = run("critic", [reply(draft()), reply(adjust(flagged)), reply(CROWDED), reply(CROWDED)])
    assert len(requests) == 4 and not outcome["revised"] and outcome["errors"] == []
    assert outcome["revision_errors"] and IDS[6] in {i["id"] for i in outcome["digest"]["items"]}
    assert "the checked draft is shown" in to_markdown(outcome["digest"], DEFAULT_PROFILE)


def test_unusable_critic_answer_keeps_the_draft():
    outcome, requests = run("critic", [reply(draft()), reply({"verdict": "?"}), reply({"verdict": "?"})])
    assert len(requests) == 3 and outcome["critic"]["verdict"] is None and outcome["critic"]["errors"]
    assert outcome["errors"] == [] and "no usable review" in to_markdown(outcome["digest"], DEFAULT_PROFILE)


def test_uncovered_interest_becomes_a_warning_after_one_repair():
    profile = copy.deepcopy(DEFAULT_PROFILE)
    profile["interests"].append({"id": "i4", "label": "AI copyright policy", "facets": [], "type": "long_term",
                                 "source": "stated", "weight": 0.5, "expires": None})
    outcome, requests = run("rules", [reply(draft()), reply(draft())], profile)
    assert len(requests) == 2 and COVERAGE_HINT.strip() in requests[1]["messages"][-1]["content"]
    assert outcome["errors"] == [] and outcome["warnings"] == [
        "Long-term interest 'AI copyright policy' (i4) has no item in the last 7 days."]
    assert "- Not covered: Long-term interest 'AI copyright policy'" in to_markdown(outcome["digest"], profile)


# ---- scoring the case set ----

def test_scoring_rules():
    case = CASES["nd-01"]
    assert all(p["caught"] and p["type_match"] for p in runner.score_case(case, perfect(case))["problems"])
    assert not any(p["caught"] for p in runner.score_case(case, PASS)["problems"])
    one_ref = runner.score_case(case, adjust(issue("near_duplicate", ["n01", "p09"])))
    assert not one_ref["problems"][0]["caught"] and one_ref["false_alarms"] == []   # names only one of the group
    debatable = runner.score_case(CASES["ctrl-a"], adjust(issue("mislabeled_interest", ["p24"])))
    assert debatable["false_alarms"] == [] and len(debatable["ignored"]) == 1
    wrong = runner.score_case(CASES["ie-02"], adjust(issue("mislabeled_interest", ["p17"])))
    assert len(wrong["false_alarms"]) == 1 and not wrong["problems"][0]["caught"]
    failed = runner.score_case(case, None)
    assert failed["failed"] and not failed["problems"][0]["caught"]


def test_perfect_critic_and_rules_only_bracket_the_scores():
    cases = list(CASES.values())
    best = runner.summarize([runner.score_case(c, perfect(c)) for c in cases])
    rules = runner.summarize([runner.score_case(c, runner.RULES_ONLY) for c in cases])
    assert best["recall"] == 1.0 and best["type_match"] == 1.0 and best["false_alarm_issues"] == 0
    assert rules["recall"] == 0.0 and rules["false_alarm_issues"] == 0
    assert best["problems"] == rules["problems"] == 19 and best["control_reviews"] == 4   # 16 cases x 1 + live-01 x 3


def test_run_reviews_offline_records_scores_and_usage():
    cases = [CASES["ie-01"], CASES["ctrl-a"]]
    replies = [reply(adjust(issue("irrelevant_exploration", ["p30"]))), reply(PASS)]
    with offline_lab(replies) as lab:
        records = runner.run_reviews(lab, cases)
    assert [r["case"] for r in records] == ["ie-01", "ctrl-a"] and all(r["usage"] for r in records)
    summary = runner.summarize([r["score"] for r in records])
    assert summary["caught"] == summary["problems"] == 1 and summary["controls_with_false_alarm"] == 0
