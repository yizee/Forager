"""Stage 5 offline tests: the LLM judges, the calibration sheet, the memory scenario cases
and the snapshot guard.

Scripted model replies; no key, network or spending. Run: .venv/bin/python -m pytest
"""

import copy
import csv
import json
import sys
from argparse import Namespace
from collections import Counter
from datetime import date
from pathlib import Path

import pytest

from forager import labkit
from forager.critic import SOURCE_CHARS
from forager.memory import MemoryStore
from forager.onboarding import validate_profile
from forager.profile import is_expired

try:
    labkit.ensure_importable()
    from lab_support.testing import offline_lab, scripted_reply
except RuntimeError as exc:  # lab/ not unzipped yet
    pytest.skip(str(exc), allow_module_level=True)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "eval"))
import calibration  # noqa: E402
import judge_runs  # noqa: E402
import run_memory_cases as memory_cases  # noqa: E402

TODAY = "2026-10-28"
PROFILE = {"interests": [
    {"id": "i1", "label": "AI agents", "facets": ["Coding agents"], "type": "long_term", "source": "stated",
     "weight": 1.0, "expires": None},
    {"id": "i2", "label": "Sora 2", "facets": [], "type": "short_term", "source": "stated", "weight": 0.8,
     "expires": "2026-11-08"}],
    "consent": {"ratings": True, "likes": True, "clicks": False, "reading_time": False},
    "exploration": 0.2, "delivery_time": "08:00"}


def make_digest(fits=("i1", "i2", None), title="Paper"):
    items = [{"id": f"p0{n}", "type": "paper", "title": f"{title} {n}", "url": f"https://arxiv.org/abs/{n}",
              "source_text": "Long abstract. " * 200 if n == 1 else f"Source text {n}.", "summary": "Summary.",
              "topics": ["t"], "reason": {"kind": "interest", "interest_id": fit, "text": "Fits."} if fit
              else {"kind": "breadth", "interest_id": None, "text": "Nearby."}}
             for n, fit in enumerate(fits, start=1)]
    brief = {"points": [{"text": f"{title}: point A.", "field": "AI agents", "cites": ["p01"]},
                        {"text": f"{title}: point B.", "field": "Video", "cites": ["p02", "p03"]}],
             "connections": [{"text": f"{title}: A meets B.", "cites": ["p01", "p03"]}],
             "changes": [{"text": "First digest.", "cites": []}]}
    return {"date": TODAY, "items": items, "brief": brief, "checks": {"mode": "critic", "critic": {"verdict": "PASS"}}}


def run_record(mode, digest, draft=None, revised=False):
    return {"repeat": 0, "mode": mode, "writer": "team", "today": TODAY, "profile": PROFILE, "digest": digest,
            "reviewed_draft": draft, "metrics": {"revised": revised}}


def check(criterion, passed=True, reason="Evidence."):
    return {"id": criterion, "passed": passed, "reason": reason}


def answer(key, expected, fails=()):
    """A valid judgement: every criterion passes except the (ref, criterion) pairs in fails."""
    return {key: [{"ref": ref, "checks": [check(c, (ref, c) not in fails) for c in criteria]}
                  for ref, criteria in expected.items()]}


def reply(data):
    return scripted_reply(json.dumps(data))


# ---- the judges ----

def test_judge_views_are_blinded_and_stable():
    digest = make_digest()
    view, expected = judge_runs.items_view(digest, PROFILE, TODAY)
    assert set(view) == {"user_interests", "items"} and "critic" not in json.dumps(view)    # no mode, no checks
    assert view["user_interests"][1] == {"name": "Sora 2", "facets": [], "kind": "short-term focus"}
    by_ref = {i["ref"]: i for i in view["items"]}
    assert set(by_ref["p01"]) == {"ref", "type", "title", "source_text", "filed_as", "stated_reason"}  # no summary
    assert len(by_ref["p01"]["source_text"]) == SOURCE_CHARS
    assert (by_ref["p02"]["filed_as"], by_ref["p03"]["filed_as"]) == ("interest match: Sora 2", "breadth")
    assert expected == {"p01": ("label_correct", "worth_showing"), "p02": ("label_correct", "worth_showing"),
                        "p03": ("worth_showing",)}
    assert judge_runs.items_view(copy.deepcopy(digest), PROFILE, TODAY)[0] == view       # same digest, same order
    brief, expected = judge_runs.brief_view(digest)
    assert [e["ref"] for e in brief["entries"]] == ["points[0]", "points[1]", "connections[0]"]
    assert expected["points[0]"] == ("supported",) and expected["connections[0]"] == ("supported", "not_overstated")
    assert [s["id"] for s in brief["sources"]] == ["p01", "p02", "p03"] and "First digest" not in json.dumps(brief)


def test_judgements_are_checked_strictly():
    _, expected = judge_runs.items_view(make_digest(), PROFILE, TODAY)
    good = answer("items", expected)
    assert judge_runs.validate("items", good, expected) == []

    def broken(change):
        data = copy.deepcopy(good)
        change(data["items"])
        return data
    cases = {
        'only "items"': {"entries": good["items"]},
        "Missing p03": broken(lambda units: units.pop()),
        "repeats one": broken(lambda units: units.append(units[0])),
        "must be one of worth_showing": broken(lambda units: units[2]["checks"].insert(0, check("label_correct"))),
        "passed must be true or false": broken(lambda units: units[0]["checks"][0].update(passed="yes")),
        "needs a reason": broken(lambda units: units[0]["checks"][0].update(reason=" ")),
        "needs exactly id, passed and reason": broken(lambda units: units[0]["checks"][0].update(score=1)),
        "missing worth_showing": broken(lambda units: units[0]["checks"].pop()),
    }
    for problem, data in cases.items():
        assert any(problem in p for p in judge_runs.validate("items", data, expected)), problem
    proposal = {"proposals[0]": judge_runs.KINDS["proposal"]["criteria"]}
    both = {"checks": [check("evidence_supports_change"), check("message_matches_change")]}
    assert judge_runs.validate("proposal", both, proposal) == []
    assert judge_runs.validate("proposal", {"checks": both["checks"][:1]}, proposal) == [
        "proposals[0]: missing message_matches_change."]


def test_a_judgement_gets_one_repair_and_a_failure_is_never_a_pass():
    view, expected = judge_runs.items_view(make_digest(), PROFILE, TODAY)
    incomplete = {"items": answer("items", expected)["items"][:2]}
    fixed = answer("items", expected, fails={("p02", "label_correct")})
    with offline_lab([reply(incomplete), reply(fixed)]) as lab:
        outcome = judge_runs.judge(lab, "items", view, expected)
        first, repair = lab.client.requests
    assert outcome["attempts"] == 2 and outcome["checks"]["p02"]["label_correct"]["passed"] is False
    assert "Missing p03" in repair["messages"][-1]["content"]
    assert any(judge_runs.CRITERIA["label_correct"] in str(m.get("content")) for m in first["messages"])
    with offline_lab([reply(incomplete), reply(incomplete)]) as lab:
        failed = judge_runs.judge(lab, "items", view, expected)
    assert failed["checks"] is None and failed["errors"]
    assert judge_runs.digest_scores(failed["checks"], None) == {}           # missing, not passed


def test_identical_views_are_judged_once_and_scored_in_code():
    final = make_digest()
    runs = [("modes.jsonl", 0, run_record("critic", final, draft=copy.deepcopy(final))),
            ("modes.jsonl", 1, run_record("rules", make_digest(fits=("i1", "i1", None), title="Other")))]
    jobs = judge_runs.jobs_for(runs)
    assert [(j["index"], j["version"], j["kind"]) for j in jobs] == [
        (0, "final", "items"), (0, "final", "brief"), (0, "reviewed_draft", "items"),
        (0, "reviewed_draft", "brief"), (1, "final", "items"), (1, "final", "brief")]
    replies = [reply(answer("items", jobs[0]["expected"], fails={("p02", "label_correct")})),
               reply(answer("entries", jobs[1]["expected"], fails={("connections[0]", "not_overstated")})),
               reply(answer("items", jobs[4]["expected"])), reply(answer("entries", jobs[5]["expected"]))]
    with offline_lab(replies) as lab:
        records = judge_runs.run_judges(lab, jobs)
        assert len(lab.client.requests) == 4                    # the draft the Critic passed is not sent again
    assert records[2]["cached_from"] == "modes.jsonl#0 final items" and records[2]["checks"] == records[0]["checks"]
    rows = {(r["index"], r["version"]): r for r in judge_runs.digest_rows(records)}
    critic = rows[(0, "final")]
    assert (critic["label_accuracy"], critic["worth_showing"], critic["support_rate"],
            critic["not_overstated"]) == (0.5, 1.0, 1.0, 0.0)
    assert (critic["breadth_share"], critic["entropy"], critic["interests_covered"]) == (0.3333, 1.0, 2)
    summary = judge_runs.summarize_digests(list(rows.values()))
    assert summary["digests"] == {"rules": 1, "critic": 1} and summary["revised_runs"] == 0
    assert summary["contrasts"]["critic - rules"]["label_accuracy"]["mean"] == -0.5
    text = judge_runs.report(records, "test")
    assert "| critic | 1 | 50% [50%, 50%]" in text and "4 judge calls (2 reused an identical view)" in text


def test_bootstrap_intervals_and_revision_pairs():
    stat = judge_runs.bootstrap([1, 0, 1, 1])
    assert stat["n"] == 4 and stat["mean"] == 0.75 and 0 <= stat["low"] <= 0.75 <= stat["high"] <= 1
    assert judge_runs.bootstrap([None])["mean"] is None
    assert judge_runs.bootstrap_diff([1, 1], [0, 0]) == {"n": [2, 2], "mean": 1.0, "low": 1.0, "high": 1.0}
    rows = [{"file": "f", "index": n, "version": version, "mode": "critic", "revised": True, "label_accuracy": value}
            for n, pair in enumerate([(0.5, 1.0), (0.75, 0.75)])
            for version, value in zip(("reviewed_draft", "final"), pair)]
    summary = judge_runs.summarize_digests(rows)
    assert summary["revised_runs"] == 2 and summary["revision"]["label_accuracy"]["mean"] == 0.25


# ---- the memory scenarios ----

@pytest.fixture
def case_store(tmp_path):
    def make(case):
        memory_cases.write_case(tmp_path / case["id"], case)
        return MemoryStore(runtime=tmp_path / case["id"], today=case["today"])
    return make


def test_memory_scenarios_are_well_formed(case_store):
    cases = {c["id"]: c for c in memory_cases.scenarios()}
    assert list(cases) == ["strong", "weak", "unconsented", "mixed", "mislabelled", "rejected", "negative", "expired"]
    texts = memory_cases.source_texts()
    for case in cases.values():
        assert validate_profile(case["profile"]) == [], case["id"]
        assert all(texts.get(s["item"]["title"]) for s in case["signals"]), case["id"]   # every item has its text
        assert len(case_store(case).usable()) >= 2, case["id"]                           # so the agent runs
    assert {e["id"] for e in case_store(cases["unconsented"]).usable()} == {"s305", "s306"}
    [rejection] = case_store(cases["rejected"]).recent_rejections()
    assert rejection["key"] == ["add_interest", "3d generation"]
    expired = cases["expired"]
    assert is_expired(expired["profile"]["interests"][-1], expired["today"])
    assert expired["profile"]["interests"][-1]["label"] == "Lumen-V 2"
    mislabelled = cases["mislabelled"]
    assert {s["item"]["interest_id"] for s in mislabelled["signals"]} == {"i5"}
    assert mislabelled["profile"]["interests"][4]["label"] == "Sora 2"


def propose(evidence):
    return scripted_reply(calls=[("propose_profile_update", {
        "action": "add_interest", "evidence": evidence, "interest_id": None, "label": "3D generation",
        "interest_type": "long_term", "weight": 0.8,
        "message": "You rated two 3D generation papers 5/5 and liked one. Add 3D generation as a long-term interest?"})])


def done():
    return scripted_reply("Proposed one change.")


def test_memory_runs_count_what_reached_the_profile_and_feed_the_judge(tmp_path):
    cases = {c["id"]: c for c in memory_cases.scenarios()}
    strong = ["s101", "s102", "s103"]
    with offline_lab([propose(strong), done(), propose(strong), done()]) as lab:
        approval, silent = memory_cases.run_cases(lab, [cases["strong"]])
    assert (approval["mode"], silent["mode"]) == ("approval", "silent")
    pick = lambda r: tuple(r["measures"][k] for k in ("shown", "written", "written_without_approval"))
    assert (pick(approval), pick(silent)) == ((1, 1, 0), (0, 1, 1))
    assert approval["views"][0]["change"] == 'Add "3D generation" as a long-term interest (weight 0.8)'
    assert approval["interests_after"][-1]["approved_on"] == TODAY
    assert silent["interests_after"][-1]["updated_silently_on"] == TODAY
    [unit] = approval["judge_units"]
    assert (unit["ref"], unit["decision"]) == ("proposals[0]", "approved")
    assert set(unit["view"]) == {"user_interests", "change", "message", "evidence", "other_signals"}
    evidence = unit["view"]["evidence"]
    assert [e["signal"] for e in evidence] == ["rated 5/5", "rated 5/5", "liked"]
    assert evidence[0]["item"]["source_text"] == memory_cases.source_texts()[evidence[0]["item"]["title"]] != ""
    assert evidence[0]["item"]["filed_as"] == "interest match: Image generation"

    with offline_lab([propose(["s301", "s305"]), done()]) as lab:
        [unconsented] = memory_cases.run_cases(lab, [cases["unconsented"]], modes=["approval"])
    m = unconsented["measures"]
    assert (m["shown"], m["written"], m["blocked"], m["unconsented_cited"]) == (0, 0, 1, ["s301"])
    assert m["unconsented_in_context"] == [] and unconsented["judge_units"] == []
    assert unconsented["signals"]["unconsented"] == ["s301", "s302", "s303", "s304"]
    with offline_lab([propose(["s601", "s602", "s603"]), done()]) as lab:
        [rejected] = memory_cases.run_cases(lab, [cases["rejected"]], modes=["silent"])
    assert (rejected["measures"]["repeats_of_rejection"], rejected["measures"]["written"]) == (1, 0)
    text = memory_cases.report([approval, silent, unconsented, rejected], "test")
    assert "| approval | 2 | 2 | 1 | 1 | 0 | 1 | 0 | 1 |" in text and "| silent | 2 | 2 | 0 | 1 | 1 | 1 | 0 | 0 |" in text
    assert "### Strong evidence (`strong`, expected: change)" in text

    silent = copy.deepcopy(silent)
    silent["judge_units"][0]["ref"] = "proposals[1]"             # the same view under another ref
    jobs = judge_runs.jobs_for([("memory.jsonl", 0, approval), ("memory.jsonl", 1, silent)])
    assert [(j["mode"], j["kind"], j["decision"]) for j in jobs] == [
        ("approval", "proposal", "approved"), ("silent", "proposal", "silent")]
    verdict = {"checks": [check("evidence_supports_change"), check("message_matches_change")]}
    with offline_lab([reply(verdict)]) as lab:                      # the same view in both modes: judged once
        records = judge_runs.run_judges(lab, jobs)
    assert records[1]["cached_from"] and list(records[1]["checks"]) == ["proposals[1]"]
    summary = judge_runs.summarize_memory(records)["by_mode"]
    assert (summary["approval"]["passed"], summary["silent"]["passed"]) == (1, 0)   # silent fails approval by design
    assert summary["silent"]["unsupported_written_unseen"] == 0
    assert "| approval | 1 | 0 | 1 | 1 | 1 | 1 | 0 | 0 |" in judge_runs.report(records, "test")

    memory = [("memory.jsonl", 0, approval), ("memory.jsonl", 1, silent)]          # a sheet for proposals only
    picked = calibration.write_sheet(tmp_path, calibration.sample([], memory), [], {"memory.jsonl"}, 619)
    assert list(picked) == ["proposals"] and len(picked["proposals"]) == 1    # the same change and message once
    assert not (tmp_path / "items.csv").exists()
    with (tmp_path / "proposals.csv").open(encoding="utf-8-sig", newline="") as f:
        [row] = list(csv.DictReader(f))
    assert row["change"] == 'Add "3D generation" as a long-term interest (weight 0.8)'
    assert "Sora 2 (short-term focus, weight 0.8)" in row["user_interests"] and "rated 5/5 on 2026-10-25" in row["evidence"]


# ---- calibration ----

def calibration_runs():
    return [("modes.jsonl", n, run_record(mode, make_digest(title=f"Paper set {n}")))
            for n, mode in enumerate(["single", "rules", "critic"] * 2)]


def test_calibration_sheet_is_blinded_and_spread_over_modes(tmp_path):
    runs = calibration_runs()
    picked = calibration.sample(runs, items=6, brief=6)
    calibration.write_sheet(tmp_path, picked, calibration.interests_of(runs), {"modes.jsonl"}, 619)
    key = json.loads((tmp_path / "key.json").read_text())
    assert Counter(row["mode"] for row in key["rows"]["items"]) == {"single": 2, "rules": 2, "critic": 2}
    assert Counter(row["mode"] for row in key["rows"]["brief"]) == {"single": 2, "rules": 2, "critic": 2}
    with (tmp_path / "items.csv").open(encoding="utf-8-sig", newline="") as f:
        items = list(csv.DictReader(f))
    assert list(items[0]) == ["row", "label_correct", "worth_showing", "note", "title", "type", "filed_as",
                              "stated_reason", "source_text"]                        # no mode column
    assert all((row["label_correct"] == "n/a") == (row["filed_as"] == "breadth") for row in items)
    assert sum(row["filed_as"] == "breadth" for row in items) == 3                    # a third per mode
    with (tmp_path / "brief.csv").open(encoding="utf-8-sig", newline="") as f:
        brief = list(csv.DictReader(f))
    assert sum(row["entry"] == "connection" for row in brief) == 3
    assert all((row["not_overstated"] == "n/a") == (row["entry"] == "point") for row in brief)
    readme = (tmp_path / "README.md").read_text()
    assert judge_runs.CRITERIA["worth_showing"] in readme and "**Sora 2** (short-term focus)" in readme


def test_calibration_scores_agreement_and_kappa(tmp_path):
    table = [(True, True)] * 6 + [(False, False)] * 2 + [(True, False), (False, True)]
    assert calibration.kappa(table)["kappa"] == pytest.approx(0.5238, abs=1e-4)
    assert calibration.kappa([(True, True)] * 3)["kappa"] is None            # chance agreement is 1
    runs = calibration_runs()
    picked = calibration.sample(runs, items=6, brief=6)
    calibration.write_sheet(tmp_path, picked, calibration.interests_of(runs), {"modes.jsonl"}, 619)
    path = tmp_path / "items.csv"
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:                                    # the author passes everything but row 1 and skips row 2
        row.update({c: "y" for c in ("label_correct", "worth_showing") if row[c] != "n/a"})
    rows[0]["worth_showing"], rows[1]["worth_showing"] = "n", ""
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    judged = [{"file": u["file"], "index": u["index"], "version": u["version"], "kind": u["kind"],
               "checks": {u["ref"]: {c: {"passed": True, "reason": "r"} for c in u["criteria"]}}}
              for u in picked["items"]]                 # the judge passes every item; brief not judged
    results = calibration.score(tmp_path, judged)
    worth = results["items.worth_showing"]
    assert (worth["n"], worth["agreement"], worth["kappa"]) == (5, 0.8, 0.0)
    assert (worth["author_fail_judge_pass"], worth["unlabelled"], worth["disagreements"]) == (1, 1, [1])
    assert results["items.label_correct"]["agreement"] == 1.0 and results["items.label_correct"]["kappa"] is None
    assert results["brief.supported"]["unlabelled"] == 6 and results["brief.not_overstated"]["unlabelled"] == 3
    assert "| items.worth_showing | 5 | 80% | 0.00 |" in calibration.score_report(results, tmp_path, ["judge.jsonl"])


def test_a_draft_prefills_the_sheet_and_the_score_counts_the_authors_changes(tmp_path):
    runs = calibration_runs()
    picked = calibration.sample(runs, items=6, brief=6)
    calibration.write_sheet(tmp_path, picked, calibration.interests_of(runs), {"modes.jsonl"}, 619)
    path = tmp_path / "items.csv"

    def read():
        with path.open(encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))

    blank = read()
    applies = lambda row: [c for c in ("label_correct", "worth_showing") if row[c] != "n/a"]
    draft = [{"row": int(r["row"]), "labels": {c: "y" for c in applies(r)},
              "reasons": {c: f"reason for {c}" for c in applies(r)},
              "unsure": ["worth_showing"] if r["row"] == "2" else []} for r in blank]
    with pytest.raises(SystemExit, match="must label exactly"):         # a missing cell writes nothing
        calibration.write_draft(tmp_path, "items", [draft[0], {**draft[1], "labels": {}}, *draft[2:]], by="Claude")
    assert read() == blank
    assert calibration.write_draft(tmp_path, "items", draft, by="Claude") == sum(len(applies(r)) for r in blank)
    rows = read()
    assert [{c: row[c] for c in ("label_correct", "worth_showing")} for row in rows] == \
           [{c: "y" if c in applies(r) else "n/a" for c in ("label_correct", "worth_showing")} for r in blank]
    assert rows[1]["note"].startswith("Draft (unsure: worth_showing) | ")
    assert "worth_showing: reason for worth_showing" in rows[1]["note"]
    assert "## Draft labels" in (tmp_path / "README.md").read_text()
    with pytest.raises(SystemExit, match="already has a draft"):
        calibration.write_draft(tmp_path, "items", draft, by="Claude")
    rows[0]["worth_showing"] = "n"                                     # the author disagrees with one label
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    judged = [{"file": u["file"], "index": u["index"], "version": u["version"], "kind": u["kind"],
               "checks": {u["ref"]: {c: {"passed": True, "reason": "r"} for c in u["criteria"]}}}
              for u in picked["items"]]
    results = calibration.score(tmp_path, judged)
    assert (results["items.worth_showing"]["drafted"], results["items.worth_showing"]["changed_from_draft"]) == (6, [1])
    assert results["items.label_correct"]["changed_from_draft"] == [] and results["brief.supported"]["drafted"] == 0
    report = calibration.score_report(results, tmp_path, ["judge.jsonl"])
    assert "Draft labels by Claude, reviewed by the author:" in report
    assert "- items.worth_showing: changed 1 of 6 (rows 1)" in report and "- items.label_correct: changed 0 of 3" in report


# ---- snapshots ----

def test_snapshot_keeps_an_existing_file(tmp_path, monkeypatch):
    from forager import __main__ as cli
    today, fetched = date.today().isoformat(), []
    monkeypatch.setattr(cli, "SNAPSHOT_DIR", tmp_path)
    monkeypatch.setattr(cli, "fetch_sources",
                        lambda names, _: fetched.append(list(names)) or {name: [{"title": name}] for name in names})
    (tmp_path / f"github-{today}.json").write_text("[]\n")
    cli.cmd_snapshot(Namespace(sources=["arxiv", "github"], max_results=30, overwrite=False))
    assert fetched == [["arxiv"]] and (tmp_path / f"github-{today}.json").read_text() == "[]\n"
    cli.cmd_snapshot(Namespace(sources=["github"], max_results=30, overwrite=True))
    assert json.loads((tmp_path / f"github-{today}.json").read_text()) == [{"title": "github"}]
