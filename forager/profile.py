"""User interest profile. Stage 1 uses a fixed default; Stage 2 adds onboarding."""

import json

from . import PROJECT_ROOT

PROFILE_PATH = PROJECT_ROOT / "runtime" / "profile.json"

# The persona used for the demo and report: an AI student following three fields.
DEFAULT_PROFILE = {
    "interests": [
        {"id": "i1", "label": "AI agents", "facets": ["tool use", "multi-agent systems", "evaluation"],
         "type": "long_term", "source": "stated", "weight": 1.0, "expires": None},
        {"id": "i2", "label": "video editing", "facets": ["video generation", "video understanding"],
         "type": "long_term", "source": "stated", "weight": 1.0, "expires": None},
        {"id": "i3", "label": "image generation", "facets": ["new models", "copyright"],
         "type": "long_term", "source": "stated", "weight": 1.0, "expires": None},
    ],
    "consent": {"ratings": True, "likes": True, "clicks": False, "reading_time": False},
    "exploration": 0.2,
    "delivery_time": "08:00",
}


def load_profile(path=PROFILE_PATH) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return json.loads(json.dumps(DEFAULT_PROFILE))
