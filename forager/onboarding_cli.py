"""Terminal front end for onboarding: numbered options stand in for clickable ones.

ask(prompt) -> str and show(text) are injected so the flow can be tested offline.
The Streamlit interface (Stage 4) reuses onboarding.py, not this module.
"""

import re

from .onboarding import EDIT_HELP, apply_edit, format_profile, validate_profile


def _numbers(reply: str, count: int) -> list[int]:
    picked = []
    for token in re.split(r"[\s,]+", reply.strip()):
        if token.isdigit() and 1 <= int(token) <= count and int(token) not in picked:
            picked.append(int(token))
    return picked


def collect_answers(clarification: dict, ask, show) -> dict:
    answers = {"facets": {}, "custom": {}, "drop": [], "adjacent": [], "short_term": []}
    show("Pick by number (e.g. '1 3'). Add your own with '+ text'. Enter = whole field. 'x' = not interested.")
    for direction in clarification["directions"]:
        show(f"\n{direction['label']}: {direction['question']}")
        for number, option in enumerate(direction["options"], start=1):
            show(f"  {number}. {option}")
        reply = ask("> ").strip()
        if reply.lower() == "x":
            answers["drop"].append(direction["id"])
            continue
        choice, _, custom = reply.partition("+")
        answers["facets"][direction["id"]] = [direction["options"][n - 1]
                                              for n in _numbers(choice, len(direction["options"]))]
        if custom.strip():
            answers["custom"][direction["id"]] = [c.strip() for c in custom.split(",") if c.strip()]
    if clarification.get("adjacent"):
        show("\nYou might also want these nearby fields (for breadth):")
        for number, entry in enumerate(clarification["adjacent"], start=1):
            show(f"  {number}. {entry['label']} - {entry.get('why', '')}")
        picked = _numbers(ask("Add which? (numbers, Enter = none) > "), len(clarification["adjacent"]))
        answers["adjacent"] = [clarification["adjacent"][n - 1]["label"] for n in picked]
    if clarification.get("short_term"):
        show("\nYou mentioned these as current focuses. Track them short-term (14 days)?")
        for number, entry in enumerate(clarification["short_term"], start=1):
            show(f"  {number}. {entry['label']} - {entry.get('why', '')}")
        picked = _numbers(ask("Track which? (numbers, Enter = none) > "), len(clarification["short_term"]))
        answers["short_term"] = [clarification["short_term"][n - 1]["label"] for n in picked]
    return answers


def edit_loop(profile: dict, ask, show) -> bool:
    """Let the user edit until they type ok (True) or quit (False)."""
    show("\n" + EDIT_HELP + "\n  quit              leave without saving")
    while True:
        show("\n" + format_profile(profile))
        command = ask("edit> ").strip()
        if command.lower() in {"quit", "q"}:
            return False
        if command.lower() == "ok":
            errors = validate_profile(profile)
            if not errors:
                return True
            show("Cannot save yet: " + "; ".join(errors))
            continue
        try:
            show(apply_edit(profile, command))
        except ValueError as exc:
            show(str(exc))
