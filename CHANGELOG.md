# Changelog

All notable changes to this project are recorded here, newest first.

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
