# Ideabazi LinkedIn Outreach OS

A Claude Code–run outreach system for Ideabazi Ventures. It finds owners and C-suite leaders (founder, CEO, president, owner, managing director) of SMB and mid-market companies in the USA, Europe, Norway, Ireland, Australia, UAE, Saudi Arabia and Singapore across Dave's 1st, 2nd and 3rd-degree LinkedIn network, matches each to the Ideabazi service that fits, writes researched icebreakers and sequences, and runs a measured daily loop that ends in a booked call at **https://cal.com/ideabazi-daveb/30min**.

The system follows one principle: **40 researched contacts that get worked beat 500 scraped ones that get ignored.** Claude does the research, the copy and the bookkeeping. Dave sets the volume and presses Send.

---

## 1. How it works

```
 SOURCE            QUALIFY           RESEARCH              APPROVE        DAILY LOOP                  MEASURE
 li-source  ──▶    ob qualify  ──▶   li-research    ──▶    ob approve ──▶ li-daily (plan → send →  ──▶ li-review
 1st: LI export    title / US /      route, score /25,     Dave edits     log) + li-log for replies    funnel by degree,
 2nd: SalesNav     5–500 staff       signal, gift, A/B     copy (gate b)  caps + 48h spacing         route, A/B variant
 3rd: Apollo/Clay                    icebreakers, copy                    dashboard.html
```

| Layer | What it is | Why |
|---|---|---|
| **CRM core** | SQLite (`data/crm.db`) + `crm/ob.py` CLI | Local, private, no SaaS fees, and Claude can drive every state change deterministically |
| **Config** | `config/outreach.toml` | ICP, offer routes, safety caps and sequences sit in one place; change strategy without touching code |
| **Skills** | `.claude/skills/li-*` | Turn the workflow into repeatable commands Dave can trigger in plain English |
| **Dashboard** | `data/dashboard.html` | KPIs, funnel, pipeline board, A/B and degree breakdowns, due-today list |
| **Engines it plugs into** | `ideabazi-outbound` (research, voice, gift, slop test), Apollo / Clay / FullEnrich / Vibe (data), Gmail (reply sync, drafts), the browser (view-only degree checks) | Reuse what's already tuned for Dave instead of rebuilding it |

---

## 2. The degree strategy (where the meetings actually come from)

| Degree | Source | Sequence | Expected reply rate | Volume role |
|---|---|---|---|---|
| **1st** | LinkedIn data export (`Connections.csv`) | DM-first, gift up front, email in parallel | Highest (30%+) | Mine this first. It's free, warm and finite |
| **2nd** | Sales Navigator lead search (2nd, US, Owner/CXO, 11–500), or Apollo search + view-only degree check | Connect note (no pitch), then DM on accept, email if verified | Medium | The scalable core. Mutuals open warm-intro paths |
| **3rd+** | Apollo / Clay / FullEnrich ICP search | Email-led, LinkedIn as a supporting channel | Lowest | Top-up volume. Verified emails matter more than degree |

**Two challenges to the original brief:**
1. **"Go through my 2nd and 3rd-degree connections" can't be done by crawling LinkedIn.** LinkedIn's terms prohibit it, detection is aggressive, and a restricted account would cost far more than the list is worth. The compliant equivalent is better anyway: Sales Navigator applies the same degree filter with clean title, geography and headcount filters, and the data providers fill in emails and firmographics.
2. **Volume is not the lever; relevance is.** LinkedIn caps invites at about 100 a week. The system enforces 15 connects a day, 80 a week and 25 DMs a day, plus 48 hours between touches. Growth comes from raising reply and meeting rates, which the review loop measures.

---

## 3. Skills: what I used and why

**From your Claude library (already tuned to you):**
- `ideabazi-outbound` is the research, scoring, gift, icebreaker, voice-profile and slop-test engine. `li-research` calls it rather than duplicating it, so one improvement improves both systems.
- `linkedin-inbox-responder` handles reply handling in `li-daily` and `li-log`. `linkedin-network-growth` covers connection strategy.
- `small-business:lead-triage` and `crm-autopilot` are useful if you later mirror this pipeline into HubSpot.

**Reviewed on GitHub and the skill marketplaces (patterns borrowed, nothing installed):**
- [composiohq/awesome-claude-skills](https://claudemarketplaces.com/skills/composiohq/awesome-claude-skills/lead-research-assistant) `lead-research-assistant`: the ICP → research → fit-score pattern.
- [ai-sales-team-claude](https://www.sourcepulse.org/projects/28017776) (~630★): qualification plus sequence structure.
- ColdIQ GTM skills, La Growth Machine's open-source skills, and the "LinkedIn Outbound Squad" ([overview](https://www.salesrobot.co/playbooks/claude-code-skills-linkedin-outreach)): reply triage, signal selling, LinkedIn touch cadence.
- Several popular repos drive LinkedIn through Playwright cookie sessions. **They were rejected deliberately** because of the account-restriction risk.

---

## 4. Setup (15 minutes, once)

```bash
python3 crm/ob.py init
# 1st-degree: LinkedIn → Settings → Data privacy → Get a copy of your data → Connections
#   save the emailed Connections.csv to data/imports/
python3 crm/ob.py import-linkedin data/imports/Connections.csv
python3 crm/ob.py qualify
```
Then tell Claude: **"research the top 10"** (`li-research`). Review the copy, approve it, and you're live.

Requirements: Python 3.11+, nothing else. Optional connectors: Apollo, Clay, FullEnrich and Vibe Prospecting (enrichment), Gmail (reply sync and drafts), and a browser session (view-only degree checks).

## 5. Daily operation (about 20 minutes)

Say **"run today's outreach, 12 new"** and `li-daily` will:
1. Sync email replies (Gmail) and ask you for LinkedIn replies and accepts, which stops those sequences.
2. Run `ob plan --volume 12`: due follow-ups first, then the 12 highest-scoring approved contacts, within the caps.
3. Hand you `data/queue-<date>.md`: connect notes, DMs and emails with profile links and paste-ready copy.
4. Log what you sent, refresh the dashboard, and give you a 3-line scorecard.

Say "Avery replied, wants a call Thursday" anytime, and `li-log` records it and drafts the reply with your booking link.

## 6. Measurement

| Metric | Healthy target | Lever if below |
|---|---|---|
| Connect accept rate | 35–50% | Connect note, ICP tightness |
| Reply rate | 15–25% (1st-degree 30%+) | Icebreaker specificity, gift quality |
| Positive share of replies | 40%+ | Offer route match |
| Meetings / contacted | 4–8% | Smaller ask: gift before the call |

Everything is sliced by **degree, offer route, icebreaker A/B variant and sequence**. `li-review` runs weekly and proposes one change at a time.

## 7. CLI reference

| Command | Purpose |
|---|---|
| `init` | Create the database |
| `import-linkedin <csv>` | Import 1st-degree connections |
| `import-csv <csv> --degree 2 --source salesnav --campaign <slug>` | Import Sales Navigator / Apollo / Clay exports (headers auto-mapped) |
| `qualify [--all]` | ICP filter; sets fit and reach |
| `list [--stage --degree --route --search --json]` / `show <id>` | Browse |
| `research-in <json>` | Load Claude's research, scores, icebreakers and per-step copy |
| `approve <ids>` | Copy approved; contact enters the send pool |
| `plan --volume N [--date]` | Build today's queue within the caps |
| `log <id> sent|accepted|replied|booked|held|proposal|won|lost|optout|bounce|nurture|skip` | Record an event |
| `metrics [--by degree|route|variant|sequence|campaign] [--since]` | Funnel |
| `dashboard` / `export <csv>` | Visual dashboard / CSV export |

**Privacy:** everything under `data/` is git-ignored. Prospect data never leaves your machine unless you export it.
