# Critic evaluation on the case set (Idea 3)

Research question (from the instructor's feedback): does a Critic agent add value beyond
simple rules? The case set (`eval/cases/critic/`) holds digests that pass every code rule
but contain problems only a reader can see, plus clean controls; see its README for how
the cases were made, audited and scored.

## Setup

- 2026-10-27, `z-ai/glm-5.3-flash` with the lab's fixed settings (reasoning effort low).
- 21 cases x 3 repeats = 63 reviews, each in a fresh Critic session
  (`eval/run_critic_cases.py`). The Critic sees the profile, the brief and each item's
  full source text, never the ground truth.
- Cost $0.036 (about $0.0006 per review); no failed reviews, no repair turns.
- Raw results: `eval/results/critic-20261027-090328.jsonl`. Every review, with each issue
  the Critic raised and its explanation: `eval/results/critic-20261027-090328.md`.
- One test run on `ie-01` before the full run (verdict PASS) is not part of the results.

## Results

| Condition | Problems caught | Type matched (of caught) | Control reviews with a false alarm | False-alarm issues |
| --- | --- | --- | --- | --- |
| Rules only | 0/60 (0%) | - | 0/12 | 0 |
| Rules + Critic | 45/60 (75%) | 100% | 0/12 | 0 |

The 60 are 20 labeled problems x 3 repeats. Rules-only scores 0 by construction.

| Problem type | Caught |
| --- | --- |
| Near-duplicates under different labels | 9/9 (100%) |
| Irrelevant exploration | 8/9 (89%) |
| Citation does not support the point | 12/15 (80%) |
| Overstated connection | 9/12 (75%) |
| Wrong interest label | 7/15 (47%) |

| Cases | Caught |
| --- | --- |
| Constructed (16 cases, one problem each) | 45/48 (94%) |
| The real digest from the first live run (`live-01`, 4 problems) | 0/12 (0%) |

Consistency: the same verdict in all three repeats for 17 of 21 cases. The three
constructed misses (`ie-01`, `ml-01`, `ml-02`) were each caught in the other two repeats;
the missed reviews were not shorter than the others (134-247 output tokens; reviews that
flagged problems: median 218), so they look like run-to-run variation rather than skipped
checks.

## What it means

1. **The Critic adds value beyond rules.** On problems that rules cannot see, it caught
   94% of the constructed ones and raised no false alarm on any clean digest, including
   the two hard negatives (same model with different information; distant but honest
   breadth). Every issue it raised was on a labeled problem or a debatable spot.
2. **The case set overestimates real-world recall.** On the real digest the Critic caught
   none of the four problems in three tries. Each constructed case contains one clear,
   isolated change; the real problems are subtler: video research filed under the user's
   Sora 2 interest, a connection that overstates, and a point that leaves out a
   near-doubling in a result.
3. **Wrong interest labels are the weakest type (47%).** With the fictional Lumen-V 2 the
   Critic caught the mislabel in 2 of 3 runs; with the real Sora 2, never. A possible
   reason, not tested here: the model's own knowledge of Sora 2 makes video-generation
   research look relevant to it.
4. **On the real digest it flagged a debatable spot instead.** In 2 of 3 runs its only
   issue was connections[1] ("both ... without retraining them from scratch"), with a
   sound reason: FlexPart is a newly trained model and WorldForge V2 trains small
   adapters. Both label audits had marked this connection debatable, so scoring ignores
   it; the labels were not changed after seeing the results.
5. **The Critic is conservative.** High precision with misses fits its instructions to
   report only clear problems. In the product this is the safer side: a false alarm
   would make the writer change a correct digest.

## Limitations

- 21 cases and 20 labeled problems; repeats measure consistency, not generality.
- The labels were written by Claude and audited twice (by Claude and by an independent
  reviewer agent); the project author's own check is still pending.
- Cases built by perturbation are easier than real errors (point 2).

## Next steps worth considering

- Evaluate on new live digests, labeled before the Critic runs: the condition that
  matters, where the Critic did worst.
- A Critic that must check every breadth item, interest label, point and connection
  explicitly before its verdict. Because these results are now known, it would need new
  cases or new live digests for a fair evaluation.
