# Ideabazi LinkedIn Outreach System

A local CRM plus Claude skills that run Dave Banerjee's (Ideabazi Ventures) LinkedIn-led outreach to US founders, CEOs, presidents and owners of SMB and mid-market companies. The goal is booked conversations at https://cal.com/ideabazi-daveb/30min.

## Layout
- `crm/ob.py` — the CLI (stdlib Python 3.11+). `python3 crm/ob.py -h`
- `crm/schema.sql` — contacts, messages (drafted copy per sequence step), touches (every event)
- `crm/dashboard.py` — renders `data/dashboard.html`
- `config/outreach.toml` — ICP, offer routes, safety caps, sequences. **Single source of truth.**
- `.claude/skills/` — `li-source` → `li-research` → `li-daily` → `li-log` → `li-review`
- `data/` — the database, imports, queues, research JSON and dashboard. **Git-ignored: it holds PII. Never commit it.**

## Pipeline stages
new → qualified | disqualified → researched → ready (approved copy) → in_sequence → replied → meeting_booked → meeting_held → proposal → won | lost. Side exits: nurture, opted_out, completed.

## Rules for Claude in this repo
- The **ideabazi-outbound** skill's hard rules apply: Claude doesn't send unless Dave approves a specific batch; nothing is fabricated; credits are stated before any paid enrichment; LinkedIn is limited to viewing plus capped connection requests in a live session.
- **Do not use Apollo.** The connected Apollo account belongs to a client, so don't read from or write to it, even where a skill (including ideabazi-outbound) lists Apollo. Use Clay / FullEnrich / Vibe Prospecting (after confirming the account is Dave's) or Sales Navigator instead.
- No LinkedIn scraping, no bulk profile crawling, no cookie or session automation tools. Data comes from LinkedIn's own data export, Sales Navigator exports, and Clay/FullEnrich/Vibe.
- Every state change goes through `ob.py` (`log`, `research-in`, `approve`). Never edit the DB by hand.
- Run `python3 crm/ob.py dashboard` after any batch of changes.
- Tests: `python3 -m unittest discover -s tests`.
