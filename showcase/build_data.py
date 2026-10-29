"""Build showcase/data.js, the data behind the static showcase page (showcase/index.html).

Everything comes from committed result files: one recorded critic-mode digest, its profile,
two proposals from the memory scenarios, and the Stage 5 numbers (judges, calibration, the
Critic case set). Free: no model calls. Run from the repo root:
  .venv/bin/python showcase/build_data.py
"""

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "eval"))
import calibration  # noqa: E402
import judge_runs  # noqa: E402

RESULTS = ROOT / "eval" / "results"
LABELS = ROOT / "eval" / "labels"
# S1, critic mode: the Critic flagged an unsupported citation and the revision fixed it.
DIGEST_RUN = ("digest-modes-20261028-151959.jsonl", 8)
MEMORY_RUN = "memory-20261028-163542.jsonl"
PENDING = ("mislabelled", "approval")   # the same signals, one supported proposal and one not
JUDGE_DIGESTS = "judge-20261028-162830.jsonl"
JUDGE_MEMORY = "judge-20261028-163754.jsonl"
CRITIC_CASES = "critic-20261027-090328.jsonl"
CRITERION_NAMES = {
    "items.label_correct": "Item label is correct",
    "items.worth_showing": "Item is worth showing",
    "brief.supported": "Brief entry is supported",
    "brief.not_overstated": "Connection is not overstated",
    "proposals.evidence_supports_change": "Proposal evidence supports the change",
    "proposals.message_matches_change": "Proposal message matches the change",
}


def digest_part() -> dict:
    record = judge_runs.load_jsonl(RESULTS / DIGEST_RUN[0])[DIGEST_RUN[1]]
    digest, draft, profile = record["digest"], record["reviewed_draft"], record["profile"]
    labels = {i["id"]: i["label"] for i in profile["interests"]}
    items = [{**{k: item[k] for k in ("id", "type", "title", "url", "summary", "source", "published")},
              "reason": {"kind": item["reason"]["kind"], "text": item["reason"]["text"],
                         "interest": labels.get(item["reason"].get("interest_id"))}}
             for item in digest["items"]]
    critic, metrics = digest["checks"]["critic"], record["metrics"]
    revision = []
    for issue in critic["issues"]:
        for ref in issue["refs"]:
            name, index = ref.rstrip("]").split("[")
            revision.append({"ref": ref, "before": draft["brief"][name][int(index)]["text"],
                             "after": digest["brief"][name][int(index)]["text"]})
    buckets = sorted(metrics["by_bucket"].items(), key=lambda kv: (kv[0] == "Breadth", -kv[1]))
    return {
        "date": digest["date"], "mode": record["mode"], "candidates": record["candidates"],
        "points": digest["brief"]["points"], "connections": digest["brief"]["connections"],
        "changes": digest["brief"]["changes"], "items": items,
        "buckets": [{"name": "Breadth" if name == "Breadth" else name, "count": n} for name, n in buckets],
        "types": metrics["by_type"], "largest_share": metrics["largest_share"],
        "uncovered": metrics["uncovered"], "valid_citations": metrics["points_with_valid_citations"],
        "heading_problems": metrics["heading_problems"],
        "team": [{"specialist": t["specialist"], "candidates": t["candidates"], "reported": len(t["reported"]),
                  "used": len(t["used"]), "overview": t["overview"]} for t in digest["checks"]["team"]],
        "critic": {"verdict": critic["verdict"], "issues": critic["issues"], "revised": critic["revised"]},
        "revision": revision,
    }, profile


def proposals_part() -> list[dict]:
    pending = []
    for record in judge_runs.load_jsonl(RESULTS / MEMORY_RUN):
        if (record["scenario"], record["mode"]) == PENDING:
            pending += [{"today": record["today"], "change": p["change"], "message": p["message"],
                         "evidence": p["evidence"]} for p in record["proposals"]]
    return pending


def interval(stat: dict) -> dict:
    return {k: stat[k] for k in ("n", "mean", "low", "high")}


def evaluation_part() -> dict:
    digest_judgements = judge_runs.load_jsonl(RESULTS / JUDGE_DIGESTS)
    memory_judgements = judge_runs.load_jsonl(RESULTS / JUDGE_MEMORY)
    summary = judge_runs.summarize_digests(judge_runs.digest_rows(digest_judgements))
    metrics = ("label_accuracy", "worth_showing", "worth_showing_breadth", "breadth_share", "entropy")
    calibrated = {**calibration.score(LABELS / "digests", digest_judgements),
                  **calibration.score(LABELS / "memory", memory_judgements)}
    by_mode = {**calibration.by_mode(LABELS / "digests", digest_judgements),
               **calibration.by_mode(LABELS / "memory", memory_judgements)}
    memory = judge_runs.load_jsonl(RESULTS / MEMORY_RUN)
    code = {}
    for mode in judge_runs.MEMORY_MODES:
        runs = [r for r in memory if r["mode"] == mode]
        total = Counter()
        for r in runs:
            m = r["measures"]
            total.update(proposals=m["proposals"], shown=m["shown"], written=m["written"],
                         without_approval=m["written_without_approval"], blocked=m["blocked"],
                         unconsented=len(m["unconsented_in_context"]) + len(m["unconsented_cited"]))
        code[mode] = {"reviews": len(runs), **total}
    cases = judge_runs.load_jsonl(RESULTS / CRITIC_CASES)
    caught = lambda rows: [sum(p["caught"] for r in rows for p in r["score"]["problems"]),
                           sum(len(r["score"]["problems"]) for r in rows)]
    controls = [r for r in cases if r["score"]["category"] == "control"]
    return {
        "modes": {mode: {m: interval(stats[m]) for m in metrics} for mode, stats in summary["by_mode"].items()},
        "contrasts": {name: {m: interval(stats[m]) for m in metrics} for name, stats in summary["contrasts"].items()},
        "revised_runs": summary["revised_runs"],
        "calibration": [{"criterion": key, "name": CRITERION_NAMES[key], "pairs": r["n"], "agreement": r["agreement"],
                         "kappa": r["kappa"], "judge_lenient": r["author_fail_judge_pass"],
                         "judge_strict": r["author_pass_judge_fail"], "drafted": r["drafted"],
                         "changed": len(r["changed_from_draft"])} for key, r in calibrated.items()],
        "kappa_threshold": calibration.KAPPA_THRESHOLD,
        "reference": {key: by_mode[key] for key in ("brief.supported", "brief.not_overstated",
                                                    "proposals.evidence_supports_change",
                                                    "proposals.message_matches_change", "proposals.all")},
        "memory_code": code,
        "critic_cases": {"constructed": caught([r for r in cases if r["case"] != "live-01"]),
                         "live": caught([r for r in cases if r["case"] == "live-01"]),
                         "rules": [0, caught(cases)[1]],
                         "control_false_alarms": [sum(bool(r["score"]["false_alarms"]) for r in controls),
                                                  len(controls)]},
    }


def main():
    digest, profile = digest_part()
    data = {"source_files": [DIGEST_RUN[0], MEMORY_RUN, JUDGE_DIGESTS, JUDGE_MEMORY, CRITIC_CASES],
            "digest": digest,
            "profile": {k: profile[k] for k in ("interests", "consent", "exploration", "setup")},
            "proposals": proposals_part(), "evaluation": evaluation_part()}
    out = Path(__file__).resolve().parent / "data.js"
    out.write_text("// Generated by showcase/build_data.py from committed result files. Do not edit.\n"
                   f"window.FORAGER = {json.dumps(data, ensure_ascii=False, indent=1)};\n")
    print(f"Wrote {out.relative_to(ROOT)} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
