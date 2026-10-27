"""Stage 4 interface: the approval worker, UI helpers, and the Streamlit pages end to end.

Pages run headless with streamlit.testing.v1.AppTest against a temporary runtime folder
and the lab's scripted model: no key, network or spending.
"""

import json
import time
from contextlib import contextmanager
from datetime import date
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from forager import labkit, storage, ui_runtime
from forager.digest import prepare_candidates
from forager.memory import MemoryStore
from forager.onboarding import save_profile
from forager.signals import load_signals, record_signal
from forager.sources import load_snapshot
from forager.team import SPECIALISTS

try:
    labkit.ensure_importable()
    from lab_support.testing import offline_lab, scripted_reply
except RuntimeError as exc:  # lab/ not unzipped yet
    pytest.skip(str(exc), allow_module_level=True)

APP = str(Path(__file__).resolve().parent.parent / "forager" / "app.py")
TODAY = date.today().isoformat()


def interest(n, label, kind="long_term", expires=None):
    return {"id": f"i{n}", "label": label, "facets": [], "type": kind, "source": "stated", "weight": 1.0,
            "expires": expires}


def profile(**consent):
    return {"interests": [interest(1, "AI agents"), interest(2, "Video editing")],
            "consent": {"ratings": False, "likes": False, "clicks": False, "reading_time": False, **consent},
            "exploration": 0.2, "delivery_time": "08:00"}


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    monkeypatch.setenv("FORAGER_RUNTIME_DIR", str(tmp_path))
    return tmp_path


def use_replies(monkeypatch, replies):
    @contextmanager
    def fake():
        with offline_lab(replies) as lab:
            yield lab
    monkeypatch.setattr(ui_runtime, "open_connection", fake)


def reply(data):
    return scripted_reply(json.dumps(data))


def wait_for(condition, seconds=10):
    end = time.time() + seconds
    while not condition():
        if time.time() > end:
            raise AssertionError("timed out")
        time.sleep(0.05)


# ---- the approval worker ----

def memory_setup(runtime):
    store = MemoryStore(runtime=runtime, today=TODAY)
    save_profile(profile(ratings=True), store.profile_path)
    item = {"id": "p01", "type": "paper", "title": "A video model", "topics": [], "reason": {}}
    ids = [record_signal(store.signals_path, store.profile(), "ratings", dict(item, id=f"p0{n}"), TODAY, 5)["id"]
           for n in (1, 2, 3)]
    return store, ids


def proposal(ids, label):
    return scripted_reply(calls=[("propose_profile_update", {
        "action": "add_interest", "message": f"You rated three items 5/5. Add {label}?", "evidence": ids,
        "interest_id": None, "label": label, "interest_type": "short_term", "weight": 0.8})])


def test_worker_waits_for_each_answer(runtime, monkeypatch):
    store, ids = memory_setup(runtime)
    use_replies(monkeypatch, [proposal(ids, "Video generation"), proposal(ids, "Sora 2"),
                              scripted_reply("Done.")])
    worker = ui_runtime.ReviewWorker(store).start()
    wait_for(lambda: worker.pending)
    first = worker.pending["token"]
    assert "Video generation" in worker.pending["view"]["change"]
    assert worker.answer(first, True) and not worker.answer(first, True)        # a repeated click is ignored
    wait_for(lambda: worker.pending and worker.pending["token"] != first)
    assert worker.answer(worker.pending["token"], False)
    wait_for(lambda: not worker.running)
    assert worker.error is None and worker.result["status"] == "completed"
    labels = [i["label"] for i in store.profile()["interests"]]
    assert "Video generation" in labels and "Sora 2" not in labels
    assert [e["decision"] for e in store.history()] == ["approved", "rejected"]


def test_unanswered_proposal_is_rejected_after_the_timeout(runtime, monkeypatch):
    store, ids = memory_setup(runtime)
    before = store.profile_path.read_bytes()
    use_replies(monkeypatch, [proposal(ids, "Video generation"), scripted_reply("Nothing changed.")])
    worker = ui_runtime.ReviewWorker(store, timeout=0.2).start()
    wait_for(lambda: not worker.running)
    assert store.profile_path.read_bytes() == before and [e["decision"] for e in store.history()] == ["rejected"]


def test_worker_reports_errors(runtime, monkeypatch):
    store, _ = memory_setup(runtime)

    @contextmanager
    def broken():
        raise RuntimeError("Lab package not found")
        yield
    monkeypatch.setattr(ui_runtime, "open_connection", broken)
    worker = ui_runtime.ReviewWorker(store).start()
    wait_for(lambda: not worker.running)
    assert worker.error == "Lab package not found" and worker.result is None


# ---- helpers ----

def test_event_lines():
    assert ui_runtime.event_line({"type": "turn_started", "agent": "Critic"}) == "Critic: working..."
    assert ui_runtime.event_line({"type": "turn_completed", "agent": "Critic", "status": "completed",
                                  "usage": {"cost_usd": 0.0012}}) == "Critic: completed ($0.0012)"


def test_topic_distribution_and_week():
    digests = [{"items": [{"reason": {"kind": "interest", "interest_id": "i1"}},
                          {"reason": {"kind": "interest", "interest_id": "i1"}},
                          {"reason": {"kind": "breadth"}}]}]
    assert ui_runtime.topic_distribution(digests, profile()) == {"AI agents": 2, "Breadth": 1}
    assert ui_runtime.week_of(["2026-10-19", "2026-10-21", "2026-10-27"], "2026-10-27") == ["2026-10-21", "2026-10-27"]


def test_profile_rows_round_trip_with_edits():
    original = profile()["interests"]
    rows = ui_runtime.interest_rows(profile(), TODAY)
    rows[0]["label"], rows[0]["facets"] = "LLM agents", "tool use, evaluation"
    rows = [rows[0], {"id": None, "label": "3D generation", "facets": "", "type": "short_term", "weight": 0.5}]
    interests = ui_runtime.rows_to_interests(rows, original, TODAY)
    assert [(i["id"], i["label"]) for i in interests] == [("i1", "LLM agents"), ("i3", "3D generation")]
    assert interests[0]["facets"] == ["tool use", "evaluation"] and interests[0]["source"] == "stated"
    assert interests[1]["origin"] == "manual" and interests[1]["expires"]                 # 14 days by default


# ---- pages ----

def app():
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    return at


def go(at, page):
    at.sidebar.radio(key="page").set_value(page).run()
    assert not at.exception, [e.value for e in at.exception]
    return at


CLARIFICATION = {
    "directions": [{"id": "d1", "label": "AI agents", "question": "Which parts?",
                    "options": ["tool use", "evaluation", "coding agents"]},
                   {"id": "d2", "label": "Video editing", "question": "Which parts?",
                    "options": ["editing tools", "pipelines", "effects"]}],
    "adjacent": [{"label": "AI copyright policy", "why": "Nearby.", "related_to": "d2"}],
    "short_term": [{"label": "Sora 2", "why": "You mentioned it."}]}


def test_setup_page_builds_and_saves_a_profile(runtime, monkeypatch):
    use_replies(monkeypatch, [reply(CLARIFICATION)])
    at = go(app(), "Set up")
    at.text_area(key="setup_description").input("AI student into agents and video editing.").run()
    at.button(key="setup_ask").click().run()
    at.session_state["setup_facets_d1"] = ["tool use", "evaluation"]
    at.session_state["setup_drop_d2"] = True
    at.session_state["setup_adjacent"] = ["AI copyright policy"]
    at.session_state["setup_short"] = ["Sora 2"]
    at.button(key="setup_build").click().run()
    at.toggle(key="setup_consent_ratings").set_value(True).run()
    at.button(key="setup_save").click().run()
    assert not at.exception, [e.value for e in at.exception]
    saved = json.loads(storage.profile_path().read_text())
    assert [i["label"] for i in saved["interests"]] == ["AI agents", "AI copyright policy", "Sora 2"]
    assert saved["interests"][0]["facets"] == ["tool use", "evaluation"]
    assert saved["consent"] == {"ratings": True, "likes": False, "clicks": False, "reading_time": False}


def snapshot_candidates():
    return prepare_candidates([item for path in storage.latest_snapshots() for item in load_snapshot(path)])


def writer_draft():
    ids = [c["id"] for c in snapshot_candidates()][:6]              # interleaved: p01, r01, (n01,) p02, ...
    reasons = ["i1", "i1", "i2", "i2", None, None]
    items = [{"id": i, "summary": "Core contribution.", "topics": ["t"],
              "reason": {"kind": "interest", "interest_id": r, "text": "match"} if r
              else {"kind": "breadth", "interest_id": None, "text": "nearby"}} for i, r in zip(ids, reasons)]
    return ids, {"brief": {"points": [{"text": f"Point {n}.", "field": "AI agents", "cites": [ids[n]]}
                                      for n in range(5)],
                           "connections": [], "changes": [{"text": "First digest.", "cites": []}]},
                 "items": items}


def team_replies(draft):
    """The Manager asks every specialist with candidates; each reports the draft's items of its source."""
    types = {c["id"]: c["type"] for c in snapshot_candidates()}
    kinds = [k for k in SPECIALISTS if k in types.values()]
    replies = [scripted_reply(calls=[(SPECIALISTS[k]["tool"], {"input": "What is new?"}) for k in kinds])]
    for kind in kinds:
        notes = [{"id": i["id"], "summary": i["summary"], "topics": i["topics"], "fit": i["reason"]["kind"],
                  "interest_id": i["reason"]["interest_id"], "why": "w"} for i in draft["items"] if types[i["id"]] == kind]
        replies += [scripted_reply(calls=[(SPECIALISTS[kind]["reader"], {})]), reply({"items": notes, "overview": "o"})]
    return replies + [reply(draft)]


def test_digest_page_makes_and_shows_a_digest(runtime, monkeypatch):
    save_profile(profile(likes=True), storage.profile_path())
    ids, draft = writer_draft()
    use_replies(monkeypatch, team_replies(draft) + [reply({"verdict": "PASS", "issues": []})])
    at = app()
    at.button(key="make_digest").click().run()
    assert not at.exception, [e.value for e in at.exception]
    record = storage.load_digest(TODAY)
    assert record["mode"] == "critic" and record["writer"] == "team" and record["checks"]["critic"]["verdict"] == "PASS"
    assert {c["kind"] for c in record["team_calls"]} == {c["type"] for c in snapshot_candidates()}
    subheaders = [h.value for h in at.subheader]
    assert "How this digest was checked" in subheaders and any(h.startswith(f"{ids[1]} · ") for h in subheaders)
    assert any("Critic: no problems found." in m.value for m in at.markdown)
    assert any("Written by the Manager from its specialists' notes" in m.value for m in at.markdown)
    at.button(key=f"like-{TODAY}-{ids[0]}").click().run()
    [event] = load_signals(runtime / "signals.jsonl")
    assert event["signal"] == "likes" and event["item"]["id"] == ids[0]


def test_feedback_is_not_recorded_without_consent(runtime):
    save_profile(profile(), storage.profile_path())
    storage.digest_dir().mkdir(parents=True)
    _, draft = writer_draft()
    item = {**draft["items"][0], "title": "T", "url": "https://arxiv.org/abs/x", "type": "paper"}
    (storage.digest_dir() / f"{TODAY}.json").write_text(json.dumps({"date": TODAY, "brief": draft["brief"],
                                                                     "items": [item]}))
    at = app()
    at.button(key=f"like-{TODAY}-{item['id']}").click().run()
    assert not (runtime / "signals.jsonl").exists()
    assert any("Not recorded" in t.value for t in at.toast)


def test_memory_page_approval_goes_through_the_sdk(runtime, monkeypatch):
    store, ids = memory_setup(runtime)
    use_replies(monkeypatch, [proposal(ids, "Video generation"), scripted_reply("Added it after your approval.")])
    at = go(app(), "Memory")
    at.button(key="review_start").click().run(timeout=30)
    assert any("Forager suggests" in m.value for m in at.markdown)
    approve = next(b for b in at.button if b.key and b.key.startswith("approve_"))
    approve.click().run(timeout=30)
    assert not at.exception, [e.value for e in at.exception]
    assert any("Added it after your approval." in m.value for m in at.markdown)
    added = store.profile()["interests"][-1]
    assert added["label"] == "Video generation" and added["approved_on"] == TODAY and added["source"] == "inferred"
