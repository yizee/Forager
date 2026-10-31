#!/usr/bin/env node
// Screenshots of the static showcase for the report's figures. Drives headless Google Chrome over the DevTools
// protocol (Node's built-in WebSocket, as video/make_video.mjs does) and saves element crops at 2x.
// Usage: node report/shots.mjs              figures into report/figures/
//        node report/shots.mjs --survey DIR  one full-page shot per showcase tab into DIR, to choose crops

import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const OUT = path.join(ROOT, "report", "figures");
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const SHOWCASE = pathToFileURL(path.join(ROOT, "showcase", "index.html")).href;
const PORT = 9335, WIDTH = 1280, HEIGHT = 860, SCALE = 2;

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

const sleep = ms => new Promise(r => setTimeout(r, ms));
async function evaluate(cdp, expression) {
  const { result, exceptionDetails } = await cdp.send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
  if (exceptionDetails) throw new Error(`${expression.slice(0, 80)}: ${exceptionDetails.exception?.description || exceptionDetails.text}`);
  return result.value;
}
async function open(cdp, hash) {
  const loaded = cdp.once("Page.loadEventFired");
  await cdp.send("Page.navigate", { url: `${SHOWCASE}?shot=${Date.now()}#${hash}` });
  await loaded;
  await evaluate(cdp, "document.fonts.ready.then(() => true)");
  await sleep(400);
}
async function capture(cdp, clip, file) {
  const { data } = await cdp.send("Page.captureScreenshot", { format: "png", clip: { ...clip, scale: 1 }, captureBeyondViewport: true });
  fs.writeFileSync(file, Buffer.from(data, "base64"));
  console.log(`${path.relative(ROOT, file)}  ${Math.round(clip.width)} x ${Math.round(clip.height)} CSS px`);
}
// The union of the elements' boxes (page coordinates), with padding.
async function boxOf(cdp, script, pad = 12) {
  const r = await evaluate(cdp, `(() => { const els = (${script})().filter(Boolean);
    if (!els.length) throw new Error("nothing matched");
    const rs = els.map(e => e.getBoundingClientRect());
    const x = Math.min(...rs.map(r => r.left)), y = Math.min(...rs.map(r => r.top));
    const r = Math.max(...rs.map(r => r.right)), b = Math.max(...rs.map(r => r.bottom));
    return { x: x + scrollX, y: y + scrollY, width: r - x, height: b - y }; })()`);
  return { x: Math.max(0, r.x - pad), y: Math.max(0, r.y - pad), width: r.width + 2 * pad, height: r.height + 2 * pad };
}

// Each figure: the tab, optional setup, and a function returning the elements to frame.
// The checks and the Critic sit in a 340 px side column; widened here so each card reads at report size.
const WIDE_ASIDE = `(() => { const s = document.createElement("style");
  s.textContent = ".brief-grid{grid-template-columns:minmax(0,1fr) 560px!important}"; document.head.append(s); return true; })()`;
const FIGURES = [
  { name: "brief", hash: "brief",
    els: `() => [document.querySelector("#panel-brief .masthead"), document.querySelector("#panel-brief .brief-card")]` },
  { name: "items", hash: "brief",
    els: `() => [document.querySelector("#item-p05"), document.querySelector("#item-r08")]` },
  { name: "rules", hash: "brief", setup: WIDE_ASIDE,
    els: `() => [document.querySelectorAll("#panel-brief .brief-grid > :nth-child(2) > .card")[0]]` },
  { name: "critic", hash: "brief", setup: WIDE_ASIDE,
    els: `() => [document.querySelectorAll("#panel-brief .brief-grid > :nth-child(2) > .card")[1]]` },
  { name: "profile", hash: "interests",
    els: `() => [document.querySelector("#panel-interests .card:not(.proposal)")]` },
  { name: "proposal", hash: "interests",
    els: `() => [document.querySelector("#panel-interests .card.proposal")]` },
  { name: "topics", hash: "topics",
    els: `() => [document.querySelector("#panel-topics")]` },
];

const surveyArg = process.argv.indexOf("--survey");
const surveyDir = surveyArg > 0 ? path.resolve(process.argv[surveyArg + 1]) : null;
const profileDir = fs.mkdtempSync(path.join(os.tmpdir(), "forager-shots-"));
const chrome = spawn(CHROME, ["--headless=new", `--remote-debugging-port=${PORT}`, `--user-data-dir=${profileDir}`, "--no-first-run",
  "--no-default-browser-check", "--hide-scrollbars", "--force-color-profile=srgb", `--force-device-scale-factor=${SCALE}`,
  `--window-size=${WIDTH},${HEIGHT + 87}`, "about:blank"], { stdio: "ignore" });
try {
  let target;
  for (let i = 0; i < 60 && !target; i++) {
    try { target = (await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json()).find(t => t.type === "page"); } catch { /* not up yet */ }
    if (!target) await sleep(250);
  }
  if (!target) throw new Error("Chrome did not start");
  const cdp = await CDP.connect(target.webSocketDebuggerUrl);
  await cdp.send("Page.enable");
  await cdp.send("Runtime.enable");
  await cdp.send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: "light" }] });
  if (surveyDir) {
    fs.mkdirSync(surveyDir, { recursive: true });
    for (const hash of ["brief", "interests", "topics", "evaluation"]) {
      await open(cdp, hash);
      const h = await evaluate(cdp, "document.documentElement.scrollHeight");
      await capture(cdp, { x: 0, y: 0, width: WIDTH, height: h }, path.join(surveyDir, `${hash}.png`));
    }
  } else {
    fs.mkdirSync(OUT, { recursive: true });
    for (const f of FIGURES) {
      await open(cdp, f.hash);
      if (f.setup) await evaluate(cdp, f.setup);
      await capture(cdp, await boxOf(cdp, f.els, f.pad), path.join(OUT, `${f.name}.png`));
    }
  }
} finally {
  chrome.kill();
  try { fs.rmSync(profileDir, { recursive: true, force: true, maxRetries: 3 }); } catch { /* still in use */ }
}
