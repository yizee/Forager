"""Where runtime data lives, and saving or loading digests.

FORAGER_RUNTIME_DIR points everything at another folder (used by the UI tests).
Paths are computed when called, so the variable can change while the app is running.
"""

import json
import os
from datetime import date, timedelta
from pathlib import Path

from . import PROJECT_ROOT
from .render import to_markdown

SNAPSHOT_DIR = PROJECT_ROOT / "data" / "snapshot"


def runtime_dir() -> Path:
    return Path(os.environ.get("FORAGER_RUNTIME_DIR") or PROJECT_ROOT / "runtime")


def profile_path() -> Path:
    return runtime_dir() / "profile.json"


def digest_dir() -> Path:
    return runtime_dir() / "digests"


def digest_days() -> list[str]:
    """Dates with a saved digest, oldest first."""
    return sorted(path.stem for path in digest_dir().glob("*.json"))


def load_digest(day: str) -> dict:
    return json.loads((digest_dir() / f"{day}.json").read_text())


def latest_digest(before: str) -> dict | None:
    days = [day for day in digest_days() if day < before]
    return load_digest(days[-1]) if days else None


def recent_digests(today: str, days: int = 7) -> list[dict]:
    """Saved digests from the coverage window before today."""
    since = (date.fromisoformat(today) - timedelta(days=days - 1)).isoformat()
    return [load_digest(day) for day in digest_days() if since <= day < today]


def save_digest(outcome: dict, profile: dict, today: str) -> dict:
    """Save a pipeline outcome as runtime/digests/<today>.json and .md; return the record."""
    digest = outcome["digest"]
    record = {**(digest or {}), "date": today, "mode": outcome["mode"], "writer": outcome.get("writer"),
              "check_errors": outcome["errors"], "revision_errors": outcome["revision_errors"],
              "attempts": outcome["attempts"], "usage": [t["usage"] for t in outcome["turns"]],
              "team_calls": outcome.get("team_calls") or [], "check_log": outcome.get("check_log") or []}
    digest_dir().mkdir(parents=True, exist_ok=True)
    (digest_dir() / f"{today}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    if digest:
        (digest_dir() / f"{today}.md").write_text(to_markdown(digest, profile) + "\n")
    return record


def latest_snapshots() -> list[Path]:
    """The newest snapshot file of each source."""
    newest = {}
    for path in sorted(SNAPSHOT_DIR.glob("*.json")):
        newest[path.stem.split("-")[0]] = path
    return list(newest.values())
