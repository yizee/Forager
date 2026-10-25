# Forager

A personalized agent that keeps users at the frontier of the fields they follow (AI news, papers and open-source tools) without letting the feed narrow to their latest interest.

CS 619 (Human-AI Interaction) course project · SHI YIZE

## What it does

Forager delivers a daily digest at a time the user chooses, drawn from three source types:

| Source type | Where it comes from |
| --- | --- |
| News | Tech news via RSS or a news API |
| Papers | arXiv and AI-lab research blogs |
| Open source | Trending GitHub repositories and Hugging Face models |

Each digest has two linked layers:

- **Quick brief**: 5–8 key points by field, cross-field connections and changes since last time. Every point cites the items it came from.
- **Full items**: summary, source link and a "why you see this" label.

## Three design ideas

1. **Clarification-based interest elicitation** (Week 1, intent expression). The user describes themselves in one rough sentence; the agent asks follow-ups as clickable options and shows an editable profile. Baseline: free-text description.
2. **Consented, evidence-backed preference memory** (Week 4, memory). Users opt in to each tracked signal. Profile entries are marked stated or inferred, long-term or expiring short-term. The agent proposes updates with evidence and waits for approval. Baseline: silent updates.
3. **Source specialists with a breadth-and-evidence critic** (Week 6, multiple agents). A Manager delegates to News, Paper and Open-Source Researchers. Deterministic checks (topic share, 7-day coverage, citation IDs) run in code; a Critic agent handles semantic checks that rules cannot (is an exploration item relevant, are items duplicates, do citations support a point). Baselines: single agent; rules only.

## Roadmap

Built incrementally, each stage runnable before the next starts:

- [ ] Stage 1: minimal pipeline. One source (arXiv), single agent, two-layer digest
- [ ] Stage 2: Idea 1. Clarification onboarding and JSON profile
- [ ] Stage 3: Idea 2. Ratings, consent and evidence-backed update proposals
- [ ] Stage 4: Idea 3. GitHub and news sources, source specialists, rules + Critic
- [ ] Stage 5: evaluation. Week 6 harness test cases and think-aloud study

Fallback if time is short: drop Hugging Face first.

## Key metrics

| Idea | Metric | Method |
| --- | --- | --- |
| 1 | Self-rated profile accuracy (1–7) vs. free text | User study |
| 2 | Pass rate: updates cite evidence and wait for approval | LLM-judged test cases |
| 3 | Topic diversity vs. relevance across single agent / rules / rules + Critic | Code metrics + LLM-judged relevance |
| 3 | Citation support rate of brief points | LLM-judged test cases |

## Repository layout

```
CLAUDE.md        full project brief for development (read first)
docs/            proposal, feedback and design notes
forager/         application code: sources/, digest.py, checks.py, render.py, profile.py
data/snapshot/   fixed content snapshots for offline tests and evaluation
tests/           offline tests (scripted model replies, no key needed)
lab/             course lab package, not committed (unzip lab2.zip here)
CHANGELOG.md
```

## Running

Requires Python 3.10+ and the course lab package unzipped into `lab/` (with its `.env`).

```bash
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest                    # offline, free
.venv/bin/python -m forager onboard           # set up your profile with option follow-ups (paid call)
.venv/bin/python -m forager onboard --baseline   # free-text baseline, no follow-ups
.venv/bin/python -m forager consent           # choose which feedback signals may be tracked
.venv/bin/python -m forager rate p03 5        # rate an item in the latest digest (likewise: like p03)
.venv/bin/python -m forager review            # approve or reject evidence-backed profile updates (paid call)
.venv/bin/python -m forager profile           # see the profile, what is tracked and past decisions
.venv/bin/python -m forager snapshot          # save recent arXiv papers to data/snapshot/
.venv/bin/python -m forager digest            # fetch arXiv and write today's digest (paid call)
.venv/bin/python -m forager digest --snapshot data/snapshot/arxiv-2026-10-25.json
```

Digests are written to `runtime/digests/<date>.json` and `.md`.

## Key dates

- Video (2 min): 3 Nov 2026
- Report (max 6 pages): end of Week 11
