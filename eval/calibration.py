"""Calibrate the LLM judges against the author's own labels (Stage 5).

make: draw a sample of the units the judges rate (digest items, brief entries and, when
memory runs are given, proposals), spread evenly over the modes, and write a labelling
sheet: one CSV per kind, a README with the user's interests and the criteria word for word
as the judges get them, and key.json, which maps each row back to its run and mode. The
sheet shows exactly what the judge sees, with no mode. Units with the same content appear
once. Label before looking at any judge output, and open key.json only afterwards.
score: compare the labels with a judge run: agreement, Cohen's kappa and a confusion table
per criterion, plus the rows where the author and the judge disagree. The plan uses the
judge for the full set when kappa is at least 0.6.

Usage (free; no model calls):
  .venv/bin/python eval/calibration.py make eval/results/digest-modes-<stamp>.jsonl [...] --out eval/labels/<name>
  .venv/bin/python eval/calibration.py make --memory eval/results/memory-<stamp>.jsonl --out eval/labels/<name>
  .venv/bin/python eval/calibration.py score eval/labels/<name> eval/results/judge-<stamp>.jsonl [...]
"""

import argparse
import csv
import json
import random
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "eval"))
from judge_runs import (CRITERIA, DIGEST_MODES, KINDS, MEMORY_MODES, jobs_for, load_jsonl,  # noqa: E402
                        load_runs)

SEED = 619
KAPPA_THRESHOLD = 0.6
# Each sheet: its file, the judge kind it calibrates, its criteria, and the content columns.
SHEETS = {
    "items": {"file": "items.csv", "kind": "items", "criteria": KINDS["items"]["criteria"],
              "columns": ("title", "type", "filed_as", "stated_reason", "source_text")},
    "brief": {"file": "brief.csv", "kind": "brief", "criteria": KINDS["brief"]["criteria"],
              "columns": ("entry", "field", "text", "cited_sources")},
    "proposals": {"file": "proposals.csv", "kind": "proposal", "criteria": KINDS["proposal"]["criteria"],
                  "columns": ("change", "message", "evidence", "other_signals", "user_interests")},
}
LABELS = {"y": True, "yes": True, "pass": True, "true": True, "1": True,
          "n": False, "no": False, "fail": False, "false": False, "0": False}
NOT_LABELLED = {"", "n/a", "na", "-"}


# ---- units and the sample ----

def _signal(signal: dict) -> str:
    item = signal["item"]
    return (f"{signal['signal']} on {signal['date']}; filed as {item['filed_as']}: {item['title']}\n"
            f"{item['source_text']}")


def _interest(interest: dict) -> str:
    state = ", expired" if interest.get("expired") else ""
    return f"{interest['name']} ({interest['kind']}, weight {interest.get('weight')}{state})"


def units_for(runs, fallback_profile=None) -> list[dict]:
    """Every unit the judges rate, with the content the judge sees and the sheet shows."""
    units = []
    for job in jobs_for(runs, fallback_profile):
        base = {**{k: job.get(k) for k in ("file", "index", "version", "mode")}, "kind": job["kind"]}
        if job["kind"] == "items":
            for item in job["view"]["items"]:
                units.append({**base, "sheet": "items", "ref": item["ref"], "criteria": job["expected"][item["ref"]],
                              "group": [item["title"], item["filed_as"]],
                              "content": {k: item[k] for k in SHEETS["items"]["columns"]}})
        elif job["kind"] == "brief":
            sources = {s["id"]: s for s in job["view"]["sources"]}
            for entry in job["view"]["entries"]:
                cited = [sources[c] for c in entry["cites"] if c in sources]
                units.append({**base, "sheet": "brief", "ref": entry["ref"], "criteria": job["expected"][entry["ref"]],
                              "group": [entry["text"]],
                              "content": {"entry": entry["ref"].split("[")[0].rstrip("s"),
                                          "field": entry.get("field") or "", "text": entry["text"],
                                          "cited_sources": "\n\n".join(f"[{s['id']}] {s['title']}\n{s['source_text']}"
                                                                       for s in cited)}})
        else:
            view = job["view"]
            units.append({**base, "sheet": "proposals", "ref": job["ref"], "criteria": job["expected"][job["ref"]],
                          "group": [view["change"], view["message"]],
                          "content": {"change": view["change"], "message": view["message"],
                                      "evidence": "\n\n".join(_signal(s) for s in view["evidence"]),
                                      "other_signals": "\n\n".join(_signal(s) for s in view["other_signals"]),
                                      "user_interests": "; ".join(_interest(i) for i in view["user_interests"])}})
    return units


def draw(units: list[dict], n: int, modes, minority, share: float, rng: random.Random) -> list[dict]:
    """n units spread evenly over the modes; within each mode about `share` of them are
    minority units (breadth items, or connections) when there are enough. Units with the same
    content count once, as a randomly chosen one of them."""
    shuffled = units[:]
    rng.shuffle(shuffled)
    unique = {}
    for unit in shuffled:
        unique.setdefault(json.dumps(unit["group"]), unit)
    present = [m for m in modes if any(u["mode"] == m for u in unique.values())]
    chosen = []
    for position, mode in enumerate(present):
        quota = n // len(present) + (position < n % len(present))
        pool = [u for u in unique.values() if u["mode"] == mode]
        few = [u for u in pool if minority(u)][:round(quota * share)]
        rest = [u for u in pool if u not in few]
        rest.sort(key=minority)                      # majority units first, then any minority left
        chosen += few + rest[:quota - len(few)]
    rng.shuffle(chosen)
    return chosen


def sample(runs, memory_runs=(), *, items=30, brief=30, proposals=None, seed=SEED, fallback_profile=None) -> dict:
    """The units for each sheet, in sheet order."""
    rng = random.Random(seed)
    units = units_for(runs, fallback_profile)
    memory = units_for(memory_runs)
    picked = {
        "items": draw([u for u in units if u["sheet"] == "items"], items, DIGEST_MODES,
                      lambda u: "label_correct" not in u["criteria"], 1 / 3, rng),
        "brief": draw([u for u in units if u["sheet"] == "brief"], brief, DIGEST_MODES,
                      lambda u: "not_overstated" in u["criteria"], 0.3, rng)}
    if memory and proposals:
        picked["proposals"] = draw(memory, proposals, MEMORY_MODES, lambda u: False, 0, rng)
    elif memory:                                      # every distinct proposal
        picked["proposals"] = list({json.dumps(u["group"]): u for u in memory}.values())
        rng.shuffle(picked["proposals"])
    return picked


# ---- the sheet ----

def interests_of(runs) -> list[dict]:
    views = [job["view"]["user_interests"] for job in jobs_for(runs) if job["kind"] == "items"]
    if any(view != views[0] for view in views):
        raise SystemExit("The runs were made with different profiles; make one sheet per profile.")
    return views[0] if views else []


def write_sheet(out: Path, picked: dict, interests: list[dict], run_names, seed: int) -> dict:
    """Write the sheets that have rows; return them."""
    out.mkdir(parents=True, exist_ok=True)
    picked = {name: units for name, units in picked.items() if units}
    key = {"made": date.today().isoformat(), "seed": seed, "runs": sorted(run_names), "rows": {}}
    for name, units in picked.items():
        spec = SHEETS[name]
        with (out / spec["file"]).open("w", newline="", encoding="utf-8-sig") as f:   # BOM: Excel reads UTF-8
            writer = csv.writer(f)
            writer.writerow(["row", *spec["criteria"], "note", *spec["columns"]])
            for row, unit in enumerate(units, start=1):
                labels = ["" if c in unit["criteria"] else "n/a" for c in spec["criteria"]]
                writer.writerow([row, *labels, "", *(unit["content"][c] for c in spec["columns"])])
        key["rows"][name] = [{"row": row, **{k: unit[k] for k in ("file", "index", "version", "mode", "kind", "ref")}}
                             for row, unit in enumerate(units, start=1)]
    (out / "key.json").write_text(json.dumps(key, ensure_ascii=False, indent=2) + "\n")
    (out / "README.md").write_text(readme(picked, interests, run_names))
    return picked


def readme(picked: dict, interests: list[dict], run_names) -> str:
    lines = ["# Judge calibration sheet", "",
             f"Made {date.today().isoformat()} from {', '.join(sorted(run_names))}.", "",
             "Label every row before you look at any judge output, and open `key.json` only when you have "
             "finished: it says which mode each row came from. Do not change a label after seeing the judge's "
             "answer; if one was a slip, say so in the note column instead.", "",
             "Open each CSV in a spreadsheet. In every empty criterion column write `y` (passes) or `n` (fails); "
             "`n/a` marks criteria that do not apply to the row. Use `note` for anything you are unsure about. "
             "Save as CSV with the same columns.", "",
             "| Sheet | Rows |", "| --- | --- |"]
    lines += [f"| `{SHEETS[name]['file']}` | {len(units)} |" for name, units in picked.items()]
    if interests:
        lines += ["", "## The user's interests", ""]
        lines += [f"- **{i['name']}** ({i['kind']})" + (f": {', '.join(i['facets'])}" if i["facets"] else "")
                  for i in interests]
    for name in picked:
        lines += ["", f"## `{SHEETS[name]['file']}` criteria (the judge gets the same text)", ""]
        lines += [f"- `{c}`: {CRITERIA[c]}" for c in SHEETS[name]["criteria"]]
    return "\n".join(lines) + "\n"


# ---- scoring ----

def parse_label(text: str):
    text = (text or "").strip().casefold()
    if text in NOT_LABELLED:
        return None
    if text not in LABELS:
        raise ValueError(f"Unreadable label {text!r}: use y or n.")
    return LABELS[text]


def kappa(pairs) -> dict:
    """Agreement and Cohen's kappa for (author, judge) pass/fail pairs."""
    n = len(pairs)
    both_pass = sum(a and j for a, j in pairs)
    both_fail = sum(not a and not j for a, j in pairs)
    author_only, judge_only = sum(a and not j for a, j in pairs), sum(j and not a for a, j in pairs)
    result = {"n": n, "both_pass": both_pass, "both_fail": both_fail, "author_pass_judge_fail": author_only,
              "author_fail_judge_pass": judge_only, "agreement": None, "kappa": None}
    if n:
        observed = (both_pass + both_fail) / n
        author, judge = (both_pass + author_only) / n, (both_pass + judge_only) / n
        chance = author * judge + (1 - author) * (1 - judge)
        result.update(agreement=observed, kappa=None if chance == 1 else (observed - chance) / (1 - chance))
    return result


def judge_answers(records) -> dict:
    """(file, index, version, kind, ref) -> {criterion: passed} from judge results."""
    answers = {}
    for r in records:
        for ref, checks in (r["checks"] or {}).items():
            answers[(r["file"], r["index"], r["version"], r["kind"], ref)] = {c: v["passed"] for c, v in checks.items()}
    return answers


def score(sheet: Path, judge_records) -> dict:
    """Per criterion: agreement, kappa and confusion counts; plus disagreements and gaps."""
    key = json.loads((sheet / "key.json").read_text())
    answers = judge_answers(judge_records)
    results = {}
    for name, rows in key["rows"].items():
        spec = SHEETS[name]
        with (sheet / spec["file"]).open(newline="", encoding="utf-8-sig") as f:
            labelled = {int(row["row"]): row for row in csv.DictReader(f) if (row.get("row") or "").strip()}
        for criterion in spec["criteria"]:
            pairs, disagreements, unlabelled, unjudged = [], [], 0, 0
            for entry in rows:
                cell = (labelled.get(entry["row"], {}).get(criterion) or "").strip()
                if cell.casefold() in ("n/a", "na"):
                    continue                                    # the criterion does not apply to this row
                author = parse_label(cell)
                answer = answers.get((entry["file"], entry["index"], entry["version"], entry["kind"], entry["ref"]))
                judge = (answer or {}).get(criterion)
                if author is None:
                    unlabelled += 1
                elif judge is None:
                    unjudged += 1
                else:
                    pairs.append((author, judge))
                    if author != judge:
                        disagreements.append(entry["row"])
            results[f"{name}.{criterion}"] = {**kappa(pairs), "unlabelled": unlabelled, "no_judgement": unjudged,
                                             "disagreements": disagreements}
    return results


def score_report(results: dict, sheet: Path, judge_files) -> str:
    pct = lambda v: "-" if v is None else f"{v:.0%}"
    lines = [f"# Judge calibration · {sheet.name}", "",
             f"Author's labels in `{sheet}` against {', '.join(judge_files)}. Kappa of at least "
             f"{KAPPA_THRESHOLD} means the judge is used for the full set; below that, the author's labels are the "
             "primary result for that criterion.", "",
             "| Criterion | Pairs | Agreement | Kappa | Both pass | Both fail | Author pass, judge fail "
             "| Author fail, judge pass | Unlabelled | No judgement |", "|" + " --- |" * 10]
    for name, r in results.items():
        meets = r["kappa"] is not None and r["kappa"] >= KAPPA_THRESHOLD
        k = "-" if r["kappa"] is None else f"{r['kappa']:.2f}" + (" (meets 0.6)" if meets else "")
        lines.append(f"| {name} | {r['n']} | {pct(r['agreement'])} | {k} | {r['both_pass']} | {r['both_fail']} "
                     f"| {r['author_pass_judge_fail']} | {r['author_fail_judge_pass']} | {r['unlabelled']} "
                     f"| {r['no_judgement']} |")
    lines += ["", "Rows where the author and the judge disagree:", ""]
    lines += [f"- {name}: rows {', '.join(map(str, r['disagreements']))}" for name, r in results.items()
              if r["disagreements"]] or ["- none"]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    make = sub.add_parser("make", help="write a blinded labelling sheet")
    make.add_argument("runs", nargs="*", type=Path, help="digest-modes-*.jsonl files")
    make.add_argument("--memory", nargs="*", type=Path, default=[], help="memory-*.jsonl files")
    make.add_argument("--out", type=Path, required=True)
    make.add_argument("--items", type=int, default=30)
    make.add_argument("--brief", type=int, default=30)
    make.add_argument("--proposals", type=int, help="at most this many proposals (default: all)")
    make.add_argument("--seed", type=int, default=SEED)
    scorer = sub.add_parser("score", help="compare the author's labels with judge results")
    scorer.add_argument("sheet", type=Path)
    scorer.add_argument("judge", nargs="+", type=Path, help="judge-*.jsonl files")
    args = parser.parse_args()
    if args.command == "make":
        if (args.out / "key.json").exists():
            raise SystemExit(f"{args.out} already has a sheet; choose another --out so no labels are overwritten.")
        runs, memory = load_runs(args.runs), load_runs(args.memory)
        if not runs and not memory:
            parser.error("give digest runs, memory runs (--memory), or both")
        if any(not record.get("profile") for _, _, record in runs):
            raise SystemExit("Every digest run needs its saved profile (result files from before Stage 5 lack it).")
        picked = sample(runs, memory, items=args.items, brief=args.brief, proposals=args.proposals, seed=args.seed)
        picked = write_sheet(args.out, picked, interests_of(runs), {name for name, _, _ in runs + memory}, args.seed)
        print(f"Wrote {args.out}: " + ", ".join(f"{len(units)} {name}" for name, units in picked.items()))
    else:
        records = [r for path in args.judge for r in load_jsonl(path)]
        results = score(args.sheet, records)
        text = score_report(results, args.sheet, [p.name for p in args.judge])
        (args.sheet / "agreement.md").write_text(text)
        print(text)


if __name__ == "__main__":
    main()
