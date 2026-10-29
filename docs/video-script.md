# Demo video script (2 minutes)

Due 2026-11-03. The video follows the typical user from CLAUDE.md §4: an AI student who follows AI agents, video editing and image generation, and lately Sora 2. It keeps the six beats of CLAUDE.md §9.

What is recorded where:

- **Live in the Streamlit app**: Idea 1, the clarification setup. This takes one paid call per take.
- **The showcase page** (`showcase/index.html`) for everything else.
  - It shows a recorded critic-mode digest from 27 October and proposals recorded from the memory agent.
  - A caption on screen says so. Nothing in the video claims a live run that did not happen.

The narration is about 270 words, about 135 words a minute. Times are targets; trim the pauses before the words.

## Script

### 0:00–0:15 · The problem

- **Screen**: The showcase header with the bee logo. Scroll slowly through the brief on the Brief tab.
- **On-screen text**: "Forager · a daily AI brief that stays broad".
- **Narration** (37 words):

> Keeping up with AI news, papers and tools is hard, and most feeds quietly narrow to what you clicked last week. Forager is a daily brief that stays broad, shows its sources, and asks before it learns.

### 0:15–0:45 · Idea 1: one sentence, then options to click

- **Screen**: The Streamlit app, *Set up* page.
  1. Type the sentence (below) and click *Continue*. Cut the spinner.
  2. Under "A few quick questions", click two or three options for each direction.
  3. Select a nearby field (for example *AI copyright policy*).
  4. Select Sora 2 under "Track them for 14 days?".
  5. Click *Build my profile*. Show the editable table: stated or inferred, long-term or short-term with its expiry date.
  6. Show the tracking toggles, all off.
- **On-screen text**: "Idea 1 · Clarification, not more typing".
- **Narration** (65 words):

> Setup starts with one sentence about me. Instead of asking me to write more, Forager splits it into directions and asks about each with options I can just click. It suggests nearby fields too, like AI copyright policy, and offers to follow Sora 2 for two weeks only. Nothing I don't pick goes into my profile, and tracking stays off until I turn it on.

If the live call suggests a different nearby field, name that one instead of AI copyright policy.

Sentence to type: *I'm an AI student who follows AI agents, video editing and image generation, and lately I've been following Sora 2 closely.*

### 0:45–1:10 · The two-layer brief

- **Screen**: Showcase, *Brief* tab.
  1. Hover over a point under "AI agents".
  2. Click its citation chip (for example `p08`). The page scrolls to the BrickWright card and highlights it.
  3. Point at the summary and the title link.
  4. Move to a Breadth card (for example `n06`) and its reason.
- **On-screen text**: "Recorded digest · 27 Oct". Then "Every point cites its items", then "Why you see this: interest match or breadth".
- **Narration** (57 words):

> Each morning I get a two-layer brief. Every point cites the items behind it: click one, and I land on the item, with a summary and a link to the source. And each item says why it is here: a match to one of my interests, or breadth, something next to them that I didn't ask for.

### 1:10–1:30 · Idea 2: memory you approve

- **Screen**: Showcase, *Interests* tab, right column.
  1. Show the first proposal: "Make Sora 2 a long-term interest".
  2. Slowly point along its evidence titles: WorldForge V2 (camera control), the video world-model survey, TencentARC/Looking-Ahead.
  3. Click *Reject*.
  4. On the second proposal, "Add Video generation", click *Approve*. The new interest appears on the left.
- **On-screen text**: "Idea 2 · Nothing is written until you decide". Then "Proposals recorded from the memory agent".
- **Narration** (47 words):

> From my ratings, Forager may propose a change to my profile, but it can't write anything itself: the tool pauses until I decide. Here the evidence is camera control, a video survey and a video model, not Sora 2, so I reject it and approve video generation.

### 1:30–1:50 · Idea 3: breadth you can see, checked twice

- **Screen**:
  1. Showcase, *Topics* tab: the topic chart with the "cap 4" line, then move the exploration slider.
  2. Switch to the *Brief* tab. Scroll the right column to "How this digest was checked" (all five rules ticked).
  3. Show the Critic card: "Unsupported citation · Point 7 · Connection 2", then the struck-through *before* and the new *after*.
- **On-screen text**: "Idea 3 · A Manager and 3 source specialists write; code rules and a Critic check".
- **Narration** (42 words):

> Breadth stays visible: no topic may take more than forty percent, and I set the exploration share. Code checks every digest, and then a separate Critic checks meaning. Here it caught a claim the source never made, and the point was rewritten.

### 1:50–2:00 · One result

- **Screen**: Showcase, *Evaluation* tab: the four tiles, then the "Share of breadth items" chart.
- **On-screen text**: "30 recorded digests · breadth items: single agent 23% → team with rules 36–38% · worth showing 87–88% in every mode". Last two seconds: the logo, "Forager", and "SHI YIZE · CS 619".
- **Narration** (24 words):

> Across thirty recorded digests, the team with rules raised breadth from 23 to about 37 percent, and items worth reading held at about 88.

## Recording checklist

### Before recording

- [ ] Check the budget: `cd ~/Desktop/Human-AI/forager-lab-own-key && ~/Desktop/Forager/.venv/bin/python agent.py --check`. Each setup take is one call, about $0.001.
- [ ] Start the app on a separate runtime folder, so that saving the setup does not overwrite `runtime/profile.json`:

  ```bash
  FORAGER_LAB_DIR=~/Desktop/Human-AI/forager-lab-own-key FORAGER_RUNTIME_DIR=/tmp/forager-demo .venv/bin/streamlit run forager/app.py
  ```

- [ ] Open the showcase in Chrome: `open showcase/index.html`. Set it to English and the light theme. The tabs open directly at `index.html#brief`, `#interests`, `#topics` and `#evaluation`.
- [ ] Use a 1440×900 window at 110–125% zoom. The brief keeps two columns down to 980 px wide.
- [ ] Prepare the screen:
  - Turn on Do Not Disturb.
  - Hide the bookmarks bar and the Dock.
  - Close other tabs.
  - Nothing secret may be on screen: no `.env`, no terminal showing keys.

### Recording

- [ ] Record the Streamlit setup first, because it is the only live part. Keep the best take.
- [ ] Then record the showcase shots in script order. Reload the page between takes; that resets approvals and ratings.
- [ ] Record the narration separately (QuickTime audio or the editor's voice-over). It is easier to time and to redo.
- [ ] Use macOS screen recording (Cmd+Shift+5, *Record Selected Portion*). Keep the cursor slow and deliberate.

### Editing

- [ ] Cut every wait: the setup spinner and page loads.
- [ ] Add the on-screen text from the script, one caption at a time, at the bottom or top-left.
- [ ] Keep the "recorded" captions on the brief and on the proposals.
- [ ] Check the total length is no more than 2:00, and that the narration and the clicks line up.
- [ ] Export 1080p MP4.

## Automated recording

The video can also be built without screen recording, from the same script.

- **`video/make_video.mjs`** drives Google Chrome (headless) over the DevTools protocol and writes one JPEG per frame at 1920×1080.
  - The subtitles, the section labels, a cursor and click rings are drawn into each frame.
  - The narration comes from the macOS `say` voice Samantha. Each subtitle is one narration line, timed to its audio.
  - Scene 2 runs the real setup in the Streamlit app, so it makes one paid call, about $0.001. The other scenes use the showcase page.
- **`video/encode.swift`** uses AVFoundation to turn the frames into H.264 and lay the narration lines at their start times. It writes:
  - `forager-demo.mp4`, with the narration;
  - `forager-demo-silent.mp4`, with subtitles but no sound, for recording your own voice-over;
  - `forager-demo.srt`, the subtitles as a separate file.

Commands (the showcase server and the demo app come from `.claude/launch.json`: "showcase" on port 8765, "forager-demo" on port 8502):

```bash
node video/make_video.mjs
swiftc -O -swift-version 5 video/encode.swift -o video/build/encode && video/build/encode video/build
```

Notes:

- The output goes to `video/build/`, which git ignores.
- `node video/make_video.mjs --scenes 3,4` renders only some scenes, for checking.
- Chrome runs with a real device scale factor, not emulated metrics. With emulated metrics, the mouse moves Chrome synthesizes after each screenshot land at the wrong coordinates and hide every hover tooltip.

## Facts behind the narration

These are the numbers and claims the narration relies on; all are in `docs/stage5-results.md`.

- **"The tool pauses until I decide"**: `propose_profile_update` uses `needs_approval=True`. In the evaluation, 0 of 9 approval-mode changes were written without approval.
- **"No topic may take more than forty percent"**: a hard rule in code. The recorded digest has AI agents 4/10 and breadth 4/10.
- **"A claim the source never made"**: the Critic's issue on `r08`. The source never says the method improves physics plausibility, and the revision removed that claim.
- **"From 23 to about 37 percent"**: breadth share for single agent 23%, rules 36%, rules + Critic 38%. The interval for rules − single is [+9, +18] points.
  - The contrast covers the specialist team and the rules together, which is why the narration says "the team with rules".
  - "Worth showing" is 87–88% in all three modes.
- The video does not claim that the Critic itself raised breadth or quality. End to end, critic − rules showed no measurable difference; that belongs in the report.
