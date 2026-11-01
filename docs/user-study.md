# User study: Idea 1 accuracy and think-aloud

This study fills the report's open parts: the last sentence of "Findings in brief" (§1), §6.4 and Table 4.
It follows the plan in `docs/stage5-eval-plan.md` (Idea 1 section). One session takes about 35 minutes.

| Part | What the participant does | Minutes | Measures |
| --- | --- | --: | --- |
| 0 | Consent, think-aloud warm-up | 4 | |
| 1 | Sets up a profile twice: clarification (C) and free text (F), order alternating | 15 | Accuracy 1–7 per profile; edits and time (logged by the app) |
| 2 | Reviews two proposed profile changes, one built on mislabelled evidence | 5 | Approve or reject each; what they looked at |
| 3 | Finds why a digest item appears and tries to see fewer like it | 8 | What they find and try |
| 4 | Debrief questions | 3 | Answers, verbatim where possible |

## Participants

Two or three people who follow AI news, papers or tools. Aim for different kinds of reader, so the
profiles differ and the clarification questions are tested on more than one kind of interest:

- someone who mainly reads **papers** (for example a research student);
- someone who mainly **builds with open-source tools** (for example a developer);
- someone who mainly follows **industry news and products** (for example a business or design student).

Not the author, and not someone who has seen the app or the demo video. The author may do one dry run
first (not counted) to check the setup and timing.

Order of the two setups: P1 C then F, P2 F then C, P3 C then F.

## Before the first session (researcher)

1. Offline tests pass: `.venv/bin/python -m pytest -q`.
2. The lab copy has budget left: in `~/Desktop/Human-AI/forager-lab-own-key`, run
   `../../Forager/.venv/bin/python agent.py --check`. A session makes about 12 model requests
   (two setups and one digest), well under a cent.
3. Copy `eval/study/ratings-template.csv` to `eval/study/ratings.csv`.
4. Print this file's record sheet (end of this file), one per participant.
5. In a second browser tab, open `showcase/index.html#interests` in English. Reload it before each
   participant so no decision from the last session shows. Do not show the other showcase pages,
   especially Evaluation, which states the study's expected result.

## Session script

Say the quoted parts in your own words but keep their meaning; use English or Chinese, whichever the
participant prefers. Do not explain the design ideas, and do not help unless the participant is stuck
for more than a minute (note it if you do).

### 0. Consent and warm-up (4 min)

> "Thanks for helping. I'm testing a prototype called Forager, which builds a daily brief of AI news,
> papers and open-source projects. I'm testing the app, not you; there are no wrong answers. It takes
> about 35 minutes. I'll write notes but not your name. With your permission I'll also record audio,
> only to check my notes, and delete it afterwards. You can stop at any time. Is that OK?"

Note the answer (consent yes/no, audio yes/no) on the record sheet.

> "While you use it, please think aloud: say what you're looking at, what you expect and what you're
> trying to do. To practise, tell me out loud how you would find what time a café near here opens."

During the tasks the only prompts are neutral ones: "What is on your mind?", "Keep talking", "What are
you looking for?" Never say whether something is right.

### 1. Setting up a profile, twice (15 min)

Ask first, before any app is open:

> "In one sentence, describe yourself and what you'd want a daily AI brief to follow."

Write the sentence on the record sheet. The participant uses the same sentence in both setups (they may
copy it).

**First setup.** Start the app for this participant and condition, in a terminal:

```bash
eval/study_app.sh P1 clarification
```

or `eval/study_app.sh P1 free_text`. It opens `http://localhost:8501`. Go to **Set up**. For free text,
turn on the toggle "Study baseline: build the profile straight from this sentence, without questions"
before handing over; for clarification leave it off.

> "Please enter your sentence and set up your profile. Then answer any questions the app asks."

When the profile table appears (in clarification after "Build my profile", in free text right after
"Continue"), and **before** the participant edits anything, ask:

> "Looking at this profile as it is now: how much do you agree with 'This profile describes what I
> want to follow'? 1 is strongly disagree, 7 is strongly agree."

Write the number down, then:

> "Now change anything you want until it's right, and save it."

They may also set the consent switches and the exploration slider; that is not counted as editing.
The app logs the profile as built, as saved, and the time spent (without the wait for the model).

**Second setup.** Stop the app (Ctrl+C in the terminal), start it for the other condition, and repeat
the same steps with the same sentence.

**For part 3**, the app must run in the clarification folder. If the second setup was free text, stop
the app and start `eval/study_app.sh P1 clarification` again. On **Digest**, leave the defaults and
click **Make digest**; it takes about a minute, so start it now and go to part 2 meanwhile.

### 2. Two proposed changes (5 min)

Switch to the showcase tab (Interests page).

> "This is the profile of another user, an AI student who follows AI agents, video editing and image
> generation and has recently been following Sora 2. Based on their ratings, the app suggests two
> changes. Imagine this is your profile: decide for each whether you would approve it or reject it."

Do not point at the evidence. Note for each proposal: the decision, and whether the participant read
or mentioned the evidence items (and what they said about them). The "Make Sora 2 a long-term
interest" proposal is the mislabelled one: its rated items are about camera control, a video
world-model survey and a video model, not Sora 2. Record "yes" in `rejected_mislabelled` only if
they reject it.

### 3. Why is this here? (8 min)

Back in the app, on the digest just made (the participant's own clarification profile).

> "This is today's brief built from your profile. Pick one item you would rather not see. Find out
> why Forager shows it to you, then do whatever you would do so that you see fewer items like it."

Observe where they look (the label "Interest match" or "Breadth", "Why you see this", the brief's
headings, the Memory or Topics page) and what they try (rating it low, the exploration slider, editing
interests, giving up). Note what they expected to find and did not. There is no single correct answer;
whatever they try, or cannot find, is the data.

### 4. Debrief (3 min)

1. "Of the two ways to set up your profile, which would you use, and why?"
2. "Did anything in the profiles surprise you?"
3. "In the two suggestions, what did you look at to decide?"
4. "Was there anything in the brief that made you trust it more, or less?"

> "Thank you. That's everything."

## After each session

- Fill the participant's row in `eval/study/ratings.csv`: `accuracy_clarification`,
  `accuracy_free_text` (the numbers given before editing), `rejected_mislabelled` and `approved_other`
  (yes/no), `preferred_setup` (C, F or none).
- Type up the record sheet the same day, keeping observations and interpretations in separate columns.
  Delete the audio once the notes are checked.
- The app's data stays in `runtime/study/` (not committed); it includes the participant's sentence.

## After all sessions

```bash
.venv/bin/python eval/study_summary.py
```

It prints Table 4 (accuracy, edits and time for each setup, and the proposal decision), medians and
the kind of each edit, and warns if a setup was not saved or ran in the wrong mode. Then, in the report
doc's English tab:

- §6.4: check the first paragraph against what was actually done (n, order, anything changed), fill
  Table 4 with the printed rows, and replace the observations placeholder with 3–4 sentences, marking
  interpretations as such.
- §1 Findings in brief: one sentence on clarification versus free text, with n.

Then export the English tab to `report/report.md` and run `report/build.py` (main body must stay within
6 pages).

---

## Record sheet (one per participant)

Participant: P__ Date: ______ Order: C→F / F→C Consent: yes / no Audio: yes / no

Sentence: ________________________________________________________________

| | Clarification (C) | Free text (F) |
| --- | --- | --- |
| Accuracy before editing (1–7) | | |
| Started at (clock) | | |

| Task | Observation: what they did and said | Interpretation (mark as such) |
| --- | --- | --- |
| 1 C: questions and options | | |
| 1 C: editing the table | | |
| 1 F: editing the table | | |
| 2 Proposal "Sora 2 long-term" (first): approve / reject | | |
| 2 Proposal "Video generation" (second): approve / reject | | |
| 3 Item chosen; where they looked | | |
| 3 What they tried to see fewer | | |
| 4 Debrief answers | | |
| Help given (when, what) | | |
