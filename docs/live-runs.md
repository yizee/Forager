# Live runs

Paid runs against `z-ai/glm-5.3-flash` with the course key. Offline tests cover the
same code paths with scripted replies; these runs check that the real model works
with them. Run artefacts (profile, digest, signals, decisions) stay in `runtime/`,
which is not committed.

## 2026-10-25: first live runs of Stages 1–3

Decisions in the onboarding and memory runs were made by Claude acting as the
CLAUDE.md persona (an AI student following AI agents, video editing and image
generation, currently following Sora 2), with the decision rule stated before each
run. These are functional checks, not user-study data.

| Stage | Run | Requests | Cost (USD) | Result |
| --- | --- | --- | --- | --- |
| 2 | Clarification, run 1 | 1 | 0.00028 | Passed code checks; "Sora 2" returned as both a direction and a short-term item (see 1) |
| 2 | Clarification, run 2 | 1 | 0.00027 | Sora 2 short-term only; a "Student focus" direction about content format appeared (see 1) |
| 2 | Clarification, run 3 | 1 | 0.00025 | Three topic directions, three adjacent fields, Sora 2 short-term; persona confirmed and saved the profile |
| 1 | Digest from `data/snapshot/arxiv-2026-10-25.json` | 1 | 0.00164 | Code checks PASS on the first attempt; 8/8 brief points cite included items; 11 items (2 breadth) |
| 3 | Memory review, run 1 | 3 | 0.00116 | Two proposals, both rejected; profile file byte-identical |
| 3 | Memory review, run 2 | 2 | 0.00080 | Did not repeat either rejected change; one new proposal, rejected |
| 3 | Memory review, run 3 | 2 | 0.00086 | "Add 3D generation (long-term, 0.8)" approved; tool ran only after approval; evidence and approval date written |

Total recorded by the local ledger (`lab/.lab-state`): $0.0053, 0 web searches.

Persona decision rules for the memory reviews: run 1, approve changes that strengthen
video topics but not weight changes (too crude: it also rejected raising Sora 2);
run 2, approve only a new video-related interest; run 3, approve any new interest
(after adding 5/5 ratings and a like on two image-to-3D papers, to exercise the
write path).

## Observations for the report

1. **Clarifier output needed code checks, not only instructions (Idea 1).** In run 1
   the model listed "Sora 2" as a direction and as a short-term item; accepting both
   would have created two interests with the same label. Fixed at four levels:
   instructions, a code check that triggers the repair turn, de-duplication in
   `build_profile`, and unique labels in `validate_profile`. Run 2 then asked about
   the user's role ("Student focus") instead of a topic; one instruction line fixed it.
2. **Rules pass, semantic problems remain (Idea 3 motivation).** The digest passed
   every code check, yet:
   - two items labelled "Interest match (Sora 2)" are not about Sora 2 (camera
     control in video diffusion; a survey of video world models);
   - image-to-3D papers are labelled "Image generation";
   - one cross-field connection is overstated ("structured verification or
     reciprocal training signals beats scaling raw supervision").
   These are the Critic's targets: exploration relevance, label accuracy and
   unsupported connections.
3. **Label errors propagate into memory (Ideas 2 and 3).** The wrong "Sora 2" labels
   travelled with the user's ratings into the memory agent, which proposed raising
   Sora 2's weight and then making it long-term. The evidence IDs were real and
   consented, so every code check passed; only a semantic check could see that the
   evidence is about video generation, not Sora 2. A Critic that catches label
   errors in the digest therefore also protects the preference memory.
4. **The approval gate behaved as designed (Idea 2).** Three rejections left the
   profile file byte-identical; the agent's final messages reported the outcomes
   accurately; after rejections it did not repeat them and said so; the one approved
   change was written only after approval, marked `inferred`, with its evidence.

## 2026-10-27: the three digest modes with the Manager and its specialists (Stage 4)

`eval/run_digest_modes.py` ran single, rules and critic once each on the same
profile (the persona: AI agents, video editing, image generation, AI copyright
policy, Sora 2 short-term, 3D generation) and the same snapshots:
`arxiv-2026-10-25.json` (the arXiv API answered 429 to five attempts today, so the
10-25 papers were reused), `github-2026-10-27.json` and `news-2026-10-27.json`.
24 candidates: 8 papers, 8 repositories, 8 news stories. Previous digest and 7-day
history: the 10-25 digest. Raw results: `eval/results/digest-modes-20261027-113548.jsonl`;
every digest with the Manager's questions: the `.md` next to it.

| Mode | Writer | Requests | Cost (USD) | Time | Code rules | Items (paper/repo/news) | Largest topic | Breadth | Critic |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single | single | 1 | 0.0021 | 9 s | not enforced; topic share and source mix would pass, 1 interest uncovered | 10 (4/3/3) | AI agents 40% | 40% | – |
| rules | team | 9 | 0.0074 | 29 s | PASS after one repair turn | 12 (5/4/3) | AI agents 33% | 33% | – |
| critic | team | 10 | 0.0081 | 32 s | PASS first time | 10 (4/4/2) | AI agents 40% | 30% | ADJUST, 1 issue, revised |

Every brief point cites included items (8/8 in each mode). The code rules were
applied to all three digests after the run, single mode included (the runner now
does this itself): with the 10-25 digest in the 7-day window, the single writer
left AI copyright policy uncovered, because it labelled SpectralCanary (dataset-use
auditing for text-to-image training) as image generation; both team digests
labelled it AI copyright policy, which the case-set audit also judged correct.
Total for the three runs: $0.0177; ledger $0.0603 of $1.

### Observations for the report

1. **The delegation ran as designed.** In both team runs the Manager asked all three
   specialists in its first response (one request; separate turns would have taken
   two more). Each specialist called its tool, read only its own 8 items and reported
   6; no specialist answer needed cleaning by code. The questions named the user's
   interests and facets and listed the source's candidates. The News researcher said
   plainly that no story was about video editing, image or 3D generation or Sora 2,
   instead of forcing a match. Cost: 9–10 requests instead of 1, about 3.5 times the
   single writer, and about 30 s instead of 9 s.
2. **The Critic caught a wrong label that came from a specialist.** The Paper
   researcher marked p03 (a survey of video world models) as matching Video editing.
   The Manager may only use labels a specialist gave, so it kept it. The Critic flagged
   it (mislabeled_interest: "it never discusses editing, editing tools, or editing
   pipelines") and the Manager's revision moved it to breadth. In rules mode, with no
   Critic, the same label stayed. This is the layering of Idea 3: code makes sure an
   interest label comes from an agent that read the text; only a semantic check can
   tell whether that agent was right. The same paper was labelled "Sora 2" by the
   10-25 single writer, a label the Critic never caught in the case-set evaluation.
3. **One wrong label got past the Critic.** Both team runs labelled r08 (Tencent ARC's
   autoregressive video-generation repository) "Sora 2"; its text never mentions Sora.
   Under the case set's labelling rules this is a mislabeled_interest problem, and as
   in the case-set evaluation (Sora 2: 0 of 3) the Critic accepted a "Sora 2-style
   video generation" label. The single writer, which saw every source, marked both
   p03 and r08 as breadth. One run cannot settle it, but a plausible cause fits: each
   specialist sees only its slice and was told to report "interest matches first", a
   local version of the coverage pressure seen on 10-25. The specialist instructions
   now say to use "interest" only for the interest itself, not a neighbouring topic,
   and that reporting no matches is fine (not yet re-run live).
4. **Presentation slip.** In the critic run the Manager grouped brief points by source
   ("papers", "repos", "news") instead of by field; the single and rules runs grouped
   by field. The Manager's instructions now say to group by topic field (not yet
   re-run live).
5. **What this run did not record.** The rules run needed one repair turn, but which
   check triggered it was not saved. Each writer attempt's check results are now
   kept (`check_log` in the outcome, the digest record and the runner's results).
6. "Changes since last time" noticed that FlexPart, SpectralCanary and BrickWright
   reappear from the 10-25 digest, which used the same arXiv snapshot.

## 2026-10-27 (afternoon): rules and critic again, to check the two instruction changes

Same profile, snapshots (arXiv 10-25, GitHub and news 10-27), previous digest and
history as the morning run; rules and critic once each. Results:
`eval/results/digest-modes-20261027-164540.jsonl` and `.md`.

| Mode | Requests | Cost | Time | Outcome |
| --- | --- | --- | --- | --- |
| rules | 8 | $0.0072 | 40.0 s | no digest: the Manager's answer was cut off |
| critic | 8 | $0.0078 | 48.1 s | no digest: the Manager's answer was cut off |

Total $0.0150; ledger $0.0753 of $1.

In both runs the Manager asked all three specialists in its first response, and each
specialist read its 8 items and reported 6. The Manager's final answer then reached
the lab's limit of 4,096 completion tokens per response, which includes reasoning.
The lab's transport rejected it ("Model output was truncated"), so no digest was
written.

| Manager's final answer | Prompt tokens | Reasoning tokens | Completion tokens |
| --- | --- | --- | --- |
| morning, rules | 5,274 | 680 | 2,731 |
| morning, critic | 5,405 | 565 | 2,273 |
| afternoon, rules | 5,937 | 2,045 | 4,096 (cut off) |
| afternoon, critic | 6,092 | 2,930 | 4,096 (cut off) |

### What could still be checked: the specialists' labels

Specialist notes are recorded even when the Manager fails (`team_calls`).

- **r08** is Tencent ARC's video-generation repository. Both morning team runs
  labelled it "Sora 2". Both afternoon runs marked it as breadth: "Not editing itself,
  but frontier video-generation research directly relevant to Sora 2".
- **p03** is the video world-model survey. The morning critic run labelled it "Video
  editing". Both afternoon runs marked it as breadth.
- **Two borderline labels appeared, in the critic run only.** n05 (GPT-6.1 Terra's
  price cut) and p02 (a proxy metric for embodied policies) were both labelled AI
  agents. The rules run marked both as breadth. The specialists still disagree on
  items that sit next to an interest.

These judgments are Claude's and the author has not checked them. The grouping change
(points by field, not by source) could not be checked, because no digest was written.

### Change made

- **The Manager now gives only item IDs.** It no longer writes the items' summaries,
  topics and reasons. It may mark a reported interest match as breadth instead, but
  not the reverse. Code copies each item's summary, topics and fit from the note of
  the specialist that read it (`Team.fill`). On the morning critic digest, this cuts
  the JSON from about 2,350 to about 950 tokens (characters / 4).
- **Shorter reasoning.** The Manager's instructions ask it to keep its reasoning
  short. They also say what a field is: an interest's label, otherwise a short area
  name.
- **Rewrite after a lost answer.** If the Manager's answer is lost after every
  specialist has answered, it writes the digest once more from their notes, in a
  session without tools. This takes one request instead of asking the specialists
  again. The rewrite is recorded (`rewritten`, `check_log` stage "rewrite") and
  shown in "How this digest was checked".
- **The single writer is unchanged.** Its instructions are identical byte for byte.

These changes have not been run live yet.

### Observations for the report

1. **The output limit is a design constraint for a Manager.** Every response,
   reasoning included, must fit in 4,096 tokens, and the Manager writes the largest
   answer in the system. After the instruction changes its reasoning grew from
   565–680 to 2,045–2,930 tokens. The specialists' longer notes also added about 650
   prompt tokens. Two runs cannot separate the new grouping instruction from
   run-to-run variation.
2. **Each agent now writes about what it read.** Item summaries come from the
   specialist that read the source, not from a Manager that saw only titles and
   notes. This is cheaper, and the Manager can no longer restate a note
   inaccurately.
3. **The narrower specialist instruction removed both known wrong labels** (r08 and
   p03) in both runs, judged from the specialists' notes.

## 2026-10-27 (evening): rules and critic again, with the Manager naming items

Same profile, snapshots (arXiv 10-25, GitHub and news 10-27), previous digest and
history as the two earlier runs; rules and critic once each, with the changes above.
Results: `eval/results/digest-modes-20261027-184748.jsonl` and `.md`.

| Mode | Requests | Cost | Time | Outcome |
| --- | --- | --- | --- | --- |
| rules | 9 | $0.0067 | 37.3 s | digest; rules passed after one repair |
| critic | 12 | $0.0094 | 47.0 s | digest; Critic ADJUST (1 issue), revised once |

Total $0.0161; ledger $0.0913 of $1.

### The Manager's answer fits

Neither run was cut off, so neither needed the rewrite. The Manager's answer, now
item IDs only, is about half as long as in the morning:

| Manager's final answer | Prompt tokens | Reasoning tokens | Completion tokens | Answer tokens |
| --- | --- | --- | --- | --- |
| morning, rules | 5,274 | 680 | 2,731 | 2,051 |
| morning, critic | 5,405 | 565 | 2,273 | 1,708 |
| afternoon, rules | 5,937 | 2,045 | 4,096 (cut off) | – |
| afternoon, critic | 6,092 | 2,930 | 4,096 (cut off) | – |
| evening, rules | 5,507 | 1,279 | 2,204 | 925 |
| evening, critic | 5,809 | 335 | 1,280 | 945 |

Answer tokens are completion tokens minus reasoning tokens. Every item's summary and
topics came from its specialist's note. The Manager still wrote its own reason for
three breadth items in each run (rules: p03, r02, n05; critic: p03, r02, n06). The fit
stayed breadth and the text paraphrased the note. Code allows this, although the
instructions ask for a reason only when the Manager shows a reported match as breadth.

### Points are grouped by field

Both runs grouped brief points by topic, never by source:

- rules: AI agents (3), Video generation, Model releases, Agent tooling
- critic: AI agents (4), 3D generation, Sora 2, Video generation, AI copyright policy

The morning critic run grouped them as papers, repos and news.

### Labels

These judgments are Claude's and the author has not checked them.

- **r08** (Tencent ARC's video-generation repository) was breadth in the rules run.
  In the critic run its specialist labelled it "Sora 2" again ("relevant to
  Sora-style models"), and the Critic did not flag it. Since the instruction change,
  the label has come back in 1 of 4 runs. In live digests the Critic has missed this
  label both times it appeared. It also never caught a Sora 2 label in the case-set
  evaluation.
- **p03** (the video world-model survey) was breadth in both runs.
- **p05** (SpectralCanary, which audits whether a text-to-image model was trained on
  a collection) was AI copyright policy in the rules run and breadth in the critic run
  ("Not copyright policy per se"). Both readings are defensible.
- **p04** (pruning candidate solutions for reasoning models at test time) was
  labelled AI agents in the rules run. The abstract is about reasoning models, not
  agents, so the label is a stretch.

### Headings and labels can disagree

The Manager chooses each point's heading; the specialists choose each item's fit.
Nothing in code ties the two together.

- In the critic digest, SpectralCanary's point sits under the heading "AI copyright
  policy". The item itself is breadth, and "How this digest was checked" says AI
  copyright policy has no item in the last 7 days. A reader sees both on one page.
- n06 (a Qwen model tried to send a file after saying it would use no tools) is
  breadth, but its point sits under "AI agents".
- The topic-share rule counts items. AI agents has 4 of 10 items in both runs, at the
  40% limit. In the quick brief, which readers see first, it has 3 of 6 points
  (rules) and 4 of 8 (critic).

### Repairs and the Critic

- **rules**: the first draft had 5 breadth items out of 11 (45%, over the 40% limit);
  the repair brought it to 4 of 10.
- **critic**: the first draft cited p03 in a connection without including it; the
  repair fixed that. The repaired draft left AI copyright policy uncovered, which is
  a warning, not a failure.
- **The Critic** returned ADJUST with one issue: points[1] called OpenAI's dots
  "meeting-aware", which n01's one-sentence source does not say. The revision
  dropped the phrase. The final point still says the change is "a sign that coding
  agents are becoming the foundation of OpenAI's everyday AI strategy", which the
  source does not state either. The runner keeps only the final digest, so it is
  unknown whether the revision added this.
- The revision's rule check asked once more for AI copyright policy. No specialist
  had matched an item to it, and the Manager may not add a match itself, so this
  repair could not succeed and cost one request.
- "Changes since last time" in the critic digest starts "First digest" but mentions
  the 10-25 brief in the same sentence. The Critic does not review that section.

### Change made

- **Interest headings must match the items' fits.** A point whose heading is an
  interest's label must cite an item matched to that interest; otherwise the Manager
  gets one repair turn (`check_headings`, part of `Team.check`). Both headings flagged
  above (SpectralCanary under AI copyright policy, n06 under AI agents) would have been
  sent back. The check applies to the team writer only. It is not one of the code
  rules that every Critic case is built to pass, so the case set and its scores are
  unchanged. On the first live digest (`live-01`) it would flag points[4]: a "Video
  editing" heading over WorldForge V2, which that digest labelled Sora 2.
- **The runner keeps the draft the Critic reviewed** (`reviewed_draft`), and its report
  lists what the revision changed. It also measures heading mismatches for every mode,
  single included.

These changes have not been run live yet.

### Observations for the report

1. **Giving the Manager less to write fixed the length problem.** Both answers fit
   well inside the 4,096-token limit (2,204 and 1,280 tokens), and no rewrite was
   needed. One run per mode cannot show how often the limit would still be reached.
2. **Headings are interest claims too.** The team rule says only a specialist that
   read an item can match it to an interest. It covers labels but not headings. A
   natural extension: a point under an interest's heading must cite an item matched
   to that interest. Because headings are unchecked, the brief can also look more
   one-sided than the items.
3. **The Sora 2 label is the most persistent error.** The narrower specialist
   instruction removed it in 3 of 4 runs, and the Critic has not caught it in any
   live digest or case so far.
4. **To measure what a revision changes, keep the reviewed draft.** Stage 5 compares
   rules and critic across runs. A comparison within a run also needs the draft the
   Critic reviewed, not only the final digest.
