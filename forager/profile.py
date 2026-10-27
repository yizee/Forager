"""User interest profile: storage, defaults and which interests are currently active."""

import json
import os
from datetime import date
from pathlib import Path

from . import PROJECT_ROOT

# FORAGER_RUNTIME_DIR moves runtime data elsewhere (see storage.py; read once here).
RUNTIME_DIR = Path(os.environ.get("FORAGER_RUNTIME_DIR") or PROJECT_ROOT / "runtime")
PROFILE_PATH = RUNTIME_DIR / "profile.json"

# The persona used for the demo and report: an AI student following three fields.
# Consent is off: nothing is tracked until the user opts in to each signal.
DEFAULT_PROFILE = {
    "interests": [
        {"id": "i1", "label": "AI agents", "facets": ["tool use", "multi-agent systems", "evaluation"],
         "type": "long_term", "source": "stated", "weight": 1.0, "expires": None},
        {"id": "i2", "label": "video editing", "facets": ["video generation", "video understanding"],
         "type": "long_term", "source": "stated", "weight": 1.0, "expires": None},
        {"id": "i3", "label": "image generation", "facets": ["new models", "copyright"],
         "type": "long_term", "source": "stated", "weight": 1.0, "expires": None},
    ],
    "consent": {"ratings": False, "likes": False, "clicks": False, "reading_time": False},
    "exploration": 0.2,
    "delivery_time": "08:00",
}


def load_profile(path=PROFILE_PATH) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return json.loads(json.dumps(DEFAULT_PROFILE))


def is_expired(interest: dict, today: str | None = None) -> bool:
    """A short-term interest stops counting the day after its expiry date."""
    today = today or date.today().isoformat()
    return interest.get("type") == "short_term" and bool(interest.get("expires")) and interest["expires"] < today


def active_interests(profile: dict, today: str | None = None) -> list[dict]:
    """Interests the digest may use. Expired short-term ones wait for the user's decision."""
    return [i for i in profile.get("interests", []) if not is_expired(i, today)]


def expired_interests(profile: dict, today: str | None = None) -> list[dict]:
    return [i for i in profile.get("interests", []) if is_expired(i, today)]
