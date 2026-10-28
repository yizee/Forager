# Judge calibration sheet

Made 2026-10-28 from digest-modes-20261028-151959.jsonl, digest-modes-20261028-152801.jsonl.

Label every row before you look at any judge output, and open `key.json` only when you have finished: it says which mode each row came from. Do not change a label after seeing the judge's answer; if one was a slip, say so in the note column instead.

Open each CSV in a spreadsheet. In every empty criterion column write `y` (passes) or `n` (fails); `n/a` marks criteria that do not apply to the row. Use `note` for anything you are unsure about. Save as CSV with the same columns.

| Sheet | Rows |
| --- | --- |
| `items.csv` | 30 |
| `brief.csv` | 30 |

## The user's interests

- **AI agents** (long-term interest): Agent frameworks and tooling, Agent benchmarks and evaluation, Coding agents
- **Video editing** (long-term interest): AI-assisted editing tools, Open-source editing pipelines
- **Image generation** (long-term interest): Diffusion model research, Controllable generation (editing, inpainting), New model releases
- **AI copyright policy** (long-term interest)
- **Sora 2** (short-term focus)
- **3D generation** (long-term interest)

## `items.csv` criteria (the judge gets the same text)

- `label_correct`: Interest matches only. The source text is mainly about the named interest, or about one of that interest's facets. Work on a neighbouring topic, or work that mentions the interest only in passing, fails.
- `worth_showing`: Every item. Given all of the user's interests, the user would plausibly want to see this item today. Judge the item itself, not where it was filed. For a breadth item, the stated reason must also be true of the source text and give a real link to the user's interests or a plausible new direction for them; a shared word or an invented link fails.

## `brief.csv` criteria (the judge gets the same text)

- `supported`: Points and connections. Each factual claim in the entry is stated in, or follows directly from, the source texts of the items it cites. Names, numbers, rankings and results must match, and a claim that needs a source the entry does not cite fails. Framing words such as "notable" are fine when the sources bear them out.
- `not_overstated`: Connections only. The link the connection draws between its items is no stronger than the sources allow: a loose analogy presented as a shared method, a dependency, a trend or a consequence fails.
