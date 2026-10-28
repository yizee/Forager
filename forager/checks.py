"""Deterministic digest checks, run in code on every digest (never left to the model).

Structure and citation IDs (Stage 1), plus the Stage 4 rules: topic share, 7-day
coverage of long-term interests and source-type mix. Everything these rules cannot
judge (relevance, duplicates, whether a citation supports a point) is the Critic's job.

check_headings ties the brief's interest headings to the items' labels. The team writer
is held to it (Team.check); it is not one of check_rules, whose four rules every Critic
case is built to pass.
"""

from collections import Counter
from datetime import date, timedelta

from .profile import active_interests

MIN_POINTS, MAX_POINTS = 5, 8
REASON_KINDS = {"interest", "breadth"}
MAX_TOPIC_SHARE = 0.40
MIN_ITEMS_FOR_SHARE = 5
COVERAGE_DAYS = 7


def check_digest(digest: dict, candidate_ids: set[str]) -> list[str]:
    """Return a list of problems; an empty list means the digest passes."""
    errors = []
    items = digest.get("items")
    brief = digest.get("brief")
    if not isinstance(items, list) or not items:
        return ["'items' must be a non-empty list."]
    if not isinstance(brief, dict):
        return ["'brief' must be an object with points, connections and changes."]

    item_ids = []
    for index, item in enumerate(items):
        item_id = item.get("id") if isinstance(item, dict) else None
        if item_id not in candidate_ids:
            errors.append(f"items[{index}] has id {item_id!r}, which is not a candidate ID.")
            continue
        if item_id in item_ids:
            errors.append(f"Item {item_id} appears more than once.")
        item_ids.append(item_id)
        if not str(item.get("summary", "")).strip():
            errors.append(f"Item {item_id} has no summary.")
        reason = item.get("reason")
        if not isinstance(reason, dict) or reason.get("kind") not in REASON_KINDS or not str(reason.get("text", "")).strip():
            errors.append(f"Item {item_id} needs reason.kind ('interest' or 'breadth') and reason.text.")
    included = set(item_ids)

    points = brief.get("points")
    if not isinstance(points, list) or not MIN_POINTS <= len(points) <= MAX_POINTS:
        count = len(points) if isinstance(points, list) else 0
        errors.append(f"The brief needs {MIN_POINTS}-{MAX_POINTS} points; it has {count}.")
        points = points if isinstance(points, list) else []
    sections = [("points", points), ("connections", brief.get("connections") or []),
                ("changes", brief.get("changes") or [])]
    for section, entries in sections:
        for index, entry in enumerate(entries):
            label = f"brief.{section}[{index}]"
            if not isinstance(entry, dict) or not str(entry.get("text", "")).strip():
                errors.append(f"{label} needs non-empty text.")
                continue
            if section == "points" and not str(entry.get("field", "")).strip():
                errors.append(f"{label} needs a field.")
            cites = entry.get("cites")
            if section != "changes" and (not isinstance(cites, list) or not cites):
                errors.append(f"{label} must cite at least one item ID.")
                continue
            for cited in cites or []:
                if cited not in included:
                    where = "a candidate that is not in items" if cited in candidate_ids else "an unknown ID"
                    errors.append(f"{label} cites {cited!r}, {where}.")
    return errors


def citation_stats(digest: dict) -> dict:
    """Share of brief points whose citations all resolve to included items."""
    included = {item.get("id") for item in digest.get("items", []) if isinstance(item, dict)}
    points = (digest.get("brief") or {}).get("points") or []
    valid = sum(1 for p in points if isinstance(p, dict) and p.get("cites")
                and all(c in included for c in p["cites"]))
    return {"points": len(points), "points_with_valid_citations": valid}


def topic_bucket(item: dict) -> str:
    """Interest items count toward their interest; all breadth items share one bucket."""
    reason = item.get("reason") or {}
    if reason.get("kind") == "interest" and reason.get("interest_id"):
        return reason["interest_id"]
    return "breadth"


def check_topic_share(digest: dict, limit: float = MAX_TOPIC_SHARE) -> list[str]:
    items = digest.get("items") or []
    if len(items) < MIN_ITEMS_FOR_SHARE:
        return []
    bucket, count = Counter(topic_bucket(i) for i in items).most_common(1)[0]
    if count / len(items) > limit:
        return [f"'{bucket}' has {count} of {len(items)} items ({count / len(items):.0%}); the limit is {limit:.0%}."]
    return []


def balance_note(digest: dict, labels: dict, limit: float = MAX_TOPIC_SHARE) -> str | None:
    """For a repair turn: each topic's item count and the most any topic may have, so that
    fixing one problem does not break the topic-share rule. None when the rule does not apply."""
    items = [i for i in digest.get("items") or [] if isinstance(i, dict)]
    if len(items) < MIN_ITEMS_FOR_SHARE:
        return None
    counts = Counter(topic_bucket(i) if isinstance(i.get("reason"), dict) else "breadth" for i in items)
    cap = int(limit * len(items) + 1e-9)
    shown = ", ".join(f"{labels.get(bucket, bucket)} {n}" for bucket, n in counts.most_common())
    return (f"Balance now: {len(items)} items, so no interest, and not the breadth items together, may have "
            f"more than {cap} ({limit:.0%}). Counts: {shown}. Keep every count within that while you fix "
            "the problems above.")


def uncovered_interests(digest: dict, profile: dict, history=(), today: str | None = None,
                        days: int = COVERAGE_DAYS) -> list[dict]:
    """Active long-term interests with no item in the last `days` days, this digest included."""
    today = today or digest.get("date") or date.today().isoformat()
    since = (date.fromisoformat(today) - timedelta(days=days - 1)).isoformat()
    covered = {topic_bucket(i) for i in digest.get("items") or []}
    for past in history:
        if since <= past.get("date", "") <= today:
            covered |= {topic_bucket(i) for i in past.get("items") or []}
    return [i for i in active_interests(profile, today) if i["type"] == "long_term" and i["id"] not in covered]


def coverage_message(interest: dict, days: int = COVERAGE_DAYS) -> str:
    return f"Long-term interest '{interest['label']}' ({interest['id']}) has no item in the last {days} days."


def check_coverage(digest: dict, profile: dict, history=(), today: str | None = None,
                   days: int = COVERAGE_DAYS) -> list[str]:
    """Each active long-term interest needs an item in the last `days` days, this digest included."""
    return [coverage_message(i, days) for i in uncovered_interests(digest, profile, history, today, days)]


def check_source_mix(digest: dict, available_types) -> list[str]:
    """With two or more source types available, a digest must use at least two."""
    available = set(available_types)
    if len(available) < 2:
        return []
    used = {i.get("type") for i in digest.get("items") or []}
    if len(used) < 2:
        return [f"All items are of type {', '.join(sorted(map(str, used))) or 'none'}; "
                f"use at least two of: {', '.join(sorted(available))}."]
    return []


def _label_key(text) -> str:
    return " ".join(str(text or "").split()).casefold()


def check_headings(digest: dict, interests) -> list[str]:
    """A point whose field is an interest's label must cite an item matched to that interest;
    otherwise the heading claims a match that no item's label supports."""
    ids_by_label = {}
    for interest in interests:
        ids_by_label.setdefault(_label_key(interest.get("label")), set()).add(interest.get("id"))
    items = digest.get("items") if isinstance(digest.get("items"), list) else []
    matched = {item["id"]: item["reason"].get("interest_id") for item in items
               if isinstance(item, dict) and isinstance(item.get("id"), str) and isinstance(item.get("reason"), dict)
               and item["reason"].get("kind") == "interest"}
    brief = digest.get("brief") if isinstance(digest.get("brief"), dict) else {}
    points = brief.get("points") if isinstance(brief.get("points"), list) else []
    problems = []
    for index, point in enumerate(points):
        ids = ids_by_label.get(_label_key(point.get("field"))) if isinstance(point, dict) else None
        cites = point.get("cites") if ids and isinstance(point.get("cites"), list) else []
        if ids and not any(isinstance(c, str) and matched.get(c) in ids for c in cites):
            problems.append(f"brief.points[{index}] is under the heading '{point['field']}', an interest's label, "
                            "but none of the items it cites matches that interest. Put the point under a short "
                            "area name instead.")
    return problems


def check_rules(digest: dict, profile: dict, candidate_ids: set[str], *, available_types,
                history=(), today: str | None = None) -> dict[str, list[str]]:
    """All code rules, by rule name. A digest passes when every list is empty."""
    return {"structure_and_citations": check_digest(digest, candidate_ids),
            "topic_share": check_topic_share(digest),
            "coverage": check_coverage(digest, profile, history, today),
            "source_mix": check_source_mix(digest, available_types)}


def rule_errors(results: dict[str, list[str]]) -> list[str]:
    return [error for errors in results.values() for error in errors]
