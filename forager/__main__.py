"""Command line entry point.

  python -m forager onboard               set up your interest profile (Idea 1; paid call)
  python -m forager onboard --baseline    free-text baseline: no follow-up questions
  python -m forager snapshot              fetch recent arXiv papers into data/snapshot/
  python -m forager digest                fetch arXiv now and write today's digest (paid call)
  python -m forager digest --snapshot P   use a fixed snapshot file instead of fetching
  python -m forager consent               choose which feedback signals Forager may track (Idea 2)
  python -m forager rate p03 5            rate an item in the latest digest (if ratings are on)
  python -m forager like p03              like an item in the latest digest (if likes are on)
  python -m forager review                review expired interests and the agent's proposals (paid call)
  python -m forager review --silent-baseline   baseline: the agent updates the profile without asking
  python -m forager profile               show the profile, what is tracked and recent decisions
"""

import argparse
import json
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from . import PROJECT_ROOT, labkit
from .checks import citation_stats
from .memory import MIN_EVIDENCE, MemoryStore
from .memory_cli import approval_prompt, ask_consent, find_item, review_expired
from .profile import PROFILE_PATH, load_profile
from .render import to_markdown
from .signals import SIGNALS, describe, load_signals, purge_signal, record_signal
from .sources import arxiv

DIGEST_DIR = PROJECT_ROOT / "runtime" / "digests"
SNAPSHOT_DIR = PROJECT_ROOT / "data" / "snapshot"


def print_turns(event):
    if event.get("type") in {"turn_started", "turn_completed"}:
        print(f"[{event['type']}] {event.get('status', '')}".rstrip())


@contextmanager
def lab_connection():
    labkit.ensure_importable()
    from lab_support import open_lab
    with open_lab(labkit.lab_dir()) as lab:
        try:
            yield lab
        finally:
            print(lab.ledger.summary())


def latest_digest(before: str) -> dict | None:
    paths = sorted(p for p in DIGEST_DIR.glob("*.json") if p.stem < before)
    return json.loads(paths[-1].read_text()) if paths else None


def cmd_onboard(args):
    from .onboarding import build_profile, clarify, profile_from_text, save_profile
    from .onboarding_cli import collect_answers, edit_loop

    if PROFILE_PATH.exists() and input("A profile already exists. Replace it? [y/N] ").strip().lower() != "y":
        return
    description = input("Describe yourself and what you follow, in one sentence:\n> ").strip()
    with lab_connection() as lab:
        if args.baseline:
            outcome = profile_from_text(lab, description, on_event=print_turns)
            profile = outcome.get("profile")
        else:
            outcome = clarify(lab, description, on_event=print_turns)
            profile = None
            if not outcome["errors"]:
                answers = collect_answers(outcome["data"], input, print)
                profile = build_profile(outcome["data"], answers, description=description)
    if profile is None:
        print("Setup failed:", outcome["errors"])
        return
    if not edit_loop(profile, input, print):
        print("Not saved.")
        return
    ask_consent(profile, MemoryStore().signals_path, input, print)
    # Keep only signals the new profile allows; anything else collected before is deleted.
    for key, allowed in profile["consent"].items():
        if not allowed:
            purge_signal(MemoryStore().signals_path, key)
    save_profile(profile)
    print(f"Saved {PROFILE_PATH.relative_to(PROJECT_ROOT)}")


def require_profile() -> bool:
    if PROFILE_PATH.exists():
        return True
    print("No profile yet. Run: python -m forager onboard")
    return False


def cmd_consent(args):
    from .onboarding import save_profile
    if not require_profile():
        return
    store = MemoryStore()
    profile = store.profile()
    ask_consent(profile, store.signals_path, input, print)
    save_profile(profile, store.profile_path)


def cmd_feedback(args):
    if not require_profile():
        return
    store = MemoryStore()
    signal, value = ("ratings", args.score) if args.command == "rate" else ("likes", 1)
    try:
        item, digest_date = find_item(DIGEST_DIR, args.item, args.date)
        event = record_signal(store.signals_path, store.profile(), signal, item, digest_date, value)
    except ValueError as exc:
        print(exc)
        return
    if event is None:
        print(f"Not recorded: {SIGNALS[signal]['label'].lower()} are off. Turn them on with: python -m forager consent")
    else:
        print("Recorded:", describe(event))


def cmd_review(args):
    from .memory import review
    if not require_profile():
        return
    store = MemoryStore()
    review_expired(store, input, print)
    if len(store.usable()) < MIN_EVIDENCE:
        print(f"Not enough consented feedback yet (need at least {MIN_EVIDENCE} signals from the last 30 days).")
        return
    with lab_connection() as lab:
        outcome = review(lab, store, approval_prompt(input, print), silent=args.silent_baseline,
                         on_event=print_turns)
    print("\n" + (outcome["answer"] or outcome.get("error") or outcome.get("reason", "")))
    for entry in outcome["proposals"]:
        print(f"  [{entry['decision']}] {entry['change']}")


def cmd_profile(args):
    from .onboarding import format_profile
    if not require_profile():
        return
    store = MemoryStore()
    print(format_profile(store.profile()))
    events = load_signals(store.signals_path)
    print(f"\nStored signals ({len(events)}):" + ("" if events else " none"))
    for event in events[-10:]:
        print("  -", describe(event))
    history = store.history()
    if history:
        print("\nRecent profile decisions:")
        for entry in history[-5:]:
            print(f"  {entry['time'][:10]} [{entry['decision']}] {entry['change']}")


def cmd_snapshot(args):
    papers = arxiv.fetch(max_results=args.max_results)
    path = SNAPSHOT_DIR / f"arxiv-{date.today().isoformat()}.json"
    arxiv.save_snapshot(papers, path)
    print(f"Saved {len(papers)} papers to {path.relative_to(PROJECT_ROOT)}")


def cmd_digest(args):
    from .digest import generate_digest

    raw = arxiv.load_snapshot(args.snapshot) if args.snapshot else arxiv.fetch(max_results=args.max_results)
    today = date.today().isoformat()
    profile = load_profile()
    with lab_connection() as lab:
        outcome = generate_digest(lab, profile, raw, previous=latest_digest(today), today=today,
                                  on_event=print_turns)

    digest = outcome["digest"]
    DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    record = {**(digest or {}), "date": today, "check_errors": outcome["errors"],
              "attempts": outcome["attempts"], "usage": [t["usage"] for t in outcome["turns"]]}
    (DIGEST_DIR / f"{today}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    if digest:
        (DIGEST_DIR / f"{today}.md").write_text(to_markdown(digest, profile) + "\n")
        print(citation_stats(digest))
    print("Checks:", "PASS" if not outcome["errors"] else outcome["errors"])
    print(f"Saved runtime/digests/{today}.json and .md (attempts: {outcome['attempts']})")


def main():
    parser = argparse.ArgumentParser(prog="forager")
    sub = parser.add_subparsers(dest="command", required=True)
    onboard = sub.add_parser("onboard", help="set up your interest profile")
    onboard.add_argument("--baseline", action="store_true", help="free-text baseline, no follow-up questions")
    onboard.set_defaults(func=cmd_onboard)
    snap = sub.add_parser("snapshot", help="save recent arXiv papers as a fixed snapshot")
    snap.add_argument("--max-results", type=int, default=30)
    snap.set_defaults(func=cmd_snapshot)
    dig = sub.add_parser("digest", help="generate today's digest (one or two paid model calls)")
    dig.add_argument("--snapshot", type=Path, help="snapshot JSON to use instead of fetching")
    dig.add_argument("--max-results", type=int, default=30)
    dig.set_defaults(func=cmd_digest)
    sub.add_parser("consent", help="choose which feedback signals Forager may track").set_defaults(func=cmd_consent)
    rate = sub.add_parser("rate", help="rate a digest item 1-5")
    rate.add_argument("item")
    rate.add_argument("score", type=int)
    rate.add_argument("--date", help="digest date (default: latest)")
    rate.set_defaults(func=cmd_feedback)
    like = sub.add_parser("like", help="like a digest item")
    like.add_argument("item")
    like.add_argument("--date", help="digest date (default: latest)")
    like.set_defaults(func=cmd_feedback)
    rev = sub.add_parser("review", help="review expired interests and proposed profile updates")
    rev.add_argument("--silent-baseline", action="store_true",
                     help="evaluation baseline: apply the agent's updates without asking")
    rev.set_defaults(func=cmd_review)
    sub.add_parser("profile", help="show the profile, tracked signals and recent decisions").set_defaults(func=cmd_profile)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
