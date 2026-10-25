"""Idea 1: clarification-based interest elicitation.

One rough sentence -> the agent splits it into directions and asks one question
per direction as clickable options, suggests adjacent fields, and lists any
specific short-term focus the user mentioned. The user's selections are turned
into a profile by code (build_profile), so the model cannot add preferences the
user did not pick. The user edits and confirms the profile before it is saved.

Baseline (free text): the agent turns the same sentence directly into a profile
with no questions (profile_from_text).
"""

import json
import re
from datetime import date, timedelta

from .jsonagent import ask_json, context_input, json_agent_factory, run_plain
from .profile import PROFILE_PATH

SHORT_TERM_DAYS = 14
ADJACENT_WEIGHT = 0.5
SHORT_TERM_WEIGHT = 0.8

CLARIFY_INSTRUCTIONS = """You help a user set up Forager, a daily digest of AI news,
papers and open-source tools. The user describes themselves in one rough sentence.
Turn it into clickable follow-up questions; do not ask them to type more.

Return ONLY one JSON object, no Markdown fences:
{
  "directions": [{"id": "d1", "label": "<short field name>",
                  "question": "<one question about this field>",
                  "options": ["<3-6 short, distinct options>"]}],
  "adjacent": [{"label": "<adjacent field>", "why": "<one sentence>", "related_to": "<direction id>"}],
  "short_term": [{"label": "<specific model, release or event>", "why": "<one sentence>"}]
}

Rules:
- directions: 1-5 fields the user actually mentioned or clearly implied. Never add
  a field the user did not mention; that is what adjacent is for.
- options: concrete sub-topics a digest could filter on (e.g. "video generation
  models", "editing tools and plugins"), not levels of enthusiasm. 3-6 per question.
- adjacent: 1-3 neighbouring fields the user might want for breadth (e.g. "AI
  copyright policy" for image generation). They are suggestions; the user decides.
- short_term: only specific, time-bound things the user explicitly mentioned (a
  model release, an event). Return [] if there are none.
- Keep labels under 6 words and questions under 20 words. Write in English.
"""

BASELINE_INSTRUCTIONS = """You set up a Forager interest profile from the user's own
description, without asking any questions.

Return ONLY one JSON object, no Markdown fences:
{"interests": [{"label": "<short field name>", "facets": ["<sub-topic>", ...]}]}

Include 1-8 interests based on the description. Keep labels under 6 words.
"""


def _labels(entries):
    return [e.get("label", "").strip().casefold() for e in entries if isinstance(e, dict)]


def check_clarification(data: dict) -> list[str]:
    errors = []
    directions = data.get("directions")
    if not isinstance(directions, list) or not 1 <= len(directions) <= 5:
        return ["'directions' must be a list of 1-5 entries."]
    ids = []
    for index, direction in enumerate(directions):
        label = f"directions[{index}]"
        if not isinstance(direction, dict):
            errors.append(f"{label} must be an object.")
            continue
        if not str(direction.get("id", "")).strip() or direction.get("id") in ids:
            errors.append(f"{label} needs a unique id.")
        ids.append(direction.get("id"))
        for key in ("label", "question"):
            if not str(direction.get(key, "")).strip():
                errors.append(f"{label} needs a non-empty {key}.")
        options = direction.get("options")
        if not isinstance(options, list) or not 3 <= len(options) <= 6:
            errors.append(f"{label} needs 3-6 options.")
        elif len({str(o).strip().casefold() for o in options}) != len(options) or not all(str(o).strip() for o in options):
            errors.append(f"{label} options must be non-empty and distinct.")
    adjacent = data.get("adjacent")
    if not isinstance(adjacent, list) or not 1 <= len(adjacent) <= 3:
        errors.append("'adjacent' must be a list of 1-3 suggestions.")
    else:
        direction_labels = set(_labels(directions))
        for index, entry in enumerate(adjacent):
            if not isinstance(entry, dict) or not str(entry.get("label", "")).strip():
                errors.append(f"adjacent[{index}] needs a label.")
            elif entry["label"].strip().casefold() in direction_labels:
                errors.append(f"adjacent[{index}] repeats a direction; suggest a different field.")
    short_term = data.get("short_term", [])
    if not isinstance(short_term, list) or any(not isinstance(e, dict) or not str(e.get("label", "")).strip()
                                               for e in short_term):
        errors.append("'short_term' must be a list of objects with a label (or []).")
    return errors


def clarify(lab, description: str, *, on_event=None) -> dict:
    """Ask the agent for option-based follow-up questions. Returns ask_json's outcome."""
    description = description.strip()
    if not description or len(description) > 1000:
        raise ValueError("Describe yourself in one sentence (under 1,000 characters).")
    session = lab.session(agent_factory=json_agent_factory("Interest clarifier", CLARIFY_INSTRUCTIONS),
                          runner=run_plain, input_builder=context_input("", ""),
                          on_event=on_event, agent_id="clarifier")
    return ask_json(session, "User's description: " + description, check_clarification)


def _interest(number, label, facets, *, type_="long_term", weight=1.0, expires=None, origin):
    return {"id": f"i{number}", "label": label.strip(), "facets": facets, "type": type_,
            "source": "stated", "weight": weight, "expires": expires, "origin": origin}


def build_profile(clarification: dict, answers: dict, today: str | None = None, *,
                  description: str = "") -> dict:
    """Turn the user's selections into a profile. Only selected items are included.

    answers = {"facets": {direction_id: [option, ...]}, "custom": {direction_id: [text]},
               "drop": [direction_id], "adjacent": [label], "short_term": [label]}
    A direction is kept unless dropped, even with no facets selected (whole field).
    """
    today = today or date.today().isoformat()
    expires = (date.fromisoformat(today) + timedelta(days=SHORT_TERM_DAYS)).isoformat()
    interests = []
    dropped = set(answers.get("drop", []))
    for direction in clarification["directions"]:
        if direction["id"] in dropped:
            continue
        offered = {str(o) for o in direction["options"]}
        facets = [o for o in answers.get("facets", {}).get(direction["id"], []) if o in offered]
        facets += [c.strip() for c in answers.get("custom", {}).get(direction["id"], []) if c.strip()]
        interests.append(_interest(len(interests) + 1, direction["label"], facets, origin="clarification"))
    offered_adjacent = {a["label"] for a in clarification.get("adjacent", [])}
    for label in answers.get("adjacent", []):
        if label in offered_adjacent:
            interests.append(_interest(len(interests) + 1, label, [], weight=ADJACENT_WEIGHT, origin="suggested"))
    offered_short = {s["label"] for s in clarification.get("short_term", [])}
    for label in answers.get("short_term", []):
        if label in offered_short:
            interests.append(_interest(len(interests) + 1, label, [], type_="short_term",
                                       weight=SHORT_TERM_WEIGHT, expires=expires, origin="clarification"))
    return new_profile(interests, method="clarification", description=description, today=today)


def new_profile(interests, *, method, description, today):
    # Nothing is tracked until the user opts in to each signal (Idea 2, Stage 3).
    return {"interests": interests,
            "consent": {"ratings": False, "likes": False, "clicks": False, "reading_time": False},
            "exploration": 0.2, "delivery_time": "08:00",
            "setup": {"method": method, "description": description, "date": today}}


def check_baseline(data: dict) -> list[str]:
    interests = data.get("interests")
    if not isinstance(interests, list) or not 1 <= len(interests) <= 8:
        return ["'interests' must be a list of 1-8 entries."]
    return [f"interests[{i}] needs a label." for i, e in enumerate(interests)
            if not isinstance(e, dict) or not str(e.get("label", "")).strip()]


def profile_from_text(lab, description: str, today: str | None = None, *, on_event=None) -> dict:
    """Baseline: one free-text description straight to a profile, no questions."""
    today = today or date.today().isoformat()
    session = lab.session(agent_factory=json_agent_factory("Profile extractor", BASELINE_INSTRUCTIONS),
                          runner=run_plain, input_builder=context_input("", ""),
                          on_event=on_event, agent_id="baseline-extractor")
    outcome = ask_json(session, "User's description: " + description.strip(), check_baseline)
    if outcome["data"] is not None and not outcome["errors"]:
        interests = [_interest(n, e["label"], [str(f) for f in e.get("facets", [])], origin="free_text")
                     for n, e in enumerate(outcome["data"]["interests"], start=1)]
        outcome["profile"] = new_profile(interests, method="free_text", description=description, today=today)
    return outcome


# ---- editing and saving (no model involved) ----

def validate_profile(profile: dict) -> list[str]:
    errors = []
    interests = profile.get("interests", [])
    if not interests:
        errors.append("The profile needs at least one interest.")
    ids = [i.get("id") for i in interests]
    if len(set(ids)) != len(ids):
        errors.append("Interest ids must be unique.")
    for interest in interests:
        if not str(interest.get("label", "")).strip():
            errors.append(f"Interest {interest.get('id')} needs a label.")
        if interest.get("type") not in {"long_term", "short_term"}:
            errors.append(f"Interest {interest.get('id')} type must be long_term or short_term.")
        if interest.get("source") not in {"stated", "inferred"}:
            errors.append(f"Interest {interest.get('id')} source must be stated or inferred.")
        if not 0 < float(interest.get("weight", 0)) <= 1:
            errors.append(f"Interest {interest.get('id')} weight must be in (0, 1].")
        if interest.get("type") == "short_term" and not interest.get("expires"):
            errors.append(f"Short-term interest {interest.get('id')} needs an expiry date.")
    if not 0 <= float(profile.get("exploration", -1)) <= 1:
        errors.append("Exploration must be between 0 and 1.")
    if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", str(profile.get("delivery_time", ""))):
        errors.append("Delivery time must be HH:MM.")
    return errors


EDIT_HELP = """Edit commands:
  rm N              remove interest N
  w N 0.5           set the weight of interest N (0-1]
  facets N a, b     replace the facets of interest N
  add LABEL         add a long-term interest
  short N           make interest N short-term (expires in 14 days); 'long N' reverses
  exp 0.3           set the exploration share (0-1)
  time 07:30        set the delivery time
  ok                save the profile"""


def apply_edit(profile: dict, command: str, today: str | None = None) -> str:
    """Apply one edit command in place. Returns a message; raises ValueError if invalid."""
    today = today or date.today().isoformat()
    parts = command.strip().split(maxsplit=1)
    if not parts:
        raise ValueError("Empty command.")
    verb, rest = parts[0].lower(), parts[1].strip() if len(parts) > 1 else ""
    interests = profile["interests"]

    def pick(token):
        if not token.isdigit() or not 1 <= int(token) <= len(interests):
            raise ValueError(f"Choose an interest number from 1 to {len(interests)}.")
        return interests[int(token) - 1]

    if verb == "rm":
        interest = pick(rest)
        interests.remove(interest)
        return f"Removed {interest['label']}."
    if verb == "w":
        number, _, value = rest.partition(" ")
        interest, weight = pick(number), float(value)
        if not 0 < weight <= 1:
            raise ValueError("Weight must be in (0, 1].")
        interest["weight"] = weight
        return f"{interest['label']} weight set to {weight}."
    if verb == "facets":
        number, _, value = rest.partition(" ")
        interest = pick(number)
        interest["facets"] = [f.strip() for f in value.split(",") if f.strip()]
        return f"{interest['label']} facets updated."
    if verb == "add":
        if not rest:
            raise ValueError("Give a label, e.g. 'add AI safety'.")
        number = max([int(i["id"][1:]) for i in interests if i["id"][1:].isdigit()] or [0]) + 1
        interests.append(_interest(number, rest, [], origin="manual"))
        return f"Added {rest}."
    if verb in {"short", "long"}:
        interest = pick(rest)
        interest["type"] = "short_term" if verb == "short" else "long_term"
        interest["expires"] = ((date.fromisoformat(today) + timedelta(days=SHORT_TERM_DAYS)).isoformat()
                               if verb == "short" else None)
        return f"{interest['label']} is now {interest['type']}."
    if verb == "exp":
        value = float(rest)
        if not 0 <= value <= 1:
            raise ValueError("Exploration must be between 0 and 1.")
        profile["exploration"] = value
        return f"Exploration set to {value}."
    if verb == "time":
        if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", rest):
            raise ValueError("Use HH:MM, e.g. 07:30.")
        profile["delivery_time"] = rest
        return f"Delivery time set to {rest}."
    raise ValueError("Unknown command.\n" + EDIT_HELP)


def format_profile(profile: dict) -> str:
    lines = ["Your profile:"]
    for number, interest in enumerate(profile["interests"], start=1):
        facets = ", ".join(interest.get("facets") or []) or "whole field"
        term = (f"short-term until {interest['expires']}" if interest["type"] == "short_term" else "long-term")
        lines.append(f"  {number}. {interest['label']} [{facets}] · {term} · {interest['source']}"
                     f" · weight {interest['weight']}")
    lines.append(f"  Exploration share: {profile['exploration']} · Delivery time: {profile['delivery_time']}")
    return "\n".join(lines)


def save_profile(profile: dict, path=PROFILE_PATH) -> None:
    errors = validate_profile(profile)
    if errors:
        raise ValueError("; ".join(errors))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n")
