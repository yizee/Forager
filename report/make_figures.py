"""Figures for the report that are not screenshots of the showcase (report/shots.mjs makes those).

- figures/modes.svg: the three digest modes, mean and bootstrap 95% interval per metric, read from the
  tables in docs/stage5-results.md so the figure cannot drift from the reported numbers.
- figures/setup-options.png, figures/setup-profile.png: the Idea 1 screens, cropped from the frames of the
  recorded demo video (video/build/frames, kept locally and not committed). Only with --crop-video: every
  recording makes a new live call, so a later render may show other options than the report describes.

Run: .venv/bin/python report/make_figures.py [--crop-video]
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIGURES = ROOT / "report" / "figures"
RESULTS = ROOT / "docs" / "stage5-results.md"
FRAMES = ROOT / "video" / "build" / "frames"

# Crops in frame pixels (1920 x 1080), clear of the video's caption and label overlays.
CROPS = {
    "setup-options": ("f00840.jpg", (455, 120, 1660, 822)),
    "setup-profile": ("f01180.jpg", (455, 105, 1830, 790)),
}

INK, MUTED, GRID, SERIES = "#1e1c17", "#6b675e", "#e4e1d8", "#2a78d6"
FONT = "Helvetica Neue, Helvetica, Arial, sans-serif"


def mode_rows() -> dict:
    """{mode: {column: (mean, low, high)}} from the per-mode table in section 2 of the results."""
    text = RESULTS.read_text()
    section = text[text.index("## 2. Idea 3"):text.index("## 3. Idea 2")]
    lines = [l for l in section.splitlines() if l.startswith("|")]
    header = [c.strip() for c in lines[0].strip("|").split("|")]
    rows = {}
    for line in lines[2:]:
        cells = [c.strip() for c in line.strip("|").split("|")]
        if cells[0] not in ("single", "rules", "critic"):
            break
        values = {}
        for name, cell in zip(header[1:], cells[1:]):
            m = re.fullmatch(r"([\d.]+)%? \[([\d.]+), ([\d.]+)\]", cell)
            if m:
                values[name] = tuple(float(x) for x in m.groups())
        rows[cells[0]] = values
    return rows


def modes_svg(rows: dict) -> str:
    panels = [("Breadth share", "Breadth items, % of items", "code"),
              ("Worth showing", "Items worth showing, %", "judge, κ 0.89"),
              ("Label accuracy", "Interest labels correct, %", "judge, κ 0.79")]
    modes = [("single", "Single agent"), ("rules", "Team + rules"), ("critic", "Team + rules + Critic")]
    width, label_w, gap, right, top, row_h = 600, 96, 30, 10, 34, 22
    panel_w = (width - label_w - right - gap * (len(panels) - 1)) / len(panels)
    height = top + row_h * len(modes) + 26
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" font-family="{FONT}">',
           f'<rect width="{width}" height="{height}" fill="#ffffff"/>']
    for k, (_, name) in enumerate(modes):
        y = top + row_h * k + row_h / 2
        out.append(f'<text x="{label_w - 8}" y="{y + 3.2}" font-size="9" fill="{INK}" text-anchor="end">{name}</text>')
    for p, (column, title, note) in enumerate(panels):
        x0 = label_w + p * (panel_w + gap)
        sx = lambda v: x0 + panel_w * v / 100
        out.append(f'<text x="{x0}" y="12" font-size="9.2" font-weight="600" fill="{INK}">{title}</text>')
        out.append(f'<text x="{x0}" y="23" font-size="8" fill="{MUTED}">{note}</text>')
        for tick in (0, 25, 50, 75, 100):
            out.append(f'<line x1="{sx(tick):.1f}" y1="{top - 2}" x2="{sx(tick):.1f}" y2="{top + row_h * len(modes)}" '
                       f'stroke="{GRID}" stroke-width="1"/>')
            out.append(f'<text x="{sx(tick):.1f}" y="{top + row_h * len(modes) + 11}" font-size="8" fill="{MUTED}" '
                       f'text-anchor="middle">{tick}</text>')
        for k, (mode, _) in enumerate(modes):
            mean, low, high = rows[mode][column]
            y = top + row_h * k + row_h / 2
            out.append(f'<line x1="{sx(low):.1f}" y1="{y}" x2="{sx(high):.1f}" y2="{y}" stroke="{SERIES}" '
                       f'stroke-width="2" stroke-linecap="round" stroke-opacity="0.45"/>')
            out.append(f'<circle cx="{sx(mean):.1f}" cy="{y}" r="4.2" fill="{SERIES}" stroke="#ffffff" stroke-width="2"/>')
            out.append(f'<text x="{sx(mean):.1f}" y="{y - 6.5}" font-size="7.8" fill="{INK}" text-anchor="middle">'
                       f'{mean:g}</text>')
    out.append("</svg>")
    return "\n".join(out)


def crop_frames() -> None:
    if not FRAMES.exists():
        print("video frames not found: keeping the existing setup screenshots")
        return
    from PIL import Image
    for name, (frame, box) in CROPS.items():
        Image.open(FRAMES / frame).crop(box).save(FIGURES / f"{name}.png", optimize=True)
        print(f"figures/{name}.png from {frame}")


if __name__ == "__main__":
    FIGURES.mkdir(parents=True, exist_ok=True)
    rows = mode_rows()
    (FIGURES / "modes.svg").write_text(modes_svg(rows))
    print("figures/modes.svg:", {m: {c: v[0] for c, v in r.items()} for m, r in rows.items()})
    if "--crop-video" in sys.argv:
        crop_frames()
