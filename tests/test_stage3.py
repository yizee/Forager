"""Stage 3 offline tests (Idea 2): consent, evidence-backed proposals, approval gate.

Scripted model replies drive the real SDK approval interruptions; no key, network
or spending. Run: .venv/bin/python -m pytest
"""

import json

import pytest

from forager import labkit
from forager.digest import context_message
from forager.memory import MemoryStore, check_proposal, resolve_expired, review
from forager.memory_cli import approval_prompt, ask_consent, find_item, review_expired
from forager.onboarding import save_profile
from forager.profile import active_interests
from forager.signals import load_signals, purge_signal, record_signal, set_consent, usable_signals

try:
    labkit.ensure_importable()
    from lab_support.testing import offline_lab, scripted_reply
except RuntimeError as exc:  # lab/ not unzipped yet
    pytest.skip(str(exc), allow_module_level=True)

TODAY = "2026-10-26"
NOW = "2026-10-25T09:00:00"


def base_profile():
    interest = lambda n, label, **extra: {"id": f"i{n}", "label": label, "facets": [], "type": "long_term",
                                          "source": "stated", "weight": 1.0, "expires": None, **extra}
    return {"interests": [interest(1, "AI agents"), interest(2, "video editing"), interest(3, "image generation")],
            "consent": {"ratings": True, "likes": True, "clicks": False, "reading_time": False},
            "exploration": 0.2, "delivery_time": "08:00"}


def item(n, title, topics):
    return {"id": f"p{n:02d}", "type": "paper", "title": title, "topics": topics,
            "reason": {"kind": "interest", "interest_id": "i2"}}


@pytest.fixture
def store(tmp_path):
    store = MemoryStore(runtime=tmp_path, today=TODAY)
    profile = base_profile()
    save_profile(profile, store.profile_path)
    sora = [item(3, "Sora 2 system card", ["video generation"]),
            item(5, "Sora 2 physics benchmark", ["video generation"]),
            item(7, "Editing with Sora 2 storyboards", ["video editing"])]
    store.ids = [record_signal(store.signals_path, profile, "ratings", it, "2026-10-25", 5, now=NOW)["id"]
                 for it in sora]
    store.ids.append(record_signal(store.signals_path, profile, "likes", sora[0], "2026-10-25", now=NOW)["id"])
    # A click stored while clicks were allowed, before the user turned them off.
    click = {"id": "sclick1", "time": NOW, "signal": "clicks", "value": 1, "digest": "2026-10-25",
             "item": {"id": "p09", "type": "paper", "title": "Diffusion editing", "topics": [],
                      "reason_kind": "interest", "interest_id": "i3"}}
    with store.signals_path.open("a") as log:
        log.write(json.dumps(click) + "\n")
    return store


def proposal(store, **changes):
    args = {"action": "add_interest", "evidence": store.ids[:3], "interest_id": None, "label": "Sora 2",
            "interest_type": "short_term", "weight": 0.8,
            "message": "You rated three Sora 2 items 5/5. Track Sora 2 as a short-term focus?"}
    args.update(changes)
    return args


def call(args):
    return scripted_reply(calls=[("propose_profile_update", args)])


def done(text="Proposed one change."):
    return scripted_reply(text)


class Decider:
    def __init__(self, *answers):
        self.answers, self.views = list(answers), []

    def __call__(self, view):
        self.views.append(view)
        return self.answers.pop(0)


def last_tool_output(request):
    return [m for m in request["messages"] if m.get("role") == "tool"][-1]["content"]


def memory_context(request):
    [content] = [m["content"] for m in request["messages"] if "Memory context" in str(m.get("content"))]
    return content


# ---- consent ----

def test_signals_are_stored_only_with_consent(store):
    profile = store.profile()
    before = store.signals_path.read_text()
    assert record_signal(store.signals_path, profile, "clicks", item(1, "x", []), "2026-10-25") is None
    assert store.signals_path.read_text() == before
    with pytest.raises(ValueError):
        record_signal(store.signals_path, profile, "ratings", item(1, "x", []), "2026-10-25", 6)


def test_only_currently_consented_recent_signals_are_usable(store):
    old = {**load_signals(store.signals_path)[0], "id": "sold", "time": "2026-09-01T09:00:00"}
    with store.signals_path.open("a") as log:
        log.write(json.dumps(old) + "\n")
    usable = {e["id"] for e in usable_signals(store.profile(), load_signals(store.signals_path), TODAY)}
    assert usable == set(store.ids)                      # no click (consent off), no 55-day-old rating


def test_withdrawing_consent_deletes_that_signal_only(store):
    profile = store.profile()
    assert set_consent(profile, store.signals_path, "likes", False) == 1
    remaining = load_signals(store.signals_path)
    assert {e["signal"] for e in remaining} == {"ratings", "clicks"} and len(remaining) == 4
    assert purge_signal(store.signals_path, "clicks") == 1


def test_consent_prompt_toggles_and_purges(store):
    profile, shown = store.profile(), []
    ask_consent(profile, store.signals_path, lambda _: "1 3 9", shown.append)
    assert profile["consent"] == {"ratings": False, "likes": True, "clicks": True, "reading_time": False}
    assert any("Deleted 3 stored ratings events" in s for s in shown)
    assert any("collects which items you open" in s for s in shown)


# ---- code checks on proposals ----

def test_proposal_checks(store):
    profile, events = store.profile(), {e["id"]: e for e in store.usable()}
    assert check_proposal(proposal(store), profile, events, today=TODAY) == []
    cases = {
        "Cite at least 2": proposal(store, evidence=store.ids[:1]),
        "not among the consented signals": proposal(store, evidence=[store.ids[0], "sclick1"]),
        "already in the profile": proposal(store, label="Video Editing"),
        "needs a weight": proposal(store, weight=1.5),
        "interest_id must be one of": proposal(store, action="remove_interest", interest_id="i9"),
        "already long_term": proposal(store, action="set_type", interest_id="i1", interest_type="long_term"),
        "action must be one of": proposal(store, action="rewrite_everything"),
        "message must": proposal(store, message=" "),
    }
    for expected, bad in cases.items():
        assert any(expected in e for e in check_proposal(bad, profile, events, today=TODAY)), expected


# ---- the approval gate (real SDK interruptions, scripted model) ----

def test_approved_proposal_is_written_with_evidence(store):
    decide = Decider(True)
    with offline_lab([call(proposal(store)), done()]) as lab:
        outcome = review(lab, store, decide)
        requests = lab.client.requests
    assert outcome["status"] == "completed" and len(requests) == 2
    view = decide.views[0]
    assert view["change"] == 'Add "Sora 2" as a short-term interest until 2026-11-09 (weight 0.8)'
    assert len(view["evidence"]) == 3 and view["evidence"][0].startswith("rated p03 (2026-10-25 digest) 5/5")
    sora = store.profile()["interests"][-1]
    assert sora["label"] == "Sora 2" and sora["source"] == "inferred" and sora["type"] == "short_term"
    assert sora["expires"] == "2026-11-09" and sora["approved_on"] == TODAY and len(sora["evidence"]) == 3
    assert [e["decision"] for e in store.history()] == ["approved"]
    assert json.loads(last_tool_output(requests[1]))["ok"] is True
    # The model saw consented signals only, and was told which signals are not tracked.
    context = memory_context(requests[0])
    assert store.ids[0] in context and "sclick1" not in context
    assert '"not_tracked": ["clicks", "reading_time"]' in context


def test_rejected_proposal_leaves_profile_unchanged(store):
    before = store.profile_path.read_bytes()
    decide = Decider(False)
    with offline_lab([call(proposal(store)), done("The user declined.")]) as lab:
        outcome = review(lab, store, decide)
        requests = lab.client.requests
    assert outcome["status"] == "completed" and len(decide.views) == 1
    assert store.profile_path.read_bytes() == before
    assert [e["decision"] for e in store.history()] == ["rejected"]
    assert "The user rejected this proposal" in last_tool_output(requests[1])


def test_unconsented_evidence_is_blocked_before_the_user_is_asked(store):
    before = store.profile_path.read_bytes()
    decide = Decider()
    bad = proposal(store, evidence=[store.ids[0], "sclick1"])
    with offline_lab([call(bad), done("Nothing changed.")]) as lab:
        review(lab, store, decide)
        requests = lab.client.requests
    assert decide.views == [] and store.profile_path.read_bytes() == before
    [entry] = store.history()
    assert entry["decision"] == "blocked" and any("sclick1" in e for e in entry["errors"])
    assert "Blocked by Forager's checks; the user was not asked." in last_tool_output(requests[1])


def test_rejected_change_is_not_proposed_again(store):
    with offline_lab([call(proposal(store)), done()]) as lab:
        review(lab, store, Decider(False))
    again = proposal(store, message="Sora 2 again: track it short-term?", evidence=store.ids[1:])
    decide = Decider()
    with offline_lab([call(again), done()]) as lab:
        review(lab, MemoryStore(runtime=store.runtime, today=TODAY), decide)
        context = json.loads(memory_context(lab.client.requests[0]).split("\n", 1)[1])
    assert decide.views == []
    assert [e["decision"] for e in store.history()] == ["rejected", "blocked"]
    [rejection] = context["recent_rejections"]
    assert rejection["change"] == 'Add "Sora 2" as a short-term interest until 2026-11-09 (weight 0.8)'


def test_at_most_three_proposals_per_review(store):
    labels = ["Sora 2", "video generation", "storyboarding", "physics benchmarks"]
    replies = [call(proposal(store, label=label)) for label in labels] + [done()]
    decide = Decider(True, True, True)
    with offline_lab(replies) as lab:
        review(lab, store, decide)
    assert len(decide.views) == 3
    assert [e["decision"] for e in store.history()] == ["approved"] * 3 + ["blocked"]
    assert len(store.profile()["interests"]) == 6


def test_silent_baseline_writes_without_asking(store):
    with offline_lab([call(proposal(store)), done()]) as lab:
        review(lab, store, silent=True)
    sora = store.profile()["interests"][-1]
    assert sora["label"] == "Sora 2" and sora["updated_silently_on"] == TODAY and "approved_on" not in sora
    assert [e["decision"] for e in store.history()] == ["silent"]


def test_no_model_call_without_enough_consented_signals(store):
    profile = store.profile()
    set_consent(profile, store.signals_path, "ratings", False)
    save_profile(profile, store.profile_path)
    with offline_lab([]) as lab:
        outcome = review(lab, store, Decider())
        assert lab.client.requests == []
    assert outcome["status"] == "skipped"


def test_approval_prompt_shows_code_generated_change_and_evidence():
    shown = []
    decide = approval_prompt(lambda _: "y", shown.append)
    assert decide({"message": "Track Sora 2?", "change": 'Add "Sora 2"', "evidence": ["rated p03 5/5"]})
    assert '  Change: Add "Sora 2"' in shown and "    - rated p03 5/5" in shown


# ---- short-term expiry ----

def expired_store(store):
    profile = store.profile()
    profile["interests"].append({"id": "i4", "label": "Sora 2", "facets": [], "type": "short_term",
                                 "source": "inferred", "weight": 0.8, "expires": "2026-10-20"})
    save_profile(profile, store.profile_path)
    return profile


def test_expired_short_term_interest_stops_counting(store):
    profile = expired_store(store)
    assert [i["label"] for i in active_interests(profile, TODAY)] == ["AI agents", "video editing", "image generation"]
    assert "Sora 2" not in context_message(profile, [], None, TODAY)
    assert "Sora 2" in context_message(profile, [], None, "2026-10-20")   # still active on its last day


@pytest.mark.parametrize("reply, check", [
    ("k", lambda i: i["type"] == "short_term" and i["expires"] == "2026-11-09"),
    ("l", lambda i: i["type"] == "long_term" and i["expires"] is None),
    ("r", lambda i: i is None),
    ("", lambda i: i["expires"] == "2026-10-20"),
])
def test_user_decides_about_expired_interest(store, reply, check):
    expired_store(store)
    review_expired(store, lambda _: reply, lambda _: None)
    sora = next((i for i in store.profile()["interests"] if i["id"] == "i4"), None)
    assert check(sora)
    assert len(store.history()) == (0 if reply == "" else 1)


def test_resolve_rejects_active_interest(store):
    with pytest.raises(ValueError):
        resolve_expired(store, "i1", "keep")


# ---- feedback lookup ----

def test_find_item_in_latest_digest(tmp_path):
    for day, title in [("2026-10-24", "old"), ("2026-10-25", "new")]:
        (tmp_path / f"{day}.json").write_text(json.dumps({"items": [{"id": "p01", "title": title}]}))
    assert find_item(tmp_path, "p01") == ({"id": "p01", "title": "new"}, "2026-10-25")
    assert find_item(tmp_path, "p01", "2026-10-24")[0]["title"] == "old"
    with pytest.raises(ValueError):
        find_item(tmp_path, "p99")
