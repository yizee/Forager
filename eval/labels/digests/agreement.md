# Judge calibration · digests

Author's labels in `eval/labels/digests` against judge-20261028-162830.jsonl. Kappa of at least 0.6 means the judge is used for the full set; below that, the author's labels are the primary result for that criterion.

| Criterion | Pairs | Agreement | Kappa | Both pass | Both fail | Author pass, judge fail | Author fail, judge pass | Unlabelled | No judgement |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| items.label_correct | 20 | 90% | 0.79 (meets 0.6) | 11 | 7 | 0 | 2 | 0 | 0 |
| items.worth_showing | 30 | 97% | 0.89 (meets 0.6) | 24 | 5 | 0 | 1 | 0 | 0 |
| brief.supported | 30 | 80% | 0.17 | 23 | 1 | 1 | 5 | 0 | 0 |
| brief.not_overstated | 9 | 56% | 0.14 | 3 | 2 | 1 | 3 | 0 | 0 |

Rows where the author and the judge disagree:

- items.label_correct: rows 9, 15
- items.worth_showing: rows 29
- brief.supported: rows 2, 10, 13, 19, 21, 30
- brief.not_overstated: rows 13, 14, 19, 20

Draft labels by fresh Claude agents (Opus 5.5), one per CSV, that saw only a copy of the CSV and README.md, reviewed by the author:

- items.label_correct: changed 0 of 20
- items.worth_showing: changed 0 of 30
- brief.supported: changed 0 of 30
- brief.not_overstated: changed 0 of 9

By mode, on the same rows: how many pass by the labels and by the judge (`.all`: every criterion of the row passes).

| Criterion | Mode | Rows | Labels pass | Judge pass |
| --- | --- | --- | --- | --- |
| items.label_correct | single | 7 | 3 (43%) | 3 (43%) |
| items.label_correct | rules | 6 | 2 (33%) | 3 (50%) |
| items.label_correct | critic | 4 | 4 (100%) | 4 (100%) |
| items.label_correct | critic · reviewed draft | 3 | 2 (67%) | 3 (100%) |
| items.worth_showing | single | 10 | 7 (70%) | 7 (70%) |
| items.worth_showing | rules | 10 | 9 (90%) | 9 (90%) |
| items.worth_showing | critic | 6 | 4 (67%) | 5 (83%) |
| items.worth_showing | critic · reviewed draft | 4 | 4 (100%) | 4 (100%) |
| items.all | single | 10 | 5 (50%) | 5 (50%) |
| items.all | rules | 10 | 6 (60%) | 7 (70%) |
| items.all | critic | 6 | 4 (67%) | 5 (83%) |
| items.all | critic · reviewed draft | 4 | 3 (75%) | 4 (100%) |
| brief.supported | single | 10 | 9 (90%) | 10 (100%) |
| brief.supported | rules | 10 | 7 (70%) | 9 (90%) |
| brief.supported | critic | 6 | 5 (83%) | 6 (100%) |
| brief.supported | critic · reviewed draft | 4 | 3 (75%) | 3 (75%) |
| brief.not_overstated | single | 3 | 3 (100%) | 3 (100%) |
| brief.not_overstated | rules | 3 | 0 (0%) | 1 (33%) |
| brief.not_overstated | critic | 1 | 0 (0%) | 1 (100%) |
| brief.not_overstated | critic · reviewed draft | 2 | 1 (50%) | 1 (50%) |
| brief.all | single | 10 | 9 (90%) | 10 (100%) |
| brief.all | rules | 10 | 6 (60%) | 8 (80%) |
| brief.all | critic | 6 | 5 (83%) | 6 (100%) |
| brief.all | critic · reviewed draft | 4 | 2 (50%) | 2 (50%) |
