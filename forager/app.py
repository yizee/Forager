"""Forager in the browser. Run from the project folder: .venv/bin/streamlit run forager/app.py

Pages: Digest (two-layer brief, ratings, how it was made and checked), Set up (Idea 1), Memory
(Idea 2: consent, visible profile, evidence-backed updates you approve) and Topics
(Idea 3: this week's topic mix, exploration share). Paid model calls happen only on
buttons marked "paid".
"""

import sys
import time
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from forager import storage, ui_runtime  # noqa: E402
from forager.digest import generate_digest  # noqa: E402
from forager.memory import MIN_EVIDENCE, MemoryStore, resolve_expired  # noqa: E402
from forager.onboarding import build_profile, clarify, profile_from_text, save_profile, validate_profile  # noqa: E402
from forager.profile import active_interests, expired_interests, is_expired, load_profile  # noqa: E402
from forager.render import team_line  # noqa: E402
from forager.signals import SIGNALS, describe, load_signals, purge_signal, record_signal, set_consent  # noqa: E402
from forager.sources import arxiv, github, load_snapshot, news  # noqa: E402

MODES = {"critic": "Team + rules + Critic", "rules": "Team + rules", "single": "Single agent"}
ISSUE_NAMES = {"irrelevant_exploration": "Irrelevant exploration", "near_duplicate": "Near-duplicate",
               "unsupported_citation": "Citation does not support the point",
               "overstated_connection": "Overstated connection", "mislabeled_interest": "Wrong interest label"}


def today() -> str:
    return date.today().isoformat()


def md(text) -> str:
    """Plain text for st.markdown: dollar signs would otherwise start LaTeX."""
    return str(text or "").replace("$", "\\$")


def current_profile() -> dict | None:
    path = storage.profile_path()
    return load_profile(path) if path.exists() else None


def memory_store() -> MemoryStore:
    return MemoryStore(runtime=storage.runtime_dir(), today=today())


def cites(ids) -> str:
    return " ".join(f"[{i}](#{i})" for i in ids or [])


# ---- Digest ----

def digest_page():
    st.header("Today's digest")
    profile = current_profile()
    if profile is None:
        st.info("Set up your interests first (Set up page).")
        return
    days = storage.digest_days()
    with st.expander("Make a new digest", expanded=not days):
        snapshots = storage.latest_snapshots()
        use_snapshots = st.toggle("Use the saved snapshots (same items every time)", value=True, key="use_snapshots")
        st.caption("Snapshots: " + ", ".join(p.name for p in snapshots) if use_snapshots
                   else "Fetches recent arXiv papers, GitHub repositories and tech news now.")
        mode = st.segmented_control("Pipeline", list(MODES), format_func=MODES.get, default="critic", key="mode")
        st.caption("Team: a Manager delegates to a Paper, an Open-source and a News researcher, each reading "
                   "only its own source. Single agent: one writer reads everything (the baseline).")
        if st.button("Make digest (paid model calls)", type="primary", key="make_digest"):
            make_digest(profile, snapshots if use_snapshots else None, mode or "critic")
    if not days:
        return
    day = st.selectbox("Date", list(reversed(days)), key="digest_day")
    show_digest(storage.load_digest(day), profile, day)


def make_digest(profile: dict, snapshots, mode: str):
    day = today()
    with st.status("Making the digest...", expanded=True) as status:
        if snapshots:
            raw = [item for path in snapshots for item in load_snapshot(path)]
        else:
            status.write("Fetching arXiv, GitHub and tech news...")
            raw = arxiv.fetch() + github.fetch() + news.fetch()
        try:
            with ui_runtime.open_connection() as lab:
                outcome = generate_digest(lab, profile, raw, mode=mode, previous=storage.latest_digest(day),
                                          history=storage.recent_digests(day), today=day,
                                          on_event=lambda event: status.write(ui_runtime.event_line(event)))
        except Exception as exc:
            status.update(label=f"Could not make the digest: {exc}", state="error")
            return
        storage.save_digest(outcome, profile, day)
        if outcome["digest"] is None:
            status.update(label="The writer gave no usable digest; see the saved record.", state="error")
            return
        status.update(label="Digest ready", state="complete")
    st.session_state.digest_day = day
    st.rerun()


def show_digest(record: dict, profile: dict, day: str):
    labels = {i["id"]: i["label"] for i in profile["interests"]}
    brief = record.get("brief") or {}
    st.subheader("Quick brief")
    fields = {}
    for point in brief.get("points") or []:
        fields.setdefault(point.get("field") or "Other", []).append(point)
    for field, points in fields.items():
        st.markdown(f"**{md(field)}**\n" + "\n".join(f"- {md(p['text'])} {cites(p.get('cites'))}" for p in points))
    if brief.get("connections"):
        st.markdown("**Cross-field connections**\n" + "\n".join(
            f"- {md(c['text'])} {cites(c.get('cites'))}" for c in brief["connections"]))
    if brief.get("changes"):
        st.markdown("**Changes since last time**\n" + "\n".join(
            f"- {md(c['text'])} {cites(c.get('cites'))}".rstrip() for c in brief["changes"]))
    st.subheader("Full items")
    for item in record.get("items") or []:
        show_item(item, labels, day)
    show_checks(record.get("checks"))


def show_item(item: dict, labels: dict, day: str):
    with st.container(border=True):
        st.subheader(f"{item['id']} · {item['title']}", anchor=item["id"])
        reason = item.get("reason") or {}
        if reason.get("kind") == "breadth":
            st.badge("Breadth: something next to your interests", icon=":material/explore:", color="orange")
        else:
            label = labels.get(reason.get("interest_id"), reason.get("interest_id") or "interest")
            st.badge(f"Interest match: {label}", icon=":material/target:", color="blue")
        st.caption(f"Why you see this: {md(reason.get('text'))}")
        st.write(md(item.get("summary")))
        where = " · ".join(str(part) for part in (item.get("type", "item"), item.get("source"), item.get("published"))
                           if part)
        st.markdown(f"[{md(where)}]({item.get('url', '')})")
        with st.container(horizontal=True, vertical_alignment="center", gap="medium"):
            st.feedback("stars", key=f"rate-{day}-{item['id']}", on_change=rate, args=(item, day))
            st.button("Like", icon=":material/thumb_up:", key=f"like-{day}-{item['id']}", on_click=like,
                      args=(item, day))


def record_feedback(signal: str, item: dict, day: str, value=1):
    profile = current_profile()
    event = record_signal(memory_store().signals_path, profile, signal, item, day, value) if profile else None
    if event is None:
        st.toast(f"Not recorded: {SIGNALS[signal]['label'].lower()} are off. You can turn them on in Memory.")
    else:
        st.toast("Recorded: " + describe(event))


def rate(item: dict, day: str):
    stars = st.session_state.get(f"rate-{day}-{item['id']}")
    if stars is not None:
        record_feedback("ratings", item, day, stars + 1)


def like(item: dict, day: str):
    record_feedback("likes", item, day)


def show_checks(checks: dict | None):
    if not checks:
        return
    st.subheader("How this digest was checked")
    writer = team_line(checks)
    if writer:
        st.markdown(f"- {md(writer)}")
    if checks.get("team"):
        with st.expander("What the Manager asked its specialists"):
            for row in checks["team"]:
                st.markdown(f"**{row['specialist']}** · {row['candidates']} {row['plural']}, "
                            f"{len(row['reported'])} reported, {len(row['used'])} used")
                for question in row["questions"] or ["(not asked)"]:
                    st.markdown(f"> {md(question)}")
                if row.get("overview"):
                    st.caption(md(row["overview"]))
    scope = ("structure and citations" if checks.get("mode") == "single"
             else "structure, citations, topic share, coverage and source mix")
    st.markdown(f"- Code rules ({scope}): {'passed' if checks.get('rules_passed') else 'not all passed'}.")
    for warning in checks.get("warnings") or []:
        st.markdown(f"- Not covered: {md(warning)}")
    critic = checks.get("critic")
    if critic is None:
        return
    if critic.get("errors"):
        st.markdown("- Critic: no usable review this time; the digest passed the code rules.")
    elif critic.get("verdict") == "PASS":
        st.markdown("- Critic: no problems found.")
    else:
        reviser = "the Manager" if checks.get("writer") == "team" else "the writer"
        outcome = (f"{reviser} revised the digest once" if critic.get("revised")
                   else "the revision broke a code rule, so the checked draft is shown")
        st.markdown(f"- Critic: {len(critic['issues'])} issue(s); {outcome}.")
        for issue in critic["issues"]:
            st.markdown(f"    - {ISSUE_NAMES.get(issue['type'], issue['type'])} ({', '.join(issue['refs'])}): "
                        f"{md(issue['explanation'])}")


# ---- Set up (Idea 1) ----

def setup_page():
    st.header("Set up your interests")
    state = st.session_state.setdefault("setup", {})
    if current_profile():
        st.caption("You already have a profile. Saving here replaces it.")
    description = st.text_area("Describe yourself and what you follow, in one sentence", key="setup_description",
                               placeholder="I'm an AI student who follows AI agents, video editing and image "
                                           "generation, and lately Sora 2.")
    baseline = st.toggle("Study baseline: build the profile straight from this sentence, without questions",
                         key="setup_baseline")
    if st.button("Continue (1 paid call)", type="primary", key="setup_ask", disabled=not description.strip()):
        with st.spinner("Preparing questions..." if not baseline else "Building your profile..."):
            try:
                with ui_runtime.open_connection() as lab:
                    outcome = (profile_from_text(lab, description) if baseline else clarify(lab, description))
            except Exception as exc:
                st.error(f"The call did not complete: {exc}")
                return
        if outcome["errors"]:
            st.error("The answer could not be used: " + "; ".join(outcome["errors"]))
            return
        state.clear()
        state.update(description=description.strip(), clarification=None if baseline else outcome["data"],
                     draft=outcome.get("profile"))
    if state.get("clarification") and not state.get("draft"):
        ask_questions(state)
    if state.get("draft"):
        edit_and_save(state)


def ask_questions(state: dict):
    data = state["clarification"]
    st.subheader("A few quick questions")
    st.caption("Pick what fits. Nothing you do not pick ends up in your profile.")
    for direction in data["directions"]:
        st.pills(f"{direction['label']}: {direction['question']}", direction["options"], selection_mode="multi",
                 key=f"setup_facets_{direction['id']}")
        left, right = st.columns([3, 1])
        left.text_input("Add your own (comma-separated)", key=f"setup_custom_{direction['id']}",
                        label_visibility="collapsed", placeholder="Add your own, comma-separated")
        right.checkbox("Not interested", key=f"setup_drop_{direction['id']}")
    st.pills("You might also like these nearby fields", [a["label"] for a in data["adjacent"]],
             selection_mode="multi", key="setup_adjacent")
    st.caption(" · ".join(f"{a['label']}: {md(a.get('why'))}" for a in data["adjacent"]))
    if data.get("short_term"):
        st.pills("You mentioned these as current focuses. Track them for 14 days?",
                 [s["label"] for s in data["short_term"]], selection_mode="multi", key="setup_short")
    if st.button("Build my profile", type="primary", key="setup_build"):
        ids = [d["id"] for d in data["directions"]]
        answers = {
            "facets": {i: st.session_state.get(f"setup_facets_{i}") or [] for i in ids},
            "custom": {i: [c for c in (st.session_state.get(f"setup_custom_{i}") or "").split(",") if c.strip()]
                       for i in ids},
            "drop": [i for i in ids if st.session_state.get(f"setup_drop_{i}")],
            "adjacent": st.session_state.get("setup_adjacent") or [],
            "short_term": st.session_state.get("setup_short") or []}
        state["draft"] = build_profile(data, answers, description=state["description"])
        st.rerun()


def edit_and_save(state: dict):
    draft = state["draft"]
    st.subheader("Your profile: edit anything, then save")
    rows = st.data_editor(
        ui_runtime.interest_rows(draft, today()), num_rows="dynamic", hide_index=True, key="setup_editor",
        disabled=["id", "source", "status"],
        column_config={"type": st.column_config.SelectboxColumn("type", options=["long_term", "short_term"]),
                       "weight": st.column_config.NumberColumn("weight", min_value=0.1, max_value=1.0, step=0.1),
                       "facets": st.column_config.TextColumn("facets (comma-separated)")})
    st.markdown("**What Forager may learn from.** Nothing is tracked unless you turn it on.")
    consent = {key: st.toggle(f"{info['label']}: {info['collects']}", key=f"setup_consent_{key}",
                              help=f"Used to {info['use']}. Turning it off later deletes what was collected.")
               for key, info in SIGNALS.items()}
    exploration = st.slider("Exploration share", 0.0, 0.5, float(draft.get("exploration", 0.2)), 0.05,
                            key="setup_exploration", help="About this share of each digest goes to things next "
                                                          "to your interests that you did not ask for.")
    if st.button("Save profile", type="primary", key="setup_save"):
        profile = {**draft, "interests": ui_runtime.rows_to_interests(rows, draft["interests"], today()),
                   "consent": consent, "exploration": exploration}
        errors = validate_profile(profile)
        if errors:
            st.error("; ".join(errors))
            return
        for key, allowed in consent.items():
            if not allowed:
                purge_signal(memory_store().signals_path, key)
        save_profile(profile, storage.profile_path())
        state.clear()
        st.success("Saved. Your next digest will use this profile.")


# ---- Memory (Idea 2) ----

def memory_page():
    st.header("What Forager knows about you")
    profile = current_profile()
    if profile is None:
        st.info("Set up your interests first (Set up page).")
        return
    store = memory_store()
    st.subheader("Your interests")
    for interest in profile["interests"]:
        show_interest(interest)
    st.subheader("What Forager may learn from")
    st.caption("Only signals you turn on are recorded and used. Turning one off deletes what was collected.")
    for key, info in SIGNALS.items():
        st.toggle(f"{info['label']}: {info['collects']}", value=bool(profile.get("consent", {}).get(key)),
                  key=f"consent_{key}", on_change=change_consent, args=(key,), help=f"Used to {info['use']}.")
    for interest in expired_interests(profile, today()):
        with st.container(border=True):
            st.markdown(f"**{md(interest['label'])}** was a short-term interest until {interest['expires']} and is "
                        "no longer used in your digest.")
            keep, long, remove = st.columns(3)
            for column, choice, text in ((keep, "keep", "Keep 14 more days"), (long, "long", "Make long-term"),
                                         (remove, "remove", "Remove")):
                if column.button(text, key=f"expired_{choice}_{interest['id']}"):
                    st.toast(resolve_expired(store, interest["id"], choice))
                    st.rerun()
    events = load_signals(store.signals_path)
    with st.expander(f"Stored feedback ({len(events)})"):
        for event in events[-20:]:
            st.markdown(f"- {md(describe(event))}")
    st.subheader("Suggested updates")
    review_section(store)
    history = store.history()
    if history:
        with st.expander(f"Past decisions ({len(history)})"):
            for entry in history[-20:]:
                st.markdown(f"- {entry['time'][:10]} `{entry['decision']}` {md(entry['change'])}")


def show_interest(interest: dict):
    with st.container(border=True):
        st.markdown(f"**{md(interest['label'])}** " + (f"· {md(', '.join(interest['facets']))}"
                                                       if interest.get("facets") else ""))
        if interest["type"] == "long_term":
            term, color = "Long-term", "blue"
        elif is_expired(interest, today()):
            term, color = f"Expired {interest['expires']}", "gray"
        else:
            term, color = f"Short-term until {interest['expires']}", "violet"
        source = "You said this" if interest["source"] == "stated" else "Learned from your feedback"
        st.markdown(f":{color}-badge[{term}] :green-badge[{source}] :gray-badge[weight {interest['weight']}]")
        if interest.get("evidence"):
            with st.expander("Evidence" + (f" · approved by you on {interest['approved_on']}"
                                           if interest.get("approved_on") else "")):
                for line in interest["evidence"]:
                    st.markdown(f"- {md(line)}")


def change_consent(key: str):
    profile = current_profile()
    allowed = st.session_state[f"consent_{key}"]
    deleted = set_consent(profile, memory_store().signals_path, key, allowed)
    save_profile(profile, storage.profile_path())
    note = f" Deleted {deleted} stored events." if deleted else ""
    st.toast(f"{SIGNALS[key]['label']}: {'on' if allowed else 'off'}.{note}")


def review_section(store: MemoryStore):
    worker = st.session_state.get("review_worker")
    if worker is None:
        usable = len(store.usable())
        st.caption(f"{usable} signal(s) you allowed, from the last 30 days. Forager suggests changes only with "
                   f"evidence and changes nothing without your approval.")
        if st.button("Review my feedback (paid)", key="review_start", disabled=usable < MIN_EVIDENCE):
            st.session_state.review_worker = ui_runtime.ReviewWorker(store).start()
            st.rerun()
        return
    pending = worker.pending
    if pending:
        view = pending["view"]
        with st.container(border=True):
            st.markdown(f"**Forager suggests:** {md(view['message'])}")
            st.markdown(f"**Change:** {md(view['change'])}")
            st.markdown("**Evidence, from signals you allowed:**\n" + "\n".join(f"- {md(e)}" for e in view["evidence"]))
            approve, reject = st.columns(2)
            if approve.button("Approve", type="primary", key=f"approve_{pending['token']}"):
                worker.answer(pending["token"], True)
                st.rerun()
            if reject.button("Reject", key=f"reject_{pending['token']}"):
                worker.answer(pending["token"], False)
                st.rerun()
        return
    if worker.running:
        st.info("The memory agent is reviewing your feedback...")
        time.sleep(0.5)
        st.rerun()
    if worker.error:
        st.error(f"The review stopped: {worker.error}. Your profile is unchanged.")
    elif worker.result["status"] == "skipped":
        st.info(worker.result["reason"])
    else:
        st.markdown(md(worker.result["answer"]))
        for entry in worker.result["proposals"]:
            st.markdown(f"- `{entry['decision']}` {md(entry['change'])}")
    if worker.usage:
        st.caption(worker.usage)
    if st.button("Done", key="review_done"):
        del st.session_state.review_worker
        st.rerun()


# ---- Topics (Idea 3) ----

def topics_page():
    st.header("Your topic mix")
    profile = current_profile()
    if profile is None:
        st.info("Set up your interests first (Set up page).")
        return
    days = ui_runtime.week_of(storage.digest_days(), today())
    digests = [storage.load_digest(day) for day in days]
    st.caption(f"Items in your digests from the last 7 days ({len(digests)} digest(s)).")
    distribution = ui_runtime.topic_distribution(digests, profile)
    if distribution:
        st.bar_chart(pd.DataFrame({"items": distribution}), horizontal=True)
        covered = set(distribution)
        missing = [i["label"] for i in active_interests(profile, today())
                   if i["type"] == "long_term" and i["label"] not in covered]
        if missing:
            st.warning("Not covered this week: " + ", ".join(missing))
    else:
        st.info("No digest in the last 7 days yet.")
    st.slider("Exploration share", 0.0, 0.5, float(profile.get("exploration", 0.2)), 0.05, key="exploration",
              on_change=save_setting, args=("exploration",),
              help="About this share of each digest goes to things next to your interests that you did not ask "
                   "for. Forager labels them 'Breadth'.")
    delivery = datetime.strptime(profile.get("delivery_time", "08:00"), "%H:%M").time()
    st.time_input("Daily digest time", delivery, key="delivery_time", on_change=save_setting,
                  args=("delivery_time",), help="Saved with your profile; this prototype does not send digests "
                                                "on a schedule.")


def save_setting(name: str):
    profile = current_profile()
    value = st.session_state[name]
    profile[name] = value.strftime("%H:%M") if name == "delivery_time" else float(value)
    save_profile(profile, storage.profile_path())
    st.toast("Saved.")


# ---- page frame ----

PAGES = {"Digest": digest_page, "Set up": setup_page, "Memory": memory_page, "Topics": topics_page}

st.set_page_config(page_title="Forager", page_icon=":material/eco:", layout="wide")
with st.sidebar:
    st.title("Forager")
    page = st.radio("Go to", list(PAGES), key="page")
    current = current_profile()
    st.caption(f"Profile: {len(current['interests'])} interests" if current else "No profile yet")
    spend = ui_runtime.budget()
    if spend:
        st.caption(f"Course budget used: \\${spend['cost']:.3f} of \\$1.00 ({spend['requests']} requests)")
PAGES[page]()
