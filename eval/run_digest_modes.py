"""Run the three digest pipelines on the same snapshots and profile, and keep every result.

The modes are the Idea 3 conditions: single (one writer, structure checks only), rules
(the Manager and its specialists, plus the code rules) and critic (plus the Critic and
one revision). Every run uses fresh sessions on one lab connection (one ledger); the
previous digest and the 7-day history come from runtime/ and are the same for all runs.
Code measures what it can without a model: source and topic mix, breadth share, citations,
the code rules applied to every mode's digest (single mode does not enforce them, but
they are measured the same way), the Critic's verdict, cost and time.

Usage (paid; prints an estimate and asks before starting):
  .venv/bin/python eval/run_digest_modes.py
  .venv/bin/python eval/run_digest_modes.py --modes rules critic --repeats 2
  .venv/bin/python eval/run_digest_modes.py --save critic     # also make that run today's digest
Results go to eval/results/digest-modes-<timestamp>.jsonl and .md.
"""

import argparse
import json
import sys
import time
from collections import Counter
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from forager import labkit, storage  # noqa: E402
from forager.checks import check_rules, citation_stats, topic_bucket  # noqa: E402
from forager.digest import MODES, generate_digest, prepare_candidates  # noqa: E402
from forager.profile import load_profile  # noqa: E402
from forager.render import to_markdown  # noqa: E402
from forager.sources import load_snapshot  # noqa: E402

RESULT_DIR = ROOT / "eval" / "results"
# Planning figures per run, from the Stage 1 writer ($0.0016) and the Critic case set
# ($0.0006 a review), with the team's extra requests and a repair turn allowed for.
ESTIMATED_COST = {"single": 0.003, "rules": 0.008, "critic": 0.012}


def metrics(digest: dict | None, profile: dict, candidates=(), history=(), today: str | None = None) -> dict:
    """What code can measure about one digest; the code rules run whatever the mode."""
    if not digest:
        return {}
    rules = check_rules(digest, profile, {c["id"] for c in candidates}, available_types={c["type"] for c in candidates},
                        history=history, today=today)
    items = digest.get("items") or []
    labels = {i["id"]: i["label"] for i in profile.get("interests", [])}
    buckets = Counter(labels.get(topic_bucket(i), topic_bucket(i)) if topic_bucket(i) != "breadth" else "Breadth"
                      for i in items)
    largest = buckets.most_common(1)[0] if buckets else ("", 0)
    checks = digest.get("checks") or {}
    critic = checks.get("critic") or {}
    return {"items": len(items), "by_type": dict(Counter(i.get("type") for i in items)),
            "by_bucket": dict(buckets.most_common()), "largest_bucket": largest[0],
            "largest_share": round(largest[1] / len(items), 2) if items else 0,
            "breadth_share": round(buckets.get("Breadth", 0) / len(items), 2) if items else 0,
            "rule_problems": len(rules["structure_and_citations"] + rules["topic_share"] + rules["source_mix"]),
            "uncovered": len(rules["coverage"]), **citation_stats(digest),
            "critic_verdict": critic.get("verdict"), "critic_issues": len(critic.get("issues") or []),
            "revised": bool(critic.get("revised"))}


def run_modes(lab, profile: dict, raw: list[dict], modes, repeats: int = 1, *, today: str, previous=None,
              history=(), on_event=None, on_record=None) -> list[dict]:
    """One record per (repeat, mode), in the order run."""
    records = []
    for repeat in range(repeats):
        for mode in modes:
            before, started = dict(lab.ledger.data), time.time()
            outcome = generate_digest(lab, profile, raw, mode=mode, previous=previous, history=history,
                                      today=today, on_event=on_event)
            after = lab.ledger.data
            record = {"repeat": repeat, "mode": mode, "writer": outcome["writer"], "today": today,
                      "candidates": dict(Counter(c["type"] for c in outcome["candidates"])),
                      "errors": outcome["errors"], "warnings": outcome["warnings"],
                      "revision_errors": outcome["revision_errors"], "attempts": outcome["attempts"],
                      "requests": after["requests"] - before["requests"],
                      "cost": round(after["cost"] - before["cost"], 6),
                      "cost_known": not (after["unknown_cost"] or after["pending"]),
                      "seconds": round(time.time() - started, 1),
                      "metrics": metrics(outcome["digest"], profile, outcome["candidates"], history, today),
                      "digest": outcome["digest"], "team_calls": outcome["team_calls"],
                      "check_log": outcome["check_log"], "outcome": outcome}
            records.append(record)
            if on_record:
                on_record(record)
    return records


def summary_table(records: list[dict]) -> str:
    rows = ["| Run | Mode | Writer | Hard rules | Items | Types | Largest topic | Breadth | Uncovered | Critic | "
            "Requests | Cost (USD) | Seconds |", "|" + " --- |" * 13]
    for r in records:
        m = r["metrics"]
        if not m:
            rows.append(f"| {r['repeat'] + 1} | {r['mode']} | {r['writer']} | no digest: {'; '.join(r['errors'])[:80]} "
                        f"| | | | | | | {r['requests']} | {r['cost']:.4f} | {r['seconds']} |")
            continue
        critic = "" if r["mode"] != "critic" else (
            f"{m['critic_verdict'] or 'unusable'}" + (f", {m['critic_issues']} issue(s)" if m["critic_issues"] else "")
            + (", revised" if m["revised"] else ""))
        types = ", ".join(f"{k} {v}" for k, v in sorted(m["by_type"].items()))
        rules = ("PASS" if not m["rule_problems"] else f"{m['rule_problems']} broken") + (" (errors)" if r["errors"] else "")
        rows.append(f"| {r['repeat'] + 1} | {r['mode']} | {r['writer']} | {rules} "
                    f"| {m['items']} | {types} | {m['largest_bucket']} {m['largest_share']:.0%} "
                    f"| {m['breadth_share']:.0%} | {m['uncovered']} | {critic} | {r['requests']} | {r['cost']:.4f} "
                    f"| {r['seconds']} |")
    return "\n".join(rows)


def report(records: list[dict], profile: dict, snapshots, stamp: str) -> str:
    lines = [f"# Digest modes · {stamp}", "", "Snapshots: " + ", ".join(Path(p).name for p in snapshots), "",
             summary_table(records), ""]
    for r in records:
        lines += [f"## Run {r['repeat'] + 1} · {r['mode']} ({r['writer']} writer)", ""]
        if r["errors"]:
            lines += ["Errors: " + "; ".join(r["errors"]), ""]
        for entry in r.get("check_log") or []:
            if entry["problems"]:
                lines.append(f"- Repair after {entry['stage']} attempt {entry['attempt']}: " + "; ".join(entry["problems"]))
        for call in r["team_calls"]:
            lines += [f"- Manager asked the {call['kind']} specialist: {call['question']}",
                      f"  - reported: {', '.join(n['id'] for n in call['notes']) or 'nothing'}"
                      + (f"; problems: {'; '.join(call['problems'])}" if call["problems"] else "")]
        if r["team_calls"]:
            lines.append("")
        if r["digest"]:
            body = to_markdown(r["digest"], profile).replace("\n# ", "\n### ").replace("\n## ", "\n#### ")
            lines += [body.split("\n", 1)[1] if body.startswith("# ") else body, ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--snapshot", type=Path, nargs="+", help="snapshot files (default: newest of each source)")
    parser.add_argument("--modes", nargs="+", choices=MODES, default=["single", "rules", "critic"])
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--today", default=date.today().isoformat())
    parser.add_argument("--save", choices=MODES, help="also save this mode's last run as today's digest in runtime/")
    parser.add_argument("--yes", action="store_true", help="skip the cost confirmation")
    args = parser.parse_args()

    snapshots = args.snapshot or storage.latest_snapshots()
    raw = [item for path in snapshots for item in load_snapshot(path)]
    profile = load_profile(storage.profile_path())
    candidates = Counter(c["type"] for c in prepare_candidates(raw))
    estimate = args.repeats * sum(ESTIMATED_COST[m] for m in args.modes)
    print("Snapshots:", ", ".join(Path(p).name for p in snapshots), "| candidates:", dict(candidates))
    print(f"{args.repeats} x {', '.join(args.modes)}: about ${estimate:.3f} "
          "(planning estimate; the ledger records the real cost).")
    if not args.yes and input("Proceed? [y/N] ").strip().lower() not in {"y", "yes"}:
        return

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULT_DIR / f"digest-modes-{stamp}.jsonl"

    def save(record):
        kept = {k: v for k, v in record.items() if k != "outcome"}
        with path.open("a") as out:
            out.write(json.dumps(kept, ensure_ascii=False) + "\n")
        m = record["metrics"]
        print(f"  {record['mode']}: {'PASS' if not record['errors'] else record['errors']}; "
              f"{m.get('items', 0)} items {m.get('by_type', {})}; ${record['cost']:.4f}; {record['seconds']}s")

    def show(event):
        from forager.ui_runtime import event_line
        if event.get("type") in {"turn_started", "turn_completed"} or event.get("type", "").startswith("tool_"):
            print("    " + event_line(event))

    labkit.ensure_importable()
    from lab_support import open_lab
    with open_lab(labkit.lab_dir()) as lab:
        records = run_modes(lab, profile, raw, args.modes, args.repeats, today=args.today,
                            previous=storage.latest_digest(args.today), history=storage.recent_digests(args.today),
                            on_event=show, on_record=save)
        print(lab.ledger.summary())
    (RESULT_DIR / f"digest-modes-{stamp}.md").write_text(report(records, profile, snapshots, stamp) + "\n")
    print("\n" + summary_table(records))
    print(f"\nSaved {path.relative_to(ROOT)} and .md")
    if args.save:
        chosen = [r for r in records if r["mode"] == args.save and r["digest"]]
        if chosen:
            storage.save_digest(chosen[-1]["outcome"], profile, args.today)
            print(f"Saved the {args.save} run as runtime/digests/{args.today}.json")


if __name__ == "__main__":
    main()
