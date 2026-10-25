"""Deterministic digest checks, run in code on every digest (never left to the model).

Stage 1 covers structure and citation IDs. Stage 4 adds topic share, 7-day
interest coverage and source-type mix.
"""

MIN_POINTS, MAX_POINTS = 5, 8
REASON_KINDS = {"interest", "breadth"}


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
