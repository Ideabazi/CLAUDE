---
name: li-autopilot
description: The scheduled daily outreach run. Restore the CRM, sync replies, source and research 10 new US founder prospects from Clay, build today's send queue and republish the dashboard, then report to Dave. Use when a scheduled task says "daily outreach autopilot run", or when Dave says "run the autopilot now".
---

# li-autopilot — the daily unattended run

Dave's settings (27 Oct 2026): **10 new prospects a day, 7 days a week**, Clay enrichment approved. Nothing is sent: Dave approves the copy and sends LinkedIn touches himself. This run prepares everything up to the send.

## 0. Set up (every run)
1. `cd` to the repo. Make sure you're on `claude/youthful-euler-drnd4o` and current: `git fetch origin claude/youthful-euler-drnd4o && git checkout claude/youthful-euler-drnd4o && git pull --ff-only`.
2. If `data/crm.db` is missing (a fresh container), restore it from the dashboard:
   - Read https://claude.ai/artifact/1VW4dQU9Jw6z4ppgEUB1k2 with the Artifact tool (`action: "read"`) and note the saved file it names.
   - Run `python3 crm/ob.py restore <that file>`.
   - If the read or restore fails, **stop**. Report the failure to Dave. Never start from an empty CRM: duplicates and lost history cost more than a skipped day.
3. Run `python3 -m unittest discover -s tests` and stop if it fails.

## 1. Sync replies (email only; LinkedIn is Dave's)
For each `in_sequence` contact with an email, search Gmail for mail from that address since `last_touch_at`. Log replies with `li-log` rules. Skip this step if Gmail isn't connected, and say so in the report.

## 2. Source 10 new prospects (Clay, Dave's "Ideabazi" workspace)
- **Check the workspace first:** `get-current-workspace` must return "Ideabazi". If it returns anything else, stop. **Never use Apollo.**
- **Company search** (free). Use `industry`, `company_size in ("11-50","51-200")`, `company_type = "Privately Held"`, `year_founded >= 2016`, and `products_and_services is_similar_to (...)`. Exclude `description contains ("outsourcing","offshore","staff augmentation","development services")`. The company search has no country filter, so keep rows whose returned `country` is "United States".
- **Rotate the angle** by day of the week, so the list doesn't keep returning the same companies:
  - Mon: B2B SaaS for sales/RevOps/finance teams
  - Tue: vertical SaaS for SMBs (home services, pet care, salons, clinics, fitness)
  - Wed: healthcare/legal/accounting practice software
  - Thu: B2B marketplaces and e-commerce enablement
  - Fri: HR/payroll/compliance SaaS
  - Sat: construction/property/field-service SaaS
  - Sun: B2B agencies and consultancies (11–50) that sell to SaaS
- **Find the decision-maker** with `search-contacts`: up to 10 domains per call, `experiences.any(is_current = true and job_title is_similar_to ("Founder","Co-Founder","CEO","President","Owner"))`, `limit 1 by clay_company_id`.
  - Keep only people whose `location_name` is in the United States.
- **Dedupe before spending credits:** run `python3 crm/ob.py list --search "<company>" --json`. Skip anyone already in the CRM (including disqualified and nurture).
- **Enrich** exactly the 10 kept companies and people, never more:
  - company: Open Jobs, Recent News, Latest Funding
  - contact: Custom "Recent LinkedIn Posts" (last 60 days)
  - Note the number of data points used in the report.
- **Import:** write a CSV to `data/imports/clay-<date>.csv` (columns as in `clay-2026-10-27.csv`), then run `import-csv --source clay --campaign obdg-saas-founders` and `qualify`.

## 3. Research and draft (li-research rules, ideabazi-outbound voice)
- **Use only dated facts from the enrichment** (jobs with `posted_at`, news with dates, hires with start months). Ignore Clay's "Growth Opportunity Analysis" text, which is generic and was not observed.
- **Score each prospect.** Signal without a date = 1. Total under 15 → `nurture`, no copy.
- **Contacts with no verified email:** set `"sequence": "second_degree"` and draft steps 0 (connect note, 300 characters or fewer), 1 (DM on accept, 80 words or fewer) and 3 (DM day 10, 60 words or fewer). Alternate `icebreaker_choice` A/B.
- **Validate before loading.** Every icebreaker is 20 words or fewer, with no banned words, no em dashes and no exclamation marks. Respect each step's ceiling. The script pattern is in `data/research/*.json` history.
- **Load and leave at `researched`:** `research-in data/research/<date>-autopilot.json`. Never `approve`; approval is Dave's.

## 4. Queue
Run `python3 crm/ob.py plan` with the default volume of 10 new starts. It only starts contacts Dave has approved, so yesterday's approvals go out today. Follow-ups are added automatically.

## 5. Publish and back up
1. Run `python3 crm/ob.py dashboard --artifact --out data/dashboard-site.html`.
2. Publish it to https://claude.ai/artifact/1VW4dQU9Jw6z4ppgEUB1k2 (`url` + `file_path`). This page is also the CRM backup, so a failed publish is a failed run.
3. Commit and push code or config changes only. Never commit `data/`.

## 6. Report to Dave (short)
- **New today:** how many found, researched and nurtured, with the top 3 (name, company, one-line signal).
- **Waiting for approval:** the IDs plus Icebreaker A for each. Ask him to reply "approve li-00xx …" or send edits.
- **Today's queue:** counts by channel, and the location of the copy (`data/queue-<date>.md`). Ask him to reply "sent all" when done.
- **Replies or meetings** since yesterday.
- **Clay data points used today.**
- **On Fridays,** also run `li-review` and add its one recommended change.

## Never
- Send, connect, DM or post on LinkedIn, or create Gmail drafts, in this unattended run.
- Use Apollo.
- Enrich more than 10 new prospects a day.
- Invent a signal, a fact or a mutual connection.
