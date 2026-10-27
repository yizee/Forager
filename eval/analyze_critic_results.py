"""Summarize a Critic case-set run (eval/run_critic_cases.py output) as Markdown.

Usage: .venv/bin/python eval/analyze_critic_results.py eval/results/critic-<timestamp>.jsonl
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "eval"))
from run_critic_cases import RULES_ONLY, load_cases, score_case, summarize  # noqa: E402


def load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def pct(value):
    return "-" if value is None else f"{value:.0%}"


def report(records: list[dict]) -> str:
    cases = {c["id"]: c for c in load_cases()}
    repeats = max(r["repeat"] for r in records) + 1
    critic = summarize([r["score"] for r in records])
    rules = summarize([score_case(cases[r["case"]], RULES_ONLY) for r in records])
    cost = sum(u.get("cost_usd") or 0 for r in records for u in r["usage"])
    tokens_in = sum(u.get("prompt_tokens") or 0 for r in records for u in r["usage"])
    tokens_out = sum(u.get("completion_tokens") or 0 for r in records for u in r["usage"])
    repairs = sum(r["attempts"] > 1 for r in records)

    lines = [f"Reviews: {len(records)} ({len({r['case'] for r in records})} cases x {repeats} repeats); "
             f"failed: {critic['failed_reviews']}; "
             f"needed a repair turn: {repairs}; cost ${cost:.4f} ({tokens_in} tokens in, {tokens_out} out).", "",
             "| Condition | Problems caught | Type matched (of caught) | Controls with a false alarm | "
             "False-alarm issues |", "| --- | --- | --- | --- | --- |"]
    for name, s in (("Rules only", rules), ("Rules + Critic", critic)):
        lines.append(f"| {name} | {s['caught']}/{s['problems']} ({pct(s['recall'])}) | {pct(s['type_match'])} | "
                     f"{s['controls_with_false_alarm']}/{s['control_reviews']} | {s['false_alarm_issues']} "
                     f"(in {s['reviews_with_false_alarm']}/{s['reviews']} reviews) |")
    lines += ["", "Recall by problem type (Rules + Critic):", ""]
    lines += [f"- {kind}: {pct(value)}" for kind, value in critic["recall_by_type"].items()]

    by_case = defaultdict(list)
    for record in records:
        by_case[record["case"]].append(record)
    lines += ["", "| Case | Verdicts | Problems caught per repeat | False alarms per repeat |", "| --- | --- | --- | --- |"]
    for case_id in sorted(by_case):
        runs = sorted(by_case[case_id], key=lambda r: r["repeat"])
        verdicts = " ".join(r["score"]["verdict"] or "failed" for r in runs)
        caught = " ".join(f"{sum(p['caught'] for p in r['score']['problems'])}/{len(r['score']['problems'])}"
                          for r in runs)
        alarms = " ".join(str(len(r["score"]["false_alarms"])) for r in runs)
        lines.append(f"| `{case_id}` | {verdicts} | {caught} | {alarms} |")
    consistent = sum(len({r["score"]["verdict"] for r in runs}) == 1 for runs in by_case.values())
    lines += ["", f"Same verdict in every repeat: {consistent}/{len(by_case)} cases.", "", "Issues the Critic raised:", ""]
    for record in sorted(records, key=lambda r: (r["case"], r["repeat"])):
        review = record["review"] or {}
        score = record["score"]
        false_alarms = [json.dumps(i, sort_keys=True) for i in score["false_alarms"]]
        ignored = [json.dumps(i, sort_keys=True) for i in score["ignored"]]
        for issue in review.get("issues", []):
            key = json.dumps(issue, sort_keys=True)
            tag = "FALSE ALARM" if key in false_alarms else "debatable" if key in ignored else "on target"
            lines.append(f"- `{record['case']}` #{record['repeat']} [{tag}] {issue['type']} {issue['refs']}: "
                         f"{issue.get('explanation', '')}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print(report(load(Path(sys.argv[1]))))
