"""Feedback signals (Idea 2). A signal is stored only if the user consented to it,
used only while consent is still on, and deleted when consent is withdrawn.
"""

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

USABLE_DAYS = 30

# The order here is the order shown to the user when asking for consent.
SIGNALS = {
    "ratings": {"label": "Ratings", "collects": "the 1-5 score you give an item",
                "use": "suggest stronger or weaker interests"},
    "likes": {"label": "Likes", "collects": "items you like",
              "use": "suggest new or stronger interests"},
    "clicks": {"label": "Clicks", "collects": "which items you open",
               "use": "notice topics you keep opening"},
    "reading_time": {"label": "Reading time", "collects": "how long an opened item stays open",
                     "use": "tell skimmed items from read ones"},
}


def check_value(signal: str, value) -> int:
    if signal not in SIGNALS:
        raise ValueError(f"Unknown signal {signal!r}.")
    if signal == "ratings" and not (isinstance(value, int) and 1 <= value <= 5):
        raise ValueError("A rating must be a whole number from 1 to 5.")
    if signal == "reading_time" and not (isinstance(value, int) and 1 <= value <= 3600):
        raise ValueError("Reading time must be 1-3600 seconds.")
    return value if signal in {"ratings", "reading_time"} else 1


def record_signal(path: Path, profile: dict, signal: str, item: dict, digest_date: str,
                  value=1, *, now: str | None = None) -> dict | None:
    """Append one signal if the user consented to it; return the event, or None if not stored."""
    value = check_value(signal, value)
    if not profile.get("consent", {}).get(signal, False):
        return None
    reason = item.get("reason") or {}
    event = {"id": "s" + uuid4().hex[:6], "time": now or datetime.now().isoformat(timespec="seconds"),
             "signal": signal, "value": value, "digest": digest_date,
             "item": {"id": item["id"], "type": item.get("type"), "title": item.get("title", ""),
                      "topics": item.get("topics", []), "reason_kind": reason.get("kind"),
                      "interest_id": reason.get("interest_id")}}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as log:
        log.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


def load_signals(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def usable_signals(profile: dict, events: list[dict], today: str | None = None,
                   days: int = USABLE_DAYS) -> list[dict]:
    """Signals the agent may see: consent on now, and from the last `days` days."""
    today = today or date.today().isoformat()
    since = (date.fromisoformat(today) - timedelta(days=days)).isoformat()
    consent = profile.get("consent", {})
    return [e for e in events if consent.get(e.get("signal"), False) and since <= e["time"][:10] <= today]


def purge_signal(path: Path, signal: str) -> int:
    """Delete every stored event of one signal type; return how many were removed."""
    events = load_signals(path)
    kept = [e for e in events if e.get("signal") != signal]
    if len(kept) != len(events):
        path.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in kept))
    return len(events) - len(kept)


def set_consent(profile: dict, signals_path: Path, signal: str, allowed: bool) -> int:
    """Change consent for one signal. Withdrawing it deletes what was collected.

    Returns the number of deleted events. The caller saves the profile.
    """
    if signal not in SIGNALS:
        raise ValueError(f"Unknown signal {signal!r}.")
    profile.setdefault("consent", {})[signal] = allowed
    return 0 if allowed else purge_signal(signals_path, signal)


def describe(event: dict) -> str:
    item = event["item"]
    title = item.get("title", "")
    title = title if len(title) <= 80 else title[:77] + "..."
    day, ref = event["time"][:10], f"{item['id']} ({event['digest']} digest)"
    verb = {"ratings": f"rated {ref} {event['value']}/5", "likes": f"liked {ref}",
            "clicks": f"opened {ref}", "reading_time": f"read {ref} for {event['value']} s"}[event["signal"]]
    return f"{verb} on {day}: {title}"
