#!/usr/bin/env node
// Records the Forager demo video. Drives Google Chrome (headless) over the DevTools protocol and writes one
// JPEG per frame, with the subtitles, a section label and a cursor drawn into the page; narration comes from
// macOS `say`. video/encode.swift then turns the frames and narration into MP4.
//
// Needs the showcase on :8765 and the demo Streamlit app on :8502 (.claude/launch.json "showcase" and
// "forager-demo"). Scene 2 makes one paid model call (the clarification step, about $0.001).
// Usage: node video/make_video.mjs [--scenes 1,3] [--voice video/voice]
//   --scenes  render only these scenes (default: all six)
//   --voice   narrate with your own takes (NN.wav from video/voice_studio.py, one per line of video/forager-demo.srt)
//             instead of the synthetic voice; the timing then follows your takes

import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const BUILD = path.join(ROOT, "video", "build");
const FRAMES = path.join(BUILD, "frames");
const AUDIO = path.join(BUILD, "audio");
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const SHOWCASE = "http://localhost:8765/index.html";
const STREAMLIT = "http://localhost:8502/";
const FPS = 30;
const VIEW = { width: 1536, height: 864, scale: 1.25 };   // CSS pixels; frames come out at 1920 x 1080
const VOICE = "Samantha", RATE = 172, GAP = 0.24;
const SENTENCE = "I'm an AI student who follows AI agents, video editing and image generation, and lately I've been following Sora 2 closely.";

// ---------- narration ----------
const audioSeconds = file => Number(/estimated duration: ([\d.]+)/.exec(spawnSync("afinfo", [file]).stdout.toString())[1]);
function tts(text, file) {
  const run = spawnSync("say", ["-v", VOICE, "-r", String(RATE), "-o", file, text]);
  if (run.status !== 0) throw new Error(`say failed: ${run.stderr}`);
  return audioSeconds(file);
}
// Your own takes, matched to the lines by their text, so a line the live scene leaves out cannot shift the rest.
const voiceArg = process.argv.indexOf("--voice");
const TAKES = voiceArg > 0 ? loadTakes(path.resolve(process.argv[voiceArg + 1])) : null;
function loadTakes(dir) {
  const takes = new Map(), missing = [];
  for (const block of fs.readFileSync(path.join(ROOT, "video", "forager-demo.srt"), "utf8").trim().split(/\n\s*\n/)) {
    const rows = block.split("\n");
    const file = path.join(dir, `${String(Number(rows[0]) - 1).padStart(2, "0")}.wav`);
    if (fs.existsSync(file)) takes.set(rows.slice(2).join(" ").trim(), file); else missing.push(rows[0]);
  }
  if (missing.length) throw new Error(`no take for line(s) ${missing.join(", ")} in ${dir}: record them in the studio first`);
  return takes;
}

// ---------- a minimal DevTools protocol client (Node's built-in WebSocket) ----------
class CDP {
  static async connect(url) {
    const ws = new WebSocket(url);
    await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
    return new CDP(ws);
  }
  constructor(ws) {
    this.ws = ws; this.next = 0; this.pending = new Map(); this.listeners = new Map();
    ws.onmessage = event => {
      const msg = JSON.parse(event.data);
      if (msg.id) {
        const wait = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        if (msg.error) wait.reject(new Error(`${wait.method}: ${msg.error.message}`)); else wait.resolve(msg.result);
      } else (this.listeners.get(msg.method) || []).forEach(fn => fn(msg.params));
    };
  }
  send(method, params = {}) {
    const id = ++this.next;
    this.ws.send(JSON.stringify({ id, method, params }));
    return new Promise((resolve, reject) => this.pending.set(id, { resolve, reject, method }));
  }
  once(method) {
    return new Promise(resolve => {
      const fn = params => { this.listeners.set(method, (this.listeners.get(method) || []).filter(f => f !== fn)); resolve(params); };
      this.listeners.set(method, [...(this.listeners.get(method) || []), fn]);
    });
  }
}

// ---------- what is drawn over every page: subtitles, label, cursor, click ring, title and end cards ----------
const bee = `data:image/svg+xml;base64,${fs.readFileSync(path.join(ROOT, "showcase", "bee.svg")).toString("base64")}`;
const OVERLAY = `(() => {
  if (window.__rec) return;
  Element.prototype.scrollIntoView = function () {};          // the recorder animates scrolling itself
  const css = \`
    #rec-layer{position:fixed;inset:0;pointer-events:none;z-index:2147483647;font-family:-apple-system,system-ui,"Segoe UI",sans-serif}
    #rec-caption{position:absolute;left:50%;bottom:34px;transform:translateX(-50%);max-width:1080px;width:max-content;padding:10px 20px;
      border-radius:12px;background:rgba(22,21,18,.84);color:#fff;font-size:25px;line-height:1.38;font-weight:500;text-align:center}
    #rec-caption:empty{display:none}
    #rec-label{position:absolute;left:30px;bottom:124px;padding:9px 15px;border-radius:11px;background:rgba(47,106,61,.95);color:#fff;
      font-size:17px;font-weight:650;max-width:760px;line-height:1.3}
    #rec-label small{display:block;font-size:13.5px;font-weight:500;opacity:.88;margin-top:3px}
    #rec-label:empty{display:none}
    #rec-cursor{position:absolute;left:0;top:0;width:24px;height:24px;margin:-2px 0 0 -3px;filter:drop-shadow(0 1.5px 2.5px rgba(0,0,0,.35))}
    #rec-ring{position:absolute;width:40px;height:40px;margin:-20px 0 0 -20px;border-radius:50%;border:3px solid #2f6a3d;opacity:0}
    #rec-card{position:absolute;inset:0;display:none;flex-direction:column;align-items:center;justify-content:center;gap:14px;
      background:#f4f1e8;color:#1e1c17;text-align:center}
    #rec-card img{width:150px;height:150px}
    #rec-card .t{font-family:"Iowan Old Style",Georgia,serif;font-size:74px;font-weight:600;letter-spacing:-.02em;line-height:1}
    #rec-card .s{font-size:24px;color:#545046}
    #rec-card .b{font-size:16px;color:#7d786c;margin-top:18px;letter-spacing:.04em}
  \`;
  const style = document.createElement("style"); style.textContent = css;
  const layer = document.createElement("div"); layer.id = "rec-layer";
  layer.innerHTML = '<div id="rec-card"><img alt=""><div class="t">Forager</div><div class="s"></div><div class="b"></div></div>' +
    '<div id="rec-label"></div><div id="rec-caption"></div><div id="rec-ring"></div>' +
    '<svg id="rec-cursor" viewBox="0 0 24 24"><path d="M4 2.5v17.2l4.6-4.4 3 6.6 2.9-1.3-3-6.5h6.4z" fill="#111" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>';
  const mount = () => { (document.body || document.documentElement).append(style, layer); };
  if (document.body) mount(); else document.addEventListener("DOMContentLoaded", mount);
  const $ = id => layer.querySelector(id);
  let last = {};
  window.__rec = { set(s) {
    if (!layer.isConnected) mount();
    if (s.caption !== last.caption) $("#rec-caption").textContent = s.caption;
    const label = s.label ? s.label.title + "|" + (s.label.note || "") : "";
    if (label !== last.label) {
      const el = $("#rec-label"); el.textContent = "";
      if (s.label) { el.append(s.label.title); if (s.label.note) { const n = document.createElement("small"); n.textContent = s.label.note; el.append(n); } }
    }
    const c = $("#rec-cursor"); c.style.transform = "translate(" + s.cursor[0] + "px," + s.cursor[1] + "px)";
    c.style.opacity = s.cursorHidden ? 0 : 1;
    const r = $("#rec-ring");
    if (s.ring) { r.style.left = s.ring.x + "px"; r.style.top = s.ring.y + "px"; r.style.opacity = 1 - s.ring.p; r.style.transform = "scale(" + (0.5 + s.ring.p) + ")"; }
    else r.style.opacity = 0;
    const card = $("#rec-card");
    if (s.card) {
      card.style.display = "flex"; card.style.opacity = s.card.opacity;
      card.querySelector("img").src = "${bee}";
      card.querySelector(".s").textContent = s.card.sub; card.querySelector(".b").textContent = s.card.by;
    } else card.style.display = "none";
    last = { caption: s.caption, label };
  } };
})();`;
// Streamlit's own chrome (Deploy button, running indicator) is hidden so the app reads cleanly on video.
const STREAMLIT_CSS = `[data-testid="stToolbar"],[data-testid="stStatusWidget"],[data-testid="stDecoration"]{visibility:hidden!important}`;

// ---------- the director: every action advances video time by whole frames ----------
const ease = p => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2);
class Director {
  constructor(cdp) {
    this.cdp = cdp; this.frame = 0; this.cursor = [VIEW.width * 0.62, VIEW.height * 0.55]; this.cursorHidden = false;
    this.captions = []; this.audio = []; this.narrationEnd = 0; this.label = null; this.cards = []; this.ring = null;
    this.scroller = "window"; this.keep = [];
  }
  get t() { return this.frame / FPS; }
  async js(expression) {
    const r = await this.cdp.send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
    if (r.exceptionDetails) throw new Error(`page error: ${r.exceptionDetails.exception?.description || r.exceptionDetails.text}`);
    return r.result.value;
  }
  cardAt(t) {
    for (const c of this.cards) {
      if (t >= c.start && t < c.end) {
        const fadeIn = c.fadeIn ? Math.min(1, (t - c.start) / c.fadeIn) : 1;
        const fadeOut = c.fadeOut ? Math.min(1, (c.end - t) / c.fadeOut) : 1;
        return { opacity: Math.min(fadeIn, fadeOut), sub: c.sub, by: c.by };
      }
    }
    return null;
  }
  async capture() {
    const t = this.t;
    const caption = this.captions.find(c => t >= c.start && t < c.end);
    let ring = null;
    if (this.ring && t - this.ring.start < 0.45) ring = { x: this.ring.x, y: this.ring.y, p: (t - this.ring.start) / 0.45 };
    for (const k of this.keep) await this.js(k);
    const state = { caption: caption ? caption.text : "", label: this.label, cursor: this.cursor, cursorHidden: this.cursorHidden, ring, card: this.cardAt(t) };
    await this.js(`window.__rec && window.__rec.set(${JSON.stringify(state)})`);
    const { data } = await this.cdp.send("Page.captureScreenshot", { format: "jpeg", quality: 90 });
    fs.writeFileSync(path.join(FRAMES, `f${String(this.frame).padStart(5, "0")}.jpg`), Buffer.from(data, "base64"));
    this.frame += 1;
  }
  async frames(n, each) { for (let i = 0; i < n; i++) { if (each) await each(i, n); await this.capture(); } }
  async hold(seconds) { await this.frames(Math.max(0, Math.round(seconds * FPS))); }
  async say(text, spoken = text.replace(/Sora 2/g, "Sora two")) {
    if (this.t < this.narrationEnd + GAP) await this.hold(this.narrationEnd + GAP - this.t);
    let file = path.join(AUDIO, `n${String(this.audio.length).padStart(2, "0")}.aiff`), duration;
    if (TAKES) {
      file = TAKES.get(text.trim());
      if (!file) throw new Error(`no recorded take for "${text}" (the live scene may have suggested another field: run again)`);
      duration = audioSeconds(file);
    } else duration = tts(spoken, file);
    this.audio.push({ file, start: this.t, duration, text });
    this.captions.push({ text, start: this.t, end: this.t + duration + 0.2 });
    this.narrationEnd = this.t + duration;
  }
  async spoken(extra = 0) { const end = this.narrationEnd + extra; if (this.t < end) await this.hold(end - this.t); }
  async mouse(type, extra = {}) {
    await this.cdp.send("Input.dispatchMouseEvent", { type, x: this.cursor[0], y: this.cursor[1],
      button: type === "mouseMoved" && !extra.buttons ? "none" : "left", clickCount: type === "mouseMoved" ? 0 : 1, ...extra });
  }
  async moveTo(x, y, seconds = 0.7, extra = {}) {
    const [x0, y0] = this.cursor, n = Math.max(1, Math.round(seconds * FPS));
    await this.frames(n, async i => { const p = ease((i + 1) / n); this.cursor = [x0 + (x - x0) * p, y0 + (y - y0) * p]; await this.mouse("mouseMoved", extra); });
  }
  async rect(expr) {
    const r = await this.js(`(() => { const el = ${expr}; if (!el) return null; const b = el.getBoundingClientRect(); return { x: b.x, y: b.y, w: b.width, h: b.height }; })()`);
    if (!r) throw new Error(`no element for ${expr}`);
    return r;
  }
  async point(expr, fx = 0.5, fy = 0.5) {
    await this.reveal(expr);
    const r = await this.rect(expr);
    return [r.x + r.w * fx, r.y + r.h * fy];
  }
  async moveToEl(expr, seconds = 0.7, fx = 0.5, fy = 0.5) { const [x, y] = await this.point(expr, fx, fy); await this.moveTo(x, y, seconds); }
  async click() {
    await this.mouse("mousePressed");
    this.ring = { start: this.t, x: this.cursor[0], y: this.cursor[1] };
    await this.hold(2 / FPS);
    await this.mouse("mouseReleased");
    await this.hold(0.25);
  }
  scrollExpr() { return this.scroller === "window" ? "document.scrollingElement" : `document.querySelector('${this.scroller}')`; }
  async scrollTo(top, seconds = 0.9) {
    const from = await this.js(`${this.scrollExpr()}.scrollTop`);
    const n = Math.max(1, Math.round(seconds * FPS));
    await this.frames(n, async i => {
      const y = from + (top - from) * ease((i + 1) / n);
      await this.js(`${this.scrollExpr()}.scrollTop = ${y}`);
      await this.mouse("mouseMoved");
    });
  }
  async reveal(expr, where = 0.42) {   // scroll so the element sits clear of the subtitles
    const r = await this.rect(expr);
    if (r.y >= 70 && r.y + r.h <= VIEW.height - 190) return;
    const top = await this.js(`${this.scrollExpr()}.scrollTop`);
    await this.scrollTo(Math.max(0, top + r.y + r.h / 2 - VIEW.height * where), 0.9);
  }
  async type(text, seconds) {
    const n = Math.max(1, Math.round(seconds * FPS));
    let done = 0;
    await this.frames(n, async i => {
      const upto = Math.round(text.length * (i + 1) / n);
      if (upto > done) { await this.cdp.send("Input.insertText", { text: text.slice(done, upto) }); done = upto; }
    });
  }
  async key(key, code, keyCode) {
    await this.cdp.send("Input.dispatchKeyEvent", { type: "keyDown", key, code, windowsVirtualKeyCode: keyCode });
    await this.cdp.send("Input.dispatchKeyEvent", { type: "keyUp", key, code, windowsVirtualKeyCode: keyCode });
  }
  async waitFor(expr, timeout = 120000) {   // off camera: no frames while waiting
    const until = Date.now() + timeout;
    while (Date.now() < until) {
      if (await this.js(`!!(${expr})`)) return;
      await new Promise(r => setTimeout(r, 300));
    }
    throw new Error(`timed out waiting for ${expr}`);
  }
  async open(url, settle = 900) {
    // A fresh query string makes every visit a full load, so the load event always fires (a hash-only change would not).
    const [base, hash = ""] = url.split("#");
    const fresh = `${base}${base.includes("?") ? "&" : "?"}rec=${Date.now()}${hash ? `#${hash}` : ""}`;
    const loaded = this.cdp.once("Page.loadEventFired");
    await this.cdp.send("Page.navigate", { url: fresh });
    await Promise.race([loaded, new Promise((_, reject) => setTimeout(() => reject(new Error(`no load event for ${url}`)), 30000))]);
    await new Promise(r => setTimeout(r, settle));
  }
}

// ---------- the six scenes ----------
const text = expr => `[...document.querySelectorAll('${expr}')]`;
const byText = (selector, words) => `${text(selector)}.find(el => el.textContent.trim().startsWith(${JSON.stringify(words)}))`;

async function scene1(v) {
  v.label = null;
  await v.open(`${SHOWCASE}#brief`);
  v.scroller = "window";
  v.cursorHidden = true;
  v.cards.push({ start: v.t, end: v.t + 3.4, fadeOut: 0.5, sub: "A daily AI brief that stays broad", by: "SHI YIZE · CS 619 Human-AI Interaction" });
  await v.hold(0.5);
  await v.say("Keeping up with AI news, papers and tools is hard,");
  await v.hold(2.4);
  v.cursorHidden = false;
  await v.say("and most feeds quietly narrow to what you clicked last week.");
  await v.scrollTo(260, 3.2);
  await v.say("Forager keeps me in the loop: a daily brief that stays broad, shows its sources, and asks before it learns.");
  await v.moveToEl(byText(".point", "BrickWright"), 1.2, 0.3, 0.3);
  await v.spoken(0.35);
}

async function scene2(v) {
  await v.open(STREAMLIT, 2500);
  await v.waitFor(byText('[data-testid="stSidebar"] label', "Set up"));
  await v.js(`(() => { const s = document.createElement("style"); s.textContent = ${JSON.stringify(STREAMLIT_CSS)}; document.head.append(s); })()`);
  v.scroller = '[data-testid="stMain"]';
  v.label = { title: "Idea 1 · Intent expression: options, not more typing", note: "Live in the Streamlit app" };
  await v.hold(0.4);
  await v.moveToEl(byText('[data-testid="stSidebar"] label', "Set up"), 0.8);
  await v.click();
  await v.waitFor('document.querySelector(\'[data-testid="stTextArea"] textarea\')');
  await v.say("Setup starts with one sentence about me.");
  await v.moveToEl('document.querySelector(\'[data-testid="stTextArea"] textarea\')', 0.6, 0.2, 0.4);
  await v.click();
  await v.type(SENTENCE, 3.0);
  await v.key("Tab", "Tab", 9);
  await v.waitFor(`!${byText("button", "Continue")}.disabled`, 20000);
  await v.moveToEl(byText("button", "Continue"), 0.6);
  await v.click();
  await v.waitFor(byText('[data-testid="stHeading"], h3', "A few quick questions"), 150000);   // the model call, off camera
  await v.waitFor("document.querySelectorAll('[data-testid=\"stButtonGroup\"]').length > 1", 20000);
  await new Promise(r => setTimeout(r, 1200));
  const groups = await v.js(`[...document.querySelectorAll('[data-testid="stButtonGroup"]')].map((g, i) => {
      const wrap = g.closest('[data-testid="stElementContainer"]') || g.parentElement;
      const label = wrap.querySelector('[data-testid="stWidgetLabel"]');
      return { i, label: label ? label.textContent.trim() : "", options: [...g.querySelectorAll("button")].map(b => b.textContent.trim()) };
    })`);
  fs.writeFileSync(path.join(BUILD, "clarification.json"), JSON.stringify(groups, null, 2));
  const pill = (g, j) => `document.querySelectorAll('[data-testid="stButtonGroup"]')[${g}].querySelectorAll("button")[${j}]`;
  const adjacent = groups.find(g => g.label.startsWith("You might also like"));
  const shortTerm = groups.find(g => g.label.startsWith("You mentioned"));
  const directions = groups.filter(g => g !== adjacent && g !== shortTerm);
  await v.say("Instead of asking me to write more, Forager splits it into directions");
  await v.moveToEl(pill(directions[0].i, 0), 0.8);
  await v.click();
  if (directions[0].options.length > 1) { await v.moveToEl(pill(directions[0].i, 1), 0.5); await v.click(); }
  await v.say("and asks about each with options to click, because recognizing what I want is easier than recalling it.");
  for (const d of directions.slice(1, 3)) { await v.moveToEl(pill(d.i, 0), 0.7); await v.click(); }
  let pick = adjacent ? adjacent.options.findIndex(o => /copyright/i.test(o)) : -1;
  if (adjacent && pick < 0) pick = 0;
  if (adjacent) {
    await v.say(`It suggests nearby fields too, like ${adjacent.options[pick].replace(/\s+/g, " ")},`);
    await v.moveToEl(pill(adjacent.i, pick), 0.9);
    await v.click();
  }
  const sora = shortTerm ? shortTerm.options.findIndex(o => /sora/i.test(o)) : -1;
  if (sora >= 0) {
    await v.say("and offers to follow Sora 2 for two weeks only.");
    await v.moveToEl(pill(shortTerm.i, sora), 0.8);
    await v.click();
  }
  await v.spoken(0.1);
  await v.moveToEl(byText("button", "Build my profile"), 0.7);
  await v.click();
  await v.waitFor(byText('[data-testid="stHeading"], h3', "Your profile"), 20000);
  await new Promise(r => setTimeout(r, 1500));
  await v.say("Nothing I don't pick goes into my profile,");
  await v.reveal(byText('[data-testid="stHeading"], h3', "Your profile"), 0.22);
  await v.moveToEl('document.querySelector(\'[data-testid="stDataFrameGlideDataEditor"]\') || document.querySelector(\'[data-testid="stDataFrame"]\')', 0.9, 0.35, 0.35);
  await v.say("and tracking stays off until I turn it on.");
  await v.moveToEl('document.querySelector(\'[data-testid="stCheckbox"]\')', 0.9, 0.06, 0.5);
  await v.spoken(0.35);
}

async function scene3(v) {
  await v.open(`${SHOWCASE}#brief`);
  v.scroller = "window";
  v.label = { title: "Verifiable output: every point cites its items", note: "Recorded digest · 27 Oct (rules and Critic mode)" };
  await v.say("Each morning I get a two-layer brief.");
  await v.scrollTo(150, 1.2);
  await v.moveToEl(byText(".point", "Agent tooling"), 0.9, 0.35, 0.3);
  await v.say("Every point cites the items behind it:");
  const chip = `document.querySelector('.cite[aria-label^="Open p08"]')`;
  await v.moveToEl(chip, 1.0);
  await v.spoken(0.1);
  await v.say("click one to check the source myself.");
  await v.click();
  v.keep.push(`document.getElementById("item-p08").classList.add("flash")`);
  const card = await v.rect(`document.getElementById("item-p08")`);
  const top = await v.js("document.scrollingElement.scrollTop");
  await v.scrollTo(top + card.y + card.h / 2 - VIEW.height * 0.42, 1.0);
  await v.moveToEl(`document.querySelector("#item-p08 .item-title")`, 0.8, 0.3, 0.5);
  await v.hold(0.5);
  await v.spoken(0.1);
  v.keep = [];
  await v.js(`document.getElementById("item-p08").classList.remove("flash")`);
  await v.say("And each item says why it is here:");
  await v.moveToEl(`document.querySelector("#item-p08 .pill")`, 0.8, 0.4, 0.5);
  await v.say("one of my interests, or breadth I didn't ask for.");
  await v.moveToEl(`document.querySelector("#item-n06 .pill")`, 1.4, 0.3, 0.5);
  await v.moveToEl(`document.querySelector("#item-n06 .reason-text")`, 0.8, 0.4, 0.5);
  await v.spoken(0.4);
}

async function scene4(v) {
  if (!(await v.js("location.href")).startsWith(SHOWCASE)) await v.open(`${SHOWCASE}#brief`);   // when scenes are rendered alone
  v.scroller = "window";
  v.label = { title: "Idea 2 · Memory with consent: nothing is written until you decide", note: "Proposals recorded from the memory agent (scenario runs, 28 Oct)" };
  await v.moveToEl(byText(".tab", "Interests"), 0.8);
  await v.click();
  await v.hold(0.3);
  const first = `document.querySelectorAll(".proposal")[0]`;
  await v.say("From my ratings, Forager may propose a change to my profile,");
  await v.moveToEl(`${first}.querySelector("h3")`, 0.9, 0.3, 0.5);
  await v.say("but it can't write anything itself: the system pauses until I decide, and the evidence comes from code, not the agent's words.");
  await v.scrollTo(230, 1.0);
  await v.moveToEl(`${first}.querySelector(".btn.primary")`, 0.9);
  await v.say("Here the evidence is camera control, a video survey and a video model, not Sora 2,");
  for (let k = 0; k < 4; k += 1) {
    if (k === 2) continue;   // the like repeats the first item
    await v.moveToEl(`${first}.querySelectorAll(".evidence li")[${k}].querySelector(".ev-title")`, 0.9, 0.35, 0.5);
    await v.hold(0.3);
  }
  await v.say("so I reject it and approve video generation.");
  await v.moveToEl(byText(".btn", "Reject"), 0.7);
  await v.click();
  const second = `[...document.querySelectorAll(".proposal")].find(p => p.querySelector(".btn.primary"))`;
  await v.moveToEl(`${second}.querySelector(".btn.primary")`, 0.9);
  await v.click();
  await v.hold(0.3);
  await v.moveToEl(`document.querySelector(".interest-row.new")`, 1.0, 0.3, 0.4);
  await v.spoken(0.35);
}

async function scene5(v) {
  v.scroller = "window";
  v.label = { title: "Idea 3 · Multi-agent + Critic: breadth you can see, checked twice", note: "A Manager and three source specialists write; code rules and a Critic check" };
  await v.moveToEl(byText(".tab", "Topics"), 0.8);
  await v.click();
  await v.hold(0.4);
  await v.say("Breadth stays visible: no topic may take more than forty percent,");
  await v.moveToEl(`document.querySelector("#panel-topics .chart svg .mark path")`, 0.9, 0.9, 0.5);
  await v.hold(0.5);
  await v.moveToEl(`document.querySelector("#panel-topics .threshold")`, 0.8, 0.5, 0.25);
  await v.say("and I set the exploration share.");
  const slider = `document.querySelector('#panel-topics input[type="range"]')`;
  const s = await v.rect(slider);
  await v.moveTo(s.x + s.w * 0.4, s.y + s.h / 2, 0.8);
  await v.mouse("mousePressed");
  await v.moveTo(s.x + s.w * 0.62, s.y + s.h / 2, 0.8, { buttons: 1 });
  await v.mouse("mouseReleased");
  await v.spoken(0.1);
  await v.say("A manager and three source specialists write it; code checks every digest, and a separate Critic checks meaning.");
  await v.moveToEl(byText(".tab", "Brief"), 0.7);
  await v.click();
  await v.hold(0.3);
  await v.moveToEl(`document.querySelector(".aside .card")`, 0.8, 0.45, 0.45);
  await v.hold(0.4);
  const issue = `document.querySelector(".aside .issue")`;
  await v.reveal(issue, 0.3);
  await v.moveToEl(issue, 0.8, 0.4, 0.3);
  await v.say("Here it caught a claim the source never made, and the point was rewritten.");
  await v.moveToEl(`document.querySelector(".aside .diff .before")`, 0.9, 0.5, 0.5);
  await v.hold(0.6);
  await v.moveToEl(`document.querySelector(".aside .diff .after")`, 0.8, 0.5, 0.5);
  await v.spoken(0.35);
}

async function scene6(v) {
  v.scroller = "window";
  v.label = { title: "Evaluation · 30 recorded digests", note: "Breadth items: single agent 23% → team with rules 36–38% · worth showing 87–88% in every mode" };
  await v.moveToEl(byText(".tab", "Evaluation"), 0.8);
  await v.click();
  await v.hold(0.3);
  await v.say("Across thirty recorded digests, the team with rules raised breadth from 23 to about 37 percent, with no loss in relevance.");
  await v.moveToEl(`document.querySelector("#panel-evaluation .tile")`, 0.8, 0.5, 0.5);
  const chart = `document.querySelector("#panel-evaluation .fig-grid .figure")`;
  await v.reveal(chart, 0.45);
  await v.moveToEl(`${chart}.querySelectorAll(".mark .ci-dot")[1]`, 0.9);
  await v.hold(0.5);
  await v.moveToEl(`document.querySelectorAll("#panel-evaluation .fig-grid .figure")[1].querySelectorAll(".mark .ci-dot")[1]`, 0.9);
  await v.say("The Critic caught 45 of 48 planted errors, but helped little on real digests.");
  await v.scrollTo(0, 0.9);
  await v.moveToEl(`document.querySelectorAll("#panel-evaluation .tile")[3]`, 0.9, 0.5, 0.55);
  await v.spoken(0.35);
  v.label = null;
  v.cursorHidden = true;
  v.cards.push({ start: v.t, end: v.t + 2.8, fadeIn: 0.4, sub: "Forage widely. Show your sources. Ask before you learn.", by: "SHI YIZE · CS 619 Human-AI Interaction" });
  await v.hold(2.8);
}

// ---------- run ----------
const SCENES = [scene1, scene2, scene3, scene4, scene5, scene6];
const pickArg = process.argv.indexOf("--scenes");
const chosen = pickArg > 0 ? process.argv[pickArg + 1].split(",").map(Number) : [1, 2, 3, 4, 5, 6];

fs.rmSync(FRAMES, { recursive: true, force: true });
fs.rmSync(AUDIO, { recursive: true, force: true });
fs.mkdirSync(FRAMES, { recursive: true });
fs.mkdirSync(AUDIO, { recursive: true });
for (const old of fs.readdirSync(BUILD).filter(name => name.startsWith("chrome-profile"))) {
  try { fs.rmSync(path.join(BUILD, old), { recursive: true, force: true, maxRetries: 3 }); } catch { /* still in use: leave it */ }
}
const profileDir = path.join(BUILD, `chrome-profile-${Date.now()}`);
// A real scale factor rather than emulated metrics: with emulated metrics, Chrome's synthetic mouse moves after each
// screenshot land at coordinates divided by the scale, which "leaves" whatever is hovered and hides its tooltip.
// The window is 87 px taller than the viewport it holds.
const chrome = spawn(CHROME, ["--headless=new", "--remote-debugging-port=9333", `--user-data-dir=${profileDir}`, "--no-first-run",
  "--no-default-browser-check", "--hide-scrollbars", "--mute-audio", "--force-color-profile=srgb",
  `--force-device-scale-factor=${VIEW.scale}`, `--window-size=${VIEW.width},${VIEW.height + 87}`, "about:blank"], { stdio: "ignore" });
try {
  let target;
  for (let i = 0; i < 60 && !target; i++) {
    try { target = (await (await fetch("http://127.0.0.1:9333/json/list")).json()).find(t => t.type === "page"); } catch { /* not up yet */ }
    if (!target) await new Promise(r => setTimeout(r, 250));
  }
  if (!target) throw new Error("Chrome did not start");
  const cdp = await CDP.connect(target.webSocketDebuggerUrl);
  await cdp.send("Page.enable");
  await cdp.send("Runtime.enable");
  const size = (await cdp.send("Runtime.evaluate", { expression: "[innerWidth, innerHeight, devicePixelRatio]", returnByValue: true })).result.value;
  if (size[0] !== VIEW.width || size[1] !== VIEW.height || size[2] !== VIEW.scale) {
    throw new Error(`viewport is ${size.join(" x ")}, wanted ${VIEW.width} x ${VIEW.height} at ${VIEW.scale}: adjust --window-size`);
  }
  await cdp.send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: "light" }] });
  await cdp.send("Page.addScriptToEvaluateOnNewDocument", { source: OVERLAY });
  const v = new Director(cdp);
  const started = Date.now();
  for (const n of chosen) {
    const before = v.t;
    await SCENES[n - 1](v);
    console.log(`scene ${n}: ${(v.t - before).toFixed(1)} s (video ends at ${v.t.toFixed(1)} s, ${((Date.now() - started) / 1000).toFixed(0)} s elapsed)`);
  }
  const srt = v.captions.map((c, i) => {
    const stamp = s => { const ms = Math.round(s * 1000); const h = Math.floor(ms / 3600000), m = Math.floor(ms / 60000) % 60, sec = Math.floor(ms / 1000) % 60;
      return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")},${String(ms % 1000).padStart(3, "0")}`; };
    return `${i + 1}\n${stamp(c.start)} --> ${stamp(Math.min(c.end, v.t))}\n${c.text}\n`;
  }).join("\n");
  fs.writeFileSync(path.join(BUILD, "forager-demo.srt"), srt);
  fs.writeFileSync(path.join(BUILD, "timeline.json"), JSON.stringify({ fps: FPS, frames: v.frame, duration: v.t,
    audio: v.audio.map(a => ({ file: a.file, start: a.start })) }, null, 1));
  console.log(`done: ${v.frame} frames, ${v.t.toFixed(1)} s of video, ${v.audio.length} narration lines` +
    (TAKES ? ", from the recorded takes" : ""));
  if (v.t > 120) console.log(`warning: the video is ${v.t.toFixed(1)} s, over two minutes: re-record the slowest lines`);
} finally {
  chrome.kill();
}
