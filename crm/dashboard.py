"""Render the CRM dashboard as one self-contained HTML file (no external requests)."""
from __future__ import annotations

import json

TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Outreach CRM</title>
<style>
:root {
  --bg: #f7f7f5; --panel: #ffffff; --ink: #1d1d1b; --muted: #6b6b66; --line: #e4e4df;
  --accent: #2f5bd3; --good: #1f8a5b; --warn: #b7791f; --bad: #c0392b; --chip: #eef1fb;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #121212; --panel: #1b1b1b; --ink: #ececea; --muted: #9a9a94; --line: #2c2c2a;
    --accent: #7b9cff; --good: #4cc38a; --warn: #e0a84a; --bad: #ef6b5b; --chip: #232a3d;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font: 14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, sans-serif; }
header { padding: 20px 16px 8px; max-width: 1280px; margin: 0 auto; display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px; align-items: baseline; }
h1 { font-size: 20px; margin: 0; }
h2 { font-size: 13px; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); margin: 0 0 10px; font-weight: 600; }
main { max-width: 1280px; margin: 0 auto; padding: 8px 16px 40px; display: grid; gap: 16px; }
.muted { color: var(--muted); }
.panel { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 16px; overflow: hidden; }
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; }
.kpi .v { font-size: 26px; font-weight: 650; font-variant-numeric: tabular-nums; }
.kpi .l { color: var(--muted); font-size: 12px; }
.funnel .row { display: grid; grid-template-columns: 130px 1fr 60px; gap: 10px; align-items: center; margin: 6px 0; }
.bar { height: 14px; background: var(--chip); border-radius: 4px; overflow: hidden; }
.bar > span { display: block; height: 100%; background: var(--accent); }
.grid2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; }
table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
th, td { text-align: left; padding: 7px 8px; border-bottom: 1px solid var(--line); vertical-align: top; }
th { font-size: 12px; color: var(--muted); font-weight: 600; cursor: pointer; white-space: nowrap; }
.scroll { overflow-x: auto; }
.chip { display: inline-block; padding: 1px 8px; border-radius: 999px; background: var(--chip); font-size: 12px; white-space: nowrap; }
.s-replied, .s-meeting_booked, .s-meeting_held, .s-proposal { color: var(--good); }
.s-won { background: var(--good); color: #fff; }
.s-lost, .s-opted_out, .s-disqualified { color: var(--bad); }
.overdue { color: var(--bad); font-weight: 600; }
.board { display: grid; grid-auto-flow: column; grid-auto-columns: minmax(200px, 1fr); gap: 10px; overflow-x: auto; padding-bottom: 6px; }
.col { background: var(--bg); border: 1px solid var(--line); border-radius: 8px; padding: 8px; min-height: 80px; }
.col h3 { font-size: 12px; margin: 0 0 6px; display: flex; justify-content: space-between; }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 6px 8px; margin: 6px 0; font-size: 12px; }
.card b { display: block; font-size: 13px; }
input, select { font: inherit; padding: 6px 8px; border: 1px solid var(--line); border-radius: 6px; background: var(--panel); color: var(--ink); }
.filters { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }
a { color: var(--accent); }
</style>
</head>
<body>
<header>
  <h1>Outreach CRM <span class="muted" style="font-weight:400">· __OWNER__</span></h1>
  <span class="muted">Generated __GENERATED__ · regenerate with <code>python3 crm/ob.py dashboard</code></span>
</header>
<main>
  <section class="kpis" id="kpis"></section>

  <section class="grid2">
    <div class="panel funnel"><h2>Funnel (contacted cohort)</h2><div id="funnel"></div></div>
    <div class="panel"><h2>Due today &amp; overdue</h2><div class="scroll"><table id="due"></table></div>
      <p class="muted" id="queuehint"></p></div>
  </section>

  <section class="panel"><h2>Pipeline</h2><div class="board" id="board"></div></section>

  <section class="grid2">
    <div class="panel"><h2>By degree</h2><div class="scroll"><table id="m-degree"></table></div></div>
    <div class="panel"><h2>By offer route</h2><div class="scroll"><table id="m-route"></table></div></div>
    <div class="panel"><h2>Icebreaker A/B</h2><div class="scroll"><table id="m-variant"></table></div></div>
    <div class="panel"><h2>Recent activity</h2><div class="scroll"><table id="feed"></table></div></div>
  </section>

  <section class="panel">
    <h2>All contacts</h2>
    <div class="filters">
      <input id="q" placeholder="Search name, company, title" size="28">
      <select id="fstage"><option value="">All stages</option></select>
      <select id="fdeg"><option value="">All degrees</option><option>1</option><option>2</option><option>3</option></select>
    </div>
    <div class="scroll"><table id="all"></table></div>
  </section>
</main>
<script>
const D = __DATA__;
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const today = new Date().toISOString().slice(0, 10);
const m = (D.metrics.all && D.metrics.all[0]) || {contacted:0, connects:0, accepted:0, replied:0, positive:0, booked:0, held:0, won:0};
const pct = (a, b) => b ? Math.round(100 * a / b) + "%" : "—";

document.getElementById("kpis").innerHTML = [
  ["Contacts in CRM", D.contacts.length],
  ["Qualified ICP", D.contacts.filter(c => !["new","disqualified"].includes(c.stage)).length],
  ["Contacted", m.contacted],
  ["Connect accept", pct(m.accepted, m.connects)],
  ["Reply rate", pct(m.replied, m.contacted)],
  ["Positive replies", m.positive],
  ["Meetings booked", m.booked],
  ["Won", m.won],
].map(([l, v]) => `<div class="panel kpi"><div class="v">${esc(v)}</div><div class="l">${esc(l)}</div></div>`).join("");

const steps = [["Contacted", m.contacted], ["Accepted", m.accepted], ["Replied", m.replied], ["Positive", m.positive], ["Booked", m.booked], ["Held", m.held], ["Won", m.won]];
const base = Math.max(1, m.contacted);
document.getElementById("funnel").innerHTML = steps.map(([l, v]) =>
  `<div class="row"><span>${l}</span><div class="bar"><span style="width:${100 * v / base}%"></span></div><span>${v} <span class="muted">${pct(v, base)}</span></span></div>`).join("");

const due = D.contacts.filter(c => c.stage === "in_sequence" && c.next_touch_due && c.next_touch_due <= today)
  .sort((a, b) => a.next_touch_due.localeCompare(b.next_touch_due));
document.getElementById("due").innerHTML = due.length
  ? "<tr><th>ID</th><th>Name</th><th>Company</th><th>Step</th><th>Due</th></tr>" + due.map(c =>
    `<tr><td>${esc(c.id)}</td><td>${c.linkedin_url ? `<a href="${esc(c.linkedin_url)}" target="_blank" rel="noopener">${esc(c.first_name)} ${esc(c.last_name)}</a>` : esc(c.first_name + " " + c.last_name)}</td>
     <td>${esc(c.company)}</td><td>${esc(c.sequence)} #${esc(c.step)}</td><td class="${c.next_touch_due < today ? "overdue" : ""}">${esc(c.next_touch_due)}</td></tr>`).join("")
  : "<tr><td class='muted'>Nothing due. Run <code>ob plan --volume N</code> to start new contacts.</td></tr>";
document.getElementById("queuehint").innerHTML = D.queue_file ? `Copy for today's touches: <code>data/${esc(D.queue_file)}</code>` : "";

const order = ["qualified","researched","ready","in_sequence","replied","meeting_booked","meeting_held","proposal","won","nurture","lost","completed"];
document.getElementById("board").innerHTML = order.map(s => {
  const cs = D.contacts.filter(c => c.stage === s).sort((a, b) => b.score - a.score);
  return `<div class="col"><h3><span>${s.replace("_", " ")}</span><span class="muted">${cs.length}</span></h3>` +
    cs.slice(0, 12).map(c => `<div class="card"><b>${esc(c.first_name)} ${esc(c.last_name)}</b>${esc(c.title || "")}<br><span class="muted">${esc(c.company || "")} · ${c.degree || "?"}° · ${c.score}/25</span></div>`).join("") +
    (cs.length > 12 ? `<div class="muted">+${cs.length - 12} more</div>` : "") + "</div>";
}).join("");

function mtable(id, rows) {
  const el = document.getElementById(id);
  if (!rows || !rows.length) { el.innerHTML = "<tr><td class='muted'>No sends yet.</td></tr>"; return; }
  el.innerHTML = "<tr><th>Group</th><th>Contacted</th><th>Accept</th><th>Reply</th><th>Positive</th><th>Booked</th></tr>" +
    rows.map(r => `<tr><td>${esc(r.grp ?? "—")}</td><td>${r.contacted}</td><td>${r.accept_rate}</td><td>${r.reply_rate}</td><td>${r.positive_rate}</td><td>${r.booked}</td></tr>`).join("");
}
mtable("m-degree", D.metrics.degree); mtable("m-route", D.metrics.route); mtable("m-variant", D.metrics.variant);

const byId = Object.fromEntries(D.contacts.map(c => [c.id, c]));
document.getElementById("feed").innerHTML = D.touches.length
  ? "<tr><th>When</th><th>Contact</th><th>Event</th></tr>" + D.touches.slice(0, 25).map(t => {
      const c = byId[t.contact_id] || {};
      return `<tr><td>${esc(t.ts.slice(0, 16).replace("T", " "))}</td><td>${esc(c.first_name)} ${esc(c.last_name)}</td><td>${esc(t.event)} ${esc(t.channel || "")} ${t.detail ? "<span class='muted'>" + esc(t.detail) + "</span>" : ""}</td></tr>`; }).join("")
  : "<tr><td class='muted'>No activity yet.</td></tr>";

const fstage = document.getElementById("fstage");
D.stages.forEach(s => fstage.insertAdjacentHTML("beforeend", `<option>${s}</option>`));
let sortKey = "score", sortDir = -1;
const cols = [["id","ID"],["degree","°"],["stage","Stage"],["score","Score"],["first_name","First"],["last_name","Last"],["title","Title"],["company","Company"],["route","Route"],["next_touch_due","Next due"]];
function renderAll() {
  const q = document.getElementById("q").value.toLowerCase(), st = fstage.value, dg = document.getElementById("fdeg").value;
  const rows = D.contacts.filter(c => (!st || c.stage === st) && (!dg || String(c.degree) === dg) &&
    (!q || [c.first_name, c.last_name, c.company, c.title].join(" ").toLowerCase().includes(q)))
    .sort((a, b) => ((a[sortKey] ?? "") > (b[sortKey] ?? "") ? 1 : -1) * sortDir);
  document.getElementById("all").innerHTML = "<tr>" + cols.map(([k, l]) => `<th data-k="${k}">${l}${k === sortKey ? (sortDir > 0 ? " ▲" : " ▼") : ""}</th>`).join("") + "</tr>" +
    rows.slice(0, 500).map(c => "<tr>" + cols.map(([k]) => k === "stage" ? `<td><span class="chip s-${esc(c.stage)}">${esc(c.stage)}</span></td>`
      : k === "first_name" && c.linkedin_url ? `<td><a href="${esc(c.linkedin_url)}" target="_blank" rel="noopener">${esc(c.first_name)}</a></td>` : `<td>${esc(c[k])}</td>`).join("") + "</tr>").join("");
  document.querySelectorAll("#all th").forEach(th => th.onclick = () => { const k = th.dataset.k; sortDir = k === sortKey ? -sortDir : -1; sortKey = k; renderAll(); });
}
["q", "fstage", "fdeg"].forEach(id => document.getElementById(id).addEventListener("input", renderAll));
renderAll();
</script>
</body>
</html>
"""


def render(data: dict) -> str:
    payload = json.dumps(data, default=str).replace("</", "<\\/")
    return (TEMPLATE.replace("__DATA__", payload)
            .replace("__OWNER__", data["owner"]["name"])
            .replace("__GENERATED__", data["generated"].replace("T", " ")))
