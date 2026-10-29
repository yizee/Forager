/* Forager showcase: renders window.FORAGER (showcase/data.js) into four views. Nothing here calls a
   model or saves anything: ratings, likes and approvals only change this page. */
(() => {
  "use strict";
  const D = window.FORAGER;
  const main = document.querySelector("main");
  if (!D) {
    main.textContent = "showcase/data.js is missing. Run: .venv/bin/python showcase/build_data.py";
    return;
  }

  // ---------- DOM helpers: every string goes in as text, never as HTML ----------
  const h = (tag, props, ...kids) => {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(props || {})) {
      if (value == null || value === false) continue;
      if (key === "class") node.className = value;
      else if (key === "text") node.textContent = value;
      else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
      else node.setAttribute(key, value === true ? "" : value);
    }
    for (const kid of kids.flat(Infinity)) {
      if (kid == null || kid === false) continue;
      node.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
    }
    return node;
  };
  const SVG_NS = "http://www.w3.org/2000/svg";
  const s = (tag, attrs, ...kids) => {
    const node = document.createElementNS(SVG_NS, tag);
    for (const [key, value] of Object.entries(attrs || {})) {
      if (value == null) continue;
      if (key === "text") node.textContent = value;
      else node.setAttribute(key, value);
    }
    for (const kid of kids.flat(Infinity)) if (kid) node.append(kid);
    return node;
  };
  const PATHS = {
    paper: "M4 1.5h5.5L13 5v9.5H4z M9.5 1.5V5H13 M6.5 8h4 M6.5 10.5h4",
    repo: "M5.5 4 2 8l3.5 4 M10.5 4 14 8l-3.5 4",
    news: "M2 3.5h9.5v9H3.5A1.5 1.5 0 0 1 2 11z M11.5 6H14v5.5a1.25 1.25 0 0 1-2.5 0 M4.5 6h4.5 M4.5 8.5h4.5 M4.5 11h3",
    check: "M3 8.5l3.2 3.2L13 4.8",
    cross: "M4.5 4.5l7 7 M11.5 4.5l-7 7",
    pen: "M3 13l.6-2.6 7.2-7.2 2 2-7.2 7.2z M9.4 4.6l2 2",
    moon: "M13.5 9.5A5.5 5.5 0 1 1 6.5 2.5a4.5 4.5 0 0 0 7 7z",
    sun: "M8 5a3 3 0 1 1 0 6 3 3 0 0 1 0-6z M8 1v1.5 M8 13.5V15 M1 8h1.5 M13.5 8H15 M3.1 3.1l1 1 M11.9 11.9l1 1 M3.1 12.9l1-1 M11.9 4.1l1-1",
  };
  const icon = name => s("svg", { viewBox: "0 0 16 16", class: "icon", "aria-hidden": "true" }, s("path", { d: PATHS[name] }));
  const store = {
    get(key) { try { return localStorage.getItem(key); } catch (e) { return null; } },
    set(key, value) { try { localStorage.setItem(key, value); } catch (e) { /* storage blocked: nothing to remember */ } },
  };

  // ---------- formatting ----------
  const pct = x => (x == null ? "–" : `${Math.round(x * 100)}%`);
  const signed = x => `${x >= 0 ? "+" : "−"}${Math.abs(Math.round(x * 100))}`;
  const interval = st => `${signed(st.mean)} pts [${signed(st.low)}, ${signed(st.high)}]`;
  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const day = iso => { const [y, m, d] = iso.slice(0, 10).split("-").map(Number); return new Date(Date.UTC(y, m - 1, d)); };
  const shortDate = iso => `${day(iso).getUTCDate()} ${MONTHS[day(iso).getUTCMonth()]}`;
  const longDate = iso => day(iso).toLocaleDateString("en-GB",
    { weekday: "long", day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });
  const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;
  const safeUrl = url => (/^https?:\/\//i.test(url || "") ? url : null);
  const TYPE = { paper: "Paper", repo: "Repository", news: "News" };
  const TYPES = { paper: ["paper", "papers"], repo: ["repository", "repositories"], news: ["news story", "news stories"] };
  const ISSUE = { irrelevant_exploration: "Irrelevant exploration", near_duplicate: "Near-duplicate",
    unsupported_citation: "Unsupported citation", overstated_connection: "Overstated connection",
    mislabeled_interest: "Mislabelled interest" };
  const refName = ref => {
    const m = /^(points|connections)\[(\d+)\]$/.exec(ref);
    return m ? `${m[1] === "points" ? "Point" : "Connection"} ${Number(m[2]) + 1}` : ref;
  };
  const tile = (label, value, sub) => h("div", { class: "card tile" }, h("div", { class: "tile-label", text: label }),
    h("div", { class: "tile-value", text: value }), sub ? h("div", { class: "tile-sub", text: sub }) : null);
  const key = (cls, text) => h("span", { class: "key" }, h("span", { class: `swatch ${cls}` }), text);
  const footNote = () => h("footer", { class: "panel-foot" }, "Showcase page built from recorded runs (",
    D.source_files.map((file, i) => [i ? ", " : "", h("code", { text: file })]),
    "). Nothing here calls a model, and ratings, likes and decisions are not saved.");

  // ---------- tooltip: values lead, labels follow; same on hover and focus ----------
  const tip = h("div", { class: "tooltip", role: "tooltip", hidden: true });
  document.body.append(tip);
  function attachTip(target, [value, label, extra], group) {
    const show = (x, y) => {
      tip.replaceChildren(h("strong", { text: value }), label ? h("span", { text: label }) : null,
        extra ? h("span", { class: "tip-extra", text: extra }) : null);
      tip.hidden = false;
      const { width, height } = tip.getBoundingClientRect();
      tip.style.left = `${Math.max(8, Math.min(window.innerWidth - width - 8, x + 14))}px`;
      tip.style.top = `${y - height - 12 < 8 ? y + 18 : y - height - 12}px`;
      if (group) group.classList.add("lift");
    };
    const hide = () => { tip.hidden = true; if (group) group.classList.remove("lift"); };
    target.addEventListener("pointermove", e => show(e.clientX, e.clientY));
    target.addEventListener("pointerleave", hide);
    target.addEventListener("focus", () => { const r = target.getBoundingClientRect(); show(r.left + r.width / 2, r.top); });
    target.addEventListener("blur", hide);
    if (!(target instanceof HTMLButtonElement)) target.setAttribute("tabindex", "0");
  }

  // ---------- charts: inline SVG, thin marks, one tooltip, a table view for each ----------
  const charts = [];
  const tableOf = (head, rows) => h("table", { class: "data-table" },
    h("thead", null, h("tr", null, head.map(t => h("th", { scope: "col", text: t })))),
    h("tbody", null, rows.map(row => h("tr", null, row.map((cell, i) => {
      const { text, cls } = typeof cell === "object" ? cell : { text: cell };
      return i === 0 ? h("th", { scope: "row", text }) : h("td", { class: cls, text });
    })))));
  function figure({ title, sub, legend, draw, table }) {
    const chart = h("div", { class: "chart", role: "img", "aria-label": title });
    const tableBox = h("div", { class: "table-wrap", hidden: true }, table());
    const toggle = h("button", { class: "link-btn", type: "button", "aria-pressed": "false", text: "Table" });
    toggle.addEventListener("click", () => {
      const showTable = tableBox.hidden;
      tableBox.hidden = !showTable;
      chart.hidden = showTable;
      toggle.textContent = showTable ? "Chart" : "Table";
      toggle.setAttribute("aria-pressed", String(showTable));
      if (!showTable) draw(chart);
    });
    const fig = h("figure", { class: "card figure" },
      h("div", { class: "fig-head" }, h("div", null, h("h3", { text: title }), sub ? h("p", { class: "fig-sub", text: sub }) : null), toggle),
      legend, chart, tableBox);
    charts.push({ fig, chart, draw });
    return fig;
  }
  const drawCharts = panel => charts.forEach(c => { if (panel.contains(c.fig) && !c.chart.hidden) c.draw(c.chart); });
  const widthOf = box => Math.max(260, Math.floor(box.clientWidth || 520));
  const barPath = (x0, y, w, height, r = 4) => {   // rounded at the data end, square at the baseline
    if (w <= 0) return "";
    const rr = Math.min(r, w, height / 2), x1 = x0 + w;
    return `M${x0},${y}H${x1 - rr}Q${x1},${y} ${x1},${y + rr}V${y + height - rr}Q${x1},${y + height} ${x1 - rr},${y + height}H${x0}Z`;
  };

  function dotChart(box, { rows, domain, ticks }) {
    const W = widthOf(box), rowH = 42, padL = W < 380 ? 104 : 128, padR = 52, top = 4, plotH = rows.length * rowH;
    const H = top + plotH + 24;
    const x = v => padL + ((v - domain[0]) / (domain[1] - domain[0])) * (W - padL - padR);
    const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, width: W, height: H });
    for (const t of ticks) svg.append(s("line", { class: "grid-line", x1: x(t), x2: x(t), y1: top, y2: top + plotH }),
      s("text", { class: "tick", x: x(t), y: H - 6, "text-anchor": "middle", text: pct(t) }));
    rows.forEach((r, i) => {
      const cy = top + i * rowH + rowH / 2;
      const g = s("g", { class: "mark" },
        s("text", { class: "row-label", x: padL - 12, y: cy + 4, "text-anchor": "end", text: r.label }),
        s("line", { class: "ci", x1: x(r.low), x2: x(r.high), y1: cy, y2: cy }),
        s("circle", { class: "ci-dot", cx: x(r.mean), cy, r: 5.5 }),
        s("text", { class: "value-label", x: x(r.high) + 8, y: cy + 4, text: pct(r.mean) }));
      const hit = s("rect", { class: "hit", x: 0, y: cy - rowH / 2, width: W, height: rowH });
      g.append(hit);
      attachTip(hit, [pct(r.mean), r.label, `95% interval ${pct(r.low)}–${pct(r.high)} · ${r.n} digests`], g);
      svg.append(g);
    });
    box.replaceChildren(svg);
  }

  function barChart(box, { rows, max, ticks, cap, format, above = false }) {
    const W = widthOf(box), barH = 18, rowH = above ? 46 : 34, padL = above ? 0 : (W < 380 ? 112 : 150), padR = 44;
    const top = cap ? 22 : 4, plotH = rows.length * rowH, H = top + plotH + (ticks ? 22 : 4);
    const x = v => padL + (v / max) * (W - padL - padR);
    const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, width: W, height: H });
    if (ticks) for (const t of ticks) svg.append(s("line", { class: "grid-line", x1: x(t), x2: x(t), y1: top, y2: top + plotH }),
      s("text", { class: "tick", x: x(t), y: H - 4, "text-anchor": "middle", text: format(t) }));
    if (cap) {   // drawn before the rows, so row labels (with a surface halo) stay readable where they cross it
      const cx = x(cap.value);
      svg.append(s("line", { class: "threshold", x1: cx, x2: cx, y1: top - 6, y2: top + plotH }),
        s("text", { class: "threshold-label", x: cx, y: top - 10, "text-anchor": "middle", text: cap.label }));
    }
    rows.forEach((r, i) => {
      const rowTop = top + i * rowH, y = above ? rowTop + 22 : rowTop + (rowH - barH) / 2;
      const label = r.valueLabel ?? format(r.value);
      const g = s("g", { class: "mark" },
        s("text", { class: "row-label", x: above ? 0 : padL - 10, y: above ? rowTop + 14 : y + barH / 2 + 4,
          "text-anchor": above ? "start" : "end", text: r.label }),
        s("path", { class: r.cls, d: barPath(padL, y, x(r.value) - padL, barH) }),
        s("text", { class: "value-label", x: x(r.value) + 6, y: y + barH / 2 + 4, text: label }));
      const hit = s("rect", { class: "hit", x: 0, y: rowTop, width: W, height: rowH });
      g.append(hit);
      attachTip(hit, [label, r.label, r.extra], g);
      svg.append(g);
    });
    svg.append(s("line", { class: "axis-line", x1: padL, x2: padL, y1: top, y2: top + plotH }));
    box.replaceChildren(svg);
  }

  function stackChart(box, { rows, total }) {
    const W = widthOf(box), barH = 24, rowH = 80, top = 4, H = top + rows.length * rowH;
    const x = v => (v / total) * W;
    const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, width: W, height: H });
    rows.forEach((r, i) => {
      const rowTop = top + i * rowH, y = rowTop + 20;
      svg.append(s("text", { class: "row-label", x: 0, y: rowTop + 12, text: r.label }));
      let acc = 0;
      r.segments.forEach((seg, j) => {
        const last = j === r.segments.length - 1;
        const x0 = x(acc) + (j ? 1 : 0), x1 = x(acc + seg.value) - (last ? 0 : 1);   // a 2px surface gap between segments
        acc += seg.value;
        if (seg.value <= 0) return;
        const g = s("g", { class: "mark" },
          last ? s("path", { class: seg.cls, d: barPath(x0, y, x1 - x0, barH) })
            : s("rect", { class: seg.cls, x: x0, y, width: Math.max(0, x1 - x0), height: barH }),
          x1 - x0 > 28 ? s("text", { class: "in-label", x: (x0 + x1) / 2, y: y + barH / 2 + 4, "text-anchor": "middle", text: String(seg.value) }) : null);
        const hit = s("rect", { class: "hit", x: x0, y: y - 4, width: Math.max(0, x1 - x0), height: barH + 8 });
        g.append(hit);
        attachTip(hit, [`${seg.value} of ${total}`, seg.name, r.label], g);
        svg.append(g);
      });
      svg.append(s("text", { class: "note-label", x: 0, y: y + barH + 18, text: r.note }));
    });
    box.replaceChildren(svg);
  }

  // ---------- the digest ----------
  const digest = D.digest, profile = D.profile;
  const itemsById = new Map(digest.items.map(item => [item.id, item]));
  const interestLabels = new Set(profile.interests.map(i => i.label));
  const revisedRefs = new Set(digest.revision.map(r => r.ref));

  function jumpTo(id) {
    const card = document.getElementById(`item-${id}`);
    if (!card) return;
    card.scrollIntoView({ behavior: "smooth", block: "center" });
    card.classList.remove("flash");
    void card.offsetWidth;
    card.classList.add("flash");
    setTimeout(() => card.classList.remove("flash"), 1800);
  }
  function citeChip(id) {
    const item = itemsById.get(id);
    const chip = h("button", { class: "cite", type: "button", "aria-label": item ? `Open ${id}: ${item.title}` : id },
      item ? icon(item.type) : null, id);
    chip.addEventListener("click", () => jumpTo(id));
    if (item) attachTip(chip, [item.title, `${TYPE[item.type]} · ${item.source}`, "Click to jump to the item"]);
    return chip;
  }
  function revisedMark(ref) {
    if (!revisedRefs.has(ref)) return null;
    const mark = h("span", { class: "revised" }, icon("pen"), "Revised");
    attachTip(mark, ["Revised after the Critic", refName(ref), "Before and after: see the Critic panel"]);
    return mark;
  }
  function feedback() {
    let rating = 0;
    const stars = [1, 2, 3, 4, 5].map(n => h("button", { class: "star", type: "button", "aria-label": `Rate ${n} of 5`, text: "★" }));
    const paint = () => stars.forEach((b, i) => { b.classList.toggle("on", i < rating); b.setAttribute("aria-pressed", String(i < rating)); });
    stars.forEach((b, i) => b.addEventListener("click", () => { rating = rating === i + 1 ? 0 : i + 1; paint(); }));
    const like = h("button", { class: "like", type: "button", "aria-pressed": "false", text: "Like" });
    like.addEventListener("click", () => like.setAttribute("aria-pressed", String(like.getAttribute("aria-pressed") !== "true")));
    return h("div", { class: "feedback" }, h("span", { class: "label", text: "Rate" }), stars, like);
  }
  function itemCard(item) {
    const url = safeUrl(item.url);
    const interest = item.reason.kind === "interest";
    return h("article", { class: "card item", id: `item-${item.id}` },
      h("div", { class: "item-meta" }, icon(item.type), h("span", { text: `${TYPE[item.type]} · ${item.source} · ${shortDate(item.published)}` }),
        h("span", { class: "id-chip", text: item.id })),
      url ? h("a", { class: "item-title", href: url, target: "_blank", rel: "noopener noreferrer", text: item.title })
        : h("span", { class: "item-title", text: item.title }),
      h("p", { class: "item-summary", text: item.summary }),
      h("div", { class: "reason" },
        h("span", { class: "pill" }, h("span", { class: `dot ${interest ? "interest" : "breadth"}` }),
          interest ? `Interest match · ${item.reason.interest}` : "Breadth"),
        h("span", { class: "reason-text", text: item.reason.text })),
      feedback());
  }

  function renderBrief(panel) {
    const total = Object.values(digest.candidates).reduce((a, b) => a + b, 0);
    const fields = [];
    digest.points.forEach((p, i) => {
      let field = fields.find(f => f.name === p.field);
      if (!field) fields.push(field = { name: p.field, points: [] });
      field.points.push({ ...p, ref: `points[${i}]` });
    });
    const brief = h("article", { class: "card brief-card", "aria-label": "Brief" },
      fields.map(f => h("section", { class: "field" },
        h("h3", { class: "field-name" }, interestLabels.has(f.name) ? h("span", { class: "dot interest", title: "One of your interests" }) : null, f.name),
        f.points.map(p => h("p", { class: "point" }, p.text, " ", p.cites.map(citeChip), revisedMark(p.ref))))),
      digest.connections.length ? h("section", { class: "brief-sub" }, h("h3", { class: "field-name", text: "Across fields" }),
        digest.connections.map((c, i) => h("p", { class: "connection" }, c.text, " ", c.cites.map(citeChip), revisedMark(`connections[${i}]`)))) : null,
      digest.changes.length ? h("section", { class: "brief-sub" }, h("h3", { class: "field-name", text: "Since your last brief" }),
        digest.changes.map(c => h("p", { class: "change" }, c.text, " ", (c.cites || []).map(citeChip)))) : null);

    const longTerm = profile.interests.filter(i => i.type === "long_term").length;
    const n = digest.items.length, cap = Math.floor(0.4 * n + 1e-9);
    const buckets = digest.buckets.map(b => `${b.name === "Breadth" ? "breadth" : b.name} ${b.count}`).join(" · ");
    const types = Object.entries(digest.types).map(([t, k]) => plural(k, ...TYPES[t])).join(" · ");
    const rules = [
      ["No topic above 40% of the items", `${buckets} (at most ${cap} of ${n} each)`, digest.largest_share <= 0.4],
      ["Every long-term interest seen in the last 7 days", `${longTerm - digest.uncovered} of ${longTerm} covered`, digest.uncovered === 0],
      ["More than one kind of source", types, Object.keys(digest.types).length > 1],
      ["Every point cites an item in this digest", `${digest.valid_citations} of ${digest.points.length} points`,
        digest.valid_citations === digest.points.length],
      ["Interest headings cite matching items", digest.heading_problems ? plural(digest.heading_problems, "problem", "problems") : "No problems",
        !digest.heading_problems],
    ];
    const rulesCard = h("section", { class: "card" },
      h("h2", { class: "block", text: "How this digest was checked" }),
      h("p", { class: "sub", text: "Rules run in code on every digest; no model decides whether to check." }),
      rules.map(([name, detail, ok]) => h("div", { class: "check" }, h("span", { class: ok ? "ok" : "" }, icon(ok ? "check" : "cross")),
        h("span", { class: "check-name", text: name }), h("span", { class: "check-detail", text: detail }))));
    const critic = digest.critic;
    const criticCard = h("section", { class: "card" },
      h("h2", { class: "block", text: "Critic" }),
      h("p", { class: "sub", text: "A separate agent that reads only your profile, the brief and each item's source text, and checks what rules cannot." }),
      h("span", { class: "badge" }, icon(critic.verdict === "PASS" ? "check" : "pen"),
        critic.verdict === "PASS" ? "Passed" : `Asked for one revision · ${plural(critic.issues.length, "issue", "issues")}`),
      critic.issues.map(issue => h("div", { class: "issue" },
        h("div", { class: "issue-type" }, ISSUE[issue.type] || issue.type, issue.refs.map(r => h("span", { class: "ref", text: refName(r) }))),
        h("p", { text: issue.explanation }))),
      digest.revision.length ? h("div", { class: "diff" }, digest.revision.map(r => [
        h("div", { class: "diff-label", text: `${refName(r.ref)} · before and after` }),
        h("p", { class: "before", text: r.before }), h("p", { class: "after", text: r.after })])) : null);
    const teamCard = h("section", { class: "card" },
      h("h2", { class: "block", text: "Who wrote it" }),
      h("p", { class: "sub", text: "A Manager sees only titles and asks three specialists; each reads only its own source." }),
      digest.team.map(t => h("div", { class: "team-row" },
        h("div", { class: "team-top" }, h("b", { text: t.specialist }), h("span", { text: `read ${t.candidates} · used ${t.used}` })),
        h("details", null, h("summary", { text: "Notes" }), h("p", { text: t.overview })))));

    panel.replaceChildren(h("div", { class: "brief-grid" },
      h("div", null,
        h("header", { class: "masthead" }, h("div", { class: "kicker", text: longDate(digest.date) }), h("h1", { text: "Today's brief" }),
          h("div", { class: "meta-line" }, h("span", { text: `${total} candidates from arXiv, GitHub and the news` }),
            h("span", { text: `${n} chosen` }), h("span", { class: "badge" }, icon("check"), "Checked by rules and the Critic"))),
        brief,
        h("div", { class: "items-head" }, h("h2", { text: `All ${n} items` }),
          h("div", { class: "legend" }, h("span", { class: "key" }, h("span", { class: "dot interest" }), "Interest match"),
            h("span", { class: "key" }, h("span", { class: "dot breadth" }), "Breadth: next to your interests"))),
        h("div", { class: "items" }, digest.items.map(itemCard))),
      h("aside", { class: "aside", "aria-label": "How this digest was checked" }, rulesCard, criticCard, teamCard)), footNote());
  }

  // ---------- interests and memory ----------
  const EVIDENCE = /^(rated|liked|opened|read) (\S+) \((\d{4}-\d{2}-\d{2}) digest\)(?: (\d)\/5| for (\d+) s)? on (\d{4}-\d{2}-\d{2}): (.*)$/;
  function evidenceItem(line) {
    const m = EVIDENCE.exec(line);
    if (!m) return h("li", null, h("span", { class: "ev-kind", text: "Signal" }), h("span", { class: "ev-title", text: line }));
    const [, verb, id, digestDay, score, seconds, when, title] = m;
    const kind = { rated: `★ ${score}/5`, liked: "♥ Like", opened: "Opened", read: `Read ${seconds} s` }[verb];
    return h("li", null, h("span", { class: "ev-kind", text: kind }),
      h("span", null, h("span", { class: "ev-title", text: title }),
        h("span", { class: "ev-meta", text: `${id} · ${shortDate(digestDay)} digest · ${shortDate(when)}` })));
  }
  const ORIGIN = { clarification: "From your setup answers", suggested: "Suggested at setup; you accepted it",
    free_text: "From your own description", manual: "Added by you" };
  const ADD = /^Add "(.+)" as a (long|short)-term interest(?: until (\S+))? \(weight ([\d.]+)\)$/;
  const MAKE_LONG = /^Make "(.+)" a long-term interest$/;
  const decisions = {};
  function currentInterests() {
    const list = profile.interests.map(i => ({ ...i }));
    D.proposals.forEach((p, k) => {
      if (decisions[k] !== "approved") return;
      const add = ADD.exec(p.change);
      if (add) list.push({ label: add[1], type: `${add[2]}_term`, expires: add[3] || null, weight: Number(add[4]),
        source: "inferred", origin: "proposal", approved_on: p.today, evidence: p.evidence, facets: [], fresh: true });
      const long = MAKE_LONG.exec(p.change);
      const target = long && list.find(i => i.label === long[1]);
      if (target) Object.assign(target, { type: "long_term", expires: null, fresh: true, madeLong: p.today });
    });
    return list;
  }
  function interestRow(i) {
    const term = i.type === "short_term" ? `Short-term · until ${shortDate(i.expires)}` : "Long-term";
    let origin = i.origin === "proposal" ? `Approved ${shortDate(i.approved_on)} from a proposed change` : ORIGIN[i.origin] || "";
    if (i.madeLong) origin += ` · made long-term ${shortDate(i.madeLong)}, approved by you`;
    return h("div", { class: `interest-row${i.fresh ? " new" : ""}` },
      h("div", { class: "interest-name", text: i.label }),
      h("div", { class: "weight" }, h("span", { class: "meter", role: "img", "aria-label": `Weight ${i.weight}` },
        h("span", { style: `width:${Math.round(i.weight * 100)}%` })), `weight ${i.weight.toFixed(1)}`),
      h("div", { class: "tags" }, h("span", { class: "tag strong", text: i.source === "stated" ? "Stated by you" : "Inferred" }),
        h("span", { class: "tag strong", text: term }), (i.facets || []).map(f => h("span", { class: "tag", text: f }))),
      origin ? h("div", { class: "origin", text: origin }) : null,
      i.evidence && i.evidence.length ? h("details", { class: "origin" }, h("summary", { text: `Evidence (${plural(i.evidence.length, "signal", "signals")})` }),
        h("ul", { class: "evidence" }, i.evidence.map(evidenceItem))) : null);
  }
  function proposalCard(p, k, rerender) {
    const decided = decisions[k];
    const decide = value => () => { decisions[k] = value; rerender(); };
    return h("article", { class: "card proposal" },
      h("div", { class: "kicker", text: "Proposed change" }),
      h("h3", { text: p.change }),
      h("blockquote", { class: "says" }, h("small", { text: "Forager says" }), p.message),
      h("div", { class: "ev-head", text: `Evidence from your allowed signals (${p.evidence.length})` }),
      h("ul", { class: "evidence" }, p.evidence.map(evidenceItem)),
      h("div", { class: "actions" }, decided
        ? [h("span", { class: "decision" }, icon(decided === "approved" ? "check" : "cross"),
            decided === "approved" ? "Approved · written to your profile" : "Rejected · Forager won't suggest this again for 30 days"),
          h("button", { class: "link-btn", type: "button", text: "Undo", onclick: decide(undefined) })]
        : [h("button", { class: "btn primary", type: "button", text: "Approve", onclick: decide("approved") }),
          h("button", { class: "btn", type: "button", text: "Reject", onclick: decide("rejected") })]));
  }
  const SIGNALS = [["ratings", "Ratings"], ["likes", "Likes"], ["clicks", "Clicks"], ["reading_time", "Reading time"]];
  const consentCard = () => h("section", { class: "card", style: "padding:18px 20px" },
    h("h2", { class: "block", text: "What Forager may track" }),
    h("p", { class: "sub", text: "Signals you haven't allowed are never recorded or used; withdrawing one deletes what was collected." }),
    SIGNALS.map(([name, label]) => {
      const on = Boolean(profile.consent[name]);
      return h("div", { class: "consent-row" }, h("span", { text: label }),
        h("span", { class: "switch-wrap" }, on ? "Allowed" : "Off", h("span", { class: `switch${on ? " on" : ""}`, "aria-hidden": "true" })));
    }));

  function renderInterests(panel) {
    const waiting = D.proposals.filter((_, k) => !decisions[k]).length;
    const left = h("div", null,
      h("div", { class: "kicker", text: "Idea 1 · Interests from one sentence" }),
      h("h2", { class: "section-title", text: "Your interests" }),
      h("p", { class: "lede", text: "You described yourself in one sentence; Forager split it into directions and asked about each with options to pick. Every interest says where it came from." }),
      h("blockquote", { class: "quote" }, `“${profile.setup.description}”`, h("small", { text: `Your setup sentence · ${shortDate(profile.setup.date)}` })),
      h("div", { class: "card" }, currentInterests().map(interestRow)));
    const right = h("div", { class: "stack" },
      h("div", null, h("div", { class: "kicker", text: "Idea 2 · Memory you approve" }),
        h("h2", { class: "section-title", text: waiting ? `${plural(waiting, "change", "changes")} waiting for you` : "Nothing waiting" }),
        h("p", { class: "lede", text: "Forager can't change your profile by itself: the tool that writes it pauses until you decide. The change and the evidence are generated by code, apart from the agent's wording." })),
      D.proposals.map((p, k) => proposalCard(p, k, () => renderInterests(panel))),
      consentCard());
    panel.replaceChildren(h("div", { class: "two-col" }, left, right), footNote());
  }

  // ---------- topics ----------
  function renderTopics(panel) {
    const n = digest.items.length, cap = Math.floor(0.4 * n + 1e-9);
    const rows = digest.buckets.map(b => ({ label: b.name, value: b.count, cls: b.name === "Breadth" ? "s2" : "s1",
      extra: `${pct(b.count / n)} of today's items` }));
    const topicFigure = figure({
      title: "Today's items by topic", sub: `${n} items · no topic may take more than ${cap} (40%)`,
      legend: h("div", { class: "legend" }, key("s1", "Interest match"), key("s2", "Breadth")),
      draw: box => barChart(box, { rows, max: Math.max(cap + 1, ...rows.map(r => r.value)), cap: { value: cap, label: `cap ${cap}` }, format: String }),
      table: () => tableOf(["Topic", "Items", "Share"], rows.map(r => [r.label, String(r.value), pct(r.value / n)])),
    });
    const sources = type => [...new Set(digest.items.filter(i => i.type === type).map(i => i.source))].join(", ");
    const typeTiles = h("div", { class: "tiles compact" }, ["paper", "repo", "news"].filter(t => digest.types[t]).map(t =>
      tile(TYPES[t][1].replace(/^./, c => c.toUpperCase()), String(digest.types[t]), sources(t))));
    const today = new Map();
    digest.items.forEach(i => { if (i.reason.kind === "interest") today.set(i.reason.interest, (today.get(i.reason.interest) || 0) + 1); });
    const coverage = h("section", { class: "card", style: "padding:18px 20px" },
      h("h2", { class: "block", text: "Your interests this week" }),
      h("p", { class: "sub", text: "Every long-term interest must appear at least once in 7 days; a short-term one lapses when it expires." }),
      profile.interests.map(i => h("div", { class: "cover-row" }, h("span", { text: i.label }),
        h("span", { text: [today.get(i.label) ? `${plural(today.get(i.label), "item", "items")} today` : i.type === "long_term" ? "Earlier this week" : "None today",
          i.type === "short_term" ? `short-term until ${shortDate(i.expires)}` : null].filter(Boolean).join(" · ") }))));
    const breadthToday = (digest.buckets.find(b => b.name === "Breadth") || { count: 0 }).count;
    const value = h("span", { class: "slider-value" });
    const hint = h("p", { class: "note" });
    const slider = h("input", { type: "range", min: "0", max: "0.5", step: "0.05", value: String(profile.exploration), "aria-label": "Exploration share" });
    const update = () => { const v = Number(slider.value); value.textContent = pct(v); hint.textContent = `About ${Math.round(v * n)} of ${n} items go to things next to your interests.`; };
    slider.addEventListener("input", update);
    update();
    const explore = h("section", { class: "card", style: "padding:18px 20px" },
      h("h2", { class: "block", text: "Exploration share" }),
      h("p", { class: "sub", text: "Breadth items rotate the feed, the way rotating crops keeps a field from wearing out." }),
      h("div", { class: "slider-row" }, slider, value), hint,
      h("p", { class: "note", text: `Today: ${breadthToday} of ${n} items were breadth, with the setting at ${pct(profile.exploration)}. Moving the slider here does not rebuild the digest.` }));
    panel.replaceChildren(
      h("div", { class: "kicker", text: "Idea 3 · Breadth you can see" }),
      h("h2", { class: "section-title", text: "Topic mix" }),
      h("p", { class: "lede", text: "A feed that only follows what you clicked last week narrows. Forager shows how today's items split across your interests and breadth, and keeps any one topic below 40%." }),
      h("div", { class: "two-col" }, h("div", { class: "stack" }, topicFigure, typeTiles), h("div", { class: "stack" }, coverage, explore)),
      footNote());
  }

  // ---------- evaluation ----------
  function renderEvaluation(panel) {
    const E = D.evaluation, M = E.modes, C = E.contrasts, R = E.reference;
    const NAMES = { single: "Single agent", rules: "Rules", critic: "Rules + Critic" };
    const memoryCode = E.memory_code, cases = E.critic_cases;
    const rounded = (modes, metric) => modes.map(m => Math.round(M[m][metric].mean * 100));
    const range = values => (Math.min(...values) === Math.max(...values) ? `${values[0]}%` : `${Math.min(...values)}–${Math.max(...values)}%`);
    const tiles = h("div", { class: "tiles" },
      tile("Breadth items, rule modes", range(rounded(["rules", "critic"], "breadth_share")),
        `single agent ${pct(M.single.breadth_share.mean)} · ${interval(C["rules - single"].breadth_share)}`),
      tile("Items worth showing", range(rounded(["single", "rules", "critic"], "worth_showing")), "about the same in all three modes"),
      tile("Profile changes written without approval", `${memoryCode.approval.without_approval} of ${memoryCode.approval.written}`,
        `silent baseline: ${memoryCode.silent.without_approval} of ${memoryCode.silent.written}`),
      tile("Constructed problems the Critic caught", `${cases.constructed[0]} of ${cases.constructed[1]}`,
        `rules alone: ${cases.rules[0]} · first real digest: ${cases.live[0]} of ${cases.live[1]}`));

    const modeRows = metric => ["single", "rules", "critic"].map(m => ({ label: NAMES[m], ...M[m][metric] }));
    const dots = (title, sub, metric, domain, ticks) => figure({
      title, sub, draw: box => dotChart(box, { rows: modeRows(metric), domain, ticks }),
      table: () => tableOf(["Mode", "Mean", "95% interval", "Digests"],
        modeRows(metric).map(r => [r.label, pct(r.mean), `${pct(r.low)}–${pct(r.high)}`, String(r.n)])),
    });
    const metrics = [["label_accuracy", "Label accuracy"], ["worth_showing", "Worth showing"],
      ["worth_showing_breadth", "Breadth items worth showing"], ["breadth_share", "Breadth share"]];
    const cell = st => ({ text: interval(st), cls: st.low > 0 || st.high < 0 ? "clear" : null });
    const contrasts = h("div", { class: "card figure" },
      h("div", { class: "fig-head" }, h("div", null, h("h3", { text: "Differences between modes" }),
        h("p", { class: "fig-sub", text: "Percentage points with 95% intervals; bold where the interval excludes zero" }))),
      h("div", { class: "table-wrap" }, tableOf(["", "Rules − single agent", "Rules + Critic − rules"],
        metrics.map(([m, name]) => [name, cell(C["rules - single"][m]), cell(C["critic - rules"][m])]))));
    const idea3 = h("section", { class: "eval-section" },
      h("div", { class: "kicker", text: "Idea 3 · Specialists, rules and a Critic" }),
      h("h2", { text: "More breadth, no less worth reading" }),
      h("p", { class: "lede", text: "30 recorded digests, 10 per mode on two snapshot sets. An LLM judge rated every item; breadth is counted in code. Dots are means, lines 95% bootstrap intervals." }),
      h("div", { class: "fig-grid" },
        dots("Share of breadth items", "Per digest, counted in code", "breadth_share", [0, 0.6], [0, 0.2, 0.4, 0.6]),
        dots("Items worth showing", "Per digest, judged", "worth_showing", [0, 1], [0, 0.25, 0.5, 0.75, 1])),
      h("div", { style: "margin-top:16px" }, contrasts),
      h("p", { class: "note", style: "margin-top:10px", text: "Rules and Rules + Critic are written by the Manager and three specialists; the single agent writes alone, so rules − single measures both changes together. Rules + Critic − rules shows no difference that excludes zero." }));

    const groups = Object.keys(R["brief.supported"]);
    const groupName = g => (g.includes("·") ? "Rules + Critic, draft before revision" : NAMES[g] || g);
    const sum = (table, field) => Object.values(table).reduce((a, r) => a + r[field], 0);
    const supported = R["brief.supported"], notOver = R["brief.not_overstated"];
    const citations = h("section", { class: "eval-section" },
      h("div", { class: "kicker", text: "Idea 3 · Do citations hold up?" }),
      h("h2", { text: `${sum(supported, "labels")} of ${sum(supported, "n")} brief entries are supported` }),
      h("p", { class: "lede", text: `By the reference labels; the judge passed ${sum(supported, "judge")} of the same ${sum(supported, "n")}. Only ${sum(notOver, "labels")} of ${sum(notOver, "n")} cross-field connections are not overstated. With about 10 entries per mode, the modes can't be told apart.` }),
      h("div", { class: "card figure" }, h("div", { class: "table-wrap" }, tableOf(
        ["Mode", "Entries supported", "Same entries, judge", "Connections not overstated"],
        groups.map(g => [groupName(g), `${supported[g].labels} of ${supported[g].n}`, `${supported[g].judge} of ${supported[g].n}`,
          notOver[g] ? `${notOver[g].labels} of ${notOver[g].n}` : "–"])))));

    const evidence = R["proposals.evidence_supports_change"], both = R["proposals.all"];
    const stackRows = ["approval", "silent"].map(m => ({
      label: m === "approval" ? "Approval (Forager)" : "Silent updates (baseline)",
      segments: [{ name: "Evidence supports the change", value: evidence[m].labels, cls: "s1" },
        { name: "Evidence does not support it", value: evidence[m].n - evidence[m].labels, cls: "s2" }],
      note: m === "approval" ? `All ${memoryCode.approval.shown} shown to the user before anything was written`
        : `All ${memoryCode.silent.written} written without asking`,
    }));
    const stackFigure = figure({
      title: "The same proposals, seen or unseen", sub: `${evidence.approval.n} written changes per mode, against the reference labels`,
      legend: h("div", { class: "legend" }, key("s1", "Evidence supports the change"), key("s2", "Evidence does not support it")),
      draw: box => stackChart(box, { rows: stackRows, total: evidence.approval.n }),
      table: () => tableOf(["Mode", "Supported", "Not supported", "Shown before writing"],
        stackRows.map((r, i) => [r.label, String(r.segments[0].value), String(r.segments[1].value), i === 0 ? "All" : "None"])),
    });
    const blocked = memoryCode.approval.blocked + memoryCode.silent.blocked;
    const unconsented = memoryCode.approval.unconsented + memoryCode.silent.unconsented;
    const idea2 = h("section", { class: "eval-section" },
      h("div", { class: "kicker", text: "Idea 2 · Approval versus silent updates" }),
      h("h2", { text: "Approval doesn't make proposals better; it makes the bad ones visible" }),
      h("p", { class: "lede", text: "8 scenarios × 2 modes × 2 repeats. In approval mode a scripted user approved everything it was shown, the worst case for approval." }),
      h("div", { class: "fig-grid" }, stackFigure, h("div", { class: "stack" },
        tile("Approval-mode pass rate", pct(both.approval.labels / both.approval.n),
          `${both.approval.labels} of ${both.approval.n} by the reference labels · the judge alone said ${both.approval.judge} of ${both.approval.n}`),
        tile("Unconsented signals that reached the agent", String(unconsented), "clicks and reading time were switched off"),
        tile("Repeats of a rejected change, blocked by code", String(blocked), "none of them reached the user"))));

    const cal = E.calibration, threshold = E.kappa_threshold;
    const count = field => cal.reduce((a, c) => a + c[field], 0);
    const below = cal.filter(c => c.kappa == null || c.kappa < threshold).length;
    const kappaRows = cal.map(c => ({ label: c.name, value: Math.max(0, c.kappa || 0), valueLabel: c.kappa == null ? "–" : c.kappa.toFixed(2),
      cls: c.kappa >= threshold ? "s1" : "de",
      extra: `${c.pairs} pairs · ${pct(c.agreement)} agreement · ${c.kappa >= threshold ? "judge used" : "reference labels used"}` }));
    const kappaFigure = figure({
      title: "Agreement with the reference labels (Cohen's κ)", sub: `At ${threshold} or above the judge is used; below it, the reference labels are the result`,
      legend: h("div", { class: "legend" }, key("s1", "Judge used"), key("de", "Reference labels used")),
      draw: box => barChart(box, { rows: kappaRows, max: 1, ticks: [0, 0.2, 0.4, 0.6, 0.8, 1], cap: { value: threshold, label: `κ ${threshold}` },
        format: v => v.toFixed(1), above: true }),
      table: () => tableOf(["Criterion", "Pairs", "Agreement", "κ", "Judge passed, reference failed", "Judge failed, reference passed"],
        cal.map(c => [c.name, String(c.pairs), pct(c.agreement), c.kappa == null ? "–" : c.kappa.toFixed(2), String(c.judge_lenient), String(c.judge_strict)])),
    });
    const calibration = h("section", { class: "eval-section" },
      h("div", { class: "kicker", text: "Can we trust the LLM judge?" }),
      h("h2", { text: `The judge errs one way: ${count("judge_lenient")} of ${count("judge_lenient") + count("judge_strict")} disagreements are passes` }),
      h("p", { class: "lede", text: `Reference labels were drafted blind by Claude agents and reviewed by the author (${count("changed")} of ${count("drafted")} changed). The judge is the same model as the Critic and shares its blind spots, so ${below} of ${cal.length} criteria use the reference labels.` }),
      kappaFigure);

    panel.replaceChildren(
      h("div", { class: "kicker", text: "Stage 5 evaluation" }),
      h("h2", { class: "section-title", text: "What the evaluation found" }),
      h("p", { class: "lede", text: "Recorded runs on fixed snapshots, rated by an LLM judge that was first checked against reference labels." }),
      tiles, idea3, citations, idea2, calibration, footNote());
  }

  // ---------- tabs and theme ----------
  const TABS = [["brief", "Brief"], ["interests", "Interests"], ["topics", "Topics"], ["evaluation", "Evaluation"]];
  const RENDER = { brief: renderBrief, interests: renderInterests, topics: renderTopics, evaluation: renderEvaluation };
  const nav = document.querySelector(".tabs");
  const panels = Object.fromEntries(TABS.map(([id]) => [id, document.getElementById(`panel-${id}`)]));
  const rendered = new Set();
  const buttons = TABS.map(([id, name]) => h("button", { class: "tab", type: "button", role: "tab", id: `tab-${id}`,
    "aria-controls": `panel-${id}`, text: name, onclick: () => select(id, true) }));
  nav.append(...buttons);
  function select(id, fromClick) {
    if (!panels[id]) id = "brief";
    TABS.forEach(([tab], i) => {
      const on = tab === id;
      buttons[i].setAttribute("aria-selected", String(on));
      buttons[i].tabIndex = on ? 0 : -1;
      panels[tab].hidden = !on;
    });
    if (!rendered.has(id)) { RENDER[id](panels[id]); rendered.add(id); }
    drawCharts(panels[id]);
    if (fromClick) { history.replaceState(null, "", `#${id}`); window.scrollTo({ top: 0 }); }
    store.set("forager-tab", id);
  }
  nav.addEventListener("keydown", e => {
    const i = buttons.indexOf(document.activeElement);
    if (i < 0 || (e.key !== "ArrowLeft" && e.key !== "ArrowRight")) return;
    const next = buttons[(i + (e.key === "ArrowRight" ? 1 : buttons.length - 1)) % buttons.length];
    next.focus();
    next.click();
  });
  window.addEventListener("hashchange", () => select(location.hash.slice(1)));
  let resizeTimer;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => drawCharts(Object.values(panels).find(p => !p.hidden)), 120);
  });

  const root = document.documentElement, themeButton = document.querySelector(".theme-btn");
  const isDark = () => (root.dataset.theme ? root.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches);
  const paintTheme = () => {
    themeButton.replaceChildren(icon(isDark() ? "sun" : "moon"));
    themeButton.setAttribute("aria-label", isDark() ? "Switch to light theme" : "Switch to dark theme");
  };
  themeButton.addEventListener("click", () => {
    root.dataset.theme = isDark() ? "light" : "dark";
    store.set("forager-theme", root.dataset.theme);
    paintTheme();
  });
  paintTheme();
  select(location.hash.slice(1) || store.get("forager-tab") || "brief");
})();
