"""What the Streamlit app needs that is not Streamlit: the lab connection, the background
memory review that waits for the user's approvals, and small data helpers.

Approvals stay SDK-enforced: memory.review runs in a worker thread, the SDK pauses at each
needs_approval call, and decide() hands the proposal to the page and blocks until the
user answers. Each proposal carries a token, so a stale or repeated click cannot answer
the next proposal.
"""

import json
import queue
import threading
from collections import Counter
from contextlib import contextmanager
from datetime import date, timedelta

from . import labkit
from .memory import review
from .profile import is_expired
from .team import SPECIALISTS

ASKS = {spec["tool"]: spec["name"] for spec in SPECIALISTS.values()}         # the Manager's as_tool() calls
READS = {spec["reader"]: spec["plural"] for spec in SPECIALISTS.values()}    # each specialist's own tool


@contextmanager
def open_connection():
    """The paid lab connection. Tests replace this with lab_support.testing.offline_lab."""
    labkit.ensure_importable()
    from lab_support import open_lab
    with open_lab(labkit.lab_dir()) as lab:
        yield lab


class ReviewWorker:
    """Runs one memory review in a thread; the page answers its approval requests."""

    def __init__(self, store, *, timeout: float = 600):
        self.store, self.timeout = store, timeout
        self.pending = None                      # {"token": n, "view": {...}} while the SDK waits
        self.result = self.error = self.usage = None
        self._answers = queue.Queue()
        self._tokens = 0
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()
        return self

    @property
    def running(self) -> bool:
        return self._thread.is_alive()

    def answer(self, token: int, approve: bool) -> bool:
        """Answer the proposal with this token; returns False if it is no longer pending."""
        with self._lock:
            if not self.pending or self.pending["token"] != token:
                return False
            self.pending = None
        self._answers.put((token, approve))
        return True

    def _decide(self, view: dict) -> bool:
        with self._lock:
            self._tokens += 1
            token = self._tokens
            self.pending = {"token": token, "view": view}
        try:
            while True:
                answered, approve = self._answers.get(timeout=self.timeout)
                if answered == token:
                    return approve
        except queue.Empty:                      # no answer in time: reject, nothing is written
            with self._lock:
                self.pending = None
            return False

    def _run(self):
        try:
            with open_connection() as lab:
                self.result = review(lab, self.store, self._decide)
                self.usage = lab.ledger.summary()
        except Exception as exc:                 # shown on the page; the profile is unchanged
            self.error = str(exc)


def _question(arguments) -> str:
    """The Manager's question from an as_tool() call's arguments ('{"input": "..."}')."""
    try:
        question = json.loads(arguments).get("input", "")
    except (TypeError, ValueError, AttributeError):
        question = ""
    question = " ".join(str(question).split())
    return question if len(question) <= 160 else question[:157] + "..."


def event_line(event: dict) -> str:
    """One readable line per lab event, for the progress log."""
    kind = event.get("type", "")
    agent = event.get("agent") or "agent"
    tool = event.get("tool", "")
    result = event.get("result")
    if kind == "turn_started":
        return f"{agent}: working..."
    if kind == "turn_completed":
        cost = (event.get("usage") or {}).get("cost_usd")
        return f"{agent}: {event.get('status')}" + (f" (${cost:.4f})" if cost else "")
    if tool in ASKS and kind == "tool_started":
        return f"{agent} asks the {ASKS[tool]}: {_question(event.get('arguments'))}"
    if tool in ASKS and kind == "tool_completed":
        items = result.get("items") if isinstance(result, dict) else None
        return f"{ASKS[tool]} reported {len(items or [])} items."
    if tool in READS and kind == "tool_started":
        return f"{agent}: reading today's {READS[tool]}..."
    if tool in READS and kind == "tool_completed":
        return f"{agent}: read {len(result) if isinstance(result, list) else 'the'} {READS[tool]}."
    if kind.startswith("tool_"):
        return f"{agent}: {kind.replace('_', ' ')} {tool}".rstrip()
    return f"{agent}: {kind}"


def topic_distribution(digests: list[dict], profile: dict) -> dict[str, int]:
    """Items per interest (by label) and breadth across the given digests."""
    labels = {i["id"]: i["label"] for i in profile.get("interests", [])}
    counts = Counter()
    for digest in digests:
        for item in digest.get("items") or []:
            reason = item.get("reason") or {}
            if reason.get("kind") == "interest":
                counts[labels.get(reason.get("interest_id"), reason.get("interest_id") or "other")] += 1
            else:
                counts["Breadth"] += 1
    return dict(counts.most_common())


def week_of(digest_days: list[str], today: str) -> list[str]:
    since = (date.fromisoformat(today) - timedelta(days=6)).isoformat()
    return [day for day in digest_days if since <= day <= today]


def interest_rows(profile: dict, today: str | None = None) -> list[dict]:
    """The profile's interests as editable table rows."""
    return [{"id": i["id"], "label": i["label"], "facets": ", ".join(i.get("facets") or []),
             "type": i["type"], "weight": i["weight"], "expires": i.get("expires") or "",
             "source": i["source"], "status": "expired" if is_expired(i, today) else "active"}
            for i in profile.get("interests", [])]


def rows_to_interests(rows: list[dict], original: list[dict], today: str) -> list[dict]:
    """Edited table rows back to interests; existing ones keep their other fields."""
    by_id = {i["id"]: i for i in original}
    used = [int(i["id"][1:]) for i in original if i["id"][1:].isdigit()]
    next_id = max(used or [0]) + 1
    interests = []
    for row in rows:
        label = str(row.get("label") or "").strip()
        if not label:
            continue
        old = by_id.get(row.get("id"))
        if old is None:
            old = {"id": f"i{next_id}", "source": "stated", "origin": "manual"}
            next_id += 1
        kind = row.get("type") if row.get("type") in ("long_term", "short_term") else "long_term"
        expires = str(row.get("expires") or "").strip() or None
        if kind == "short_term" and not expires:
            expires = (date.fromisoformat(today) + timedelta(days=14)).isoformat()
        interests.append({**old, "label": label, "type": kind, "expires": expires if kind == "short_term" else None,
                          "facets": [f.strip() for f in str(row.get("facets") or "").split(",") if f.strip()],
                          "weight": float(row.get("weight") or 1.0)})
    return interests


def budget(lab_dir=None) -> dict | None:
    """Spending recorded by the lab's local ledger, without opening a connection."""
    try:
        path = (lab_dir or labkit.lab_dir()) / ".lab-state" / "usage.json"
        data = json.loads(path.read_text())
    except (OSError, ValueError, RuntimeError):
        return None
    return {"cost": data.get("cost", 0.0), "requests": data.get("requests", 0)}
