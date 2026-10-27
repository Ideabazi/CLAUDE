---
name: li-autopilot
description: The scheduled daily outreach run. Restore the CRM, sync replies, source and research 10 new owner/C-suite prospects in Dave's target regions from Clay, build today's send queue and republish the dashboard, then report to Dave. Use when a scheduled task says "daily outreach autopilot run", or when Dave says "run the autopilot now".
---

# li-autopilot — the daily unattended run

Dave's settings (27 Oct 2026): **10 new prospects a day, 7 days a week**, Clay enrichment approved, **copy auto-approved** when it scores 15+ and passes every check. This run sends nothing; the `li-sender` run at 10:10am PT sends the approved touches from Dave's browser.

## 0. Set up (every run)
1. `cd` to the repo. Make sure you're on `claude/youthful-euler-drnd4o` and current: `git fetch origin claude/youthful-euler-drnd4o && git checkout claude/youthful-euler-drnd4o && git pull --ff-only`.
2. **Always** restore from the dashboard, because the sender run updates it after this session last saw it:
   - Read https://claude.ai/artifact/1VW4dQU9Jw6z4ppgEUB1k2 with the Artifact tool (`action: "read"`) and note the saved file it names.
   - Run `python3 crm/ob.py restore <that file> --force`.
   - If the read or restore fails, **stop**. Report the failure to Dave. Never start from an empty or stale CRM: duplicates and lost history cost more than a skipped day.
3. Run `python3 -m unittest discover -s tests` and stop if it fails.

## 1. Sync replies (email only; LinkedIn is Dave's)
For each `in_sequence` contact with an email, search Gmail for mail from that address since `last_touch_at`. Log replies with `li-log` rules. Skip this step if Gmail isn't connected, and say so in the report.

## 2. Source 10 new prospects (Clay, Dave's "Ideabazi" workspace)
- **Check the workspace first:** `get-current-workspace` must return "Ideabazi". If it returns anything else, stop. **Never use Apollo.**
- **Company search** (free). Use `industry`, `company_size in ("11-50","51-200")`, `company_type = "Privately Held"`, `year_founded >= 2016`, and `products_and_services is_similar_to (...)`. Exclude `description contains ("outsourcing","offshore","staff augmentation","development services")`. The company search has no country filter, so keep rows whose returned `country` is in Dave's regions: United States, any European country (UK, EU, Switzerland, Norway, Ireland, etc.), Australia, United Arab Emirates (Dubai), Saudi Arabia, Singapore. Aim for roughly 5 USA, 3 Europe/UK/Ireland/Norway and 2 from Australia, UAE, Saudi Arabia or Singapore each day.
- **Rotate the angle** by day of the week, so the list doesn't keep returning the same companies:
  - Mon: B2B SaaS for sales/RevOps/finance teams
  - Tue: vertical SaaS for SMBs (home services, pet care, salons, clinics, fitness)
  - Wed: healthcare/legal/accounting practice software
  - Thu: B2B marketplaces and e-commerce enablement
  - Fri: HR/payroll/compliance SaaS
  - Sat: construction/property/field-service SaaS
  - Sun: B2B agencies and consultancies (11–50) that sell to SaaS
- **Find the decision-maker** with `search-contacts`: up to 10 domains per call, `experiences.any(is_current = true and job_title is_similar_to ("Founder","Co-Founder","CEO","President","Owner","Managing Director","Chief Revenue Officer","Chief Marketing Officer","Chief Operating Officer"))`, `limit 1 by clay_company_id`.
  - **Owner or C-suite only.** No VPs, heads, directors, managers or leads, ever (Dave, 27 Oct 2026).
  - Keep only people whose `location_name` is in an allowed region (`config/outreach.toml` → `[icp.regions]`).
- **Dedupe before spending credits:** run `python3 crm/ob.py list --search "<company>" --json`. Skip anyone already in the CRM (including disqualified and nurture).
- **Enrich** exactly the 10 kept companies and people, never more:
  - company: Open Jobs, Recent News, Latest Funding
  - contact: Custom "Recent LinkedIn Posts" (last 60 days)
  - Note the number of data points used in the report.
- **Import:** write a CSV to `data/imports/clay-<date>.csv` (columns as in `clay-2026-10-27.csv`), then run `import-csv --source clay --campaign obdg-saas-founders` and `qualify --enforce`. That check disqualifies any non-CXO or out-of-region contact, including ones already in nurture or in a sequence. Never research a contact `qualify` rejected.

## 3. Research and draft (li-research rules, ideabazi-outbound voice)
- **Use only dated facts from the enrichment** (jobs with `posted_at`, news with dates, hires with start months). Ignore Clay's "Growth Opportunity Analysis" text, which is generic and was not observed.
- **Score each prospect.** Signal without a date = 1. Total under 15 → `nurture`, no copy.
- **Contacts with no verified email:** set `"sequence": "second_degree"` and draft steps 0 (connect note, 300 characters or fewer), 1 (DM on accept, 80 words or fewer) and 3 (DM day 10, 60 words or fewer). Alternate `icebreaker_choice` A/B.
- **Validate before loading.** Every icebreaker is 20 words or fewer, with no banned words, no em dashes and no exclamation marks. Respect each step's ceiling. The script pattern is in `data/research/*.json` history.
- **Load and approve:** run `research-in data/research/<date>-autopilot.json`, then `approve` every new contact scoring 15+ whose copy passed validation (Dave's standing approval, 27 Oct 2026). Anything that failed a check stays `researched` and goes in the report.

## 4. Queue
Run `python3 crm/ob.py plan` with the default volume of 10 new starts, so the report can preview the day. The sender run re-plans at 10:10am and does the sending. The caps (8 connects, 20 messages) hold any overflow for later days.

## 5. Publish and back up
1. Run `python3 crm/ob.py dashboard --artifact --out data/dashboard-site.html`.
2. Publish it to https://claude.ai/artifact/1VW4dQU9Jw6z4ppgEUB1k2 (`url` + `file_path`). This page is also the CRM backup, so a failed publish is a failed run.
3. Commit and push code or config changes only. Never commit `data/`.

## 6. Report to Dave (short)
- **New today:** how many found, researched and nurtured, with the top 3 (name, company, one-line signal).
- **Auto-approved today:** the IDs plus the icebreaker in use. Say: "These send at 10:10am PT; reply 'hold li-00xx' to stop any of them."
- **Today's queue:** counts by channel. Remind him the Claude desktop app must be open at 10:10am PT for the sender run.
- **Replies or meetings** since yesterday.
- **Clay data points used today.**
- **On Fridays,** also run `li-review` and add its one recommended change.

## Never
- Send, connect, DM or post on LinkedIn, or create Gmail drafts, in this run (sending is `li-sender`'s job).
- Use Apollo.
- Enrich more than 10 new prospects a day.
- Invent a signal, a fact or a mutual connection.
