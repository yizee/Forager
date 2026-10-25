"""Terminal front end for Idea 2: consent, feedback, approvals and expired interests.

ask(prompt) -> str and show(text) are injected so the flows can be tested offline.
"""

import json
import re
from pathlib import Path

from .memory import resolve_expired
from .profile import expired_interests
from .signals import SIGNALS, set_consent


def ask_consent(profile: dict, signals_path: Path, ask, show) -> None:
    """Show every signal with what it collects; the user toggles each by number."""
    consent = profile.setdefault("consent", {})
    show("\nForager can learn from these signals. Nothing is tracked unless you turn it on.")
    show("Turning a signal off later deletes what was collected for it.")
    keys = list(SIGNALS)
    for number, key in enumerate(keys, start=1):
        info = SIGNALS[key]
        state = "ON" if consent.get(key) else "off"
        show(f"  {number}. [{state}] {info['label']}: collects {info['collects']}; used to {info['use']}.")
    reply = ask("Toggle which? (numbers, Enter = no change) > ")
    for token in dict.fromkeys(re.split(r"[\s,]+", reply.strip())):
        if not (token.isdigit() and 1 <= int(token) <= len(keys)):
            continue
        key = keys[int(token) - 1]
        allowed = not consent.get(key, False)
        deleted = set_consent(profile, signals_path, key, allowed)
        note = f" Deleted {deleted} stored {SIGNALS[key]['label'].lower()} events." if deleted else ""
        show(f"{SIGNALS[key]['label']}: {'on' if allowed else 'off'}.{note}")


def approval_prompt(ask, show):
    """decide(view) for memory.review: show the change and code-resolved evidence, ask y/N."""
    def decide(view: dict) -> bool:
        show("\nForager suggests a profile change:")
        show(f'  "{view["message"]}"')
        show(f"  Change: {view['change']}")
        show("  Evidence (from signals you allowed):")
        for line in view["evidence"]:
            show(f"    - {line}")
        return ask("Approve? [y/N] ").strip().lower() in {"y", "yes"}
    return decide


def review_expired(store, ask, show) -> list[str]:
    """Ask about each expired short-term interest. Enter leaves it inactive for now."""
    done = []
    for interest in expired_interests(store.profile(), store.today):
        show(f'\n"{interest["label"]}" was a short-term interest until {interest["expires"]}; '
             "it is no longer used in your digest.")
        reply = ask("[k]eep 14 more days, make [l]ong-term, [r]emove, Enter = decide later > ").strip().lower()
        choice = {"k": "keep", "l": "long", "r": "remove"}.get(reply[:1])
        if choice:
            done.append(resolve_expired(store, interest["id"], choice))
            show(done[-1] + ".")
    return done


def find_item(digest_dir: Path, item_id: str, digest_date: str | None = None) -> tuple[dict, str]:
    """Look up an item in a saved digest (the latest one by default)."""
    if digest_date:
        path = digest_dir / f"{digest_date}.json"
    else:
        paths = sorted(digest_dir.glob("*.json"))
        if not paths:
            raise ValueError("No saved digest yet. Run: python -m forager digest")
        path = paths[-1]
    if not path.exists():
        raise ValueError(f"No digest for {digest_date}.")
    digest = json.loads(path.read_text())
    for item in digest.get("items", []):
        if item.get("id") == item_id:
            return item, path.stem
    raise ValueError(f"{item_id} is not in the {path.stem} digest.")
