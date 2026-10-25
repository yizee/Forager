"""The Critic case set: every case passes the code rules, and its ground truth is well formed.

These properties are what make the set a fair test of "does a Critic add value beyond rules".
"""

import copy
import importlib.util
import json
from collections import Counter
from pathlib import Path

import pytest

from forager.checks import check_coverage

ROOT = Path(__file__).resolve().parent.parent
CASE_DIR = ROOT / "eval" / "cases" / "critic"
spec = importlib.util.spec_from_file_location("build_critic_cases", ROOT / "eval" / "build_critic_cases.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

CASES = {path.stem: json.loads(path.read_text()) for path in sorted(CASE_DIR.glob("*.json"))}
SNAPSHOT = json.loads((ROOT / "data" / "snapshot" / "arxiv-2026-10-25.json").read_text())


@pytest.mark.parametrize("case_id", sorted(CASES))
def test_every_case_passes_all_rules_and_has_valid_refs(case_id):
    assert builder.validate(CASES[case_id]) == []


def test_validator_is_not_vacuous():
    case = copy.deepcopy(CASES["ctrl-a"])
    case["digest"]["items"] = [i for i in case["digest"]["items"] if i["reason"].get("interest_id") != "i4"]
    case["digest"]["brief"]["points"] = [p for p in case["digest"]["brief"]["points"]
                                         if p["field"] != "AI copyright policy"]
    case["expected"]["problems"] = [{"type": "near_duplicate", "refs": ["p99"], "explanation": ""}]
    errors = builder.validate(case)
    assert any("AI copyright policy" in e for e in errors)          # coverage rule fires
    assert "ref p99 not in digest" in errors and "verdict does not match problems" in errors


def test_mislabel_is_what_lets_ml03_pass_coverage():
    case = CASES["ml-03"]
    corrected = copy.deepcopy(case["digest"])
    next(i for i in corrected["items"] if i["id"] == "p29")["reason"] = {"kind": "breadth", "text": "privacy"}
    assert check_coverage(case["digest"], case["profile"], today=case["today"]) == []
    assert check_coverage(corrected, case["profile"], today=case["today"]) == [
        "Long-term interest 'AI copyright policy' (i4) has no item in the last 7 days."]


def test_live_digest_fails_coverage_without_the_added_history():
    case = CASES["live-01"]
    assert check_coverage(case["digest"], case["profile"], [], case["today"]) == [
        "Long-term interest 'AI copyright policy' (i4) has no item in the last 7 days."]


def test_balanced_case_mix():
    counts = Counter(case["category"] for case in CASES.values())
    assert counts["control"] >= 4
    assert all(counts[kind] >= 3 for kind in builder.ISSUE_TYPES)   # each problem type has 3+ cases
    for case in CASES.values():
        for entry in case["expected"]["problems"]:
            if entry["type"] == "near_duplicate":
                assert len(entry["refs"]) >= 2


def test_real_items_are_unaltered_and_synthetic_items_are_marked():
    by_url = {paper["url"]: paper for paper in SNAPSHOT}
    for case in CASES.values():
        for item in case["digest"]["items"]:
            if item["synthetic"]:
                assert item["url"].startswith("https://example.com/") and item["type"] in {"news", "repo"}
            else:
                paper = by_url[item["url"]]
                assert (item["title"], item["source_text"]) == (paper["title"], paper["abstract"])


def test_committed_cases_match_a_fresh_build(tmp_path):
    builder.main(tmp_path)
    built = {path.name: path.read_text() for path in tmp_path.iterdir() if path.is_file()}
    committed = {path.name: path.read_text() for path in CASE_DIR.iterdir() if path.is_file()}
    assert built == committed
