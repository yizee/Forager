"""Run the Critic on the case set and score it against the ground truth.

Every review uses a fresh Critic session (empty history) on one lab connection (one
ledger), as in the lab's evaluation_example. Scoring follows eval/cases/critic/README.md.
A PASS-only review stands in for rules-only, which by construction flags nothing here.

Usage (paid; prints an estimate and asks before starting):
  .venv/bin/python eval/run_critic_cases.py --repeats 3
  .venv/bin/python eval/run_critic_cases.py --cases ie-01,uc-03
Results go to eval/results/critic-<timestamp>.jsonl; a summary is printed at the end.
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from forager import labkit  # noqa: E402
from forager.critic import critique  # noqa: E402

CASE_DIR = ROOT / "eval" / "cases" / "critic"
RESULT_DIR = ROOT / "eval" / "results"
# Planning figure per review (about 7k tokens in, 1k out, plus occasional repairs).
# The ledger records the real cost.
ESTIMATED_COST_PER_REVIEW = 0.002
RULES_ONLY = {"verdict": "PASS", "issues": []}


def load_cases(ids=None) -> list[dict]:
    cases = [json.loads(path.read_text()) for path in sorted(CASE_DIR.glob("*.json"))]
    if ids:
        missing = set(ids) - {c["id"] for c in cases}
        if missing:
            raise SystemExit(f"Unknown cases: {', '.join(sorted(missing))}")
        cases = [c for c in cases if c["id"] in ids]
    return cases


def score_case(case: dict, review: dict | None) -> dict:
    """Score one review. review is {"verdict", "issues"}, or None if the Critic gave no usable answer."""
    expected = case["expected"]
    issues = review["issues"] if review and review["verdict"] == "ADJUST" else []
    problems = []
    for problem in expected["problems"]:
        need = 2 if problem["type"] == "near_duplicate" else 1
        matching = [i for i in issues if len(set(i["refs"]) & set(problem["refs"])) >= need]
        problems.append({"type": problem["type"], "refs": problem["refs"], "caught": bool(matching),
                         "type_match": any(i["type"] == problem["type"] for i in matching)})
    problem_refs = {ref for problem in expected["problems"] for ref in problem["refs"]}
    debatable = set(expected["debatable"])
    false_alarms, ignored = [], []
    for issue in issues:
        refs = set(issue["refs"])
        if refs & problem_refs:
            continue
        (ignored if refs <= debatable else false_alarms).append(issue)
    return {"case": case["id"], "category": case["category"], "failed": review is None,
            "verdict": review["verdict"] if review else None, "problems": problems,
            "false_alarms": false_alarms, "ignored": ignored}


def summarize(scores: list[dict]) -> dict:
    problems = [p for s in scores for p in s["problems"]]
    caught = [p for p in problems if p["caught"]]
    by_type = defaultdict(lambda: [0, 0])
    for problem in problems:
        by_type[problem["type"]][0] += problem["caught"]
        by_type[problem["type"]][1] += 1
    controls = [s for s in scores if s["category"] == "control"]
    return {
        "reviews": len(scores), "failed_reviews": sum(s["failed"] for s in scores),
        "problems": len(problems), "caught": len(caught),
        "recall": len(caught) / len(problems) if problems else None,
        "type_match": sum(p["type_match"] for p in caught) / len(caught) if caught else None,
        "recall_by_type": {kind: hit / total for kind, (hit, total) in sorted(by_type.items())},
        "control_reviews": len(controls),
        "controls_with_false_alarm": sum(bool(s["false_alarms"]) for s in controls),
        "reviews_with_false_alarm": sum(bool(s["false_alarms"]) for s in scores),
        "false_alarm_issues": sum(len(s["false_alarms"]) for s in scores),
    }


def run_reviews(lab, cases: list[dict], repeats: int = 1, *, on_event=None, on_record=None) -> list[dict]:
    records = []
    for repeat in range(repeats):
        for case in cases:
            outcome = critique(lab, case["profile"], case["digest"], today=case["today"], on_event=on_event)
            review = outcome["data"] if not outcome["errors"] else None
            record = {"case": case["id"], "repeat": repeat, "condition": "rules+critic", "review": review,
                      "errors": outcome["errors"], "attempts": outcome["attempts"],
                      "usage": [t["usage"] for t in outcome["turns"]], "score": score_case(case, review)}
            records.append(record)
            if on_record:
                on_record(record)
    return records


def format_summary(name: str, summary: dict) -> str:
    pct = lambda value: "-" if value is None else f"{value:.0%}"
    lines = [f"{name}: caught {summary['caught']}/{summary['problems']} problems ({pct(summary['recall'])}), "
             f"type matched {pct(summary['type_match'])} of caught; false alarms on "
             f"{summary['controls_with_false_alarm']}/{summary['control_reviews']} control reviews, "
             f"{summary['false_alarm_issues']} false-alarm issues in {summary['reviews_with_false_alarm']}/"
             f"{summary['reviews']} reviews; failed reviews: {summary['failed_reviews']}"]
    lines += [f"    {kind}: {pct(value)}" for kind, value in summary["recall_by_type"].items()]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--cases", help="comma-separated case IDs (default: all)")
    parser.add_argument("--yes", action="store_true", help="skip the cost confirmation")
    args = parser.parse_args()
    cases = load_cases(args.cases.split(",") if args.cases else None)
    reviews = len(cases) * args.repeats
    print(f"{len(cases)} cases x {args.repeats} repeats = {reviews} Critic reviews, "
          f"about ${reviews * ESTIMATED_COST_PER_REVIEW:.2f} (planning estimate; the ledger records the real cost).")
    if not args.yes and input("Proceed? [y/N] ").strip().lower() not in {"y", "yes"}:
        return
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULT_DIR / f"critic-{datetime.now():%Y%m%d-%H%M%S}.jsonl"
    labkit.ensure_importable()
    from lab_support import open_lab

    def save(record):
        with out.open("a") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        score = record["score"]
        caught = sum(p["caught"] for p in score["problems"])
        print(f"  {record['case']} #{record['repeat']}: {score['verdict']} caught {caught}/{len(score['problems'])}, "
              f"false alarms {len(score['false_alarms'])}")

    with open_lab(labkit.lab_dir()) as lab:
        records = run_reviews(lab, cases, args.repeats, on_record=save)
        print(lab.ledger.summary())
    print(format_summary("Rules only", summarize([score_case(c, RULES_ONLY) for c in cases] * args.repeats)))
    print(format_summary("Rules + Critic", summarize([r["score"] for r in records])))
    print(f"Saved {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
