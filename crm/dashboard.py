"""Render the CRM dashboard as one self-contained HTML file (fonts are the only external request)."""
from __future__ import annotations

import json

# The page body is written without <html>/<head>/<body> so the same markup can be
# published as a claude.ai Artifact (which supplies that skeleton) or wrapped for a local file.
STANDALONE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
</head>
<body>
__PAGE__
</body>
</html>
"""

TEMPLATE = r"""<title>Ideabazi Outreach CRM</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: CRM app shell. Dark top bar with tabs, light work surface, record drawer from the right. */
:root {
  --bar: #1f2d3d; --bar-ink: #e8edf3; --bar-muted: #9fb0c3;
  --bg: #f3f5f8; --panel: #ffffff; --ink: #1c2733; --muted: #5f6e7e; --line: #dde3ea; --soft: #eef2f6;
  --accent: #0b7a75; --accent-soft: #e1f2f1; --good: #1f8a5b; --warn: #a86a12; --bad: #c0392b; --on-accent: #ffffff;
  --scrim: rgba(10, 18, 28, .35);
  --sans: "IBM Plex Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bar: #0f1720; --bar-ink: #e8edf3; --bar-muted: #8a9bb0;
    --bg: #121820; --panel: #18212b; --ink: #e4eaf1; --muted: #93a2b3; --line: #2a3542; --soft: #1f2a36;
    --accent: #3cc2b9; --accent-soft: #163634; --good: #4cc38a; --warn: #e0a84a; --bad: #ef6b5b; --on-accent: #0c1a19;
    --scrim: rgba(0, 0, 0, .55);
    color-scheme: dark;
  }
}
:root[data-theme="dark"] {
  --bar: #0f1720; --bar-ink: #e8edf3; --bar-muted: #8a9bb0;
  --bg: #121820; --panel: #18212b; --ink: #e4eaf1; --muted: #93a2b3; --line: #2a3542; --soft: #1f2a36;
  --accent: #3cc2b9; --accent-soft: #163634; --good: #4cc38a; --warn: #e0a84a; --bad: #ef6b5b; --on-accent: #0c1a19;
  --scrim: rgba(0, 0, 0, .55);
  color-scheme: dark;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font: 14px/1.45 var(--sans); }
body::before { content: ""; position: fixed; inset: 0 0 auto; height: env(safe-area-inset-top, 0px); z-index: 10; background: var(--bar); }
.wrap { max-width: 1320px; margin: 0 auto; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
header { background: var(--bar); color: var(--bar-ink); position: sticky; top: env(safe-area-inset-top, 0px); z-index: 5; }
header .wrap { display: flex; align-items: center; gap: 20px; flex-wrap: wrap; padding-block: 10px 0; }
.brand { font-weight: 700; letter-spacing: .01em; padding-bottom: 10px; }
.brand span { color: var(--bar-muted); font-weight: 400; }
nav { display: flex; gap: 2px; flex: 1; overflow-x: auto; min-width: 0; }
nav a { color: var(--bar-muted); text-decoration: none; padding: 8px 12px 12px; border-bottom: 3px solid transparent; white-space: nowrap; font-weight: 500; }
nav a[aria-current="page"] { color: var(--bar-ink); border-bottom-color: var(--accent); }
nav a:focus-visible, button:focus-visible, input:focus-visible, select:focus-visible, tr:focus-visible, .card:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.updated { color: var(--bar-muted); font-size: 12px; padding-bottom: 10px; font-family: var(--mono); }
main { padding-block: 20px 48px; }
.act { border: 1px solid var(--line); border-radius: 8px; padding: 12px; margin: 16px 0; background: var(--soft); }
.act .btns { display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0; }
.act button, .undo { font: inherit; font-size: 13px; border: 1px solid var(--line); background: var(--panel); color: var(--ink); border-radius: 6px; padding: 5px 10px; cursor: pointer; }
.act button.primary { background: var(--accent); color: var(--on-accent); border-color: var(--accent); }
.act button:disabled { opacity: .5; cursor: default; }
.act textarea { width: 100%; font: inherit; padding: 7px 10px; border: 1px solid var(--line); border-radius: 6px; background: var(--panel); color: var(--ink); min-height: 54px; resize: vertical; }
.act .hint { font-size: 12px; color: var(--muted); }
.pend { display: flex; justify-content: space-between; align-items: center; gap: 8px; font-size: 13px; padding: 6px 0; border-top: 1px dashed var(--line); }
.chip-pend { display: inline-block; margin-left: 6px; padding: 0 6px; border-radius: 999px; font-size: 11px; border: 1px dashed var(--warn); color: var(--warn); white-space: nowrap; }
.pending-count { color: var(--bar-ink); background: var(--warn); border-radius: 999px; padding: 1px 8px; font-size: 12px; margin-bottom: 10px; }
.toast { position: fixed; left: 50%; transform: translateX(-50%); bottom: calc(20px + env(safe-area-inset-bottom, 0px)); background: var(--ink); color: var(--panel); padding: 9px 14px; border-radius: 6px; z-index: 30; font-size: 13px; max-width: calc(100% - 32px); }
.demo { margin-bottom: 16px; padding: 8px 12px; border: 1px dashed var(--warn); border-radius: 6px; color: var(--warn); }
h2 { font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: .07em; color: var(--muted); margin: 0 0 12px; }
.panel { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 16px; min-width: 0; }
.grid { display: grid; gap: 16px; }
.cols-2 { grid-template-columns: repeat(auto-fit, minmax(min(340px, 100%), 1fr)); align-items: start; }
.kpis { display: grid; gap: 1px; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); background: var(--line); border: 1px solid var(--line); border-radius: 8px; overflow: hidden; margin-bottom: 16px; }
.kpi { background: var(--panel); padding: 14px 16px; }
.kpi .v { font-size: 26px; font-weight: 600; font-variant-numeric: tabular-nums; line-height: 1.2; }
.kpi .l { color: var(--muted); font-size: 12px; }
.kpi .s { color: var(--muted); font-size: 11px; font-family: var(--mono); }
.funnel .row { display: grid; grid-template-columns: 90px 1fr 84px; gap: 10px; align-items: center; margin: 7px 0; }
.bar { height: 12px; background: var(--soft); border-radius: 3px; overflow: hidden; }
.bar > span { display: block; height: 100%; background: var(--accent); }
.num { font-variant-numeric: tabular-nums; text-align: right; font-family: var(--mono); font-size: 13px; }
.muted { color: var(--muted); }
.scroll { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }
th { font-size: 12px; color: var(--muted); font-weight: 600; white-space: nowrap; background: var(--soft); }
th[data-k] { cursor: pointer; }
tbody tr.rec { cursor: pointer; }
tbody tr.rec:hover { background: var(--soft); }
.who b { display: block; font-weight: 600; }
.who span { color: var(--muted); font-size: 12px; }
.pill { display: inline-block; padding: 1px 8px; border-radius: 999px; font-size: 12px; font-weight: 500; white-space: nowrap; background: var(--soft); color: var(--ink); }
.pill.good { background: var(--accent-soft); color: var(--good); }
.pill.bad { color: var(--bad); }
.pill.on { background: var(--accent); color: var(--on-accent); }
.overdue { color: var(--bad); font-weight: 600; }
.chart svg { width: 100%; height: auto; display: block; }
.chart text { fill: var(--muted); font: 11px var(--mono); }
.legend { display: flex; gap: 14px; font-size: 12px; color: var(--muted); margin-top: 6px; }
.legend i { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 5px; vertical-align: -1px; }
.board { display: grid; grid-auto-flow: column; grid-auto-columns: minmax(230px, 1fr); gap: 12px; overflow-x: auto; padding-bottom: 8px; }
.col { background: var(--soft); border-radius: 8px; padding: 10px; min-height: 120px; }
.col h3 { margin: 0 0 4px; font-size: 13px; display: flex; justify-content: space-between; }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 10px; margin-top: 8px; cursor: pointer; }
.card:hover { border-color: var(--accent); }
.card b { display: block; }
.card .meta { display: flex; justify-content: space-between; gap: 8px; margin-top: 6px; font-size: 12px; color: var(--muted); }
.filters { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
input, select { font: inherit; padding: 7px 10px; border: 1px solid var(--line); border-radius: 6px; background: var(--panel); color: var(--ink); max-width: 100%; }
.feed ul { margin: 0; padding: 0; }
.feed li { list-style: none; display: grid; grid-template-columns: 120px 1fr; gap: 12px; padding: 9px 0; border-bottom: 1px solid var(--line); }
.feed time { font-family: var(--mono); font-size: 12px; color: var(--muted); }
.empty { color: var(--muted); padding: 12px 0; }
section[data-view] { display: none; }
section[data-view].on { display: block; }
.scrim { position: fixed; inset: 0; background: var(--scrim); z-index: 20; }
aside { position: fixed; top: 0; right: 0; bottom: 0; width: min(560px, 100%); background: var(--panel); z-index: 21; overflow-y: auto; border-left: 1px solid var(--line);
  padding: calc(16px + env(safe-area-inset-top, 0px)) max(20px, env(safe-area-inset-right, 0px)) calc(24px + env(safe-area-inset-bottom, 0px)) 20px; }
aside h3 { margin: 0; font-size: 20px; }
aside .close { float: right; font: inherit; border: 1px solid var(--line); background: var(--panel); color: var(--ink); border-radius: 6px; padding: 4px 10px; cursor: pointer; }
aside dl { display: grid; grid-template-columns: 110px 1fr; gap: 6px 12px; margin: 16px 0; }
aside dt { color: var(--muted); font-size: 12px; }
aside dd { margin: 0; min-width: 0; overflow-wrap: anywhere; }
aside h2 { margin-top: 18px; }
.steps { display: flex; gap: 4px; flex-wrap: wrap; }
.steps span { font-size: 11px; padding: 3px 7px; border-radius: 4px; background: var(--soft); color: var(--muted); font-family: var(--mono); }
.steps span.done { background: var(--accent-soft); color: var(--good); }
.steps span.next { background: var(--accent); color: var(--on-accent); }
.msg { border: 1px solid var(--line); border-radius: 6px; padding: 10px; margin: 8px 0; white-space: pre-wrap; }
.msg .h { display: flex; justify-content: space-between; font-size: 12px; color: var(--muted); margin-bottom: 6px; white-space: normal; }
.score { display: grid; grid-template-columns: repeat(5, 1fr); gap: 4px; }
.score div { background: var(--soft); border-radius: 4px; padding: 6px; text-align: center; font-size: 11px; color: var(--muted); }
.score b { display: block; font-size: 16px; color: var(--ink); font-variant-numeric: tabular-nums; }
@media (max-width: 520px) { .feed li { grid-template-columns: 1fr; gap: 2px; } aside dl { grid-template-columns: 1fr; } }
@media (prefers-reduced-motion: no-preference) { aside { animation: slide .18s ease-out; } @keyframes slide { from { transform: translateX(24px); opacity: .6; } } }
</style>

<header>
  <div class="wrap">
    <div class="brand">Ideabazi Outreach <span>· __OWNER__</span></div>
    <nav aria-label="Views">
      <a href="#overview" data-tab="overview">Overview</a>
      <a href="#pipeline" data-tab="pipeline">Pipeline</a>
      <a href="#contacts" data-tab="contacts">Contacts</a>
      <a href="#activity" data-tab="activity">Activity</a>
    </nav>
    <span class="pending-count" id="pendcount" hidden></span>
    <div class="updated">Updated __GENERATED__</div>
  </div>
</header>

<main class="wrap">
  <div class="demo" id="demo" hidden>Sample data: fictional contacts and simulated outreach.</div>

  <section data-view="overview">
    <div class="kpis" id="kpis"></div>
    <div class="grid cols-2">
      <div class="panel"><h2>Today's work</h2><div class="scroll"><table id="today"></table></div></div>
      <div class="panel funnel"><h2>Funnel · everyone contacted</h2><div id="funnel"></div></div>
      <div class="panel chart"><h2>Activity · last 14 days</h2><div id="chart"></div>
        <div class="legend"><span><i style="background:var(--accent)"></i>Touches sent</span><span><i style="background:var(--warn)"></i>Replies</span></div></div>
      <div class="panel"><h2>Results by campaign</h2><div class="scroll"><table id="bycampaign"></table></div></div>
    </div>
  </section>

  <section data-view="pipeline">
    <div class="board" id="board"></div>
  </section>

  <section data-view="contacts">
    <div class="panel">
      <div class="filters">
        <input id="q" placeholder="Search name, company, title" size="30" aria-label="Search contacts">
        <select id="fstage" aria-label="Stage"><option value="">All stages</option></select>
        <select id="fcamp" aria-label="Campaign"><option value="">All campaigns</option></select>
        <select id="fdeg" aria-label="Degree"><option value="">All degrees</option><option value="1">1st</option><option value="2">2nd</option><option value="3">3rd+</option></select>
        <label class="muted"><input type="checkbox" id="fdq"> Show disqualified</label>
      </div>
      <div class="scroll"><table id="all"></table></div>
      <p class="muted" id="count"></p>
    </div>
  </section>

  <section data-view="activity">
    <div class="panel feed"><h2>All activity</h2><ul id="feed"></ul></div>
  </section>
</main>

<div class="scrim" id="scrim" hidden></div>
<aside id="drawer" hidden aria-label="Contact record"></aside>
<div class="toast" id="toast" role="status" hidden></div>

<script>
const D = __DATA__;
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const today = D.today;
const C = Object.fromEntries(D.contacts.map(c => [c.id, c]));
const msgs = {}; D.messages.forEach(m => (msgs[m.contact_id] ||= []).push(m));
const tby = {}; D.touches.forEach(t => (tby[t.contact_id] ||= []).push(t));
const pct = (a, b) => b ? Math.round(100 * a / b) + "%" : "—";
const name = c => `${c.first_name || ""} ${c.last_name || ""}`.trim();
const STAGE = { qualified: ["Qualified", ""], researched: ["Researched", ""], ready: ["Approved", "good"], in_sequence: ["In sequence", "good"],
  replied: ["Replied", "on"], meeting_booked: ["Meeting booked", "on"], meeting_held: ["Meeting held", "on"], proposal: ["Proposal", "on"],
  won: ["Won", "on"], lost: ["Lost", "bad"], nurture: ["Nurture", ""], completed: ["Completed", ""], opted_out: ["Opted out", "bad"],
  disqualified: ["Disqualified", "bad"], new: ["New", ""] };
const pill = s => { const [l, k] = STAGE[s] || [s, ""]; return `<span class="pill ${k}">${esc(l)}</span>`; };
const CH = { linkedin_connect: "Connect", linkedin_dm: "Message", email: "Email" };
const EV = { sent: "Sent", accepted: "Accepted invite", replied: "Replied", booked: "Booked a meeting", held: "Meeting held", proposal: "Proposal sent",
  won: "Won", lost: "Lost", nurture: "Moved to nurture", optout: "Opted out", bounce: "Bounced", skip: "Skipped step", note: "Note" };
if (D.contacts.length && D.contacts.every(c => c.source === "demo")) document.getElementById("demo").hidden = false;

/* tabs, bookmarkable via #overview / #pipeline / #contacts / #activity */
const views = ["overview", "pipeline", "contacts", "activity"];
function show(v) {
  if (!views.includes(v)) v = "overview";
  document.querySelectorAll("section[data-view]").forEach(s => s.classList.toggle("on", s.dataset.view === v));
  document.querySelectorAll("nav a").forEach(a => a.dataset.tab === v ? a.setAttribute("aria-current", "page") : a.removeAttribute("aria-current"));
}
document.querySelectorAll("nav a").forEach(a => a.addEventListener("click", e => {
  e.preventDefault();
  try { history.replaceState(null, "", "#" + a.dataset.tab); } catch (err) {}
  show(a.dataset.tab);
}));
show(location.hash.slice(1));

/* overview */
const sent = D.touches.filter(t => t.event === "sent");
const contacted = new Set(sent.map(t => t.contact_id));
const has = ev => new Set(D.touches.filter(t => t.event === ev).map(t => t.contact_id));
const connects = new Set(sent.filter(t => t.channel === "linkedin_connect").map(t => t.contact_id));
const accepted = has("accepted"), replied = has("replied"), booked = has("booked"), held = has("held");
const positive = new Set(D.touches.filter(t => t.event === "replied" && ["interested", "question"].includes(t.sentiment)).map(t => t.contact_id));
const won = D.contacts.filter(c => c.stage === "won").length;
const weekAgo = new Date(Date.parse(today) - 6 * 864e5).toISOString().slice(0, 10);
const sentWeek = sent.filter(t => t.ts.slice(0, 10) >= weekAgo).length;
document.getElementById("kpis").innerHTML = [
  ["Approved, not started", D.contacts.filter(c => c.stage === "ready").length, "next send run"],
  ["In sequence", D.contacts.filter(c => c.stage === "in_sequence").length, "being worked"],
  ["Touches sent · 7 days", sentWeek, `cap ${D.caps.connect_requests_per_day} connects + ${D.caps.linkedin_dms_per_day} msgs/day`],
  ["Connect accept rate", pct([...accepted].filter(id => connects.has(id)).length, connects.size), `${connects.size} invites sent`],
  ["Reply rate", pct(replied.size, contacted.size), `${replied.size} of ${contacted.size} contacted`],
  ["Meetings booked", booked.size, `${held.size} held · ${won} won`],
].map(([l, v, s]) => `<div class="kpi"><div class="l">${esc(l)}</div><div class="v">${esc(v)}</div><div class="s">${esc(s)}</div></div>`).join("");

const due = D.contacts.filter(c => c.stage === "in_sequence" && c.next_touch_due && c.next_touch_due <= today)
  .sort((a, b) => a.next_touch_due.localeCompare(b.next_touch_due));
const hot = D.contacts.filter(c => ["replied", "meeting_booked"].includes(c.stage));
const todayRows = [
  ...hot.map(c => [c, "Reply yourself", pill(c.stage)]),
  ...due.map(c => [c, CH[(D.sequences[c.sequence] || [])[c.step]] || "Next touch",
    `<span class="${c.next_touch_due < today ? "overdue" : ""}">${c.next_touch_due < today ? "Overdue " : "Due "}${esc(c.next_touch_due.slice(5))}</span>`]),
  ...D.contacts.filter(c => c.stage === "ready").sort((a, b) => b.score - a.score).slice(0, 6).map(c => [c, "Starts next send run", pill("ready")]),
];
const TODAY_MAX = 10;
document.getElementById("today").innerHTML = todayRows.length
  ? "<thead><tr><th>Contact</th><th>Action</th><th>Status</th></tr></thead><tbody>" + todayRows.slice(0, TODAY_MAX).map(([c, a, s]) =>
    `<tr class="rec" tabindex="0" data-id="${esc(c.id)}"><td class="who"><b>${esc(name(c))}</b><span>${esc(c.company)}</span></td><td>${esc(a)}</td><td>${s}</td></tr>`).join("") +
    (todayRows.length > TODAY_MAX ? `<tr><td colspan="3" class="muted">+${todayRows.length - TODAY_MAX} more in Pipeline</td></tr>` : "") + "</tbody>"
  : "<tbody><tr><td class='empty'>Nothing due. The 7:40am run adds prospects; the 10:10am run sends.</td></tr></tbody>";

const fsteps = [["Contacted", contacted.size], ["Accepted", accepted.size], ["Replied", replied.size], ["Positive", positive.size], ["Booked", booked.size], ["Held", held.size], ["Won", won]];
const base = Math.max(1, contacted.size);
document.getElementById("funnel").innerHTML = fsteps.map(([l, v]) =>
  `<div class="row"><span>${l}</span><div class="bar"><span style="width:${100 * v / base}%"></span></div><span class="num">${v} · ${pct(v, contacted.size)}</span></div>`).join("");

(function chart() {
  const days = [...Array(14)].map((_, i) => new Date(Date.parse(today) - (13 - i) * 864e5).toISOString().slice(0, 10));
  const s = days.map(d => sent.filter(t => t.ts.slice(0, 10) === d).length);
  const r = days.map(d => D.touches.filter(t => t.event === "replied" && t.ts.slice(0, 10) === d).length);
  const max = Math.max(4, ...s, ...r), W = 560, H = 170, L = 28, B = 22, bw = (W - L) / 14;
  const y = v => (H - B) - v * (H - B - 10) / max;
  let g = [0, Math.round(max / 2), max].map(t => `<line x1="${L}" x2="${W}" y1="${y(t)}" y2="${y(t)}" stroke="var(--line)"/><text x="${L - 6}" y="${y(t) + 4}" text-anchor="end">${t}</text>`).join("");
  days.forEach((d, i) => {
    const x = L + i * bw;
    g += `<rect x="${x + bw * .15}" y="${y(s[i])}" width="${bw * .38}" height="${(H - B) - y(s[i])}" fill="var(--accent)" rx="2"><title>${d}: ${s[i]} sent</title></rect>`;
    g += `<rect x="${x + bw * .55}" y="${y(r[i])}" width="${bw * .3}" height="${(H - B) - y(r[i])}" fill="var(--warn)" rx="2"><title>${d}: ${r[i]} replies</title></rect>`;
    if (i % 2 === 1) g += `<text x="${x + bw / 2}" y="${H - 6}" text-anchor="middle">${d.slice(5)}</text>`;
  });
  document.getElementById("chart").innerHTML = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Touches sent and replies per day">${g}</svg>`;
})();

(function byCampaign() {
  const camps = {};
  D.contacts.forEach(c => (camps[c.campaign || "—"] ||= []).push(c.id));
  const rows = Object.entries(camps).map(([k, ids]) => {
    const n = ids.filter(id => contacted.has(id)).length;
    return [k, ids.length, n, pct(ids.filter(id => replied.has(id)).length, n), ids.filter(id => booked.has(id)).length];
  }).sort((a, b) => b[1] - a[1]);
  document.getElementById("bycampaign").innerHTML = "<thead><tr><th>Campaign</th><th class='num'>Contacts</th><th class='num'>Contacted</th><th class='num'>Reply</th><th class='num'>Meetings</th></tr></thead><tbody>" +
    rows.map(r => `<tr><td>${esc(r[0])}</td>${r.slice(1).map(v => `<td class="num">${esc(v)}</td>`).join("")}</tr>`).join("") + "</tbody>";
})();

/* pipeline board */
const cols = [["ready", "Approved"], ["in_sequence", "In sequence"], ["replied", "Replied"], ["meeting_booked", "Meeting booked"], ["meeting_held", "Meeting held"], ["proposal", "Proposal"], ["won", "Won"]];
document.getElementById("board").innerHTML = cols.map(([s, l]) => {
  const cs = D.contacts.filter(c => c.stage === s).sort((a, b) => b.score - a.score);
  return `<div class="col"><h3><span>${l}</span><span class="muted">${cs.length}</span></h3>` +
    cs.map(c => `<div class="card" tabindex="0" data-id="${esc(c.id)}"><b>${esc(name(c))}</b><span class="muted">${esc(c.title || "")}</span>` +
      `<div class="meta"><span>${esc(c.company || "")}</span><span>${c.score}/25</span></div>` +
      (c.next_touch_due ? `<div class="meta"><span>Next touch</span><span class="${c.next_touch_due < today ? "overdue" : ""}">${esc(c.next_touch_due)}</span></div>` : "") + `</div>`).join("") +
    (cs.length ? "" : `<div class="empty">None yet</div>`) + "</div>";
}).join("");

/* contacts table */
const fstage = document.getElementById("fstage"), fcamp = document.getElementById("fcamp");
[...new Set(D.contacts.map(c => c.stage))].forEach(s => fstage.insertAdjacentHTML("beforeend", `<option value="${esc(s)}">${esc((STAGE[s] || [s])[0])}</option>`));
[...new Set(D.contacts.map(c => c.campaign).filter(Boolean))].forEach(s => fcamp.insertAdjacentHTML("beforeend", `<option>${esc(s)}</option>`));
let sortKey = "score", sortDir = -1;
const REGION = { usa: "USA", europe: "Europe", norway: "Norway", ireland: "Ireland", australia: "Australia", uae: "UAE", saudi_arabia: "Saudi Arabia", singapore: "Singapore" };
const tcols = [["first_name", "Contact"], ["stage", "Stage"], ["score", "Score"], ["country", "Region"], ["campaign", "Campaign"], ["next_touch_due", "Next touch"], ["last_touch_at", "Last touch"]];
function renderAll() {
  const q = document.getElementById("q").value.toLowerCase(), st = fstage.value, cp = fcamp.value, dg = document.getElementById("fdeg").value;
  const val = (c, k) => c[k] ?? "";
  const dq = document.getElementById("fdq").checked;
  const rows = D.contacts.filter(c => (st ? c.stage === st : dq || c.stage !== "disqualified") && (!cp || c.campaign === cp) && (!dg || String(c.degree) === dg) &&
      (!q || [c.first_name, c.last_name, c.company, c.title].join(" ").toLowerCase().includes(q)))
    .sort((a, b) => (val(a, sortKey) > val(b, sortKey) ? 1 : val(a, sortKey) < val(b, sortKey) ? -1 : 0) * sortDir);
  document.getElementById("all").innerHTML = "<thead><tr>" + tcols.map(([k, l]) =>
      `<th data-k="${k}" aria-sort="${k === sortKey ? (sortDir > 0 ? "ascending" : "descending") : "none"}">${l}${k === sortKey ? (sortDir > 0 ? " ▲" : " ▼") : ""}</th>`).join("") + "</tr></thead><tbody>" +
    rows.map(c => `<tr class="rec" tabindex="0" data-id="${esc(c.id)}"><td class="who"><b>${esc(name(c))}</b><span>${esc(c.title || "")} · ${esc(c.company || "")}</span></td>` +
      `<td>${pill(c.stage)}</td><td class="num">${c.score}</td><td>${esc(REGION[c.country] || c.country || "—")}</td><td>${esc(c.campaign || "—")}</td>` +
      `<td class="${c.next_touch_due && c.next_touch_due < today ? "overdue" : ""}">${esc(c.next_touch_due || "—")}</td><td>${esc((c.last_touch_at || "—").slice(0, 10))}</td></tr>`).join("") + "</tbody>";
  document.getElementById("count").textContent = `${rows.length} of ${D.contacts.length} contacts`;
  document.querySelectorAll("#all th[data-k]").forEach(th => th.onclick = () => { const k = th.dataset.k; sortDir = k === sortKey ? -sortDir : -1; sortKey = k; renderAll(); });
}
["q", "fstage", "fcamp", "fdeg", "fdq"].forEach(id => document.getElementById(id).addEventListener("input", renderAll));
renderAll();

/* activity feed */
const line = t => `${esc(EV[t.event] || t.event)}${t.channel ? " · " + esc(CH[t.channel] || t.channel) : ""}${t.detail ? ` <span class="muted">· ${esc(t.detail)}</span>` : ""}`;
document.getElementById("feed").innerHTML = D.touches.length ? D.touches.slice(0, 300).map(t => {
  const c = C[t.contact_id] || {};
  return `<li><time>${esc(t.ts.slice(0, 16).replace("T", " "))}</time><div><b>${esc(name(c))}</b> <span class="muted">${esc(c.company || "")}</span><br>${line(t)}</div></li>`;
}).join("") : "<li class='empty'>No activity yet.</li>";

/* contact record drawer */
const drawer = document.getElementById("drawer"), scrim = document.getElementById("scrim");
function openRecord(id) {
  const c = C[id]; if (!c) return;
  const seq = D.sequences[c.sequence] || [];
  const sentSteps = new Set((tby[id] || []).filter(t => t.event === "sent").map(t => t.step));
  const stepHtml = seq.map((ch, i) => `<span class="${sentSteps.has(i) ? "done" : i === c.step && c.stage === "in_sequence" ? "next" : ""}">${i + 1} ${esc(CH[ch] || ch)}</span>`).join("");
  const ib = k => c["icebreaker_" + k.toLowerCase()] ? `<div class="msg"><div class="h"><span>Icebreaker ${k}${c.icebreaker_choice === k ? " · in use" : ""}</span></div>${esc(c["icebreaker_" + k.toLowerCase()])}</div>` : "";
  drawer.innerHTML = `<button class="close" id="close">Close</button><h3>${esc(name(c))}</h3>
    <div class="muted">${esc(c.title || "")} · ${esc(c.company || "")}</div><div style="margin-top:8px">${pill(c.stage)}</div>
    <div id="actpanel"></div>
    <dl>
      <dt>LinkedIn</dt><dd>${c.linkedin_url ? `<a href="${esc(c.linkedin_url)}" target="_blank" rel="noopener">${esc(c.linkedin_url.replace("https://www.linkedin.com", ""))}</a>` : "—"}</dd>
      <dt>Email</dt><dd>${esc(c.email || "—")}${c.email_status ? ` <span class="muted">(${esc(c.email_status)})</span>` : ""}</dd>
      <dt>Location</dt><dd>${esc(c.location || "—")}${c.country ? ` <span class="muted">(${esc(REGION[c.country] || c.country)})</span>` : ""}</dd>
      ${c.disq_reason ? `<dt>Disqualified</dt><dd>${esc(c.disq_reason)}</dd>` : ""}
      <dt>Company size</dt><dd>${esc(c.employees || "—")}</dd>
      <dt>Campaign</dt><dd>${esc(c.campaign || "—")}</dd>
      <dt>Signal</dt><dd>${esc(c.signal_note || "—")}</dd>
      <dt>Pain</dt><dd>${esc(c.pain_note || "—")}</dd>
      <dt>Notes</dt><dd>${esc(c.notes || "—")}</dd>
    </dl>
    <h2>Score · ${c.score}/25</h2>
    <div class="score">${["fit", "signal", "pain", "reach", "capacity"].map(k => `<div><b>${c[k] || 0}</b>${k}</div>`).join("")}</div>
    ${seq.length ? `<h2>Sequence</h2><div class="steps">${stepHtml}</div>` : ""}
    ${c.icebreaker_a ? `<h2>Icebreakers</h2>${ib("A")}${ib("B")}` : ""}
    ${(msgs[id] || []).length ? `<h2>Messages</h2>` + msgs[id].map(m => `<div class="msg"><div class="h"><span>Step ${m.step + 1} · ${esc(CH[m.channel] || m.channel)}</span><span>${esc(m.status)}</span></div>${m.subject ? `<b>${esc(m.subject)}</b>\n` : ""}${esc(m.body)}</div>`).join("") : ""}
    <h2>Timeline</h2>${(tby[id] || []).length ? `<div class="feed"><ul>${tby[id].map(t => `<li><time>${esc(t.ts.slice(0, 16).replace("T", " "))}</time><div>${line(t)}</div></li>`).join("")}</ul></div>` : `<p class="empty">No activity yet.</p>`}`;
  drawer.hidden = scrim.hidden = false;
  openId = id; renderActions();
  document.getElementById("close").onclick = closeRecord;
  document.getElementById("close").focus();
}
function closeRecord() { drawer.hidden = scrim.hidden = true; openId = null; }

/* ---------- updates from this page ----------
   Each button writes one document to the page's "actions" collection. The
   scheduled runs (and Claude in chat) apply pending actions to the CRM with
   `ob apply-actions`, then mark them applied; the next publish shows the result. */
let openId = null, actions = [], actionsDb = null, canWrite = false;
const ACT = [
  ["sent", "Sent next step myself"], ["accepted", "Accepted my invite"],
  ["replied", "Replied · interested", "interested"], ["replied", "Replied · question", "question"],
  ["replied", "Replied · not now", "not_now"], ["replied", "Replied · not interested", "not_interested"],
  ["booked", "Meeting booked"], ["held", "Meeting held"], ["proposal", "Proposal sent"],
  ["won", "Won"], ["lost", "Lost"], ["hold", "Hold (don't send)"], ["optout", "Opted out"],
];
const ACT_LABEL = Object.fromEntries(ACT.map(([e, l, s]) => [e + (s || ""), l]));
const actLabel = a => a.event === "note" ? "Note" : ACT_LABEL[a.event + (a.sentiment || "")] || a.event;
const pendingFor = id => actions.filter(a => a.contact_id === id && a.status === "pending");
function toast(msg) {
  const t = document.getElementById("toast"); t.textContent = msg; t.hidden = false;
  clearTimeout(toast.timer); toast.timer = setTimeout(() => { t.hidden = true; }, 4000);
}
function renderActions() {
  const el = document.getElementById("actpanel");
  if (!el || !openId) return;
  const pend = pendingFor(openId);
  const list = pend.map(a => `<div class="pend"><span>${esc(actLabel(a))}${a.note ? ` <span class="muted">· ${esc(a.note)}</span>` : ""} <span class="chip-pend">waiting for next run</span></span>` +
    (canWrite ? `<button class="undo" data-undo="${esc(a._id)}">Undo</button>` : "") + `</div>`).join("");
  if (!actionsDb) {
    el.innerHTML = pend.length ? `<div class="act">${list}</div>` : "";
    return;
  }
  el.innerHTML = `<div class="act"><b>Update this contact</b>
    <div class="btns">${ACT.map(([e, l, s]) => `<button data-ev="${e}" data-sent="${s || ""}" ${canWrite ? "" : "disabled"}>${esc(l)}</button>`).join("")}</div>
    <textarea id="actnote" placeholder="Optional note: what they said, meeting date, next step" aria-label="Note"></textarea>
    <div class="btns"><button class="primary" data-ev="note" ${canWrite ? "" : "disabled"}>Save note only</button></div>
    <div class="hint">${canWrite ? "Saved here instantly. The CRM applies it at the next run (7:40am or 10:10am PT), or right away if you ask Claude." : "View only: you can't update this page."}</div>
    ${list}</div>`;
}
async function saveAction(ev, sentiment) {
  if (!actionsDb || !openId) return;
  const note = (document.getElementById("actnote") || {}).value || "";
  const doc = { contact_id: openId, event: ev, sentiment: sentiment || null, note: note.trim().slice(0, 500), created_at: new Date().toISOString(), status: "pending" };
  try {
    await actionsDb.collection("actions").add(doc);
    toast(`Saved: ${actLabel(doc)} for ${name(C[openId])}`);
  } catch (e) {
    if (e && e.code === "invalid_argument") { canWrite = false; renderActions(); toast("This page is view-only for you."); }
    else toast("Couldn't save. Try again in a moment.");
  }
}
drawer.addEventListener("click", async e => {
  const b = e.target.closest("button[data-ev]");
  if (b && !b.disabled) { b.disabled = true; await saveAction(b.dataset.ev, b.dataset.sent); b.disabled = false; return; }
  const u = e.target.closest("button[data-undo]");
  if (u && actionsDb) {
    try { await actionsDb.collection("actions").doc(u.dataset.undo).delete(); toast("Removed."); } catch (err) { toast("Couldn't remove it. Try again."); }
  }
});
function markPending() {
  const ids = new Set(actions.filter(a => a.status === "pending").map(a => a.contact_id));
  const n = actions.filter(a => a.status === "pending").length;
  const pc = document.getElementById("pendcount");
  pc.hidden = !n; pc.textContent = `${n} update${n === 1 ? "" : "s"} waiting for the next run`;
  document.querySelectorAll("[data-id]").forEach(el => {
    const has = ids.has(el.dataset.id), chip = el.querySelector(".chip-pend");
    if (has && !chip) { const b = el.querySelector("b"); if (b) b.insertAdjacentHTML("beforeend", `<span class="chip-pend">update pending</span>`); }
    if (!has && chip) chip.remove();
  });
}
(async () => {
  if (!window.claude || !window.claude.use) return;
  const [db, user] = await Promise.all([window.claude.use("db"), window.claude.use("user")]);
  if (!db) return;
  actionsDb = db;
  canWrite = user ? await user.canEdit() : true;
  db.collection("actions").where("status", "==", "pending").onSnapshot(snap => {
    actions = snap.docs.map(d => ({ ...d.data(), _id: d.id }));
    markPending(); renderActions();
  }, () => { actionsDb = null; renderActions(); });
  renderActions();
})();
const _renderAll = renderAll;
renderAll = function () { _renderAll(); markPending(); };
scrim.onclick = closeRecord;
document.addEventListener("keydown", e => {
  if (e.key === "Escape") closeRecord();
  if (e.key === "Enter" && e.target.dataset && e.target.dataset.id) openRecord(e.target.dataset.id);
});
document.addEventListener("click", e => {
  const el = e.target.closest("[data-id]");
  if (el && !e.target.closest("a") && !drawer.contains(el)) openRecord(el.dataset.id);
});
</script>
"""


def render(data: dict, artifact: bool = False, backup: str | None = None) -> str:
    payload = json.dumps(data, default=str).replace("</", "<\\/")
    page = (TEMPLATE.replace("__DATA__", payload)
            .replace("__OWNER__", data["owner"]["name"])
            .replace("__GENERATED__", data["generated"].replace("T", " ")[:16]))
    if backup:
        page += '\n<script type="application/json" id="crm-backup">' + backup.replace("</", "<\\/") + "</script>\n"
    return page if artifact else STANDALONE.replace("__PAGE__", page)
