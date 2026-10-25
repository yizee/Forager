# Changelog

All notable changes to this project are recorded here, newest first.

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
