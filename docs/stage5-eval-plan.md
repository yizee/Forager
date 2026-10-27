# Stage 5 evaluation plan

Plan for the four core metrics in CLAUDE.md §7, written on 2026-10-27 before any
Stage 5 paid call. Costs are planning estimates from the ledger's per-run figures
(`docs/live-runs.md`); every paid script prints its own estimate and asks first.

## Constraints

- **Budget.** The lab's local ledger allows $1 in total for this lab copy and does not
  reset; $0.9087 remains. The course key's OpenRouter limit is $1 a month (resets
  2026-11-01) with $0.9071 left. The local ledger is the binding limit: about $0.90
  for the rest of the project. The plan spends about $0.50 and keeps the rest as a
  reserve for reruns and the demo.
- **Model.** Every agent and every judge is `z-ai/glm-5.3-flash`, the only model the
  lab allows. A judge from the same model as the Critic may share its blind spots, so
  every judge is calibrated against the author's labels (below) and the report says so.
- **Data.** Automated runs use committed snapshots in `data/snapshot/`, never live
  feeds, so results can be reproduced.
- **Time.** The video is due 2026-11-03; results are needed by 11-02.

## Overview

| Idea | Metric | Method | Runs | Paid (est.) | Author time |
| --- | --- | --- | --- | --- | --- |
| 3 | Diversity vs relevance: single, rules, critic | Code statistics + LLM judge of each item | 10 repeats x 3 modes = 30 digests | $0.20 digests + $0.04 judge | — |
| 3 | Citation support of brief points | LLM judge of each point and connection | same 30 digests + 10 reviewed drafts | $0.04 | — |
| 3, 2 | Judge calibration | Author labels a blinded sample | 30 items + 30 brief entries | — | about 45 min |
| 3 | Critic on fresh real digests (optional) | Author labels 3 rules digests first, then the Critic reviews each 3 times | 9 reviews | $0.01 | about 45 min |
| 3 | Author's check of the Critic case-set labels | Pending since 2026-10-26 | — | — | about 30 min |
| 2 | Evidence-backed, approved updates | Scenario cases, approval vs silent baseline; code checks + LLM judge | 8 scenarios x 2 modes x 2 repeats | $0.06 | — |
| 1 | Profile accuracy (1-7) vs free text; think-aloud | User study, 2-3 participants | 2 onboardings, 1 digest, 1 review each | $0.05 | 40 min per participant |
| — | Video material, pilots, retries | — | — | $0.07 | — |
| | **Total** | | | **about $0.47** | |

## Idea 3: diversity vs relevance, and citation support

**Conditions.** single (one writer, structure checks only), rules (Manager and
specialists + code rules), critic (rules + Critic + one revision). Same profile
(`runtime/profile.json`, the demo persona) and same snapshots in every condition.

**Snapshot sets.**
- S1: arXiv 2026-10-25, GitHub and news 2026-10-27 (the set used so far), 6 repeats.
- S2: a fresh fetch on 2026-10-28 or 10-29, committed before any run, 4 repeats. A
  second day keeps the result from depending on one day's candidates.

Runner: `eval/run_digest_modes.py --repeats N --snapshot ...`. Each run is a fresh
session; the critic runs also save the draft the Critic reviewed (`reviewed_draft`).

**Measured in code (free).**
- Diversity: breadth share, largest topic share, normalized entropy over topic
  buckets, number of interests covered today, source types used.
- Rule results, coverage warnings and heading mismatches (all modes measured the same
  way), requests, cost and time.

**LLM judges (new script `eval/judge_digests.py`).** The design follows the Week 6
rubric judge: the judge is separate from the agents, treats the digest as data, answers
each criterion with true/false and a short reason, and code computes the scores. A
malformed judgement gets one repair turn and is otherwise recorded as an error, never as
a pass. Judge inputs are blinded: no mode, writer or "How this digest was checked"
section, items shuffled.

- Item judge, one call per digest. Input: the profile's interests (labels and facets)
  and each item's title, source text, label and stated reason. Criteria per item:
  - `label_correct` (interest items only): the item is about the labelled interest
    itself, not a neighbouring topic.
  - `worth_showing`: given the profile, the user would plausibly want to see it; for a
    breadth item, its stated reason for exploration is true and relevant.
- Brief judge, one call per digest and per reviewed draft. Input: each point and
  connection with the source texts of the items it cites. Criteria:
  - `supported`: every claim is stated in, or follows directly from, the cited sources.
  - `not_overstated` (connections only): the cross-field link is no stronger than the
    sources allow.

**Calibration.** Before seeing any judge output, the author labels a blinded sample of
30 items and 30 brief entries, stratified across the three modes and including
reviewed drafts. A script makes the sheet (CSV with the source texts) and scores it
afterwards: percent agreement and Cohen's kappa per criterion. With kappa of at least
0.6 the judge is used for the full set; below that, the author-labelled sample is the
primary result and the judge is reported as secondary.

**Analysis.** Per mode: mean and bootstrap 95% CI over digests for label accuracy,
worth-showing rate, support rate, breadth share and entropy. Critic minus rules with a
CI. Within critic runs, reviewed draft vs final digest (paired). Figure: one point per
digest, diversity on x and worth-showing rate on y, coloured by mode.

**What answers the instructor's question.** Rules alone are 0 by construction on the
case set; here the comparison is end to end: does adding the Critic raise label
accuracy and support without lowering breadth? A null or negative result is reported as
it is.

**Optional: the Critic on fresh real digests.** The case set overstates the Critic on
real digests (94% on constructed cases, 0 of 12 on `live-01`). The author labels three
rules-mode digests from the runs above with the case-set scheme (types and refs, see
`eval/cases/critic/README.md`) before any review; the Critic then reviews each three
times. These labels also count toward the calibration sample.

**Author's check of the case-set labels.** The 20 labelled problems were written by
Claude and audited twice, but the author has not checked them. Agreement between
Claude's labels and the author's is reportable either way.

## Idea 2: evidence-backed updates that wait for approval

**Scenario cases (new `eval/run_memory_cases.py`).** Each case is a profile plus a
signal log, run in a temporary runtime folder:

1. Strong evidence: several 5/5 ratings and likes on one interest's items.
2. Weak evidence: a single 5/5 rating.
3. Unconsented signals only: consent switched off for the signal type in the log.
4. Mixed evidence: high and low ratings on the same topic.
5. Mislabelled evidence: high ratings on items labelled Sora 2 that are about video
   generation in general (the Stage 1 finding).
6. A change the user rejected within 30 days.
7. Negative evidence: low ratings on one interest.
8. An expired short-term interest.

**Conditions.** Approval mode (`review`; a scripted user approves every proposal that
reaches it, the worst case for approval) and the silent baseline
(`review --silent-baseline`). Code applies the same evidence checks in both; the
difference is whether the user sees and approves the change before it is written.

**Measures.**
- Code: updates written without approval (silent: all; approval: none, enforced by the
  SDK); proposals blocked by code and why; unconsented signals used (expected none in
  both).
- Judge, per proposal: `evidence_supports_change` (the evidence items' titles and texts
  justify the change) and `message_matches_change` (the agent's wording matches the
  code-generated change and evidence, with no overclaiming).
- Pass rate as defined in CLAUDE.md §7: a proposal passes when it has at least two
  consented signals, is written only after approval, and the judge accepts both
  criteria. Silent updates fail the approval part by construction, which the report
  states; the informative part is how many silent updates the judge finds unjustified
  (scenario 5 especially), i.e. changes a user would never have seen.
- Link to the user study: task 2 below shows each participant one proposal built on
  mislabelled evidence and records whether they notice it from the evidence shown.

## Idea 1: profile accuracy, and the think-aloud study

**Participants.** Two or three people who follow AI news (classmates are fine).
Verbal consent; no names in the notes; each participant gets a fresh
`FORAGER_RUNTIME_DIR` (for example `runtime/study/P1`, not committed).

**Within-subject, counterbalanced.** Each participant writes one sentence about what
they follow and sets up a profile twice in the Streamlit app: clarification (option
questions) and the free-text baseline (the Setup page's study toggle). Order alternates
between participants.

**Measures.** For each profile: accuracy rating 1-7 ("This profile describes what I
want to follow"), the number of edits needed to make it right, and time on task. With
n = 2-3 the results are descriptive only.

**Think-aloud tasks** (on the clarification profile):
1. Set up the profile from scratch (above).
2. Review a preference-update proposal, including one built on mislabelled evidence.
3. Find out why an item appears in the digest and correct a recommendation they do
   not want.

Notes keep observations (what the participant did and said) apart from
interpretations, as CLAUDE.md §7 asks.

## Budget control

- Before each paid batch: `cd lab && ../.venv/bin/python agent.py --check`.
- Each script prints an estimate and asks before spending; batches run one at a time.
- Stop a batch if its recorded cost passes 1.5 times its estimate.
- Keep at least $0.25 unspent until the video is recorded.

## Schedule

| Date | Work |
| --- | --- |
| Wed 10-28 | Offline: judge, labelling and memory-case scripts with offline tests; fetch and commit S2. Then, with approval, the 30 digest runs (about $0.20). |
| Thu 10-29 | Author: calibration labels, optional fresh Critic labels, case-set check. Then the judges, the optional Critic reviews and the Idea 2 scenarios (about $0.15). |
| Fri 10-30 to Sun 11-01 | User study sessions (about $0.05); record video material. |
| Sun 11-01 to Mon 11-02 | Analysis and figures; video script and recording. |
| Tue 11-03 | Submit the video; then the report. |

## Risks

- **arXiv answers 429** (it did on 10-27): fetch S2 early; if arXiv still fails,
  S2 reuses the 10-25 papers with fresh GitHub and news, and the report says so.
- **The Manager's output limit**: answers are now about 950 tokens, but a cut-off is
  still possible; the rewrite from notes covers it and is recorded.
- **Same-model judge**: calibration against the author's labels; criteria phrased
  differently from the Critic's instructions; the judge never sees the condition.
- **Small samples**: 10 digests per mode and 2-3 participants. Report intervals and
  effect sizes, not significance claims.
- **Participants unavailable**: the think-aloud can drop to two people; Idea 1's
  accuracy result is then reported as a pilot.

## Open decisions

1. Approve the overall budget (about $0.47 of $0.90) and the first paid batch.
2. Whether to add the second snapshot set (recommended).
3. Who the 2-3 participants are, and when.
4. Whether the author has time for the optional fresh Critic labels (about 45 min).
