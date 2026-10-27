"""Content sources. Each returns items as dicts with type, title, url, abstract (the source
text the agents see) and published; snapshots freeze them for reproducible runs."""

import json
from pathlib import Path


def save_snapshot(items: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n")


def load_snapshot(path: Path) -> list[dict]:
    return json.loads(Path(path).read_text())
