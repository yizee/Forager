"""Table 4 of the report from the user study: profile accuracy, edits and time, clarification versus free text.

Each participant sets up a profile twice in the Streamlit app, each time in its own runtime folder
(runtime/study/P1/clarification, runtime/study/P1/free_text; see docs/user-study.md). On saving, the app
appends the profile as built and as saved, with timings, to setup-log.jsonl in that folder. This script
counts the edits between the two and adds the ratings and decisions the researcher typed into the sheet
(eval/study/ratings.csv, columns as in eval/study/ratings-template.csv).

Time is the participant's own: answering the option questions plus editing the table, without the wait
for the model. Edits count changes to the interests only: an interest added or removed, a label, type or
weight changed, and each facet added or removed.

Run: .venv/bin/python eval/study_summary.py [--runtime runtime/study] [--sheet eval/study/ratings.csv]
"""

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
METHODS = ("clarification", "free_text")


def count_edits(draft: list[dict], saved: list[dict]) -> dict:
    """Edits that turned the interests as built into the interests as saved."""
    before = {i["id"]: i for i in draft}
    after = {i["id"]: i for i in saved}
    counts = {"added": len(after.keys() - before.keys()), "removed": len(before.keys() - after.keys()),
              "label": 0, "type": 0, "weight": 0, "facets": 0}
    for key in before.keys() & after.keys():
        old, new = before[key], after[key]
        counts["label"] += old["label"].strip() != new["label"].strip()
        counts["type"] += old["type"] != new["type"]
        counts["weight"] += abs(float(old.get("weight") or 1) - float(new.get("weight") or 1)) > 1e-9
        old_facets = {f.strip().lower() for f in old.get("facets") or []}
        new_facets = {f.strip().lower() for f in new.get("facets") or []}
        counts["facets"] += len(old_facets ^ new_facets)
    counts["total"] = sum(counts.values())
    return counts


def last_setup(folder: Path) -> dict | None:
    path = folder / "setup-log.jsonl"
    if not path.exists():
        return None
    lines = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return lines[-1] if lines else None


def clock(seconds) -> str:
    if seconds is None:
        return "?"
    seconds = round(seconds)
    return f"{seconds // 60}:{seconds % 60:02d}"


def summarize(runtime: Path, sheet: list[dict]) -> tuple[list[dict], list[str]]:
    rows, problems = [], []
    for entry in sheet:
        who = entry["participant"].strip()
        row = {"participant": who, "order": entry.get("order", "").strip(),
               "accuracy": {m: entry.get(f"accuracy_{m}", "").strip() or "?" for m in METHODS},
               "rejected": entry.get("rejected_mislabelled", "").strip() or "?", "edits": {}, "time": {}, "wait": {}}
        for method in METHODS:
            setup = last_setup(runtime / who / method)
            if setup is None:
                problems.append(f"{who}: no saved {method} setup in {runtime / who / method}")
                continue
            if setup.get("method") != method:
                problems.append(f"{who}/{method}: the log says {setup.get('method')}; check the Set up toggle")
            row["edits"][method] = count_edits(setup["draft"], setup["saved"])
            row["time"][method] = (setup.get("answer_seconds") or 0) + (setup.get("edit_seconds") or 0)
            row["wait"][method] = setup.get("wait_seconds")
        rows.append(row)
    return rows, problems


def table(rows: list[dict]) -> str:
    lines = ["| Participant | Order | Accuracy, clarification | Accuracy, free text | Edits (C / F) | Time (C / F) "
             "| Rejected the mislabelled proposal? |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    for r in rows:
        edits = " / ".join(str(r["edits"][m]["total"]) if m in r["edits"] else "?" for m in METHODS)
        times = " / ".join(clock(r["time"].get(m)) for m in METHODS)
        lines.append(f"| {r['participant']} | {r['order']} | {r['accuracy']['clarification']} | "
                     f"{r['accuracy']['free_text']} | {edits} | {times} | {r['rejected']} |")
    return "\n".join(lines)


def medians(rows: list[dict]) -> str:
    out = []
    for method in METHODS:
        scores = [float(r["accuracy"][method]) for r in rows if r["accuracy"][method] not in ("", "?")]
        edits = [r["edits"][method]["total"] for r in rows if method in r["edits"]]
        times = [r["time"][method] for r in rows if method in r["time"]]
        waits = [r["wait"][method] for r in rows if r["wait"].get(method) is not None]
        out.append(f"- {method}: accuracy median {statistics.median(scores) if scores else '?'}, "
                   f"edits median {statistics.median(edits) if edits else '?'}, "
                   f"time median {clock(statistics.median(times)) if times else '?'}, "
                   f"model wait median {statistics.median(waits) if waits else '?'} s")
    return "\n".join(out)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runtime", type=Path, default=ROOT / "runtime" / "study")
    parser.add_argument("--sheet", type=Path, default=ROOT / "eval" / "study" / "ratings.csv")
    args = parser.parse_args(argv)
    if not args.sheet.exists():
        print(f"No sheet at {args.sheet}: copy eval/study/ratings-template.csv and fill it in.")
        return 1
    with args.sheet.open(newline="") as handle:
        sheet = [row for row in csv.DictReader(handle) if (row.get("participant") or "").strip()]
    rows, problems = summarize(args.runtime, sheet)
    print(table(rows))
    print()
    print(medians(rows))
    for row in rows:
        for method, counts in row["edits"].items():
            detail = ", ".join(f"{k} {v}" for k, v in counts.items() if k != "total" and v)
            print(f"- {row['participant']} {method}: {detail or 'no edits'}")
    for problem in problems:
        print(f"! {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
