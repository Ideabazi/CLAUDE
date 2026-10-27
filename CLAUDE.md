# Ideabazi LinkedIn Outreach System

A local CRM plus Claude skills that run Dave Banerjee's (Ideabazi Ventures) LinkedIn-led outreach to **owners and C-suite only** (founder, CEO, president, owner, managing director, chief X officer) of SMB and mid-market companies (5–500 staff) in **USA, Europe incl. UK, Norway, Ireland, Australia, UAE/Dubai, Saudi Arabia and Singapore**. This applies to every stage, nurture included; `ob qualify --enforce` checks it. The goal is booked conversations at https://cal.com/ideabazi-daveb/30min.

## Layout
- `crm/ob.py` — the CLI (stdlib Python 3.11+). `python3 crm/ob.py -h`
- `crm/schema.sql` — contacts, messages (drafted copy per sequence step), touches (every event)
- `crm/dashboard.py` — renders `data/dashboard.html`
- `config/outreach.toml` — ICP, offer routes, safety caps, sequences. **Single source of truth.**
- `.claude/skills/` — `li-source` → `li-research` → `li-daily` → `li-log` → `li-review`; `li-autopilot` is the scheduled daily run (10 new prospects/day from Clay, 7 days/week, auto-approved); `li-sender` is the scheduled 10:10am PT send run from Dave's browser
- `data/` — the database, imports, queues, research JSON and dashboard. **Git-ignored: it holds PII. Never commit it.**

## Pipeline stages
new → qualified | disqualified → researched → ready (approved copy) → in_sequence → replied → meeting_booked → meeting_held → proposal → won | lost. Side exits: nurture, opted_out, completed.

## Rules for Claude in this repo
- The **ideabazi-outbound** skill's hard rules apply: Claude doesn't send unless Dave approves a specific batch; nothing is fabricated; credits are stated before any paid enrichment; LinkedIn is limited to viewing plus capped connection requests in a live session.
- **Automation authorized by Dave (27 Oct 2026):** the daily autopilot auto-approves every prospect scoring 15+ whose copy passes the checks, and the daily sender run (`li-sender`) sends approved LinkedIn touches from Dave's browser: at most 8 connection requests and 20 messages a day, 2–6 minutes apart, stopping on any LinkedIn warning. This replaces ideabazi-outbound's per-batch approval and "never unattended" rule for this pipeline only. Email still isn't sent.
- **The published dashboard is the source of truth.** Every scheduled run starts with `restore --force` from it and ends by republishing it, so the two runs (and this chat) never work from stale copies.
- **Do not use Apollo.** The connected Apollo account belongs to a client, so don't read from or write to it, even where a skill (including ideabazi-outbound) lists Apollo. Use Clay / FullEnrich / Vibe Prospecting (after confirming the account is Dave's) or Sales Navigator instead.
- No LinkedIn scraping, no bulk profile crawling, no cookie or session automation tools. Data comes from LinkedIn's own data export, Sales Navigator exports, and Clay/FullEnrich/Vibe.
- Every state change goes through `ob.py` (`log`, `research-in`, `approve`). Never edit the DB by hand.
- After any batch of changes, refresh the live dashboard: `python3 crm/ob.py dashboard --artifact --out data/dashboard-site.html`, then publish that file with the Artifact tool to https://claude.ai/artifact/1VW4dQU9Jw6z4ppgEUB1k2 (pass it as `url` from a new conversation). It is private to Dave and holds contact names, so never share it without asking. The page also embeds the full CRM as a backup: on a fresh container, `python3 crm/ob.py restore <file from Artifact read>` rebuilds `data/crm.db`.
- **Dashboard updates:** Dave can mark contacts on the page itself. These land in the page's `actions` collection (db capability; only Dave and editors can read or write it). Apply them with `ArtifactData` query → `ob apply-actions` → mark them `applied`. Every run does this first, and so should a chat session before it changes the CRM. Republish with `capabilities` omitted so the declaration is kept.
- Tests: `python3 -m unittest discover -s tests`.
