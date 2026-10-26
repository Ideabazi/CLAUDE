---
name: li-source
description: Pull prospects into the outreach CRM by LinkedIn degree — 1st-degree from Dave's LinkedIn data export, 2nd-degree from Sales Navigator / Apollo searches, 3rd-degree from Apollo/Clay/FullEnrich ICP searches — then run the ICP filter. Use when Dave says "load my connections", "find founders in my network", "build a list of 2nd-degree CEOs", "source new prospects", or drops a CSV into data/imports/.
---

# li-source — get the right people into the CRM

Goal: US founders / CEOs / presidents / owners of SMB and mid-market companies (5–500 employees) that fit an Ideabazi offer route in `config/outreach.toml`. Every source ends in the same place: `python3 crm/ob.py qualify`.

## Ground rules
- **No scraping LinkedIn.** Don't crawl connection lists, search results or "People also viewed" with a browser, and don't use cookie-based scrapers. LinkedIn restricts accounts for this, and Dave's account is the asset. Data comes from: LinkedIn's own data export, Sales Navigator exports or lists Dave pulls himself, and B2B data providers (Apollo, Clay, FullEnrich, Vibe Prospecting).
- Profile views in Dave's browser (for the degree check) are capped at `caps.profile_views_per_run`, 20–40 seconds apart. Stop at any checkpoint or CAPTCHA. Never log in.
- Paid enrichment: state the credit cost first and wait for a yes (ideabazi-outbound hard rule 7).
- If `data/crm.db` is missing, run `python3 crm/ob.py init` first.

## 1st-degree (warmest, do first)
1. Dave downloads the export himself: LinkedIn → Settings → Data privacy → **Get a copy of your data** → "Connections" (it arrives by email in about 10 minutes). He saves `Connections.csv` to `data/imports/`.
2. `python3 crm/ob.py import-linkedin data/imports/Connections.csv`
3. `python3 crm/ob.py qualify`
4. The export has no location or headcount. For qualified contacts, enrich in batches with Apollo `apollo_people_bulk_match` / `apollo_organizations_bulk_enrich` (up to 10 per call; state credits first), or Clay `add-contact-data-points`. Write the results back through `research-in` (location, country, employees, industry, email + email_status), then re-run `qualify --all`.

## 2nd-degree
Option A (best): **Sales Navigator** lead search. Dave runs it, or Claude walks him through it:
- Connections: 2nd · Geography: United States · Seniority: Owner/Partner, CXO · Current title: Founder OR CEO OR President OR Owner · Company headcount: 11–50, 51–200, 201–500 · Industry: per route (see config).
- Save as a lead list. Export via Dave's own export tool or a CSV copy, then `import-csv <file> --degree 2 --source salesnav --campaign <slug>`.

Option B: **Apollo** `apollo_mixed_people_api_search` with the same filters (person_titles, person_seniorities owner/founder/c_suite, person_locations United States, organization_num_employees_ranges). Searching without revealing emails is free. Export to CSV and `import-csv --degree 3`. Then **degree check**: for the top-scored rows only, open each profile in Dave's browser (view only, within the profile-view cap) and record the degree, mutual count and up to 2 mutual names through `research-in`. A 2nd-degree contact whose mutual is a client or friend becomes a warm-intro candidate.

## 3rd-degree / cold
Use Apollo, Clay `search-contacts`, FullEnrich `search_people` / `export_contacts`, or Vibe Prospecting `fetch-entities` with the ICP filters. Import with `--degree 3`. These run the `third_degree` sequence, which leads with email, so verified emails matter more than the LinkedIn degree.

## Close
Report: rows imported per source, qualified vs disqualified (with the top disqualification reasons from `disq_reason`), how many still need location or headcount, and the split by route. Suggest the next step: `li-research` on the top 10.
