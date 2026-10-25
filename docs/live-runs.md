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
