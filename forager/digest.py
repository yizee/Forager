"""Stage 1 digest writer: one agent turns candidate items into a two-layer digest.

Python prepares the candidates, the agent writes JSON, and Python checks every
digest (checks.check_digest). If the check fails, the agent gets one repair turn
with the exact problems; the result is returned either way, with its errors.
"""

import json
import re
from datetime import date

from .checks import check_digest

ABSTRACT_CHARS = 600
TYPE_PREFIX = {"paper": "p", "news": "n", "repo": "r"}

INSTRUCTIONS = """You write Forager's daily digest for one user.
You receive the user's interest profile, today's candidate items (each with an ID),
and the previous digest's brief, if any. Use only the supplied items; never invent
items, IDs, links, results or numbers.

Return ONLY one JSON object, no Markdown fences, with this shape:
{
  "brief": {
    "points": [{"text": "...", "field": "<field name>", "cites": ["<item id>", ...]}],
    "connections": [{"text": "...", "cites": ["<item id>", ...]}],
    "changes": [{"text": "...", "cites": ["<item id>", ...]}]
  },
  "items": [{"id": "<item id>", "summary": "...", "topics": ["..."],
             "reason": {"kind": "interest|breadth", "interest_id": "<profile id or null>",
                        "text": "..."}}]
}

Rules:
- items: choose 8-12 candidates worth the user's time. Mostly match the profile's
  interests, and include roughly the profile's exploration share (at least one)
  as breadth items from adjacent fields. summary: 2-3 plain sentences on the core
  contribution. reason: kind "interest" names the matching interest and why;
  kind "breadth" explains why this adjacent item is worth a look.
- brief.points: 5-8 key points grouped by field. Each point cites at least one ID
  that is in your items list, and the cited items must support the point.
- brief.connections: 0-2 cross-field links, each citing items from different fields.
  Do not overstate a link the items do not support.
- brief.changes: what is new compared with the previous brief. If there is no
  previous brief, return one entry saying this is the first digest, with cites [].
- Keep each text under 50 words. Write in English.
"""


def prepare_candidates(raw_items: list[dict], limit: int = 20) -> list[dict]:
    """Assign stable per-digest IDs (p01, n01, r01, ...) and trim long text."""
    counters, candidates = {}, []
    for raw in raw_items[:limit]:
        prefix = TYPE_PREFIX.get(raw.get("type", "paper"), "x")
        counters[prefix] = counters.get(prefix, 0) + 1
        item = dict(raw, id=f"{prefix}{counters[prefix]:02d}")
        candidates.append(item)
    return candidates


def context_message(profile: dict, candidates: list[dict], previous: dict | None, today: str) -> str:
    interests = [{k: i.get(k) for k in ("id", "label", "facets", "type", "weight", "expires")}
                 for i in profile.get("interests", [])]
    shown = [{"id": c["id"], "type": c["type"], "title": c["title"],
              "categories": c.get("categories", []), "published": c.get("published"),
              "abstract": c.get("abstract", "")[:ABSTRACT_CHARS]} for c in candidates]
    previous_brief = None
    if previous:
        previous_brief = {"date": previous.get("date"),
                          "points": [p.get("text") for p in previous.get("brief", {}).get("points", [])]}
    return json.dumps({"today": today,
                       "profile": {"interests": interests, "exploration": profile.get("exploration", 0.2)},
                       "previous_brief": previous_brief,
                       "candidates": shown}, ensure_ascii=False)


def create_digest_agent(model):
    from agents import Agent
    return Agent(name="Digest writer", model=model, instructions=INSTRUCTIONS, tools=[])


def run_digest_agent(agent, messages, run_config=None):
    from agents import Runner
    return Runner.run_sync(agent, messages, max_turns=3, run_config=run_config)


def parse_json(text: str) -> dict:
    """Extract the JSON object from a model answer, tolerating code fences."""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("No JSON object found in the answer.")
    return json.loads(text[start:end + 1])


def generate_digest(lab, profile: dict, raw_items: list[dict], *, previous=None,
                    today=None, on_event=None, max_repairs=1) -> dict:
    """Run the single-agent digest on an open lab connection.

    Returns {"digest", "candidates", "errors", "attempts", "turns"}; errors is empty
    when the final digest passes the checks.
    """
    today = today or date.today().isoformat()
    candidates = prepare_candidates(raw_items)
    candidate_ids = {c["id"] for c in candidates}
    context = context_message(profile, candidates, previous, today)

    def build_input(history, user_input, files):
        # The candidates exceed session.run's 6,000-character limit, so they go in
        # as context on the first turn; later turns reuse the history.
        if not history:
            history = [{"role": "user", "content": "Digest context (JSON):\n" + context}]
        return history + [{"role": "user", "content": user_input}]

    session = lab.session(agent_factory=create_digest_agent, runner=run_digest_agent,
                          input_builder=build_input, on_event=on_event, agent_id="digest-writer")
    request = "Write today's digest as the JSON object described in your instructions."
    turns, digest, errors = [], None, []
    for attempt in range(max_repairs + 1):
        result = session.run(request)
        turns.append(result.to_dict())
        if result.status != "completed":
            errors = [f"Agent turn {result.status}: {result.error or 'no answer'}"]
            break
        try:
            digest = parse_json(result.answer)
            errors = check_digest(digest, candidate_ids)
        except ValueError as exc:
            digest, errors = None, [f"Answer is not valid JSON: {exc}"]
        if not errors:
            break
        request = ("Your digest failed these checks. Return the corrected full JSON object only.\n- "
                   + "\n- ".join(errors[:15]))
    if digest is not None:
        digest = merge_items(digest, candidates, today)
    return {"digest": digest, "candidates": candidates, "errors": errors,
            "attempts": len(turns), "turns": turns}


def merge_items(digest: dict, candidates: list[dict], today: str) -> dict:
    """Attach source metadata (title, url, date) from code, not from the model."""
    by_id = {c["id"]: c for c in candidates}
    items = []
    for item in digest.get("items", []):
        source = by_id.get(item.get("id")) if isinstance(item, dict) else None
        if source is None:
            continue
        items.append({"id": source["id"], "type": source["type"], "title": source["title"],
                      "url": source["url"], "published": source.get("published"),
                      "summary": item.get("summary", ""), "topics": item.get("topics", []),
                      "reason": item.get("reason", {})})
    return {"date": today, "brief": digest.get("brief", {}), "items": items}
