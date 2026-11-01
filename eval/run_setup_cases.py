"""Idea 1 benchmark: does clarification build a more accurate profile than free text?

Synthetic personas (eval/cases/setup/personas.json) each have one sentence, a hidden 'wants'
paragraph and a gold profile written before any run. For every persona and repeat:

- clarification: the clarifier turns the sentence into option questions (onboarding.clarify);
  a simulated user, a separate agent that knows only the persona's wants, answers by picking
  offered options, marking directions "not interested" and choosing nearby fields and short-term
  focuses; it cannot type. Code builds the profile from those picks (onboarding.build_profile).
- free text: the baseline extractor turns the same sentence into a profile (profile_from_text).

Both profiles are scored in code against the gold profile, before any editing: which gold interests
were found, which interests nobody asked for were added, short- or long-term mistakes, which gold
facets were covered, and the edits a user would need (add missing interests, remove unrequested ones,
fix types, add missing facets). Interests are matched by the gold match terms (label hits count
double; the longest matching terms win ties). Every match is listed in the report for checking.

Usage (paid; prints an estimate and asks before starting):
  .venv/bin/python eval/run_setup_cases.py --repeats 2
Results go to eval/results/setup-<timestamp>.jsonl and .md.
"""

import argparse
import json
import re
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from forager import labkit  # noqa: E402
from forager.jsonagent import ask_json, context_input, json_agent_factory, run_plain  # noqa: E402
from forager.onboarding import build_profile, clarify, profile_from_text  # noqa: E402

CASES = ROOT / "eval" / "cases" / "setup" / "personas.json"
RESULT_DIR = ROOT / "eval" / "results"
METHODS = ("clarification", "free_text")
TODAY = "2026-11-01"
ESTIMATED_COST_PER_SETUP = 0.0012

SIM_USER_INSTRUCTIONS = """You play one person setting up Forager, a daily digest of AI news, papers
and open-source tools. You are given what this person wants and the app's setup questions. Answer the
way this person would by clicking, nothing more: for each direction pick the options that fit what
they want (none if none fit); mark a direction "not interested" only if they do not want that field
at all; pick nearby fields and short-term focuses only if they want them. You cannot type anything.

Return ONLY one JSON object, no Markdown fences:
{"facets": {"<direction id>": ["<exact option text>", ...]}, "drop": ["<direction id>"],
 "adjacent": ["<exact nearby-field label>"], "short_term": ["<exact short-term label>"]}
"""


def personas() -> list[dict]:
    return json.loads(CASES.read_text())["personas"]


# ---- the simulated user ----

def check_answers(clarification: dict):
    directions = {d["id"]: {str(o) for o in d["options"]} for d in clarification["directions"]}
    adjacent = {a["label"] for a in clarification.get("adjacent", [])}
    short = {s["label"] for s in clarification.get("short_term", [])}

    def check(data: dict) -> list[str]:
        errors = []
        facets = data.get("facets", {})
        if not isinstance(facets, dict):
            return ["'facets' must be an object keyed by direction id."]
        for key, picks in facets.items():
            if key not in directions:
                errors.append(f"facets: unknown direction id {key!r}.")
            elif not isinstance(picks, list) or any(p not in directions[key] for p in picks):
                errors.append(f"facets[{key}]: use only the exact option texts offered.")
        for field, allowed in (("drop", set(directions)), ("adjacent", adjacent), ("short_term", short)):
            values = data.get(field, [])
            if not isinstance(values, list) or any(v not in allowed for v in values):
                errors.append(f"{field}: use only the exact ids or labels offered.")
        return errors
    return check


def simulate_answers(lab, persona: dict, clarification: dict) -> dict:
    context = json.dumps({"what_you_want": persona["wants"], "setup_questions": clarification}, ensure_ascii=False)
    session = lab.session(agent_factory=json_agent_factory("Simulated user", SIM_USER_INSTRUCTIONS),
                          runner=run_plain, input_builder=context_input("This person and the questions", context),
                          agent_id="simulated-user")
    return ask_json(session, "Answer the setup questions as this person.", check_answers(clarification))


# ---- scoring ----

def term_hits(text: str, terms: list[str]) -> list[str]:
    text = text.casefold()
    return [t for t in terms if (re.search(rf"\b{re.escape(t)}\b", text) if len(t) <= 3 else t in text)]


def match(interest: dict, gold: list[dict]) -> int | None:
    """Index of the gold interest this profile interest stands for, or None."""
    label, facets = interest["label"], " ".join(interest.get("facets") or [])
    best, best_score = None, 0
    for index, entry in enumerate(gold):
        score = (2 * sum(len(t) for t in term_hits(label, entry["terms"]))
                 + sum(len(t) for t in term_hits(facets, entry["terms"])))
        if score > best_score:
            best, best_score = index, score
    return best


def score(interests: list[dict], gold: list[dict]) -> dict:
    mapping = [match(i, gold) for i in interests]
    found, rows, extra, type_errors = {}, [], [], []
    for interest, index in zip(interests, mapping):
        if index is None or index in found:
            extra.append(interest["label"])
            rows.append({"label": interest["label"], "gold": None if index is None else gold[index]["label"],
                         "status": "unrequested" if index is None else "duplicate"})
            continue
        found[index] = interest
        wrong_type = interest["type"] != gold[index]["type"]
        if wrong_type:
            type_errors.append(interest["label"])
        rows.append({"label": interest["label"], "gold": gold[index]["label"],
                     "status": "wrong type" if wrong_type else "match"})
    missing = [g["label"] for n, g in enumerate(gold) if n not in found]
    covered, missed_facets = 0, []
    for index, entry in enumerate(gold):
        same = [i for i, m in zip(interests, mapping) if m == index]
        text = " ".join(f"{i['label']} {' '.join(i.get('facets') or [])}" for i in same)
        for facet in entry["facets"]:
            if same and term_hits(text, facet["terms"]):
                covered += 1
            else:
                missed_facets.append(f"{entry['label']}: {facet['name']}")
    total_facets = sum(len(g["facets"]) for g in gold)
    return {"gold": len(gold), "found": len(found), "missing": missing, "extra": extra, "type_errors": type_errors,
            "facets": total_facets, "facets_covered": covered, "missed_facets": missed_facets,
            "recall": round(len(found) / len(gold), 4),
            "facet_recall": round(covered / total_facets, 4) if total_facets else None,
            "edits": len(missing) + len(extra) + len(type_errors) + len(missed_facets), "rows": rows}


# ---- running ----

def run_case(lab, persona: dict, method: str, repeat: int = 0) -> dict:
    spent, started = dict(lab.ledger.data), time.time()
    record = {"persona": persona["id"], "kind": persona["kind"], "clarity": persona["clarity"], "method": method,
              "repeat": repeat, "sentence": persona["sentence"], "status": "ok", "errors": []}
    if method == "clarification":
        asked = clarify(lab, persona["sentence"])
        record["clarification"] = asked["data"]
        if asked["errors"]:
            record.update(status="clarifier failed", errors=asked["errors"])
        else:
            answered = simulate_answers(lab, persona, asked["data"])
            record["answers"] = answered["data"]
            if answered["errors"]:
                record.update(status="simulated user failed", errors=answered["errors"])
            else:
                answers = {**answered["data"], "custom": {}}
                record["profile"] = build_profile(asked["data"], answers, TODAY, description=persona["sentence"])
    else:
        built = profile_from_text(lab, persona["sentence"], TODAY)
        if built["errors"]:
            record.update(status="extractor failed", errors=built["errors"])
        else:
            record["profile"] = built["profile"]
    if record.get("profile"):
        record["score"] = score(record["profile"]["interests"], persona["gold"])
    ledger = lab.ledger.data
    record.update(requests=ledger["requests"] - spent["requests"], cost=round(ledger["cost"] - spent["cost"], 6),
                  seconds=round(time.time() - started, 1))
    return record


def run_cases(lab, cases, methods=METHODS, repeats: int = 1, *, on_record=None) -> list[dict]:
    records = []
    for repeat in range(repeats):
        for persona in cases:
            for method in methods:
                records.append(run_case(lab, persona, method, repeat))
                if on_record:
                    on_record(records[-1])
    return records


# ---- report ----

def mean(values):
    values = [v for v in values if v is not None]
    return round(statistics.mean(values), 3) if values else None


def summarize(records: list[dict]) -> dict:
    out = {}
    for group in ("all", "explicit", "vague"):
        for method in METHODS:
            chosen = [r for r in records if r["method"] == method and (group == "all" or r["clarity"] == group)]
            scored = [r["score"] for r in chosen if r.get("score")]
            out[f"{group}/{method}"] = {
                "runs": len(chosen), "failed": len(chosen) - len(scored),
                "recall": mean([s["recall"] for s in scored]),
                "facet_recall": mean([s["facet_recall"] for s in scored]),
                "extra": mean([len(s["extra"]) for s in scored]),
                "type_errors": sum(len(s["type_errors"]) for s in scored),
                "edits_mean": mean([s["edits"] for s in scored]),
                "edits_median": statistics.median([s["edits"] for s in scored]) if scored else None}
    return out


def paired(records: list[dict]) -> list[dict]:
    """Per persona and repeat: clarification minus free text."""
    by = {(r["persona"], r["repeat"], r["method"]): r for r in records if r.get("score")}
    rows = []
    for (persona, repeat, method), record in sorted(by.items()):
        other = by.get((persona, repeat, "free_text"))
        if method == "clarification" and other:
            a, b = record["score"], other["score"]
            rows.append({"persona": persona, "repeat": repeat, "clarity": record["clarity"],
                         "edits": (a["edits"], b["edits"]), "recall": (a["recall"], b["recall"]),
                         "facet_recall": (a["facet_recall"], b["facet_recall"]),
                         "extra": (len(a["extra"]), len(b["extra"])),
                         "type_errors": (len(a["type_errors"]), len(b["type_errors"]))})
    return rows


def report(records: list[dict], stamp: str) -> str:
    summary = summarize(records)
    cost = sum(r["cost"] for r in records)
    lines = [f"# Idea 1 benchmark: clarification vs free text ({stamp})", "",
             f"{len(records)} setups, {sum(r['requests'] for r in records)} requests, ${cost:.4f}. "
             "Scores are for the profile as built, before any editing.", "",
             "| Group | Method | Runs | Failed | Interests found | Facets covered | Unrequested per profile "
             "| Type errors | Edits to gold (mean / median) |",
             "| --- | --- | --: | --: | --: | --: | --: | --: | --- |"]
    for key, s in summary.items():
        group, method = key.split("/")
        lines.append(f"| {group} | {method} | {s['runs']} | {s['failed']} | {s['recall']} | {s['facet_recall']} | "
                     f"{s['extra']} | {s['type_errors']} | {s['edits_mean']} / {s['edits_median']} |")
    lines += ["", "## Paired (clarification, free text)", "",
              "| Persona | Repeat | Clarity | Edits | Interests found | Facets covered | Unrequested | Type errors |",
              "| --- | --: | --- | --- | --- | --- | --- | --- |"]
    for p in paired(records):
        lines.append(f"| {p['persona']} | {p['repeat'] + 1} | {p['clarity']} | {p['edits']} | {p['recall']} | "
                     f"{p['facet_recall']} | {p['extra']} | {p['type_errors']} |")
    lines += ["", "## Every profile and its matches (check these)", ""]
    for r in records:
        head = f"### {r['persona']} / {r['method']} #{r['repeat'] + 1}: {r['status']}"
        lines += [head, ""]
        if r.get("errors"):
            lines.append("Errors: " + "; ".join(r["errors"]))
        if r.get("answers"):
            lines.append("Simulated user's picks: `" + json.dumps(r["answers"], ensure_ascii=False) + "`")
        for interest in (r.get("profile") or {}).get("interests", []):
            row = next(x for x in r["score"]["rows"] if x["label"] == interest["label"])
            lines.append(f"- {interest['label']} [{', '.join(interest.get('facets') or []) or 'whole field'}] "
                         f"{interest['type']} {interest['weight']} -> {row['gold'] or '—'} ({row['status']})")
        if r.get("score"):
            s = r["score"]
            lines.append(f"- Missing: {', '.join(s['missing']) or 'none'}; facets missed: "
                         f"{', '.join(s['missed_facets']) or 'none'}")
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--personas", nargs="+", choices=[p["id"] for p in personas()])
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--yes", action="store_true", help="skip the cost confirmation")
    args = parser.parse_args()
    cases = [p for p in personas() if not args.personas or p["id"] in args.personas]
    setups = len(cases) * len(METHODS) * args.repeats
    print(f"{len(cases)} personas x {len(METHODS)} methods x {args.repeats} repeats = {setups} setups, about "
          f"${setups * ESTIMATED_COST_PER_SETUP:.3f} (planning estimate; the ledger records the real cost).")
    if not args.yes and input("Proceed? [y/N] ").strip().lower() not in {"y", "yes"}:
        return
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULT_DIR / f"setup-{stamp}.jsonl"

    def save(record):
        with path.open("a") as out:
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
        s = record.get("score") or {}
        print(f"  {record['persona']} / {record['method']} #{record['repeat'] + 1}: {record['status']}; "
              f"found {s.get('found')}/{s.get('gold')}, edits {s.get('edits')}; ${record['cost']:.4f}")

    labkit.ensure_importable()
    from lab_support import open_lab
    with open_lab(labkit.lab_dir()) as lab:
        records = run_cases(lab, cases, METHODS, args.repeats, on_record=save)
        print(lab.ledger.summary())
    (RESULT_DIR / f"setup-{stamp}.md").write_text(report(records, stamp) + "\n")
    print(f"Saved {path.relative_to(ROOT)} and .md")


if __name__ == "__main__":
    main()
