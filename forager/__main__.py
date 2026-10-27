"""Command line entry point.

  python -m forager onboard               set up your interest profile (Idea 1; paid call)
  python -m forager onboard --baseline    free-text baseline: no follow-up questions
  python -m forager snapshot              save recent arXiv papers, GitHub repos and tech news into data/snapshot/
  python -m forager digest                fetch all sources; the Manager and its specialists write today's
                                          digest, checked by the rules and the Critic (paid calls)
  python -m forager digest --mode rules   evaluation baselines: --mode rules (no Critic), --mode single (Stage 1)
  python -m forager digest --snapshot P [P ...]   use fixed snapshot files instead of fetching
  python -m forager consent               choose which feedback signals Forager may track (Idea 2)
  python -m forager rate p03 5            rate an item in the latest digest (if ratings are on)
  python -m forager like p03              like an item in the latest digest (if likes are on)
  python -m forager review                review expired interests and the agent's proposals (paid call)
  python -m forager review --silent-baseline   baseline: the agent updates the profile without asking
  python -m forager profile               show the profile, what is tracked and recent decisions
"""

import argparse
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from . import PROJECT_ROOT, labkit
from .checks import citation_stats
from .memory import MIN_EVIDENCE, MemoryStore
from .memory_cli import approval_prompt, ask_consent, find_item, review_expired
from .profile import PROFILE_PATH, load_profile
from .signals import SIGNALS, describe, load_signals, purge_signal, record_signal
from .sources import arxiv, github, load_snapshot, news, save_snapshot
from .storage import SNAPSHOT_DIR, digest_dir, latest_digest, recent_digests, save_digest

SOURCES = ("arxiv", "github", "news")


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
        item, digest_date = find_item(digest_dir(), args.item, args.date)
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


def fetch_sources(names, max_results=30) -> dict[str, list[dict]]:
    """Fetch live items from each named source (free; no model calls)."""
    fetchers = {"arxiv": lambda: arxiv.fetch(max_results=max_results), "github": github.fetch, "news": news.fetch}
    return {name: fetchers[name]() for name in names}


def cmd_snapshot(args):
    for name, items in fetch_sources(args.sources, args.max_results).items():
        path = SNAPSHOT_DIR / f"{name}-{date.today().isoformat()}.json"
        save_snapshot(items, path)
        print(f"Saved {len(items)} {name} items to {path.relative_to(PROJECT_ROOT)}")


def print_digest_event(event):
    """Turns plus the Manager's delegation: questions asked, items read and reported."""
    from .ui_runtime import event_line
    if event.get("type") in {"turn_started", "turn_completed"} or event.get("type", "").startswith("tool_"):
        print("  " + event_line(event))


def cmd_digest(args):
    from .digest import generate_digest
    from .render import team_line

    if args.snapshot:
        raw = [item for path in args.snapshot for item in load_snapshot(path)]
    else:
        raw = [item for items in fetch_sources(args.sources, args.max_results).values() for item in items]
    today = date.today().isoformat()
    profile = load_profile()
    with lab_connection() as lab:
        outcome = generate_digest(lab, profile, raw, mode=args.mode, writer=args.writer,
                                  previous=latest_digest(today), history=recent_digests(today), today=today,
                                  on_event=print_digest_event)

    digest = outcome["digest"]
    save_digest(outcome, profile, today)
    if digest:
        print(team_line(digest["checks"]) or "")
        print(citation_stats(digest))
    print("Code rules:", "PASS" if not outcome["errors"] else outcome["errors"])
    for warning in outcome["warnings"]:
        print("Not covered:", warning)
    critic = outcome["critic"]
    if critic:
        print("Critic:", critic["verdict"] or f"no usable review {critic['errors']}")
        for issue in critic["issues"]:
            print(f"  - {issue['type']} {issue['refs']}: {issue['explanation']}")
        if critic["verdict"] == "ADJUST":
            print("Revised:", "yes" if outcome["revised"] else f"no, kept the checked draft {outcome['revision_errors']}")
    print(f"Saved runtime/digests/{today}.json and .md (mode: {outcome['mode']}, writer: {outcome['writer']}, "
          f"writer turns: {outcome['attempts']})")


def main():
    parser = argparse.ArgumentParser(prog="forager")
    sub = parser.add_subparsers(dest="command", required=True)
    onboard = sub.add_parser("onboard", help="set up your interest profile")
    onboard.add_argument("--baseline", action="store_true", help="free-text baseline, no follow-up questions")
    onboard.set_defaults(func=cmd_onboard)
    snap = sub.add_parser("snapshot", help="save recent items from each source as fixed snapshots")
    snap.add_argument("--max-results", type=int, default=30, help="arXiv papers to fetch")
    snap.add_argument("--sources", nargs="+", choices=SOURCES, default=list(SOURCES))
    snap.set_defaults(func=cmd_snapshot)
    dig = sub.add_parser("digest", help="generate today's digest (paid calls: Manager and specialists, Critic, "
                                        "one revision)")
    dig.add_argument("--snapshot", type=Path, nargs="+", help="snapshot files to use instead of fetching")
    dig.add_argument("--sources", nargs="+", choices=SOURCES, default=list(SOURCES), help="sources to fetch live")
    dig.add_argument("--max-results", type=int, default=30)
    dig.add_argument("--mode", choices=("critic", "rules", "single"), default="critic",
                     help="critic: rules + Critic (default); rules: code rules only; single: Stage 1 baseline")
    dig.add_argument("--writer", choices=("team", "single"),
                     help="team: the Manager and its specialists; single: one writer (default: single in "
                          "single mode, team otherwise)")
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
