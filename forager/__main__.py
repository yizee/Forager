"""Command line entry point.

  python -m forager onboard               set up your interest profile (Idea 1; paid call)
  python -m forager onboard --baseline    free-text baseline: no follow-up questions
  python -m forager snapshot              fetch recent arXiv papers into data/snapshot/
  python -m forager digest                fetch arXiv now and write today's digest (paid call)
  python -m forager digest --snapshot P   use a fixed snapshot file instead of fetching
"""

import argparse
import json
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from . import PROJECT_ROOT, labkit
from .checks import citation_stats
from .profile import PROFILE_PATH, load_profile
from .render import to_markdown
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
    if edit_loop(profile, input, print):
        save_profile(profile)
        print(f"Saved {PROFILE_PATH.relative_to(PROJECT_ROOT)}")
    else:
        print("Not saved.")


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
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
