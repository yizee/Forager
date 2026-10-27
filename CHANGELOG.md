# Changelog

All notable changes to this project are recorded here, newest first.

## 2026-10-27 (Critic evaluation on the case set)

### Added
- First live evaluation of the Critic: 21 cases x 3 repeats, $0.036. Rules only caught 0/60 problem instances (by construction); rules + Critic caught 45/60 (75%), all with the right problem type, with no false alarms (0/12 control reviews, 0 false-alarm issues). Constructed cases: 45/48 (94%); the real digest `live-01`: 0/12. Write-up for the report: `docs/critic-eval.md`.
- `eval/results/critic-20261027-090328.jsonl` (raw reviews) and `.md` (every review with each issue and the Critic's explanation).
- `eval/analyze_critic_results.py`: turns a run into the tables above, per-case verdicts across repeats, and a listing of every issue raised (on target, debatable or false alarm).

## 2026-10-26 (Critic case set: label audit)

### Fixed
- Critic case labels, after two audits (Claude against every source text, and an independent reviewer agent that saw only the cases and the Critic's definitions; both found the first two items on their own):
  - `live-01` points[7] is now a labeled problem (unsupported_citation): the OLMo-3 study reports the instrumental rate rising from 25.0% to 46.1% before it falls, not "no clear evidence".
  - Base A item n04 was about labeling AI-generated images but was filed under AI copyright policy; it is now a copyright item (training opt-outs). Base B point 3 called dubline open-source, which its source did not say; the source now says so.
  - "GitHub stars" is now "stars" (the source does not say GitHub); FlexPart's numbers are exact (10.5% and 16.6%); UniVOE's summary no longer adds "shadows".
- New debatable refs: points[4] in base-A cases (the point that files p24 under Image generation); p04 and p14 in `live-01`.

### Changed
- The Critic sees each source text in full (`SOURCE_CHARS` 2,000; arXiv abstracts are at most 1,920 characters). Before, 15 of 30 abstracts were cut at 1,500 characters.
- `eval/cases/critic/README.md` has a "Label audit" section with these changes and what was kept on purpose (stretched labels on the `nd-01` duplicates count toward the duplicate problem; SpectralCanary under AI copyright policy stays correct).

## 2026-10-26 (Stage 4: Critic, offline)

### Added
- `forager/critic.py` (Idea 3): an independent Critic agent with its own context. It sees the profile, the brief with refs (`points[i]`, `connections[i]`) and each item's source text, and judges only the five semantic problem types. Its answer (`PASS`/`ADJUST` with typed issues) is checked in code: valid types, refs that exist, each type naming the right kind of thing (e.g. irrelevant exploration only for breadth items, duplicates as groups of two or more); one repair turn.
- Digest pipeline modes, which are also the Idea 3 evaluation conditions: `single` (structure and citations, the Stage 1 baseline), `rules` (plus topic share, coverage and source mix, one repair turn) and `critic` (plus the Critic; on ADJUST the writer revises once and the rules run again; if the revision still breaks a rule, the rule-passing draft is kept).
- `python -m forager digest --mode critic|rules|single` (default `critic`); coverage uses the saved digests of the last 7 days.
- The digest Markdown ends with "How this digest was checked": code rules, uncovered interests and the Critic's issues.
- `eval/run_critic_cases.py`: runs the Critic on the case set (fresh session per review, `--repeats`, cost estimate and confirmation before paid calls), scores it as described in the case README, and prints rules-only next to rules + Critic.
- `tests/test_stage4_critic.py`: 14 offline tests (85 in total), including that the ground truth of every case is itself a valid Critic answer, that the Critic's view contains no ground truth, every pipeline branch, and the scorer.

### Changed
- Writer instructions now state the balance rules and say never to mark an unrelated item as matching an interest just to cover it.
- Coverage is a soft rule: after its repair turn an uncovered interest becomes a warning shown in the digest, not a failure. With some candidate sets it cannot be met honestly, and forcing it would push the writer to mislabel items.
- Digest items keep their source text (`source_text`) so the Critic can check claims against it.

## 2026-10-25 (Stage 4 started: code rules and Critic case set)

### Added
- Stage 4 code rules in `forager/checks.py`: topic share at most 40% (each interest is a bucket, all breadth items one bucket, applied from 5 items), 7-day coverage of every active long-term interest (with digest history), and source-type mix (applies only when two or more source types are available). `check_rules` reports results by rule. Applied to the first live digest, the coverage rule fires: no item covered AI copyright policy.
- `eval/cases/critic/`: 21 cases for the Idea 3 question "does a Critic add value beyond rules?". Every case passes all code rules; 16 contain one semantic problem (irrelevant exploration 3, near-duplicates under different labels 3, citations that do not support the point 4, overstated connections 3, wrong interest labels 3), 4 are controls (2 of them hard negatives), and `live-01` is the unedited first live digest with the problems found in it. Each case is self-contained: profile, digest with each item's source text, and ground truth (verdict, problem type, refs, explanation, debatable refs). The index and proposed scoring are in `eval/cases/critic/README.md`.
- `eval/build_critic_cases.py`: builds the cases from two clean base digests plus one targeted change per case; the build fails if any rule fires or a ground-truth ref does not exist. Papers are real arXiv entries from the snapshot; news and repo items are synthetic (fictional names, example.com links).
- `eval/cases/critic/sources/live-digest-2026-10-25.json`: the first live digest, kept as a fixture.
- Tests (71 in total): the rules; every case passes all rules with valid refs; the validator rejects broken cases; real papers are unaltered; the committed cases match a fresh build; in `ml-03` the wrong label is exactly what satisfies the coverage rule; `live-01` fails coverage without its added history.

## 2026-10-25 (live runs of Stages 1–3)

### Added
- `docs/live-runs.md`: first paid runs of Stages 1–3 with costs ($0.0053 in total), results and observations for the report.
- `pytest.ini`: collect only `tests/`; the course package in `lab/` has its own test suite.

### Fixed
- Onboarding could create two interests with the same label when the clarifier listed a release (e.g. "Sora 2") both as a direction and as a short-term item, as happened in the first live run. A code check now sends it back for repair; `build_profile` and the free-text baseline skip duplicate labels; `validate_profile` rejects them; the `add` edit refuses an existing label.

### Changed
- Clarifier instructions: directions are topics only, never the user's role or preferred format; specific releases belong in `short_term`; adjacent suggestions are topic fields, not source types.
- README roadmap: Stages 1–3 marked done (offline tests and live runs pass).

## 2026-10-25 (Stage 3, offline)

### Added
- `forager/signals.py` (Idea 2): ratings, likes, clicks and reading time. A signal is stored only if the user consented to it, used only while consent is on and from the last 30 days, and withdrawing consent deletes what was collected for that signal.
- `forager/memory.py`: the memory agent proposes profile changes through `propose_profile_update`, declared with `needs_approval=True`; the SDK pauses the run and nothing is written unless the user approves. Code checks every proposal before the user sees it: at least 2 distinct consented signals as evidence, a valid target, no repeat of a change rejected in the last 30 days, at most 3 proposals per review. Blocked proposals are rejected with the reason sent back to the model; the tool body checks again before writing.
- The approval prompt shows a change description and evidence generated by code from the tool arguments and the signal log, next to the agent's message.
- `runtime/proposals.jsonl`: every proposal and its outcome (`approved`, `rejected`, `blocked`, `silent`, expiry decisions), for the Idea 2 evaluation.
- Silent-update baseline: `review --silent-baseline` runs the same agent with `needs_approval=False`.
- Expired short-term interests stop counting in the digest; `review` asks the user to keep them 14 more days, make them long-term or remove them.
- Commands: `consent`, `rate`, `like`, `review`, `profile`; onboarding now ends with the consent step.
- `tests/test_stage3.py`: 20 offline tests through real SDK approval interruptions with scripted replies (38 in total).

### Changed
- `DEFAULT_PROFILE` consent is now all off; nothing is tracked without an explicit opt-in.
- Profile schema: interests can carry `evidence` (copied from the signal log), `approved_on` or `updated_silently_on`, and `origin: "proposal"`.
- The visible profile shows evidence, approval dates, expired short-term interests and which signals are tracked.

## 2026-10-25 (Stage 2, offline)

### Added
- `forager/onboarding.py` (Idea 1): one sentence → the clarifier agent returns 1–5 directions, each with one question and 3–6 options, 1–3 adjacent-field suggestions, and any short-term focus the user explicitly mentioned. Checked in code, one repair turn.
- `build_profile`: the profile is built in code from the user's selections only; options the agent did not offer are ignored, so the model cannot add preferences. Adjacent fields the user accepts get weight 0.5; selected short-term focuses expire after 14 days.
- Free-text baseline (`profile_from_text`, `onboard --baseline`) for the Idea 1 comparison.
- Profile editing (remove, weight, facets, add, short/long, exploration, delivery time) and validation before saving to `runtime/profile.json`.
- `forager/onboarding_cli.py` and `python -m forager onboard`: numbered options in the terminal stand in for clickable ones until the Streamlit UI (Stage 4).
- `forager/jsonagent.py`: shared JSON-answer, code-check and one-repair loop, used by the digest writer and the onboarding agents.
- `tests/test_stage2.py`: 9 offline tests (18 in total).

### Changed
- Profile schema: interests gain `origin` (`clarification`, `suggested`, `free_text`, `manual`); the profile gains `setup` (`method`, `description`, `date`). A new profile starts with every consent signal off until the user opts in (Stage 3).

## 2026-10-25 (plan update)

### Changed
- Roadmap: Stage 4 now starts with a hand-built set of cases where rules are expected to fail (irrelevant exploration items, near-duplicates under different labels, citations that exist but do not support the point), used while developing the Critic rather than only at evaluation time.
- `CLAUDE.md` notes that the report must explain the move of breadth checks from the Critic (proposal) to code rules (response to feedback).

## 2026-10-25 (Stage 1, offline)

### Added
- `forager/sources/arxiv.py`: fetch recent cs.AI / cs.CL / cs.CV papers from the arXiv API; save and load snapshots.
- `forager/digest.py`: single-agent digest writer on the lab connection (`open_lab`, `lab.session`). Candidates get per-digest IDs (`p01`…) and are passed as context; the agent returns JSON; titles and links are attached from source data in code. One repair turn with the exact check errors if a check fails.
- `forager/checks.py`: deterministic checks run in code on every digest (5–8 brief points, every point cites at least one included item, cited IDs exist, reason labels present).
- `forager/render.py`: two-layer Markdown digest; each citation links to the full item's anchor; "why you see this" label per item.
- `forager/profile.py`: default persona profile (AI agents, video editing, image generation) in the CLAUDE.md schema; `runtime/profile.json` overrides it.
- `python -m forager snapshot | digest` command line.
- `data/snapshot/arxiv-2026-10-25.json`: 30 recent arXiv papers for reproducible tests.
- `tests/test_stage1.py`: 9 offline tests with scripted replies (pass, repair, unrepaired failure, checks, parsing).
- `requirements.txt` with the lab's pinned versions.

### Changed
- Application code lives in `forager/` instead of `src/` (matches the CLAUDE.md layout).

## 2026-10-25

### Added
- `CLAUDE.md`: full project brief for handing off to Claude engineering mode (problem and solution, three design ideas, Lab 2 base code and budget constraints, data structure drafts, evaluation plan, staged roadmap with target dates, video outline, working rules, open questions).

### Changed
- `.gitignore` now excludes `.lab-state/`, `runtime/` and `lab/` (course code stays out of the repo while it is public).
- README layout section lists `CLAUDE.md`.

## 2026-10-15

### Added
- Repository set up with README (project overview, three design ideas, staged roadmap, key metrics).
- `docs/proposal.pdf`: submitted one-page proposal.
- `docs/feedback.md`: instructor feedback on the proposal and the planned response.

### Changed (in response to feedback)
- Idea 3 redesigned as rules + Critic: deterministic checks move to code, the Critic handles semantic checks only. Rules-only becomes the main baseline.
- Evaluation narrowed to four key metrics.
- Build plan split into five incremental stages.

## 2026-10-01

### Added
- Project proposal submitted (Forager).
