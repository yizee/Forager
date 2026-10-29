# Changelog

All notable changes to this project are recorded here, newest first.

## 2026-10-29 (Stage 5 results and judge calibration)

### Added
- `docs/stage5-results.md`: judge calibration, the three digest modes (Idea 3), approval versus silent updates (Idea 2), limitations, and what goes into the video and the report.
- `eval/labels/digests/agreement.md` and `eval/labels/memory/agreement.md`: agreement and kappa for each criterion. The author reviewed all 125 draft labels and changed none.
- `calibration.py score` now also lists, for each criterion and mode, how many rows pass by the labels and by the judge (`by_mode`). Rows from a draft the Critic reviewed are counted separately from final digests.

### Changed
- `CLAUDE.md`, `README.md` and `docs/stage5-eval-plan.md` point to the results. Three judges fall below the plan's kappa of 0.6: brief support (0.17), connections (0.14) and proposal evidence (0.27). For those criteria the reference labels are the result.

## 2026-10-29 (Draft calibration labels for the author to check)

### Added
- `eval/calibration.py draft`: pre-fills a labelling sheet with another annotator's labels, puts the reason for each in `note`, and keeps the draft in `draft-labels.json`. `score` then also reports how many draft labels the author changed. One offline test (131 in all).
- Draft labels in both sheets: 125 labels (`items.csv` 50, `brief.csv` 39, `proposals.csv` 36), 29 of them marked unsure. Each CSV was labelled by a fresh Claude agent (Opus 5.5) that saw only a copy of that CSV and its README in a scratch folder. The agents saw no `key.json`, no judge results and nothing else in the repo.

### Changed
- The calibration labels are now drafted by Claude and checked row by row by the author (the author's decision, to save time). The report will say so and give the number of labels the author changed. `docs/stage5-eval-plan.md`, `CLAUDE.md` and `README.md` describe the method and its limitation: pre-filled labels pull the reviewer towards agreeing.

## 2026-10-28 (Judges and memory scenarios run)

### Added
- `eval/results/judge-20261028-162830.jsonl` and `.md`: the judges on the 30 digests (76 judgements in 63 calls, no errors, $0.0671). `judge-20261028-162727.*` is the two-judgement pilot ($0.0020).
- `eval/results/memory-20261028-163542.jsonl` and `.md`: the eight memory scenarios, in approval and silent mode, twice each (32 reviews, no errors, $0.0160).
- `eval/results/judge-20261028-163754.jsonl` and `.md`: the judges on the 18 proposals those runs showed or wrote ($0.0061).
- `eval/labels/memory`: the blind labelling sheet for the 18 proposals. The results are summarized only after the author has labelled both sheets, so the labels stay blind.

## 2026-10-28 (The Idea 3 evaluation set: S1 and S2 on the new repair step)

### Added
- `eval/results/digest-modes-20261028-151959.jsonl` and `.md` (S1, 18 runs, $0.0349) and `eval/results/digest-modes-20261028-152801.jsonl` and `.md` (S2, 12 runs, $0.0270): the 30 digests the judges will rate.
  - Team drafts that still broke a hard rule after their repair fell from 37% (10 of 27, before the change) to 15% (3 of 20).
  - The Critic ran in 8 of 10 critic runs and asked for 3 revisions, all of which passed the rules.
- `eval/labels/digests`: the blind labelling sheet for judge calibration, with 30 items and 30 brief entries spread evenly over the modes.
- `docs/live-runs.md`: a section on these runs and the repair change's effect.

## 2026-10-28 (Repair turns keep the topic balance in view)

### Changed
- In the rule modes, every repair turn now ends with a "Balance now" line: how many items the digest has, the most any topic may have, and each topic's count. This is `balance_note` in `forager/checks.py`, passed to `ask_json` as a hint, so it is neither a problem nor logged. In the 10-28 runs, most failed repairs fixed one problem and pushed a topic over 40%.
- With the team writer, a repair turn asks for an uncovered interest only if a specialist matched some candidate to it (`Team.matched`). Otherwise there is no honest fix, and the gap stays a warning in the digest. `check_coverage` is split into `uncovered_interests` and `coverage_message`.

### Added
- Two offline tests for these changes (130 in all).

## 2026-10-28 (Ledgers reconciled; S1 re-run with the snapshot date)

### Added
- `eval/results/digest-modes-20261028-144428.jsonl` and `.md`: S1 again with `--today 2026-10-27`, 18 runs for $0.0350. No star count differs from the snapshot now. After one repair, single passed the hard rules 6/6, rules 2/6 and critic 4/6.
- `docs/live-runs.md`: how the two paused ledgers were reconciled, and the S1 re-run.

### Changed
- The course key is now the project's key (the author's decision: the labs are over). Paused ledgers are reconciled without the instructor, from OpenRouter's own numbers. The author runs the reconciliation, which keeps a backup and a record in `.lab-state/reconciliations.jsonl`. `CLAUDE.md` and the plan describe it.

## 2026-10-28 (Stage 5 digests: S1 and part of S2, then paused again)

### Added
- `eval/results/digest-modes-20261028-135519.jsonl` and `.md`: S1 in full, 18 runs for $0.0397. Single 6/6, rules 6/6 and critic 3/6 passed the hard rules. The Critic ran in 3 runs and asked for a revision each time.
- `eval/results/digest-modes-20261028-142057.jsonl` and `.md`: 5 of S2's 12 runs for $0.0128. The batch stopped when a response came back without usage and the lab paused paid calls.
- `docs/live-runs.md`: a section on both batches, covering hard rules that still failed after one repair, a date mismatch in S1, what the Critic caught and the second pause.

### Changed
- The batch ran on the course key in the lab copy, by the author's decision, without waiting for the instructor to reconcile the morning's pending request. `CLAUDE.md` and `docs/stage5-eval-plan.md` record this, and the rule that the copy must not hold the course key is withdrawn.
- Runbook: each batch passes `--today`, the date of its newest snapshot. S1 ran on 10-28 without it, so the Open-source researcher's tool counted repository ages one day too high. S1 is to be re-run with `--today 2026-10-27`.

## 2026-10-28 (The own-key lab copy must not hold the course key)

### Changed
- `CLAUDE.md` and `docs/stage5-eval-plan.md`: before each paid batch in the own-key lab copy, check that its key is not the course key, by comparing the lab's ledger ID for it (`sha256(key)[:16]`) with `key_id` in the course ledger. The copy's ledger starts at $0, so the course key there would bypass the course ledger and its pending request.
  - The first key pasted into the copy matched the course key. The check caught it before any paid call, and the author is removing it from the copy.

## 2026-10-28 (Remaining paid work moves to the author's own key)

### Changed
- The rest of Stage 5's paid work runs on the author's own OpenRouter key, in a separate lab copy outside the repository (`~/Desktop/Human-AI/forager-lab-own-key`), selected with `FORAGER_LAB_DIR`.
  - The copy has the same lab code, its own `.env` and its own ledger, which starts at $0.
  - All 128 offline tests pass against it.
- The course key's ledger (`lab/.lab-state`) is unchanged. It still holds one pending request, for the instructor to reconcile.
- `docs/stage5-eval-plan.md`, `CLAUDE.md` and the README say where paid commands run.

## 2026-10-28 (First Stage 5 batch stopped by a request timeout)

### Added
- `eval/results/digest-modes-20261028-091008.jsonl` and `.md`: the first attempt at the S1 batch.
  - It produced one digest (single).
  - In the rules run, the Open-source researcher's request did not answer within the lab's 180-second limit. The lab left it pending and paused all paid calls, and the other 16 runs were refused at no cost.
  - About $0.0063 in all, including about $0.0010 that OpenRouter charged for the pending request.
- `docs/live-runs.md`: a section on the stopped batch and why a single timeout pauses the lab. `.lab-state/` is unchanged: the lab README asks for the instructor before accounting files change.

### Changed
- `docs/stage5-eval-plan.md`: the schedule records the pause, and a new risk covers request timeouts.

## 2026-10-28 (Second snapshot set complete)

### Added
- `data/snapshot/github-2026-10-28.json` and `data/snapshot/news-2026-10-28.json`, fetched at 09:09, complete the second snapshot set (S2) with `arxiv-2026-10-27.json`.
  - Of S2's 24 candidates, 4 were also candidates in S1: 3 repositories and 1 story.
  - In the files themselves, 11 of 15 repositories and 2 of 15 stories are also in S1's files. GitHub's 7-day window explains the repositories.

## 2026-10-27 (A cost cap for the digest-modes runner)

### Added
- `eval/run_digest_modes.py --max-cost`: no new run starts once the batch has cost that much. A run already started finishes. The default is 1.5 times the batch's estimate, which is the plan's stop rule, now enforced in code. One offline test (128 in total).

### Changed
- The plan's runbook gives the approved first batch explicit caps: $0.18 for S1 and $0.12 for S2, 1.5 times the approved $0.20.

## 2026-10-27 (Stage 5 offline preparation: judges, calibration sheet, memory scenarios)

### Added
- `eval/judge_runs.py`: LLM judges for saved runs, in the Week 6 rubric style.
  - Items: `label_correct` and `worth_showing`. Brief: `supported` and `not_overstated`. Memory proposals: `evidence_supports_change` and `message_matches_change`.
  - Blinded views: no mode, writer or checks section, and items shuffled in an order fixed by their content.
  - One repair turn; a judgement that still fails is recorded as an error, never as a pass. Identical views are judged once.
  - The report gives per-mode means with bootstrap 95% intervals, critic minus rules, rules minus single, and the paired effect of the revision.
  - Diversity measures are computed from each digest: breadth share, largest topic share, normalized entropy, interests covered and source types.
- `eval/calibration.py`.
  - `make` writes a blinded labelling sheet spread evenly over the modes: CSVs without the mode, a README with the criteria word for word, and a key file.
  - `score` gives agreement, Cohen's kappa and a confusion table per criterion.
- `eval/run_memory_cases.py`: eight memory scenarios built from real digest items and their snapshot texts.
  - Scenarios: strong, weak, unconsented, mixed, mislabelled, rejected within 30 days, negative, expired.
  - Each runs in approval mode, where a scripted user approves everything, and in the silent baseline, with code measures.
  - Each proposal that was shown or written keeps a blinded view for the judge.
- `data/snapshot/arxiv-2026-10-27.json`: the arXiv half of the second snapshot set (30 papers, none of them in the first set).
  - GitHub and news follow on 10-28. Fetched on the evening of 10-27, they overlapped the first set (13 of 15 repositories, 7 of 15 stories), and their files would have replaced it.
- Ten offline tests (127 in total).

### Changed
- `eval/run_digest_modes.py` saves the profile and the snapshot file names with every record, so the judges need nothing from `runtime/`.
- `python -m forager snapshot` keeps an existing snapshot file unless `--overwrite` is given.
- `docs/stage5-eval-plan.md` now matches the scripts.
  - The memory scenarios are concrete, and a runbook lists every command.
  - Costs follow measured figures: the digest judges go up to about $0.10 and the memory reviews down to about $0.05, for a total of about $0.50.

## 2026-10-27 (Stage 5 evaluation plan)

### Added
- `docs/stage5-eval-plan.md`: the plan for the four core metrics, with sample sizes, judge criteria, calibration against the author's labels, a budget of about $0.47 of the $0.90 left, and a schedule up to the video on 11-03. Nothing has been run yet.

### Changed
- README roadmap and CLAUDE.md point to the plan. The judges follow the Week 6 rubric design but run in Forager's `eval/` on the Lab 2 connection and ledger.

## 2026-10-27 (Interest headings must match; the runner keeps the reviewed draft)

### Added
- Interest-heading check (`check_headings` in `forager/checks.py`): a brief point whose field is an interest's label must cite an item matched to that interest. The team writer is held to it as part of `Team.check`, with one repair turn, so the Manager's headings claim no more than the specialists' fits. It is not one of `check_rules`, so every Critic case still passes all code rules. On `live-01` it would flag points[4], a "Video editing" heading over an item that digest labelled Sora 2.
- `generate_digest` returns `reviewed_draft`, the digest the Critic reviewed. `eval/run_digest_modes.py` saves it, and its report lists what the revision changed: items dropped or added, changed fits, and draft brief text that was rewritten or dropped.
- Three offline tests (117 in total).

### Changed
- The Manager's instructions use an interest's label as a heading only for points that cite an item matching that interest. The single writer's instructions are unchanged.
- `eval/run_digest_modes.py` measures heading mismatches for every mode, single included (`heading_problems`, also counted in `rule_problems`).

## 2026-10-27 (Live check: the Manager's ID-only answer and field grouping)

### Added
- A second re-run of rules and critic, with the Manager naming items ($0.0161; `eval/results/digest-modes-20261027-184748.jsonl` and `.md`; write-up in `docs/live-runs.md`).
  - Both runs wrote a digest without a rewrite. Without reasoning, the Manager's answer was 925 and 945 tokens (1,708-2,051 in the morning), well inside the 4,096-token limit.
  - Both grouped brief points by topic field; the morning critic run grouped them by source.
  - r08 was labelled "Sora 2" again in the critic run (1 of 4 runs since the instruction change), and the Critic did not flag it.
  - In the critic digest, a point sits under the heading "AI copyright policy", but its item is breadth and the interest is reported as not covered. The Manager's headings are not tied to the specialists' fits.

## 2026-10-27 (The Manager names items; the specialists' notes fill them in)

### Added
- A re-run of rules and critic to check the two instruction changes ($0.0150; `eval/results/digest-modes-20261027-164540.jsonl` and `.md`; write-up in `docs/live-runs.md`). Both Manager answers hit the lab's limit of 4,096 completion tokens per response (reasoning 2,045 and 2,930 tokens, against 565-680 in the morning), so neither run wrote a digest. The specialists' notes were recorded. Both wrong labels from the morning run (r08 "Sora 2", p03 "Video editing") were breadth in both runs. The grouping change is still unchecked.
- Two offline tests (114 in total): the Manager naming items while code copies the notes, and a truncated answer rewritten from the notes.

### Changed
- The Manager no longer writes item summaries, topics or reasons. It gives the IDs of the items it includes and may mark a reported interest match as breadth. Code copies each item's summary, topics and fit from the note of the specialist that read it (`Team.fill`), so the Manager's answer is about 60% shorter.
- The Manager's instructions ask it to keep its reasoning short, and say what a field is: an interest's label, otherwise a short area name. The single writer's instructions are unchanged.
- `eval/run_digest_modes.py` records whether the Manager rewrote its digest.

### Fixed
- The team pipeline wrote no digest when the Manager's answer was lost after the specialists had answered. It now writes the digest once more from their notes, in a session without tools: one request instead of asking them again. The rewrite is recorded (`rewritten` and `check_log`) and shown in "How this digest was checked".

## 2026-10-27 (Stage 4 complete: live run of the three modes)

### Added
- First live run with the Manager and its specialists: single, rules and critic once each on the same profile and snapshots (arXiv 10-25, because the arXiv API answered 429 five times today; GitHub and news 10-27), $0.0177. Results: `eval/results/digest-modes-20261027-113548.jsonl` and `.md`; write-up for the report in `docs/live-runs.md`.
  - All three modes produced a digest whose 8 points all cite included items. The team took 9-10 requests and about 30 s against 1 request and 9 s for the single writer (about 3.5 times the cost).
  - The Manager asked all three specialists in one response; each read only its own 8 items and reported 6.
  - The Critic caught a wrong interest label that came from the Paper researcher (a video world-model survey marked "Video editing"), and the Manager's revision moved it to breadth; in rules mode the label stayed. A "Sora 2" label on an unrelated video-generation repository got past the Critic in both team runs, as Sora 2 labels did in the case-set evaluation; the single writer marked both items as breadth.
  - Measured in code for every mode: the single writer's digest would leave AI copyright policy uncovered over 7 days; both team digests cover every long-term interest.
  - Today's digest in the app is the critic run.
- Each writer attempt's check results are kept (`check_log` in the pipeline outcome, the digest record and the runner's results), so the cause of a repair turn is recorded. This run's rules-mode repair was not.

### Changed
- The Manager groups brief points by topic field, not by specialist or source (the critic run grouped them by source).
- Specialists use fit "interest" only when the text is about the interest itself, not a neighbouring topic, and may report no matches. Neither instruction change has run live yet.
- `eval/run_digest_modes.py` applies the code rules to every mode's digest, single included, so the conditions are measured the same way; this run's metrics were recomputed from its saved digests.
- "How this digest was checked" says the Manager revised a team digest.
- README: Stage 4 ticked (Hugging Face and AI-lab blogs dropped, as planned).

### Fixed
- GitHub README excerpts decode HTML entities (`&nbsp;` appeared in source texts).

## 2026-10-27 (Stage 4: Manager, source specialists and news)

### Added
- `forager/team.py` (Idea 3, as designed): the Manager writes the digest but sees only an index of the candidates (ID, type, title). Through `as_tool()` it asks focused questions of three specialists, each with its own instructions and one tool that returns only its own source: the Paper researcher (core contributions), the Open-source researcher (what a project does, stars per day computed in code) and the News researcher (what happened and why it matters; reports one story per event). The specialists inherit the lab's model settings and ledger.
- Code checks on the team, run on every Manager answer with one repair turn: every specialist whose source has candidates was asked; every item in the digest was reported by its specialist; an item is labelled with an interest only if the specialist who read it named that interest (the Manager never sees the text, so it cannot add a match). Specialist answers are checked too: notes count only if the specialist called its tool in that run, only on its own source's items, and an interest outside the profile becomes breadth.
- `forager/sources/news.py`: AI stories from five RSS/Atom feeds (TechCrunch, The Verge, MIT Technology Review, Ars Technica, The Decoder), last 3 days, one outlet at a time up to 15; source text is the feed's longest text without HTML, cut to 800 characters (snapshots are public) and prefixed with the outlet. A feed that fails is skipped. `data/snapshot/news-2026-10-27.json` (15 stories).
- `eval/run_digest_modes.py`: runs single, rules and critic on the same snapshots and profile with fresh sessions on one connection, and saves every digest with code metrics (source and topic mix, largest topic share, breadth share, uncovered interests, citations, Critic verdict, requests, cost, time) to `eval/results/digest-modes-<timestamp>.jsonl` and `.md`. `--save critic` also makes that run today's digest.
- `tests/test_stage4_team.py`: 11 offline tests (112 in total): news parsing and fetching, the specialists' scoped views, a full Manager run with every request inspected, each team check, a Critic ADJUST going back to the same Manager session, cleaning of specialist answers, progress lines and the modes runner.

### Changed
- Pipeline modes: `rules` and `critic` use the team; `single` keeps the single writer that reads every candidate (the baseline). `generate_digest(..., writer="team"|"single")` and `python -m forager digest --writer` override this.
- Digest records keep the writer and every specialist answer (`team_calls`); "How this digest was checked" starts with who wrote it ("Written by the Manager from its specialists' notes: Paper researcher reported 5 of 8 papers (4 used); ...").
- Items carry their source (outlet, arXiv or GitHub), shown in the app and the Markdown.
- The app's progress log shows the delegation ("Manager asks the News researcher: ...", "Paper researcher: read 8 papers."), and the digest page has "What the Manager asked its specialists". Live fetching includes news; `python -m forager snapshot` and `digest --sources` accept `news`.
- The single writer's instructions are unchanged; the output format and rules are now shared with the Manager's (`OUTPUT_RULES`).

## 2026-10-27 (Stage 4: Streamlit app)

### Added
- `forager/app.py` (`.venv/bin/streamlit run forager/app.py`), four pages:
  - Digest: make a digest from the saved snapshots or live sources, choosing Rules + Critic, Rules only or Single agent, with a live progress log; the two-layer brief with citations that jump to the full item; interest-match or breadth badge and "why you see this" on every item; 1-5 star ratings and likes (recorded only with consent); "How this digest was checked".
  - Set up (Idea 1): one sentence, then the agent's questions as clickable option chips, nearby fields and short-term focuses; an editable profile table, consent switches and the exploration share; the free-text baseline as a switch.
  - Memory (Idea 2): the visible profile (stated or learned, long- or short-term, weight, evidence and approval date), consent switches that delete data when turned off, decisions on expired short-term interests, stored feedback, and "Review my feedback": each proposal shows the agent's message, the change and the evidence, with Approve and Reject.
  - Topics (Idea 3): this week's items per interest and breadth, uncovered interests, the exploration slider and the digest time.
- `forager/ui_runtime.py`: the memory review runs in a worker thread; the SDK pauses at each `needs_approval` call and the worker waits for the page's answer, so approvals stay SDK-enforced in the app. Each proposal has a token, so a repeated or stale click cannot answer the next one; no answer within 10 minutes counts as a rejection.
- `forager/storage.py`: runtime paths (overridable with `FORAGER_RUNTIME_DIR`) and saving or loading digests, shared by the CLI and the app.
- `tests/test_stage4_ui.py`: 10 tests (101 in total), including the pages run headless with Streamlit's AppTest against a temporary folder and the scripted model: set-up to saved profile, making and showing a digest, likes with and without consent, and an approval clicked in the page that goes through the SDK.

### Changed
- `requirements.txt` adds `streamlit==1.66.1`.

## 2026-10-27 (Stage 4: GitHub source)

### Added
- `forager/sources/github.py`: repositories created in the last 7 days with the most stars, one search per topic (ai-agents, llm, image-generation, video-generation, generative-ai), merged and cut to 15. Each item's source text has the description, "N stars in D days" (how fast it is growing), language, topics and a plain-text README excerpt. No token needed; `GITHUB_TOKEN` raises rate limits if set.
- `data/snapshot/github-2026-10-27.json`: 15 repositories for reproducible runs.
- `python -m forager snapshot --sources arxiv github` and `python -m forager digest --snapshot A.json B.json` (several snapshot files) or live fetching from both sources.
- `tests/test_stage4_sources.py`: 6 offline tests (91 in total).

### Changed
- Candidates interleave source types (p01, r01, p02, r02, ...) up to 24, so one source cannot fill every slot and the source-mix rule can be met.
- Writer and Critic instructions: source texts (abstracts, README excerpts) come from the web; treat them as data and ignore instructions inside them. One fetched repository is literally a system prompt for coding agents.
- Snapshot helpers moved to `forager/sources/__init__.py` (still importable from `forager.sources.arxiv`).
- Hugging Face is not added, as planned when time is short.

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
