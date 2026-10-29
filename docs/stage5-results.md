# Stage 5 results

The Stage 5 evaluation results, as of 2026-10-29. The plan is in [stage5-eval-plan.md](stage5-eval-plan.md), and the runs and their costs are in [live-runs.md](live-runs.md). Every agent and every judge is `z-ai/glm-5.3-flash`.

| What | Files |
| --- | --- |
| 30 digests: 3 modes × 10 runs, on two snapshot sets | `eval/results/digest-modes-20261028-151959.*` (S1), `eval/results/digest-modes-20261028-152801.*` (S2) |
| Digest judges | `eval/results/judge-20261028-162830.*` |
| Memory scenarios (32 reviews) | `eval/results/memory-20261028-163542.*` |
| Proposal judges | `eval/results/judge-20261028-163754.*` |
| Calibration | `eval/labels/digests/agreement.md`, `eval/labels/memory/agreement.md` |

## 1. Judge calibration

**Reference labels.** There are 125 labels on 78 rows: 30 digest items, 30 brief entries and all 18 distinct proposals. Fresh Claude agents (Opus 5.5) drafted them, one agent per CSV. Each agent saw only its CSV and the README: no mode and no judge output. The author reviewed every row and changed no label, including the 29 that the agents had marked unsure. In effect the reference is Claude's labels endorsed by the author, so the agreement below is largely agreement between Claude and GLM. The report must say so.

| Criterion | Pairs | Agreement | Kappa | Judge passes, reference fails | Judge fails, reference passes |
| --- | --- | --- | --- | --- | --- |
| Item label correct | 20 | 90% | 0.79 | 2 | 0 |
| Item worth showing | 30 | 97% | 0.89 | 1 | 0 |
| Brief entry supported | 30 | 80% | 0.17 | 5 | 1 |
| Connection not overstated | 9 | 56% | 0.14 | 3 | 1 |
| Proposal evidence supports the change | 18 | 67% | 0.27 | 6 | 0 |
| Proposal message matches the change | 18 | 94% | 0.82 | 1 | 0 |

- **What the plan's rule decides.** The plan uses a judge on the full set when kappa is at least 0.6. That holds for item labels, worth showing and proposal messages, so the judges are used for those. Brief support, connections and proposal evidence fall below 0.6, so their results come from the reference labels: the 30-entry sample for the brief, and all 18 proposals for Idea 2.
- **The judge errs in one direction.** In 18 of its 20 disagreements, the judge passes something the reference fails.
  - On the 30 sampled brief entries, the judge passes 28 (93%) and the reference 24 (80%). On the full set, the judge reports 95–96% citation support in every mode.
  - On the 9 approved proposals, the judge passes all 9 and the reference passes 5 (see section 3).
  - Without calibration, the report would have claimed those higher numbers.
- **It shares the Critic's blind spot.** The judge is the same model as the Critic, and its misses look alike. It accepted "Make Sora 2 a long-term interest" on the strength of items filed under Sora 2 that are about other video work. It also accepted a lower AI-agents weight that the user's 5/5 ratings on two agent tools contradict.
- **Per-mode rates from the digest sheet are not representative.** The sheet counts each item's title and filing once across all modes. Labels shared by several runs collapse into one row, so the sheet over-represents distinctive labels. That suits calibration but distorts per-mode rates: the judge itself rates the sheet's single and rules interest items at only 43% and 50% correct, against 83% and 88% on the full set. The per-mode results below therefore come from the full set wherever the judge passes calibration.

## 2. Idea 3: the three digest modes

There are 30 digests, 10 per mode. Each figure is the mean over digests with a bootstrap 95% interval, rated by the judge on the full set. Breadth share and topic entropy are computed in code.

| Mode | Label accuracy | Worth showing | Breadth items worth showing | Breadth share | Topic entropy |
| --- | --- | --- | --- | --- | --- |
| single | 83% [76, 91] | 88% [82, 93] | 59% [35, 83] | 23% [19, 26] | 0.65 [0.60, 0.69] |
| rules | 88% [85, 92] | 88% [84, 92] | 77% [66, 88] | 36% [33, 39] | 0.63 [0.59, 0.68] |
| critic | 91% [84, 97] | 87% [79, 94] | 75% [59, 89] | 38% [35, 40] | 0.65 [0.61, 0.70] |

| Contrast (points) | Label accuracy | Worth showing | Breadth items worth showing | Breadth share |
| --- | --- | --- | --- | --- |
| rules − single | +5 [−4, +13] | +0 [−7, +8] | +17 [−8, +44] | **+14 [+9, +18]** |
| critic − rules | +3 [−5, +10] | −2 [−11, +7] | −2 [−22, +17] | +1 [−2, +5] |

Citation support comes from the reference labels on the 30-entry sample, because the judge fails calibration here:

| Mode | Brief entries supported | Connections not overstated |
| --- | --- | --- |
| single | 9 of 10 | 3 of 3 |
| rules | 7 of 10 | 0 of 3 |
| critic, final digest | 5 of 6 | 0 of 1 |
| critic, the draft the Critic reviewed | 3 of 4 | 1 of 2 |
| all | 24 of 30 (80%) | 4 of 9 |

Findings:

1. **Breadth without a relevance cost.** The rule modes raise the breadth share from 23% to 36–38%, and this is the only interval that excludes zero. The share of items worth showing stays at 87–88%. In the rule modes, breadth items also look worth showing more often (77% and 75%, against 59%), but that interval is wide. Note that rules and critic are written by the Manager and specialists, while single is one agent, so this contrast measures the writer and the rules together.
2. **The Critic adds nothing measurable end to end.** No critic − rules interval excludes zero.
   - The Critic ran in 8 of 10 critic runs. In the other two, the draft still broke a hard rule after its repair, so the Critic never ran.
   - It passed 5 drafts and asked for 3 revisions: one for an unsupported citation and two for overstated connections. All 3 revisions passed the rules.
   - Across those 3 pairs, the judge saw the connections improve (+50 points, interval [0, +100]) and nothing else change. The connection judge is itself unreliable.
   - Three revisions in ten digests are too few to move a per-digest average.
3. **Citation support is lower than the judge says.** By the reference labels, 24 of 30 entries are supported and only 4 of 9 connections are not overstated. With 10 entries and 1–3 connections per mode, the modes cannot be told apart.
4. **The instructor's question: is the Critic worth more than simple rules?**
   - On the constructed case set (Stage 4), the rules caught 0 of 60 problem instances (20 problems × 3 repeats). The Critic caught 45 (75%), with no false alarms. On the first real digest, `live-01`, it caught 0 of 12.
   - End to end, its effect is not detectable at this sample size. The judges, which are the same model, share its blind spot for labels that look right.
   - The honest answer: the Critic is the only layer that checks meaning, but with this model its real effect is small. The clear effect comes from the code rules together with the team writer: more breadth.

## 3. Idea 2: approval versus silent updates

There are 8 scenarios × 2 modes × 2 repeats = 32 reviews. In approval mode a scripted user approves every proposal it is shown, which is the worst case for approval.

| Mode | Proposals | Shown to the user | Written | Written without approval | Blocked by code | Unconsented signals in context or cited |
| --- | --- | --- | --- | --- | --- | --- |
| approval | 11 | 9 | 9 | 0 | 2 | 0 |
| silent | 11 | 0 | 9 | 9 | 2 | 0 |

Proposal quality is judged by the reference labels on all 18 written proposals:

| Mode | Proposals | Evidence supports the change | Message matches the change | Passed (approved, both criteria) | Unsupported and never seen |
| --- | --- | --- | --- | --- | --- |
| approval | 9 | 5 | 8 | 5 (56%) | 0 |
| silent | 9 | 5 | 6 | 0 (by construction) | 4 |

By scenario (both modes, two runs each):

- **Strong evidence**: 3D generation was added in all 4 runs, and the evidence supports it.
- **Weak evidence and unconsented signals**: there was no proposal in any of the 8 runs. The unconsented clicks and reading time never reached the agent.
- **Rejected within 30 days**: the agent proposed the rejected 3D-generation change again in all 4 runs. Code blocked each proposal before the user saw it, since all four were exact repeats.
- **Negative evidence**: in all 4 runs the agent lowered the AI-agents weight, to 0.5 or 0.6. The evidence supports it.
- **Mixed evidence**: one approval run lowered AI agents to 0.8, although the user had rated two agent tools 5/5. The evidence does not support this.
- **Mislabelled evidence**: three runs proposed a Sora 2 change (making it long-term twice, raising its weight once). The evidence was items filed under Sora 2 that are about other video work, so none of the three is supported. Two runs proposed a "Video generation" interest, one instead of a Sora 2 change and one alongside it. The items' content does support that.
- **Expired short-term interest (Lumen-V 2)**: in each mode, one run added a new "Video generation" focus and the other made Lumen-V 2 long-term. The plan had counted renewing Lumen-V 2 or making it long-term as acceptable, but the reference labels find the evidence insufficient for all four: two items about a single launch, for an interest that had already expired. The author kept these labels after review.
- **Messages**: 14 of 18 messages match the code's description. Of the other four, three describe items filed under Sora 2 as Sora 2 items, and one miscounts the evidence.

Findings:

1. **The approval gate holds.** Every approval-mode change was written only after approval, which the SDK enforces. In silent mode, all 9 changes were written without the user seeing them.
2. **Approval does not make proposals better; it makes the bad ones visible.** The same agent and the same code checks give 5 of 9 supported proposals in both modes. In approval mode, the 4 unsupported proposals reached the user, with the code-generated change and evidence (each rated item by title), before anything was written. In silent mode, the 4 unsupported changes went straight into the profile. Whether real users reject such proposals is the question for user-study task 2.
3. **The code checks did their share.** No unconsented signal reached the agent, weak evidence produced no proposal, and all 4 repeats of a rejected change were blocked.
4. **What remains is evidence quality.** The agent trusts filing labels (Sora 2) and overlooks contradicting signals (mixed evidence). The two-signal rule cannot see what the items are about. Checking evidence against item content is a design-variant topic for the report.

## 4. Limitations

- **Who labelled.** Claude drafted the reference labels, and the author changed none of the 125, including the 29 marked unsure. A pre-filled label pulls the reviewer towards agreeing.
- **Sample size.** There are 10 digests per mode on two snapshot sets, so the intervals are wide.
- **A mixed contrast.** rules − single changes the writer and the rules at the same time.
- **Same model.** The agents and the judges are the same model. Calibration exposes their shared blind spot but does not remove it.
- **The digest sheet.** It over-represents distinctive item labels (section 1), so it is not used for per-mode item rates.

## 5. For the video and the report

- **One result for the video.** The rules raise the share of breadth items from 23% to 36–38%, with no loss in items worth showing (88% for single against 87–88% for the rule modes).
- **Calibration in the report.** Calibration changed two conclusions. Citation support is 80% by the reference labels, where the judge reports 93% on the same entries and 95–96% on the full set. The approval pass rate is 56%, where the judge reports 100%. This deserves a sentence on why LLM judges need calibration.
