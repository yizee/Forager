# Judge calibration · memory

Author's labels in `eval/labels/memory` against judge-20261028-163754.jsonl. Kappa of at least 0.6 means the judge is used for the full set; below that, the author's labels are the primary result for that criterion.

| Criterion | Pairs | Agreement | Kappa | Both pass | Both fail | Author pass, judge fail | Author fail, judge pass | Unlabelled | No judgement |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| proposals.evidence_supports_change | 18 | 67% | 0.27 | 10 | 2 | 0 | 6 | 0 | 0 |
| proposals.message_matches_change | 18 | 94% | 0.82 (meets 0.6) | 14 | 3 | 0 | 1 | 0 | 0 |

Rows where the author and the judge disagree:

- proposals.evidence_supports_change: rows 9, 11, 12, 13, 15, 18
- proposals.message_matches_change: rows 9

Draft labels by fresh Claude agents (Opus 5.5), one per CSV, that saw only a copy of the CSV and README.md, reviewed by the author:

- proposals.evidence_supports_change: changed 0 of 18
- proposals.message_matches_change: changed 0 of 18

By mode, on the same rows: how many pass by the labels and by the judge (`.all`: every criterion of the row passes).

| Criterion | Mode | Rows | Labels pass | Judge pass |
| --- | --- | --- | --- | --- |
| proposals.evidence_supports_change | approval | 9 | 5 (56%) | 9 (100%) |
| proposals.evidence_supports_change | silent | 9 | 5 (56%) | 7 (78%) |
| proposals.message_matches_change | approval | 9 | 8 (89%) | 9 (100%) |
| proposals.message_matches_change | silent | 9 | 6 (67%) | 6 (67%) |
| proposals.all | approval | 9 | 5 (56%) | 9 (100%) |
| proposals.all | silent | 9 | 5 (56%) | 6 (67%) |
