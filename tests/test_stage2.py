"""Stage 2 offline tests (Idea 1): clarification onboarding and profile saving.

Scripted model replies; no key, network or spending. Run: .venv/bin/python -m pytest
"""

import json

import pytest

from forager import labkit
from forager.onboarding import (
    apply_edit, build_profile, check_clarification, clarify, profile_from_text,
    save_profile, validate_profile,
)
from forager.onboarding_cli import collect_answers, edit_loop
from forager.profile import load_profile

try:
    labkit.ensure_importable()
    from lab_support.testing import offline_lab, scripted_reply
except RuntimeError as exc:  # lab/ not unzipped yet
    pytest.skip(str(exc), allow_module_level=True)

DESCRIPTION = "AI student into agents, video editing and image gen, lately obsessed with Sora 2."
TODAY = "2026-10-25"


def clarification():
    return {
        "directions": [
            {"id": "d1", "label": "AI agents", "question": "Which parts of AI agents?",
             "options": ["tool use", "multi-agent systems", "agent evaluation", "coding agents"]},
            {"id": "d2", "label": "video editing", "question": "What about video editing?",
             "options": ["video generation models", "editing tools and plugins", "video understanding"]},
            {"id": "d3", "label": "image generation", "question": "Which image generation topics?",
             "options": ["new models", "open-source checkpoints", "prompting techniques"]},
        ],
        "adjacent": [{"label": "AI copyright policy", "why": "Affects image tools.", "related_to": "d3"},
                     {"label": "3D generation", "why": "Next to image and video.", "related_to": "d2"}],
        "short_term": [{"label": "Sora 2", "why": "You said you are following it closely."}],
    }


def lines(*replies):
    queue = list(replies)
    return lambda prompt="": queue.pop(0)


def test_clarification_check_accepts_valid_and_rejects_problems():
    assert check_clarification(clarification()) == []
    bad = clarification()
    bad["directions"][0]["options"] = ["only", "two"]
    bad["directions"][1]["id"] = "d1"
    bad["adjacent"] = [{"label": "AI agents", "why": "dup"}]
    errors = check_clarification(bad)
    assert any("3-6 options" in e for e in errors)
    assert any("unique id" in e for e in errors)
    assert any("repeats a direction" in e for e in errors)


def test_clarify_offline_repairs_once():
    bad = clarification()
    bad["adjacent"] = []
    replies = [scripted_reply(json.dumps(bad)), scripted_reply(json.dumps(clarification()))]
    with offline_lab(replies) as lab:
        outcome = clarify(lab, DESCRIPTION)
        first = lab.client.requests[0]["messages"]
        repair = lab.client.requests[1]["messages"][-1]["content"]
    assert outcome["errors"] == [] and outcome["attempts"] == 2
    assert any(DESCRIPTION in str(m.get("content")) for m in first)
    assert "'adjacent'" in repair


def test_clarify_rejects_empty_description():
    with offline_lab([]) as lab, pytest.raises(ValueError):
        clarify(lab, "   ")


def test_build_profile_uses_only_selected_options():
    answers = {"facets": {"d1": ["tool use", "invented by someone"], "d3": ["new models"]},
               "custom": {"d3": ["copyright lawsuits"]}, "drop": ["d2"],
               "adjacent": ["AI copyright policy", "not offered"], "short_term": ["Sora 2"]}
    profile = build_profile(clarification(), answers, TODAY, description=DESCRIPTION)
    labels = [i["label"] for i in profile["interests"]]
    assert labels == ["AI agents", "image generation", "AI copyright policy", "Sora 2"]
    agents, image, adjacent, sora = profile["interests"]
    assert agents["facets"] == ["tool use"]                       # unoffered option ignored
    assert image["facets"] == ["new models", "copyright lawsuits"]
    assert adjacent["weight"] == 0.5 and adjacent["origin"] == "suggested"
    assert sora["type"] == "short_term" and sora["expires"] == "2026-11-08"
    assert all(i["source"] == "stated" for i in profile["interests"])
    assert not any(profile["consent"].values())                   # no tracking until opt-in
    assert profile["setup"]["method"] == "clarification"
    assert validate_profile(profile) == []


def test_terminal_flow_collects_edits_and_saves(tmp_path):
    shown = []
    ask = lines("1 3", "x", "2 + copyright lawsuits", "1", "1",      # answers
                "w 2 0.7", "rm 9", "add AI safety", "time 07:30", "ok")  # edits
    answers = collect_answers(clarification(), ask, shown.append)
    assert answers["facets"]["d1"] == ["tool use", "agent evaluation"]
    assert answers["drop"] == ["d2"] and answers["custom"]["d3"] == ["copyright lawsuits"]
    profile = build_profile(clarification(), answers, TODAY)
    assert edit_loop(profile, ask, shown.append) is True
    assert any("Choose an interest number" in s for s in shown)    # rm 9 rejected, loop continued
    path = tmp_path / "profile.json"
    save_profile(profile, path)
    saved = load_profile(path)
    assert [i["label"] for i in saved["interests"]] == [
        "AI agents", "image generation", "AI copyright policy", "Sora 2", "AI safety"]
    assert saved["interests"][1]["weight"] == 0.7 and saved["delivery_time"] == "07:30"
    assert len({i["id"] for i in saved["interests"]}) == 5


def test_quit_does_not_save():
    profile = build_profile(clarification(), {"facets": {}}, TODAY)
    assert edit_loop(profile, lines("quit"), lambda _: None) is False


def test_edits_validate_input():
    profile = build_profile(clarification(), {"facets": {}}, TODAY)
    for command in ["w 1 0", "w 1 2", "exp 1.5", "time 25:00", "add", "dance"]:
        with pytest.raises(ValueError):
            apply_edit(profile, command, TODAY)
    apply_edit(profile, "short 1", TODAY)
    assert profile["interests"][0]["expires"] == "2026-11-08"
    apply_edit(profile, "long 1", TODAY)
    assert profile["interests"][0]["expires"] is None


def test_save_refuses_invalid_profile(tmp_path):
    profile = build_profile(clarification(), {"drop": ["d1", "d2", "d3"]}, TODAY)
    with pytest.raises(ValueError):
        save_profile(profile, tmp_path / "profile.json")
    assert not (tmp_path / "profile.json").exists()


def test_free_text_baseline_offline():
    reply = {"interests": [{"label": "AI agents", "facets": ["tools"]}, {"label": "Sora 2"}]}
    with offline_lab([scripted_reply(json.dumps(reply))]) as lab:
        outcome = profile_from_text(lab, DESCRIPTION, TODAY)
    profile = outcome["profile"]
    assert profile["setup"]["method"] == "free_text"
    assert [i["label"] for i in profile["interests"]] == ["AI agents", "Sora 2"]
    assert all(i["type"] == "long_term" for i in profile["interests"])
    assert validate_profile(profile) == []
