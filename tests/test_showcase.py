"""The showcase page's Chinese text is checked against the English it translates."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "showcase"))
import build_data  # noqa: E402


def minimal_data():
    return {
        "digest": {"points": [{"text": "Point one.", "field": "AI agents", "cites": ["p01"]}], "connections": [], "changes": [],
                   "items": [{"id": "p01", "summary": "A summary.", "reason": {"kind": "interest", "text": "A reason."}}],
                   "critic": {"issues": []}, "revision": [], "team": [{"specialist": "Paper researcher", "overview": "Notes."}]},
        "profile": {"interests": [{"label": "AI agents", "facets": ["Coding agents"]}], "setup": {"description": "I study AI."}},
        "proposals": [{"change": 'Add "Video generation" as a long-term interest (weight 0.9)', "message": "Add it?"}],
    }


def write_translations(path: Path, **override):
    entries = {"points[0]": "Point one.", "items.p01.summary": "A summary.", "items.p01.reason": "A reason.",
               "team.Paper researcher.overview": "Notes.", "setup": "I study AI.",
               "proposals[0].change": 'Add "Video generation" as a long-term interest (weight 0.9)',
               "proposals[0].message": "Add it?", **override}
    terms = {t: f"zh {t}" for t in ("AI agents", "Coding agents", "Breadth", "Paper researcher", "Video generation")}
    path.write_text(json.dumps({"terms": terms, "entries": {k: {"en": v, "zh": f"zh {k}"} for k, v in entries.items()}}))


def test_each_translation_sits_next_to_its_english(tmp_path, monkeypatch):
    monkeypatch.setattr(build_data, "TRANSLATIONS", tmp_path / "zh.json")
    write_translations(tmp_path / "zh.json")
    data = minimal_data()
    build_data.attach_chinese(data)
    assert data["digest"]["points"][0]["zh"] == {"text": "zh points[0]"}
    assert data["digest"]["items"][0]["reason"]["zh"] == {"text": "zh items.p01.reason"}
    assert data["proposals"][0]["zh"]["message"] == "zh proposals[0].message"
    assert data["terms_zh"]["Video generation"] == "zh Video generation"      # the label a proposal adds


def test_a_stale_or_missing_translation_stops_the_build(tmp_path, monkeypatch):
    monkeypatch.setattr(build_data, "TRANSLATIONS", tmp_path / "zh.json")
    write_translations(tmp_path / "zh.json", **{"points[0]": "An older point."})
    with pytest.raises(SystemExit, match=r"points\[0\]: the English has changed"):
        build_data.attach_chinese(minimal_data())
    data = minimal_data()
    data["digest"]["points"][0]["field"] = "Robotics"                        # a heading with no term
    write_translations(tmp_path / "zh.json")
    with pytest.raises(SystemExit, match="no translation for 'Robotics'"):
        build_data.attach_chinese(data)
