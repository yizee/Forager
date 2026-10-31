# Demo video script (2 minutes)

Due 2026-11-03. The video follows the typical user from CLAUDE.md §4: an AI student who follows AI agents, video editing and image generation, and lately Sora 2. It keeps the six beats of CLAUDE.md §9.

What is recorded where:

- **Live in the Streamlit app**: Idea 1, the clarification setup. This takes one paid call per take.
- **The showcase page** (`showcase/index.html`) for everything else.
  - It shows a recorded critic-mode digest from 27 October and proposals recorded from the memory agent.
  - A caption on screen says so. Nothing in the video claims a live run that did not happen.

The narration is about 295 words. The current cut is 1:58 long, voiced by Kokoro's Fenrir at 1.06× speed, with about 92 seconds of speech. Times are targets; trim the pauses before the words. In the last scene, the Critic line plays over the evaluation tile that shows 45 of 48.

The narration was revised on 2026-10-30 to state the course's lens, which is that the user stays in the loop, and to give each idea's reason. It also names the source specialists and answers the instructor's question about the Critic against the rules. The on-screen labels name the course concept behind each idea.

## Script

### 0:00–0:15 · The problem

- **Screen**: The showcase header with the bee logo. Scroll slowly through the brief on the Brief tab.
- **On-screen text**: "Forager · a daily AI brief that stays broad".
- **Narration** (41 words):

> Keeping up with AI news, papers and tools is hard, and most feeds quietly narrow to what you clicked last week. Forager keeps me in the loop: a daily brief that stays broad, shows its sources, and asks before it learns.

### 0:15–0:45 · Idea 1: one sentence, then options to click

- **Screen**: The Streamlit app, *Set up* page.
  1. Type the sentence (below) and click *Continue*. Cut the spinner.
  2. Under "A few quick questions", click two or three options for each direction.
  3. Select a nearby field (for example *AI copyright policy*).
  4. Select Sora 2 under "Track them for 14 days?".
  5. Click *Build my profile*. Show the editable table: stated or inferred, long-term or short-term with its expiry date.
  6. Show the tracking toggles, all off.
- **On-screen text**: "Idea 1 · Intent expression: options, not more typing".
- **Narration** (73 words):

> Setup starts with one sentence about me. Instead of asking me to write more, Forager splits it into directions and asks about each with options to click, because recognizing what I want is easier than recalling it. It suggests nearby fields too, like AI copyright policy, and offers to follow Sora 2 for two weeks only. Nothing I don't pick goes into my profile, and tracking stays off until I turn it on.

If the live call suggests a different nearby field, name that one instead of AI copyright policy.

Sentence to type: *I'm an AI student who follows AI agents, video editing and image generation, and lately I've been following Sora 2 closely.*

### 0:45–1:10 · The two-layer brief

- **Screen**: Showcase, *Brief* tab.
  1. Hover over a point under "AI agents".
  2. Click its citation chip (for example `p08`). The page scrolls to the BrickWright card and highlights it.
  3. Point at the title link.
  4. Move to a Breadth card (for example `n06`) and its reason.
- **On-screen text**: "Verifiable output: every point cites its items", noting "Recorded digest · 27 Oct".
- **Narration** (39 words):

> Each morning I get a two-layer brief. Every point cites the items behind it: click one to check the source myself. And each item says why it is here: one of my interests, or breadth I didn't ask for.

### 1:10–1:30 · Idea 2: memory you approve

- **Screen**: Showcase, *Interests* tab, right column.
  1. Show the first proposal: "Make Sora 2 a long-term interest".
  2. Slowly point along its evidence titles: WorldForge V2 (camera control), the video world-model survey, TencentARC/Looking-Ahead.
  3. Click *Reject*.
  4. On the second proposal, "Add Video generation", click *Approve*. The new interest appears on the left.
- **On-screen text**: "Idea 2 · Memory with consent: nothing is written until you decide", noting "Proposals recorded from the memory agent".
- **Narration** (57 words):

> From my ratings, Forager may propose a change to my profile, but it can't write anything itself: the system pauses until I decide, and the evidence comes from code, not the agent's words. Here the evidence is camera control, a video survey and a video model, not Sora 2, so I reject it and approve video generation.

### 1:30–1:50 · Idea 3: breadth you can see, checked twice

- **Screen**:
  1. Showcase, *Topics* tab: the topic chart with the "cap 4" line, then move the exploration slider.
  2. Switch to the *Brief* tab. Scroll the right column to "How this digest was checked" (all five rules ticked).
  3. Show the Critic card: "Unsupported citation · Point 7 · Connection 2", then the struck-through *before* and the new *after*.
- **On-screen text**: "Idea 3 · Multi-agent + Critic: breadth you can see, checked twice", noting "A Manager and three source specialists write; code rules and a Critic check".
- **Narration** (49 words):

> Breadth stays visible: no topic may take more than forty percent, and I set the exploration share. A manager and three source specialists write it; code checks every digest, and a separate Critic checks meaning. Here it caught a claim the source never made, and the point was rewritten.

### 1:50–2:00 · One result

- **Screen**: Showcase, *Evaluation* tab: the four tiles, then the "Share of breadth items" chart.
- **On-screen text**: "30 recorded digests · breadth items: single agent 23% → team with rules 36–38% · worth showing 87–88% in every mode". Last two seconds: the logo, "Forager", and "SHI YIZE · CS 619".
- **Narration** (35 words):

> Across thirty recorded digests, the team with rules raised breadth from 23 to about 37 percent, with no loss in relevance. The Critic caught 45 of 48 planted errors, but helped little on real digests.

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
- Nothing developer-facing is on screen. The Streamlit app hides the ledger line and the "paid" marks on its buttons unless `FORAGER_SHOW_COSTS=1` is set, and the showcase has no footer listing its source files (they stay in `showcase/data.js` as `source_files`).
- The final render (31 Oct, 1:59) is in `video/build/final/`. The 30 Oct version, which still showed those developer notes, is kept in `video/build/final/v1-2026-10-30/`.
- Chrome runs with a real device scale factor, not emulated metrics. With emulated metrics, the mouse moves Chrome synthesizes after each screenshot land at the wrong coordinates and hide every hover tooltip.

### Your own voice

The synthetic voice can be replaced with your own, one take per line.

1. Start the studio: `.venv/bin/python video/voice_studio.py`.
2. Open http://localhost:8766 in Chrome and allow the microphone.
3. Record each line:
   - **Space** starts and stops a take; recording again replaces it.
   - **P** plays it back.
   - **← and →** move between lines.
4. How takes are saved:
   - The studio trims the silence before and after each take and raises its peak to -1 dB.
   - Each take is saved as `video/voice/NN.wav`. Git ignores this folder, so the recordings stay on this machine.
5. Watch the projected speech time. With up to about 95 seconds of speech, the video stays within two minutes.
6. Build the video with your takes:

   ```bash
   node video/make_video.mjs --voice video/voice
   video/build/encode video/build
   ```

   - The takes are matched to the lines by their text, and each scene's timing follows your takes.
   - If the live setup scene suggests a field other than AI copyright policy, the recorder stops; run it again.

### An open-source voice (Kokoro)

`video/tts_kokoro.py` writes the same takes with Kokoro-82M, an Apache-2.0 text-to-speech model that runs locally.

- **Why not the macOS voice:** its output may be used freely, unlike the macOS system voices, whose licence (as we understand it) covers personal, non-commercial work only.
- **Where it runs:** it has its own environment, `video/build/tts-venv`, so the project's pinned packages stay as they are.
- **Model files:** `kokoro-v1.0.onnx` (326 MB) and `voices-v1.0.bin` (28 MB), from the kokoro-onnx releases on GitHub, in `video/build/kokoro`.
- **Pronunciation:** checked from the phonemes. "AI" is read as letters, "Sora 2" as "Sora two", and the numbers and "Critic" come out right.

```bash
video/build/tts-venv/bin/python video/tts_kokoro.py --samples af_heart,af_bella,am_michael,am_fenrir,bf_emma,bm_george --out video/build/samples
video/build/tts-venv/bin/python video/tts_kokoro.py --voice af_heart --out video/build/voice-af_heart
node video/make_video.mjs --voice video/build/voice-af_heart
video/build/encode video/build
```

## Facts behind the narration

These are the numbers and claims the narration relies on; all are in `docs/stage5-results.md`.

- **"Recognizing what I want is easier than recalling it"**: the design reason for Idea 1, which is recognition over recall.
- **"The system pauses until I decide"**: `propose_profile_update` uses `needs_approval=True`. In the evaluation, 0 of 9 approval-mode changes were written without approval.
- **"The evidence comes from code, not the agent's words"**: the change description and the evidence lines the user sees are generated by code from the arguments and the signal records. They are shown apart from the agent's message.
- **"No topic may take more than forty percent"**: a hard rule in code. The recorded digest has AI agents 4/10 and breadth 4/10.
- **"A claim the source never made"**: the Critic's issue on `r08`. The source never says the method improves physics plausibility, and the revision removed that claim.
- **"From 23 to about 37 percent"**: breadth share for single agent 23%, rules 36%, rules + Critic 38%. The interval for rules − single is [+9, +18] points.
  - The contrast covers the specialist team and the rules together, which is why the narration says "the team with rules".
  - "Worth showing" is 87–88% in all three modes, so there is "no loss in relevance": rules − single is +0 points [−7, +8], and that judge's kappa is 0.89.
- **"The Critic caught 45 of 48 planted errors, but helped little on real digests"**:
  - On the constructed case set (Stage 4), the Critic caught 45 of 48 problem instances (16 problems × 3 repeats), with no false alarms. The rules caught none.
  - On the first real digest, `live-01`, the Critic caught 0 of 12. End to end, no critic − rules interval excludes zero.
  - The video does not claim that the Critic raised breadth or quality.
