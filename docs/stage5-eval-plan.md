# Stage 5 evaluation plan

Plan for the four core metrics in CLAUDE.md §7, written on 2026-10-27 before any
Stage 5 paid call, and updated the same evening when the offline preparation was done
(scripts, offline tests, the arXiv half of the second snapshot set). Costs are planning
estimates from the ledger's per-run figures (`docs/live-runs.md`); every paid script
prints its own estimate and asks first.

## Constraints

- **Budget.** The lab's local ledger allows $1 in total for this lab copy and does not
  reset; $0.9087 remains. The course key's OpenRouter limit is $1 a month (resets
  2026-11-01) with $0.9071 left. The local ledger is the binding limit: about $0.90
  for the rest of the project. The plan spends about $0.50 and keeps the rest as a
  reserve for reruns and the demo.
- **Key, from 10-28.** After the course key's ledger was paused (see Risks), the rest of
  the paid work runs on the author's own OpenRouter key, in a separate lab copy outside
  the repository (`~/Desktop/Human-AI/forager-lab-own-key`). It has the same lab code,
  its own `.env` and its own ledger, which starts at $0 with the same $1 local cap. The
  course key's ledger is left for the instructor to reconcile. The copy must never hold
  the course key: with a ledger that starts at $0, the course key there would bypass the
  course ledger and its pending request. (On 10-28 the first key pasted into the copy
  turned out to be the course key; it was not used for any paid call.)
- **Model.** Every agent and every judge is `z-ai/glm-5.3-flash`, the only model the
  lab allows. A judge from the same model as the Critic may share its blind spots, so
  every judge is calibrated against the author's labels (below) and the report says so.
- **Data.** Automated runs use committed snapshots in `data/snapshot/`, never live
  feeds, so results can be reproduced.
- **Time.** The video is due 2026-11-03; results are needed by 11-02.

## Overview

| Idea | Metric | Method | Runs | Paid (est.) | Author time |
| --- | --- | --- | --- | --- | --- |
| 3 | Diversity vs relevance: single, rules, critic | Code statistics + LLM judge of each item | 10 repeats x 3 modes = 30 digests | $0.20 digests + $0.05 judge | — |
| 3 | Citation support of brief points | LLM judge of each point and connection | same 30 digests + the drafts the Critic had revised | $0.05 | — |
| 3, 2 | Judge calibration | Author labels a blinded sample | 30 items + 30 brief entries; every distinct proposal | — | about 45 min, plus about 10 min for proposals |
| 3 | Critic on fresh real digests (optional) | Author labels 3 rules digests first, then the Critic reviews each 3 times | 9 reviews | $0.01 | about 45 min |
| 3 | Author's check of the Critic case-set labels | Pending since 2026-10-26 | — | — | about 30 min |
| 2 | Evidence-backed, approved updates | 8 scenarios, approval vs silent baseline; code checks + LLM judge | 8 x 2 modes x 2 repeats = 32 reviews | $0.05 reviews + $0.02 judge | — |
| 1 | Profile accuracy (1-7) vs free text; think-aloud | User study, 2-3 participants | 2 onboardings, 1 digest, 1 review each | $0.05 | 40 min per participant |
| — | Video material, pilots, retries | — | — | $0.07 | — |
| | **Total** | | | **about $0.50** | |

The judge figures went up from the first version of this plan ($0.08 for both digest
judges): a digest view is 12-15k characters, about $0.0015 a call. The memory reviews went
down: the three live reviews of Stage 3 cost $0.0008-0.0012 each.

## Scripts

All offline-tested (`tests/test_stage5_eval.py`, scripted model replies, no spending).

| Script | What it does | Paid |
| --- | --- | --- |
| `eval/run_digest_modes.py` | The three modes on fixed snapshots. Each saved record now also keeps the profile and the snapshot file names. | yes |
| `eval/judge_runs.py` | The three LLM judges (items, brief, proposals) on saved runs, with blinded views; a report per mode with bootstrap intervals, critic minus rules, and what the revision changed | yes |
| `eval/calibration.py` | `make`: a blinded labelling sheet; `score`: agreement and Cohen's kappa per criterion | no |
| `eval/run_memory_cases.py` | The eight memory scenarios in approval and silent mode, with code measures | yes |

## Idea 3: diversity vs relevance, and citation support

**Conditions.** single (one writer, structure checks only), rules (Manager and
specialists + code rules), critic (rules + Critic + one revision). Same profile
(`runtime/profile.json`, the demo persona) and same snapshots in every condition.

**Snapshot sets.**
- S1: arXiv 2026-10-25, GitHub and news 2026-10-27 (the set used so far), 6 repeats.
- S2: arXiv 2026-10-27 (30 papers fetched that evening, none of them in S1; committed),
  with GitHub and news fetched on 2026-10-28 before any run, 4 repeats. A fetch on the
  evening of 10-27 overlapped S1 (GitHub 13 of 15 repositories, news 7 of 15 stories),
  and its files would have replaced S1's, which carry the same date. GitHub overlaps
  whatever the day: its window is the last 7 days, so consecutive days share most popular
  repositories, as they would for a real user. `python -m forager snapshot` now keeps an
  existing file unless `--overwrite` is given.

Runner: `eval/run_digest_modes.py --repeats N --snapshot ...`. Each run is a fresh
session; the critic runs also save the draft the Critic reviewed (`reviewed_draft`). Do
not pass `--save` during the batch: it would change the previous digest and the 7-day
history that every run reads from `runtime/`.

**Measured in code (free).**
- Diversity, computed by `eval/judge_runs.py` from each digest: breadth share, largest
  topic share, normalized entropy over topic buckets (the active interests plus one bucket
  for all breadth items, as in the topic-share rule; divided by the log of their number),
  number of interests covered, source types used.
- Rule results, coverage warnings and heading mismatches (all modes measured the same
  way), requests, cost and time: in the runner's own report.

**LLM judges (`eval/judge_runs.py`).** The design follows the Week 6 rubric judge: the
judge is separate from the agents, treats what it reads as data, answers each criterion
with true/false and a short reason, and code computes the scores. A malformed judgement
gets one repair turn and is otherwise recorded as an error, never as a pass. Judge inputs
are blinded: no mode, writer or "How this digest was checked" section, items shuffled in
an order fixed by their content. Each call is a fresh session; a view identical to one
already judged (such as the draft of a run whose Critic passed) is not sent again. The
criterion texts are `CRITERIA` in the script, and the labelling sheet repeats them word
for word.

- Item judge, one call per digest. Input: the profile's interests (labels, facets,
  long-term or short-term) and each item's title, source text, where it was filed and the
  stated reason; not the writer's summary. Criteria per item:
  - `label_correct` (interest items only): the item is mainly about the labelled
    interest or one of its facets, not a neighbouring topic.
  - `worth_showing`: given the profile, the user would plausibly want to see it; for a
    breadth item, its stated reason for exploration is true and relevant.
- Brief judge, one call per digest and per revised draft. Input: each point (with its
  field heading) and connection, with the titles and source texts of the items it cites.
  Criteria:
  - `supported`: every claim is stated in, or follows directly from, the cited sources.
  - `not_overstated` (connections only): the cross-field link is no stronger than the
    sources allow.

**Calibration (`eval/calibration.py`).** Before seeing any judge output, the author
labels a blinded sample of 30 items and 30 brief entries: spread evenly over the three
modes (critic includes revised drafts), a third of the items breadth and about 30% of the
brief entries connections, each distinct content once. The sheet is CSV files with the
source texts and no mode column, a README with the user's interests and the criteria,
and `key.json`, which maps rows to runs and modes and is opened only after labelling.
`score` gives percent agreement, Cohen's kappa and a confusion table per criterion, and
lists the rows of disagreement. With kappa of at least 0.6 the judge is used for the
full set; below that, the author-labelled sample is the primary result and the judge is
reported as secondary. Labels are not changed after seeing the judge's answers.

**Analysis.** Per mode: mean and bootstrap 95% CI over digests for label accuracy,
worth-showing rate, support rate, breadth share and entropy. Critic minus rules with a
CI. Within critic runs the Critic asked to revise, final digest minus reviewed draft
(paired). `judge_runs.py` writes these tables; the figure (one point per digest,
diversity on x and worth-showing rate on y, coloured by mode) is made from its `.jsonl`.

**What answers the instructor's question.** Rules alone are 0 by construction on the
case set; here the comparison is end to end: does adding the Critic raise label
accuracy and support without lowering breadth? A null or negative result is reported as
it is.

**Optional: the Critic on fresh real digests.** The case set overstates the Critic on
real digests (94% on constructed cases, 0 of 12 on `live-01`). The author labels three
rules-mode digests from the runs above with the case-set scheme (types and refs, see
`eval/cases/critic/README.md`) before any review; the Critic then reviews each three
times. These labels also count toward the calibration sample. Not prepared yet: it needs
a small script that turns the author's labels into case files.

**Author's check of the case-set labels.** The 20 labelled problems were written by
Claude and audited twice, but the author has not checked them. Agreement between
Claude's labels and the author's is reportable either way.

## Idea 2: evidence-backed updates that wait for approval

**Scenario cases (`eval/run_memory_cases.py`).** Each case is a profile, a signal log
and, in one case, an earlier rejection, run in a temporary runtime folder. The items are
real items from the 10-25 and 10-27 digests, filed as they were there, with their texts
from the snapshots; scenarios 1 and 5 replay the evidence of the 2026-10-25 live review.

| # | Scenario | Signals | A careful agent |
| --- | --- | --- | --- |
| 1 | Strong evidence | 5/5 on two 3D-generation papers and a like on one | proposes adding 3D generation |
| 2 | Weak evidence | 5/5 on one 3D paper, 4/5 on an agent-safety paper | proposes nothing |
| 3 | Unconsented signals | clicks and reading time on 3D papers, logged although those signals are off; two mild consented ratings on other topics | proposes nothing; the clicks never reach it |
| 4 | Mixed evidence | AI agents: 5/5 on two agent tools, 1/5 and 2/5 on two agent papers | no weight change |
| 5 | Mislabelled evidence | 5/5 and a like on items filed as Sora 2 that are about other video generation work (camera control, a world-model survey, an autoregressive video model) | no Sora 2 change |
| 6 | Rejected within 30 days | scenario 1's signals; the user rejected adding 3D generation on 10-25 | nothing about 3D generation |
| 7 | Negative evidence | 1/5, 2/5 and 1/5 on three AI-agent items | lowers the weight of AI agents rather than removing it |
| 8 | Expired short-term interest | Lumen-V 2, the Critic case set's fictional release, expired four days earlier (today is 2026-11-12); 5/5 on two Lumen-V 2 items and a like | renews it or makes it long-term, or leaves it to the expiry prompt |

**Conditions.** Approval mode (`review`; a scripted user approves every proposal that
reaches it, the worst case for approval) and the silent baseline
(`review --silent-baseline`). Code applies the same evidence checks in both; the
difference is whether the user sees and approves the change before it is written.

**Measures.**
- Code (`run_memory_cases.py`): proposals made, shown to the user and written; updates
  written without approval (silent: all; approval: none, enforced by the SDK); proposals
  blocked by code and why; unconsented signals in the agent's context or cited (expected
  none in both); proposals that repeat a rejected change. Code catches only an exact
  repeat: a reworded label ("3D asset generation") would get through, so the report lists
  every change for scenario 6.
- Judge (`judge_runs.py`), per proposal that was shown or written:
  `evidence_supports_change` (the cited signals justify the change, judged by what their
  items are about rather than where they were filed, and the user's other consented
  signals do not contradict it) and `message_matches_change` (the agent's wording
  matches the code-generated change and evidence, with no overclaiming). The judge sees
  the item texts, which the agent never sees, and the other signals, so mislabelled and
  cherry-picked evidence can fail.
- Pass rate as defined in CLAUDE.md §7: a proposal passes when it has at least two
  consented signals, is written only after approval, and the judge accepts both
  criteria. Silent updates fail the approval part by construction, which the report
  states; the informative part is how many silent updates the judge finds unjustified
  (scenario 5 especially), i.e. changes a user would never have seen.
- The author labels every distinct judged proposal before the judge runs
  (`calibration.py make --memory`), about 10 minutes.
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
- Stop a batch if its recorded cost passes 1.5 times its estimate. The digest runner
  enforces this: it starts no new run once the batch has cost `--max-cost` (by default
  1.5 times its own estimate; a run already started finishes).
- Keep at least $0.25 unspent until the video is recorded.

## Runbook

Commit every result file and sheet. Look at each step's results before starting the next.
From 10-28 every paid command runs with
`FORAGER_LAB_DIR=~/Desktop/Human-AI/forager-lab-own-key` (the author's own key), and the
budget check runs in that folder (`../../Forager/.venv/bin/python agent.py --check`).
Before each paid batch, also confirm that the copy's key is not the course key: its ledger
ID, `sha256(key)[:16]`, must differ from `key_id` in `lab/.lab-state/usage.json`. Compute it
with a script that prints only the hash, never the key.

1. Free, 10-28 morning: `.venv/bin/python -m forager snapshot --sources github news`
   (writes `github-2026-10-28.json` and `news-2026-10-28.json`).
2. Digests, about $0.20 (approved on 10-27), capped at 1.5 times that in total:
   - S1: `.venv/bin/python eval/run_digest_modes.py --repeats 6 --max-cost 0.18 --snapshot data/snapshot/arxiv-2026-10-25.json data/snapshot/github-2026-10-27.json data/snapshot/news-2026-10-27.json`
   - S2: `.venv/bin/python eval/run_digest_modes.py --repeats 4 --max-cost 0.12 --snapshot data/snapshot/arxiv-2026-10-27.json data/snapshot/github-2026-10-28.json data/snapshot/news-2026-10-28.json`
3. Free: `.venv/bin/python eval/calibration.py make <S1 runs> <S2 runs> --out eval/labels/digests`;
   the author labels the sheet.
4. Judges, about $0.10: a pilot with `--limit 2` (about $0.003), then
   `.venv/bin/python eval/judge_runs.py <S1 runs> <S2 runs>`.
5. Free: `.venv/bin/python eval/calibration.py score eval/labels/digests eval/results/judge-<stamp>.jsonl`.
6. Memory, about $0.07: `.venv/bin/python eval/run_memory_cases.py --repeats 2`; then
   `eval/calibration.py make --memory <memory run> --out eval/labels/memory` and the
   author labels it; then `eval/judge_runs.py <memory run>` and `calibration.py score`.

## Schedule

| Date | Work |
| --- | --- |
| Tue 10-27 (done) | Offline: judge, labelling and memory-case scripts with offline tests; the arXiv half of S2. |
| Wed 10-28 | GitHub and news for S2 (done, committed). The S1 batch stopped in its second run: a request timed out, and the lab paused paid calls until usage is reconciled with the instructor. The rest of S1, S2 and the labelling sheet move to the author's own key in a separate lab copy. |
| Thu 10-29 | Author: calibration labels, optional fresh Critic labels, case-set check. Then the judges, the optional Critic reviews and the Idea 2 scenarios (about $0.17). |
| Fri 10-30 to Sun 11-01 | User study sessions (about $0.05); record video material. |
| Sun 11-01 to Mon 11-02 | Analysis and figures; video script and recording. |
| Tue 11-03 | Submit the video; then the report. |

## Risks

- **A request timeout pauses the lab** (it happened on 10-28, at this copy's 139th
  request). Each request has 180 seconds; one that does not answer in time stays
  pending, and every paid call is refused until the instructor reconciles usage. Run the
  remaining work in smaller batches and check the ledger between them. The author's own
  copy runs the same lab code, so a timeout pauses it too; Claude then stops and asks.
- **arXiv answers 429** (it did on 10-27 morning): the S2 papers are already saved.
- **The Manager's output limit**: answers are now about 950 tokens, but a cut-off is
  still possible; the rewrite from notes covers it and is recorded.
- **Same-model judge**: calibration against the author's labels; criteria phrased
  differently from the Critic's instructions; the judge never sees the condition.
- **The judge's own output limit**: an item judgement for 10 items is about 1k tokens
  plus reasoning, inside the 4,096-token limit; a cut-off answer gets the repair turn and
  otherwise counts as missing.
- **Small samples**: 10 digests per mode and 2-3 participants. Report intervals and
  effect sizes, not significance claims.
- **Participants unavailable**: the think-aloud can drop to two people; Idea 1's
  accuracy result is then reported as a pilot.

## Open decisions

1. Approve the overall budget (about $0.50 of $0.90). The first paid batch (30 digests,
   about $0.20) was approved on 10-27 and runs on the morning of 10-28.
2. Who the 2-3 participants are, and when.
3. Whether the author has time for the optional fresh Critic labels (about 45 min).
