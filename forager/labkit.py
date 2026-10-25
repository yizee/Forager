"""Locate the course lab package (lab/) and make its modules importable.

The lab code is not part of this repository. By default it is expected in
<project>/lab/ (unzipped week3-lab-ta). FORAGER_LAB_DIR overrides the location.
The lab's .env and .lab-state/ live in that folder; never delete .lab-state/.
"""

import os
import sys
from pathlib import Path

from . import PROJECT_ROOT


def lab_dir() -> Path:
    path = Path(os.environ.get("FORAGER_LAB_DIR", PROJECT_ROOT / "lab")).expanduser().resolve()
    # Accept lab/ itself or lab/week3-lab-ta/ (as unzipped from lab2.zip).
    if not (path / "lab_support").is_dir() and (path / "week3-lab-ta" / "lab_support").is_dir():
        path = path / "week3-lab-ta"
    if not (path / "lab_support").is_dir():
        raise RuntimeError(
            f"Lab package not found at {path}. Unzip lab2.zip into lab/ "
            "or set FORAGER_LAB_DIR to the week3-lab-ta folder.")
    return path


def ensure_importable() -> Path:
    """Put the lab folder on sys.path so lab_support, agent and file_access import."""
    path = lab_dir()
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
    return path
