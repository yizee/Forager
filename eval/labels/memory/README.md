# Judge calibration sheet

Made 2026-10-28 from memory-20261028-163542.jsonl.

Label every row before you look at any judge output, and open `key.json` only when you have finished: it says which mode each row came from. Do not change a label after seeing the judge's answer; if one was a slip, say so in the note column instead.

Open each CSV in a spreadsheet. In every empty criterion column write `y` (passes) or `n` (fails); `n/a` marks criteria that do not apply to the row. Use `note` for anything you are unsure about. Save as CSV with the same columns.

| Sheet | Rows |
| --- | --- |
| `proposals.csv` | 18 |

## `proposals.csv` criteria (the judge gets the same text)

- `evidence_supports_change`: The cited signals justify this change, judged by what their items are actually about (titles and source texts, not where they were filed), and the user's other signals do not contradict it. Signals about other topics do not count, signals on a single item are not enough, and a low rating is evidence against an interest, not for it.
- `message_matches_change`: The message describes the same change as the code's description and states the evidence accurately: no wrong counts, scores or topics, and no claim the evidence does not show.

## Draft labels

Every criterion cell was pre-filled by fresh Claude agents (Opus 5.5), one per CSV, that saw only a copy of the CSV and README.md; the reason for each label is in `note`. Review every row: read the content, then the draft label and its reason, and change any label you disagree with (add your reason to the note). `draft-labels.json` keeps the draft, so the score can report how many labels you changed. Finish before you open `key.json` or any judge output.
