/* Forager showcase: renders window.FORAGER (showcase/data.js) into four views, in English or Chinese.
   Nothing here calls a model or saves anything: ratings, likes and approvals only change this page. */
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

  // ---------- language: our own strings in pairs; recorded text from the data's "zh" fields ----------
  let lang = store.get("forager-lang") === "zh" ? "zh" : "en";
  const tr = (en, zh) => (lang === "zh" ? zh : en);
  const loc = (owner, field) => (lang === "zh" && owner.zh && owner.zh[field] != null ? owner.zh[field] : owner[field]);
  const term = text => (lang === "zh" && D.terms_zh && D.terms_zh[text]) || text;

  // ---------- formatting ----------
  const pct = x => (x == null ? "–" : `${Math.round(x * 100)}%`);
  const signed = x => `${x >= 0 ? "+" : "−"}${Math.abs(Math.round(x * 100))}`;
  const interval = st => `${signed(st.mean)}${tr(" pts", " 个百分点")} [${signed(st.low)}, ${signed(st.high)}]`;
  const ofN = (k, n) => tr(`${k} of ${n}`, `${k}/${n}`);
  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const day = iso => { const [y, m, d] = iso.slice(0, 10).split("-").map(Number); return new Date(Date.UTC(y, m - 1, d)); };
  const shortDate = iso => {
    const d = day(iso);
    return tr(`${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`, `${d.getUTCMonth() + 1}月${d.getUTCDate()}日`);
  };
  const longDate = iso => day(iso).toLocaleDateString(tr("en-GB", "zh-CN"),
    { weekday: "long", day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });
  const safeUrl = url => (/^https?:\/\//i.test(url || "") ? url : null);
  const typeName = t => tr({ paper: "Paper", repo: "Repository", news: "News" }[t], { paper: "论文", repo: "代码仓库", news: "新闻" }[t]);
  const typeGroup = t => tr({ paper: "Papers", repo: "Repositories", news: "News stories" }[t], { paper: "论文", repo: "代码仓库", news: "新闻" }[t]);
  const typeCount = (t, n) => tr(
    `${n} ${{ paper: ["paper", "papers"], repo: ["repository", "repositories"], news: ["news story", "news stories"] }[t][n === 1 ? 0 : 1]}`,
    `${n} ${{ paper: "篇论文", repo: "个代码仓库", news: "条新闻" }[t]}`);
  const issueName = type => tr(
    { irrelevant_exploration: "Irrelevant exploration", near_duplicate: "Near-duplicate", unsupported_citation: "Unsupported citation",
      overstated_connection: "Overstated connection", mislabeled_interest: "Mislabelled interest" }[type],
    { irrelevant_exploration: "无关的探索内容", near_duplicate: "重复内容", unsupported_citation: "引用不支撑",
      overstated_connection: "夸大的关联", mislabeled_interest: "兴趣标签错误" }[type]) || type;
  const refName = ref => {
    const m = /^(points|connections)\[(\d+)\]$/.exec(ref);
    if (!m) return ref;
    return m[1] === "points" ? tr(`Point ${Number(m[2]) + 1}`, `要点 ${Number(m[2]) + 1}`) : tr(`Connection ${Number(m[2]) + 1}`, `关联 ${Number(m[2]) + 1}`);
  };
  const modeName = mode => tr({ single: "Single agent", rules: "Rules", critic: "Rules + Critic" }[mode],
    { single: "单 agent", rules: "仅规则", critic: "规则 + Critic" }[mode]) || mode;
  const CRITERIA_ZH = { "items.label_correct": "条目标签正确", "items.worth_showing": "条目值得看",
    "brief.supported": "速报条目有引用支撑", "brief.not_overstated": "跨领域关联没有夸大",
    "proposals.evidence_supports_change": "证据撑得起建议的改动", "proposals.message_matches_change": "建议的措辞与改动一致" };
  const tile = (label, value, sub) => h("div", { class: "card tile" }, h("div", { class: "tile-label", text: label }),
    h("div", { class: "tile-value", text: value }), sub ? h("div", { class: "tile-sub", text: sub }) : null);
  const key = (cls, text) => h("span", { class: "key" }, h("span", { class: `swatch ${cls}` }), text);
  const footNote = () => h("footer", { class: "panel-foot" }, tr("Showcase page built from recorded runs (", "展示页由记录下来的运行生成（"),
    D.source_files.map((file, i) => [i ? ", " : "", h("code", { text: file })]),
    tr("). Nothing here calls a model, and ratings, likes and decisions are not saved.",
      "）。页面不调用模型，评分、点赞和批准都不会保存。中文由 Claude 根据英文原文翻译，标题保留原文。"));

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
    const toggle = h("button", { class: "link-btn", type: "button", "aria-pressed": "false", text: tr("Table", "表格") });
    toggle.addEventListener("click", () => {
      const showTable = tableBox.hidden;
      tableBox.hidden = !showTable;
      chart.hidden = showTable;
      toggle.textContent = showTable ? tr("Chart", "图表") : tr("Table", "表格");
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
  const widthOf = box => Math.max(200, Math.floor(box.clientWidth || 520));
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
      attachTip(hit, [pct(r.mean), r.label, tr(`95% interval ${pct(r.low)}–${pct(r.high)} · ${r.n} digests`,
        `95% 区间 ${pct(r.low)}–${pct(r.high)} · ${r.n} 份简报`)], g);
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
        attachTip(hit, [ofN(seg.value, total), seg.name, r.label], g);
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
    const chip = h("button", { class: "cite", type: "button", "aria-label": item ? tr(`Open ${id}: ${item.title}`, `打开 ${id}：${item.title}`) : id },
      item ? icon(item.type) : null, id);
    chip.addEventListener("click", () => jumpTo(id));
    if (item) attachTip(chip, [item.title, `${typeName(item.type)} · ${item.source}`, tr("Click to jump to the item", "点击跳到这条内容")]);
    return chip;
  }
  function revisedMark(ref) {
    if (!revisedRefs.has(ref)) return null;
    const mark = h("span", { class: "revised" }, icon("pen"), tr("Revised", "已修改"));
    attachTip(mark, [tr("Revised after the Critic", "根据 Critic 修改过"), refName(ref),
      tr("Before and after: see the Critic panel", "修改前后的原文见 Critic 面板")]);
    return mark;
  }
  function feedback() {
    let rating = 0;
    const stars = [1, 2, 3, 4, 5].map(n => h("button", { class: "star", type: "button", "aria-label": tr(`Rate ${n} of 5`, `评 ${n} 分`), text: "★" }));
    const paint = () => stars.forEach((b, i) => { b.classList.toggle("on", i < rating); b.setAttribute("aria-pressed", String(i < rating)); });
    stars.forEach((b, i) => b.addEventListener("click", () => { rating = rating === i + 1 ? 0 : i + 1; paint(); }));
    const like = h("button", { class: "like", type: "button", "aria-pressed": "false", text: tr("Like", "点赞") });
    like.addEventListener("click", () => like.setAttribute("aria-pressed", String(like.getAttribute("aria-pressed") !== "true")));
    return h("div", { class: "feedback" }, h("span", { class: "label", text: tr("Rate", "评分") }), stars, like);
  }
  function itemCard(item) {
    const url = safeUrl(item.url);
    const interest = item.reason.kind === "interest";
    return h("article", { class: "card item", id: `item-${item.id}` },
      h("div", { class: "item-meta" }, icon(item.type), h("span", { text: `${typeName(item.type)} · ${item.source} · ${shortDate(item.published)}` }),
        h("span", { class: "id-chip", text: item.id })),
      url ? h("a", { class: "item-title", href: url, target: "_blank", rel: "noopener noreferrer", text: item.title })
        : h("span", { class: "item-title", text: item.title }),
      h("p", { class: "item-summary", text: loc(item, "summary") }),
      h("div", { class: "reason" },
        h("span", { class: "pill" }, h("span", { class: `dot ${interest ? "interest" : "breadth"}` }),
          interest ? tr(`Interest match · ${item.reason.interest}`, `兴趣匹配 · ${term(item.reason.interest)}`) : tr("Breadth", "广度补充")),
        h("span", { class: "reason-text", text: loc(item.reason, "text") })),
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
    const brief = h("article", { class: "card brief-card", "aria-label": tr("Brief", "速报") },
      fields.map(f => h("section", { class: "field" },
        h("h3", { class: "field-name" }, interestLabels.has(f.name) ? h("span", { class: "dot interest", title: tr("One of your interests", "你的兴趣之一") }) : null, term(f.name)),
        f.points.map(p => h("p", { class: "point" }, loc(p, "text"), " ", p.cites.map(citeChip), revisedMark(p.ref))))),
      digest.connections.length ? h("section", { class: "brief-sub" }, h("h3", { class: "field-name", text: tr("Across fields", "跨领域关联") }),
        digest.connections.map((c, i) => h("p", { class: "connection" }, loc(c, "text"), " ", c.cites.map(citeChip), revisedMark(`connections[${i}]`)))) : null,
      digest.changes.length ? h("section", { class: "brief-sub" }, h("h3", { class: "field-name", text: tr("Since your last brief", "与上次相比") }),
        digest.changes.map(c => h("p", { class: "change" }, loc(c, "text"), " ", (c.cites || []).map(citeChip)))) : null);

    const longTerm = profile.interests.filter(i => i.type === "long_term").length;
    const n = digest.items.length, cap = Math.floor(0.4 * n + 1e-9);
    const buckets = digest.buckets.map(b => `${b.name === "Breadth" ? tr("breadth", "广度补充") : term(b.name)} ${b.count}`).join(" · ");
    const types = ["paper", "repo", "news"].filter(t => digest.types[t]).map(t => typeCount(t, digest.types[t])).join(" · ");
    const rules = [
      [tr("No topic above 40% of the items", "没有话题超过 40%"),
        tr(`${buckets} (at most ${cap} of ${n} each)`, `${buckets}（每个最多 ${cap}/${n} 条）`), digest.largest_share <= 0.4],
      [tr("Every long-term interest seen in the last 7 days", "每个长期兴趣 7 天内都出现过"),
        tr(`${longTerm - digest.uncovered} of ${longTerm} covered`, `${longTerm - digest.uncovered}/${longTerm} 个已覆盖`), digest.uncovered === 0],
      [tr("More than one kind of source", "来源不止一种"), types, Object.keys(digest.types).length > 1],
      [tr("Every point cites an item in this digest", "每条要点都引用了本期内容"),
        tr(`${digest.valid_citations} of ${digest.points.length} points`, `${digest.valid_citations}/${digest.points.length} 条要点`),
        digest.valid_citations === digest.points.length],
      [tr("Interest headings cite matching items", "兴趣标题下引用了匹配的内容"),
        digest.heading_problems ? tr(`${digest.heading_problems} problems`, `${digest.heading_problems} 个问题`) : tr("No problems", "没有问题"),
        !digest.heading_problems],
    ];
    const rulesCard = h("section", { class: "card" },
      h("h2", { class: "block", text: tr("How this digest was checked", "这份简报是怎么检查的") }),
      h("p", { class: "sub", text: tr("Rules run in code on every digest; no model decides whether to check.", "规则由代码对每份简报执行，不由模型决定是否检查。") }),
      rules.map(([name, detail, ok]) => h("div", { class: "check" }, h("span", { class: ok ? "ok" : "" }, icon(ok ? "check" : "cross")),
        h("span", { class: "check-name", text: name }), h("span", { class: "check-detail", text: detail }))));
    const critic = digest.critic;
    const criticCard = h("section", { class: "card" },
      h("h2", { class: "block", text: "Critic" }),
      h("p", { class: "sub", text: tr("A separate agent that reads only your profile, the brief and each item's source text, and checks what rules cannot.",
        "一个独立的 agent，只读你的档案、速报和每条内容的原文，检查规则做不到的事。") }),
      h("span", { class: "badge" }, icon(critic.verdict === "PASS" ? "check" : "pen"), critic.verdict === "PASS" ? tr("Passed", "通过")
        : tr(`Asked for one revision · ${critic.issues.length} ${critic.issues.length === 1 ? "issue" : "issues"}`, `要求修改一次 · ${critic.issues.length} 个问题`)),
      critic.issues.map(issue => h("div", { class: "issue" },
        h("div", { class: "issue-type" }, issueName(issue.type), issue.refs.map(r => h("span", { class: "ref", text: refName(r) }))),
        h("p", { text: loc(issue, "explanation") }))),
      digest.revision.length ? h("div", { class: "diff" }, digest.revision.map(r => [
        h("div", { class: "diff-label", text: tr(`${refName(r.ref)} · before and after`, `${refName(r.ref)} · 修改前后`) }),
        h("p", { class: "before", text: loc(r, "before") }), h("p", { class: "after", text: loc(r, "after") })])) : null);
    const teamCard = h("section", { class: "card" },
      h("h2", { class: "block", text: tr("Who wrote it", "谁写的") }),
      h("p", { class: "sub", text: tr("A Manager sees only titles and asks three specialists; each reads only its own source.",
        "Manager 只看标题，向三个来源专家提问；每个专家只读自己来源的内容。") }),
      digest.team.map(t => h("div", { class: "team-row" },
        h("div", { class: "team-top" }, h("b", { text: term(t.specialist) }),
          h("span", { text: tr(`read ${t.candidates} · used ${t.used}`, `读了 ${t.candidates} 条 · 用了 ${t.used} 条`) })),
        h("details", null, h("summary", { text: tr("Notes", "笔记") }), h("p", { text: loc(t, "overview") })))));

    panel.replaceChildren(h("div", { class: "brief-grid" },
      h("div", null,
        h("header", { class: "masthead" }, h("div", { class: "kicker", text: longDate(digest.date) }), h("h1", { text: tr("Today's brief", "今日简报") }),
          h("div", { class: "meta-line" }, h("span", { text: tr(`${total} candidates from arXiv, GitHub and the news`, `从 arXiv、GitHub 和新闻中筛选 ${total} 条候选`) }),
            h("span", { text: tr(`${n} chosen`, `选出 ${n} 条`) }), h("span", { class: "badge" }, icon("check"), tr("Checked by rules and the Critic", "经规则和 Critic 检查")))),
        brief,
        h("div", { class: "items-head" }, h("h2", { text: tr(`All ${n} items`, `全部 ${n} 条内容`) }),
          h("div", { class: "legend" }, h("span", { class: "key" }, h("span", { class: "dot interest" }), tr("Interest match", "兴趣匹配")),
            h("span", { class: "key" }, h("span", { class: "dot breadth" }), tr("Breadth: next to your interests", "广度补充：与你的兴趣相邻")))),
        h("div", { class: "items" }, digest.items.map(itemCard))),
      h("aside", { class: "aside", "aria-label": tr("How this digest was checked", "这份简报是怎么检查的") }, rulesCard, criticCard, teamCard)), footNote());
  }

  // ---------- interests and memory ----------
  const EVIDENCE = /^(rated|liked|opened|read) (\S+) \((\d{4}-\d{2}-\d{2}) digest\)(?: (\d)\/5| for (\d+) s)? on (\d{4}-\d{2}-\d{2}): (.*)$/;
  function evidenceItem(line) {
    const m = EVIDENCE.exec(line);
    if (!m) return h("li", null, h("span", { class: "ev-kind", text: tr("Signal", "信号") }), h("span", { class: "ev-title", text: line }));
    const [, verb, id, digestDay, score, seconds, when, title] = m;
    const kind = { rated: `★ ${score}/5`, liked: tr("♥ Like", "♥ 点赞"), opened: tr("Opened", "打开过"), read: tr(`Read ${seconds} s`, `阅读 ${seconds} 秒`) }[verb];
    return h("li", null, h("span", { class: "ev-kind", text: kind }),
      h("span", null, h("span", { class: "ev-title", text: title }),
        h("span", { class: "ev-meta", text: tr(`${id} · ${shortDate(digestDay)} digest · ${shortDate(when)}`, `${id} · ${shortDate(digestDay)}的简报 · ${shortDate(when)}`) })));
  }
  const origins = () => ({ clarification: tr("From your setup answers", "来自你的设置回答"),
    suggested: tr("Suggested at setup; you accepted it", "设置时推荐，你接受了"),
    free_text: tr("From your own description", "来自你自己的描述"), manual: tr("Added by you", "你手动添加") });
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
    const term_ = i.type === "short_term" ? tr(`Short-term · until ${shortDate(i.expires)}`, `短期 · ${shortDate(i.expires)}到期`) : tr("Long-term", "长期");
    let origin = i.origin === "proposal" ? tr(`Approved ${shortDate(i.approved_on)} from a proposed change`, `${shortDate(i.approved_on)}经你批准的建议添加`)
      : origins()[i.origin] || "";
    if (i.madeLong) origin += tr(` · made long-term ${shortDate(i.madeLong)}, approved by you`, ` · ${shortDate(i.madeLong)}经你批准改为长期`);
    return h("div", { class: `interest-row${i.fresh ? " new" : ""}` },
      h("div", { class: "interest-name", text: term(i.label) }),
      h("div", { class: "weight" }, h("span", { class: "meter", role: "img", "aria-label": tr(`Weight ${i.weight}`, `权重 ${i.weight}`) },
        h("span", { style: `width:${Math.round(i.weight * 100)}%` })), tr(`weight ${i.weight.toFixed(1)}`, `权重 ${i.weight.toFixed(1)}`)),
      h("div", { class: "tags" }, h("span", { class: "tag strong", text: i.source === "stated" ? tr("Stated by you", "由你说明") : tr("Inferred", "推断") }),
        h("span", { class: "tag strong", text: term_ }), (i.facets || []).map(f => h("span", { class: "tag", text: term(f) }))),
      origin ? h("div", { class: "origin", text: origin }) : null,
      i.evidence && i.evidence.length ? h("details", { class: "origin" },
        h("summary", { text: tr(`Evidence (${i.evidence.length} ${i.evidence.length === 1 ? "signal" : "signals"})`, `证据（${i.evidence.length} 条信号）`) }),
        h("ul", { class: "evidence" }, i.evidence.map(evidenceItem))) : null);
  }
  function proposalCard(p, k, rerender) {
    const decided = decisions[k];
    const decide = value => () => { decisions[k] = value; rerender(); };
    return h("article", { class: "card proposal" },
      h("div", { class: "kicker", text: tr("Proposed change", "建议的改动") }),
      h("h3", { text: loc(p, "change") }),
      h("blockquote", { class: "says" }, h("small", { text: tr("Forager says", "Forager 说") }), loc(p, "message")),
      h("div", { class: "ev-head", text: tr(`Evidence from your allowed signals (${p.evidence.length})`, `来自你已授权信号的证据（${p.evidence.length}）`) }),
      h("ul", { class: "evidence" }, p.evidence.map(evidenceItem)),
      h("div", { class: "actions" }, decided
        ? [h("span", { class: "decision" }, icon(decided === "approved" ? "check" : "cross"),
            decided === "approved" ? tr("Approved · written to your profile", "已批准 · 已写入你的档案")
              : tr("Rejected · Forager won't suggest this again for 30 days", "已拒绝 · 30 天内不会再提出")),
          h("button", { class: "link-btn", type: "button", text: tr("Undo", "撤销"), onclick: decide(undefined) })]
        : [h("button", { class: "btn primary", type: "button", text: tr("Approve", "批准"), onclick: decide("approved") }),
          h("button", { class: "btn", type: "button", text: tr("Reject", "拒绝"), onclick: decide("rejected") })]));
  }
  const consentCard = () => h("section", { class: "card", style: "padding:18px 20px" },
    h("h2", { class: "block", text: tr("What Forager may track", "Forager 可以记录什么") }),
    h("p", { class: "sub", text: tr("Signals you haven't allowed are never recorded or used; withdrawing one deletes what was collected.",
      "没有授权的信号不会被记录或使用；撤回授权会删除已收集的数据。") }),
    [["ratings", tr("Ratings", "评分")], ["likes", tr("Likes", "点赞")], ["clicks", tr("Clicks", "点击")], ["reading_time", tr("Reading time", "阅读时长")]]
      .map(([name, label]) => {
        const on = Boolean(profile.consent[name]);
        return h("div", { class: "consent-row" }, h("span", { text: label }),
          h("span", { class: "switch-wrap" }, on ? tr("Allowed", "已允许") : tr("Off", "关闭"), h("span", { class: `switch${on ? " on" : ""}`, "aria-hidden": "true" })));
      }));

  function renderInterests(panel) {
    const waiting = D.proposals.filter((_, k) => !decisions[k]).length;
    const left = h("div", null,
      h("div", { class: "kicker", text: tr("Idea 1 · Interests from one sentence", "想法 1 · 一句话生成兴趣档案") }),
      h("h2", { class: "section-title", text: tr("Your interests", "你的兴趣") }),
      h("p", { class: "lede", text: tr("You described yourself in one sentence; Forager split it into directions and asked about each with options to pick. Every interest says where it came from.",
        "你用一句话描述自己；Forager 把它拆成几个方向，每个方向用可点选的选项追问。每条兴趣都标明了来源。") }),
      h("blockquote", { class: "quote" }, `“${loc(profile.setup, "description")}”`,
        h("small", { text: tr(`Your setup sentence · ${shortDate(profile.setup.date)}`, `你的设置原话 · ${shortDate(profile.setup.date)}`) })),
      h("div", { class: "card" }, currentInterests().map(interestRow)));
    const right = h("div", { class: "stack" },
      h("div", null, h("div", { class: "kicker", text: tr("Idea 2 · Memory you approve", "想法 2 · 经你批准的记忆") }),
        h("h2", { class: "section-title", text: waiting ? tr(`${waiting} ${waiting === 1 ? "change" : "changes"} waiting for you`, `${waiting} 条改动等你决定`)
          : tr("Nothing waiting", "没有待处理的改动") }),
        h("p", { class: "lede", text: tr("Forager can't change your profile by itself: the tool that writes it pauses until you decide. The change and the evidence are generated by code, apart from the agent's wording.",
          "Forager 不能自己改你的档案：写入档案的工具会暂停，直到你做出决定。改动内容和证据由代码生成，和 agent 的措辞分开显示。") })),
      D.proposals.map((p, k) => proposalCard(p, k, () => renderInterests(panel))),
      consentCard());
    panel.replaceChildren(h("div", { class: "two-col" }, left, right), footNote());
  }

  // ---------- topics ----------
  function renderTopics(panel) {
    const n = digest.items.length, cap = Math.floor(0.4 * n + 1e-9);
    const rows = digest.buckets.map(b => ({ label: term(b.name), value: b.count, cls: b.name === "Breadth" ? "s2" : "s1",
      extra: tr(`${pct(b.count / n)} of today's items`, `占今天内容的 ${pct(b.count / n)}`) }));
    const topicFigure = figure({
      title: tr("Today's items by topic", "今天的内容按话题分"),
      sub: tr(`${n} items · no topic may take more than ${cap} (40%)`, `${n} 条内容 · 每个话题最多 ${cap} 条（40%）`),
      legend: h("div", { class: "legend" }, key("s1", tr("Interest match", "兴趣匹配")), key("s2", tr("Breadth", "广度补充"))),
      draw: box => barChart(box, { rows, max: Math.max(cap + 1, ...rows.map(r => r.value)), cap: { value: cap, label: tr(`cap ${cap}`, `上限 ${cap}`) }, format: String }),
      table: () => tableOf([tr("Topic", "话题"), tr("Items", "条数"), tr("Share", "占比")], rows.map(r => [r.label, String(r.value), pct(r.value / n)])),
    });
    const sources = type => [...new Set(digest.items.filter(i => i.type === type).map(i => i.source))].join(", ");
    const typeTiles = h("div", { class: "tiles compact" }, ["paper", "repo", "news"].filter(t => digest.types[t]).map(t =>
      tile(typeGroup(t), String(digest.types[t]), sources(t))));
    const today = new Map();
    digest.items.forEach(i => { if (i.reason.kind === "interest") today.set(i.reason.interest, (today.get(i.reason.interest) || 0) + 1); });
    const coverage = h("section", { class: "card", style: "padding:18px 20px" },
      h("h2", { class: "block", text: tr("Your interests this week", "你这周的兴趣") }),
      h("p", { class: "sub", text: tr("Every long-term interest must appear at least once in 7 days; a short-term one lapses when it expires.",
        "每个长期兴趣 7 天内至少出现一次；短期兴趣到期就失效。") }),
      profile.interests.map(i => {
        const k = today.get(i.label);
        const status = k ? tr(`${k} ${k === 1 ? "item" : "items"} today`, `今天 ${k} 条`)
          : i.type === "long_term" ? tr("Earlier this week", "本周早些时候") : tr("None today", "今天没有");
        const expiry = i.type === "short_term" ? tr(`short-term until ${shortDate(i.expires)}`, `短期，${shortDate(i.expires)}到期`) : null;
        return h("div", { class: "cover-row" }, h("span", { text: term(i.label) }), h("span", { text: [status, expiry].filter(Boolean).join(" · ") }));
      }));
    const breadthToday = (digest.buckets.find(b => b.name === "Breadth") || { count: 0 }).count;
    const value = h("span", { class: "slider-value" });
    const hint = h("p", { class: "note" });
    const slider = h("input", { type: "range", min: "0", max: "0.5", step: "0.05", value: String(profile.exploration), "aria-label": tr("Exploration share", "探索度") });
    const update = () => {
      const v = Number(slider.value);
      value.textContent = pct(v);
      hint.textContent = tr(`About ${Math.round(v * n)} of ${n} items go to things next to your interests.`, `大约 ${Math.round(v * n)}/${n} 条内容会分给与你兴趣相邻的方向。`);
    };
    slider.addEventListener("input", update);
    update();
    const explore = h("section", { class: "card", style: "padding:18px 20px" },
      h("h2", { class: "block", text: tr("Exploration share", "探索度") }),
      h("p", { class: "sub", text: tr("Breadth items rotate the feed, the way rotating crops keeps a field from wearing out.", "广度补充让信息流轮作，就像轮作让田地不会变贫瘠。") }),
      h("div", { class: "slider-row" }, slider, value), hint,
      h("p", { class: "note", text: tr(`Today: ${breadthToday} of ${n} items were breadth, with the setting at ${pct(profile.exploration)}. Moving the slider here does not rebuild the digest.`,
        `今天：${breadthToday}/${n} 条是广度补充，设置是 ${pct(profile.exploration)}。在这里拖动滑块不会重新生成简报。`) }));
    panel.replaceChildren(
      h("div", { class: "kicker", text: tr("Idea 3 · Breadth you can see", "想法 3 · 看得见的广度") }),
      h("h2", { class: "section-title", text: tr("Topic mix", "话题分布") }),
      h("p", { class: "lede", text: tr("A feed that only follows what you clicked last week narrows. Forager shows how today's items split across your interests and breadth, and keeps any one topic below 40%.",
        "只跟着你上周点击走的信息流会越来越窄。Forager 显示今天的内容在你的兴趣和广度补充之间怎么分配，并让任何一个话题都不超过 40%。") }),
      h("div", { class: "two-col" }, h("div", { class: "stack" }, topicFigure, typeTiles), h("div", { class: "stack" }, coverage, explore)),
      footNote());
  }

  // ---------- evaluation ----------
  function renderEvaluation(panel) {
    const E = D.evaluation, M = E.modes, C = E.contrasts, R = E.reference;
    const memoryCode = E.memory_code, cases = E.critic_cases;
    const rounded = (modes, metric) => modes.map(m => Math.round(M[m][metric].mean * 100));
    const range = values => (Math.min(...values) === Math.max(...values) ? `${values[0]}%` : `${Math.min(...values)}–${Math.max(...values)}%`);
    const tiles = h("div", { class: "tiles" },
      tile(tr("Breadth items, rule modes", "广度补充占比（规则模式）"), range(rounded(["rules", "critic"], "breadth_share")),
        tr(`single agent ${pct(M.single.breadth_share.mean)} · ${interval(C["rules - single"].breadth_share)}`,
          `单 agent ${pct(M.single.breadth_share.mean)} · ${interval(C["rules - single"].breadth_share)}`)),
      tile(tr("Items worth showing", "值得看的内容"), range(rounded(["single", "rules", "critic"], "worth_showing")),
        tr("about the same in all three modes", "三种模式差不多")),
      tile(tr("Profile changes written without approval", "未经批准写入档案的改动"), ofN(memoryCode.approval.without_approval, memoryCode.approval.written),
        tr(`silent baseline: ${memoryCode.silent.without_approval} of ${memoryCode.silent.written}`, `静默基线：${memoryCode.silent.without_approval}/${memoryCode.silent.written}`)),
      tile(tr("Constructed problems the Critic caught", "Critic 在构造用例中抓到的问题"), ofN(cases.constructed[0], cases.constructed[1]),
        tr(`rules alone: ${cases.rules[0]} · first real digest: ${cases.live[0]} of ${cases.live[1]}`,
          `仅规则：${cases.rules[0]} · 第一份真实简报：${cases.live[0]}/${cases.live[1]}`)));

    const modeRows = metric => ["single", "rules", "critic"].map(m => ({ label: modeName(m), ...M[m][metric] }));
    const dots = (title, sub, metric, domain, ticks) => figure({
      title, sub, draw: box => dotChart(box, { rows: modeRows(metric), domain, ticks }),
      table: () => tableOf([tr("Mode", "模式"), tr("Mean", "均值"), tr("95% interval", "95% 区间"), tr("Digests", "简报数")],
        modeRows(metric).map(r => [r.label, pct(r.mean), `${pct(r.low)}–${pct(r.high)}`, String(r.n)])),
    });
    const metrics = [["label_accuracy", tr("Label accuracy", "标签正确率")], ["worth_showing", tr("Worth showing", "值得看")],
      ["worth_showing_breadth", tr("Breadth items worth showing", "广度补充中值得看的")], ["breadth_share", tr("Breadth share", "广度补充占比")]];
    const cell = st => ({ text: interval(st), cls: st.low > 0 || st.high < 0 ? "clear" : null });
    const contrasts = h("div", { class: "card figure" },
      h("div", { class: "fig-head" }, h("div", null, h("h3", { text: tr("Differences between modes", "模式之间的差别") }),
        h("p", { class: "fig-sub", text: tr("Percentage points with 95% intervals; bold where the interval excludes zero", "百分点，带 95% 区间；区间不含 0 的加粗") }))),
      h("div", { class: "table-wrap" }, tableOf(["", tr("Rules − single agent", "仅规则 − 单 agent"), tr("Rules + Critic − rules", "规则 + Critic − 仅规则")],
        metrics.map(([m, name]) => [name, cell(C["rules - single"][m]), cell(C["critic - rules"][m])]))));
    const idea3 = h("section", { class: "eval-section" },
      h("div", { class: "kicker", text: tr("Idea 3 · Specialists, rules and a Critic", "想法 3 · 来源专家、规则和 Critic") }),
      h("h2", { text: tr("More breadth, no less worth reading", "广度更高，值得看的没有变少") }),
      h("p", { class: "lede", text: tr("30 recorded digests, 10 per mode on two snapshot sets. An LLM judge rated every item; breadth is counted in code. Dots are means, lines 95% bootstrap intervals.",
        "30 份记录下来的简报，每种模式 10 份，来自两组快照。LLM 判定给每条内容打分；广度由代码统计。点是均值，线是 95% bootstrap 区间。") }),
      h("div", { class: "fig-grid" },
        dots(tr("Share of breadth items", "广度补充占比"), tr("Per digest, counted in code", "每份简报，代码统计"), "breadth_share", [0, 0.6], [0, 0.2, 0.4, 0.6]),
        dots(tr("Items worth showing", "值得看的内容"), tr("Per digest, judged", "每份简报，判定打分"), "worth_showing", [0, 1], [0, 0.25, 0.5, 0.75, 1])),
      h("div", { style: "margin-top:16px" }, contrasts),
      h("p", { class: "note", style: "margin-top:10px", text: tr("Rules and Rules + Critic are written by the Manager and three specialists; the single agent writes alone, so rules − single measures both changes together. Rules + Critic − rules shows no difference that excludes zero.",
        "仅规则和规则 + Critic 由 Manager 和三个来源专家写作，单 agent 独自写作，所以“仅规则 − 单 agent”同时包含两处变化。“规则 + Critic − 仅规则”没有任何区间不含 0。") }));

    const groups = Object.keys(R["brief.supported"]);
    const groupName = g => (g.includes("·") ? tr("Rules + Critic, draft before revision", "规则 + Critic，修改前的草稿") : modeName(g));
    const sum = (table, field) => Object.values(table).reduce((a, r) => a + r[field], 0);
    const supported = R["brief.supported"], notOver = R["brief.not_overstated"];
    const citations = h("section", { class: "eval-section" },
      h("div", { class: "kicker", text: tr("Idea 3 · Do citations hold up?", "想法 3 · 引用站得住吗？") }),
      h("h2", { text: tr(`${sum(supported, "labels")} of ${sum(supported, "n")} brief entries are supported`, `${sum(supported, "labels")}/${sum(supported, "n")} 条速报条目有引用支撑`) }),
      h("p", { class: "lede", text: tr(`By the reference labels; the judge passed ${sum(supported, "judge")} of the same ${sum(supported, "n")}. Only ${sum(notOver, "labels")} of ${sum(notOver, "n")} cross-field connections are not overstated. With about 10 entries per mode, the modes can't be told apart.`,
        `按参照标注统计；判定在同样的 ${sum(supported, "n")} 条里放过了 ${sum(supported, "judge")} 条。跨领域关联只有 ${sum(notOver, "labels")}/${sum(notOver, "n")} 条没有夸大。每种模式只有约 10 条，分不出模式之间的差别。`) }),
      h("div", { class: "card figure" }, h("div", { class: "table-wrap" }, tableOf(
        [tr("Mode", "模式"), tr("Entries supported", "有引用支撑"), tr("Same entries, judge", "同样条目的判定结果"), tr("Connections not overstated", "关联没有夸大")],
        groups.map(g => [groupName(g), ofN(supported[g].labels, supported[g].n), ofN(supported[g].judge, supported[g].n),
          notOver[g] ? ofN(notOver[g].labels, notOver[g].n) : "–"])))));

    const evidence = R["proposals.evidence_supports_change"], both = R["proposals.all"];
    const stackRows = ["approval", "silent"].map(m => ({
      label: m === "approval" ? tr("Approval (Forager)", "审批（Forager）") : tr("Silent updates (baseline)", "静默更新（基线）"),
      segments: [{ name: tr("Evidence supports the change", "证据撑得起改动"), value: evidence[m].labels, cls: "s1" },
        { name: tr("Evidence does not support it", "证据撑不起改动"), value: evidence[m].n - evidence[m].labels, cls: "s2" }],
      note: m === "approval" ? tr(`All ${memoryCode.approval.shown} shown to the user before anything was written`, `全部 ${memoryCode.approval.shown} 条在写入前都给用户看过`)
        : tr(`All ${memoryCode.silent.written} written without asking`, `全部 ${memoryCode.silent.written} 条没有询问就写入了`),
    }));
    const stackFigure = figure({
      title: tr("The same proposals, seen or unseen", "同样的建议，看得见还是看不见"),
      sub: tr(`${evidence.approval.n} written changes per mode, against the reference labels`, `每种模式 ${evidence.approval.n} 条写入的改动，按参照标注判断`),
      legend: h("div", { class: "legend" }, key("s1", tr("Evidence supports the change", "证据撑得起改动")), key("s2", tr("Evidence does not support it", "证据撑不起改动"))),
      draw: box => stackChart(box, { rows: stackRows, total: evidence.approval.n }),
      table: () => tableOf([tr("Mode", "模式"), tr("Supported", "撑得起"), tr("Not supported", "撑不起"), tr("Shown before writing", "写入前给用户看过")],
        stackRows.map((r, i) => [r.label, String(r.segments[0].value), String(r.segments[1].value), i === 0 ? tr("All", "全部") : tr("None", "没有")])),
    });
    const blocked = memoryCode.approval.blocked + memoryCode.silent.blocked;
    const unconsented = memoryCode.approval.unconsented + memoryCode.silent.unconsented;
    const idea2 = h("section", { class: "eval-section" },
      h("div", { class: "kicker", text: tr("Idea 2 · Approval versus silent updates", "想法 2 · 审批与静默更新") }),
      h("h2", { text: tr("Approval doesn't make proposals better; it makes the bad ones visible", "审批不会让建议变好，但会让不好的建议被看见") }),
      h("p", { class: "lede", text: tr("8 scenarios × 2 modes × 2 repeats. In approval mode a scripted user approved everything it was shown, the worst case for approval.",
        "8 个场景 × 2 种模式 × 每种 2 次。审批模式下，脚本化的用户批准了看到的每一条，这对审批最不利。") }),
      h("div", { class: "fig-grid" }, stackFigure, h("div", { class: "stack" },
        tile(tr("Approval-mode pass rate", "审批模式通过率"), pct(both.approval.labels / both.approval.n),
          tr(`${both.approval.labels} of ${both.approval.n} by the reference labels · the judge alone said ${both.approval.judge} of ${both.approval.n}`,
            `参照标注 ${both.approval.labels}/${both.approval.n} · 只看判定会是 ${both.approval.judge}/${both.approval.n}`)),
        tile(tr("Unconsented signals that reached the agent", "进入 agent 的未授权信号"), String(unconsented),
          tr("clicks and reading time were switched off", "点击和阅读时长是关闭的")),
        tile(tr("Repeats of a rejected change, blocked by code", "被代码拦下的重复建议（之前已被拒绝）"), String(blocked),
          tr("none of them reached the user", "没有一条到达用户")))));

    const cal = E.calibration, threshold = E.kappa_threshold;
    const count = field => cal.reduce((a, c) => a + c[field], 0);
    const below = cal.filter(c => c.kappa == null || c.kappa < threshold).length;
    const criterion = c => tr(c.name, CRITERIA_ZH[c.criterion] || c.name);
    const kappaRows = cal.map(c => ({ label: criterion(c), value: Math.max(0, c.kappa || 0), valueLabel: c.kappa == null ? "–" : c.kappa.toFixed(2),
      cls: c.kappa >= threshold ? "s1" : "de",
      extra: tr(`${c.pairs} pairs · ${pct(c.agreement)} agreement · ${c.kappa >= threshold ? "judge used" : "reference labels used"}`,
        `${c.pairs} 对 · 一致率 ${pct(c.agreement)} · ${c.kappa >= threshold ? "使用判定" : "使用参照标注"}`) }));
    const kappaFigure = figure({
      title: tr("Agreement with the reference labels (Cohen's κ)", "与参照标注的一致性（Cohen's κ）"),
      sub: tr(`At ${threshold} or above the judge is used; below it, the reference labels are the result`, `κ 达到 ${threshold} 就用判定，低于它就以参照标注为准`),
      legend: h("div", { class: "legend" }, key("s1", tr("Judge used", "使用判定")), key("de", tr("Reference labels used", "使用参照标注"))),
      draw: box => barChart(box, { rows: kappaRows, max: 1, ticks: [0, 0.2, 0.4, 0.6, 0.8, 1], cap: { value: threshold, label: `κ ${threshold}` },
        format: v => v.toFixed(1), above: true }),
      table: () => tableOf([tr("Criterion", "标准"), tr("Pairs", "对数"), tr("Agreement", "一致率"), "κ",
        tr("Judge passed, reference failed", "判定通过、参照不通过"), tr("Judge failed, reference passed", "判定不通过、参照通过")],
        cal.map(c => [criterion(c), String(c.pairs), pct(c.agreement), c.kappa == null ? "–" : c.kappa.toFixed(2), String(c.judge_lenient), String(c.judge_strict)])),
    });
    const lenient = count("judge_lenient"), disagreements = lenient + count("judge_strict");
    const calibration = h("section", { class: "eval-section" },
      h("div", { class: "kicker", text: tr("Can we trust the LLM judge?", "LLM 判定可信吗？") }),
      h("h2", { text: tr(`The judge errs one way: ${lenient} of ${disagreements} disagreements are passes`, `判定只在一个方向出错：${disagreements} 处不一致里有 ${lenient} 处是它放过了`) }),
      h("p", { class: "lede", text: tr(`Reference labels were drafted blind by Claude agents and reviewed by the author (${count("changed")} of ${count("drafted")} changed). The judge is the same model as the Critic and shares its blind spots, so ${below} of ${cal.length} criteria use the reference labels.`,
        `参照标注由 Claude agent 盲标初稿，作者逐条核对（${count("drafted")} 个里改了 ${count("changed")} 个）。判定和 Critic 是同一个模型，盲点也一样，所以 ${cal.length} 个标准里有 ${below} 个用参照标注。`) }),
      kappaFigure);

    panel.replaceChildren(
      h("div", { class: "kicker", text: tr("Stage 5 evaluation", "第 5 阶段评估") }),
      h("h2", { class: "section-title", text: tr("What the evaluation found", "评估发现了什么") }),
      h("p", { class: "lede", text: tr("Recorded runs on fixed snapshots, rated by an LLM judge that was first checked against reference labels.",
        "在固定快照上记录的运行，由一个先用参照标注校准过的 LLM 判定打分。") }),
      tiles, idea3, citations, idea2, calibration, footNote());
  }

  // ---------- tabs, language and theme ----------
  const TABS = [["brief", "Brief", "简报"], ["interests", "Interests", "兴趣"], ["topics", "Topics", "话题"], ["evaluation", "Evaluation", "评估"]];
  const RENDER = { brief: renderBrief, interests: renderInterests, topics: renderTopics, evaluation: renderEvaluation };
  const nav = document.querySelector(".tabs");
  const panels = Object.fromEntries(TABS.map(([id]) => [id, document.getElementById(`panel-${id}`)]));
  const rendered = new Set();
  const buttons = TABS.map(([id]) => h("button", { class: "tab", type: "button", role: "tab", id: `tab-${id}`,
    "aria-controls": `panel-${id}`, onclick: () => select(id, true) }));
  nav.append(...buttons);
  const current = () => TABS.map(([id]) => id).find(id => !panels[id].hidden) || "brief";
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
    resizeTimer = setTimeout(() => drawCharts(panels[current()]), 120);
  });

  const root = document.documentElement;
  const themeButton = document.querySelector(".theme-btn"), langButton = document.querySelector(".lang-btn");
  const isDark = () => (root.dataset.theme ? root.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches);
  const paintTheme = () => {
    themeButton.replaceChildren(icon(isDark() ? "sun" : "moon"));
    themeButton.setAttribute("aria-label", isDark() ? tr("Switch to light theme", "切换到浅色") : tr("Switch to dark theme", "切换到深色"));
  };
  themeButton.addEventListener("click", () => {
    root.dataset.theme = isDark() ? "light" : "dark";
    store.set("forager-theme", root.dataset.theme);
    paintTheme();
  });
  function paintLanguage() {
    root.lang = tr("en", "zh-CN");
    document.title = tr("Forager showcase", "Forager 展示页");
    document.getElementById("tagline").textContent = tr("Your daily AI brief, rotated for breadth", "每日 AI 简报，为广度而轮作");
    nav.setAttribute("aria-label", tr("Sections", "页面"));
    TABS.forEach(([, en, zh], i) => { buttons[i].textContent = tr(en, zh); });
    langButton.textContent = tr("中文", "EN");
    langButton.setAttribute("aria-label", tr("切换到中文", "Switch to English"));
    langButton.setAttribute("lang", tr("zh-CN", "en"));
    paintTheme();
  }
  langButton.addEventListener("click", () => {
    lang = lang === "zh" ? "en" : "zh";
    store.set("forager-lang", lang);
    const id = current(), y = window.scrollY;
    paintLanguage();
    charts.length = 0;          // the old figures leave with their panels
    rendered.clear();
    Object.values(panels).forEach(panel => panel.replaceChildren());
    select(id);
    window.scrollTo({ top: y });
  });
  paintLanguage();
  select(location.hash.slice(1) || store.get("forager-tab") || "brief");
})();
