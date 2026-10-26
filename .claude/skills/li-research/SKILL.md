---
name: li-research
description: Research qualified prospects in the outreach CRM. Confirm ICP fit and the best Ideabazi offer route, score out of 25, find a dated signal, build a real gift, write two icebreakers and draft every sequence step, then load it all back with research-in. Use when Dave says "research the top 10", "write icebreakers", "prep tomorrow's batch", or after li-source.
---

# li-research — from "qualified" to "ready to send"

This skill is the CRM wrapper around the **ideabazi-outbound** skill. Load it first: its research, scoring, gift, icebreaker, voice, slop-test and banned-word rules (Steps 4–10 and Section 0) apply here unchanged. This skill adds only the CRM plumbing.

## Steps
- **No Apollo.** The connected Apollo account belongs to a client. Wherever this file mentions Apollo, use Clay, FullEnrich or Vibe Prospecting instead (confirm the account is Dave's first).
1. **Pick the batch.** `python3 crm/ob.py list --stage qualified --json --limit N`. Default N = 10 on a new route or ICP, and up to 40 once Dave has reviewed a batch. Order: 1st-degree first, then 2nd-degree with mutuals, then the rest by score.
2. **Re-check the offer.** Try ideabazi.com; if it's unreachable, use the offer routes in `config/outreach.toml` and say so. Only cite prices and proof that are live.
3. **Research each contact** (ideabazi-outbound Step 4): their site plus 1–2 external sources, and their recent LinkedIn activity if visible (Clay recent posts or Vibe `enrich-business-linkedin-posts`; or a single view-only profile visit). Fill in any missing location, headcount or industry. **Drop anyone who is not US, outside 5–500 employees, or not the owner/economic buyer**: set `"stage": "disqualified"` with a reason in `notes`.
4. **Choose the route.** `obdg` or `aiweb` is whichever has the more visible pain. Record the reason in `pain_note`.
5. **Score** fit / signal / pain / reach / capacity (1–5 each, per ideabazi-outbound Step 6). A signal needs a date and a source, or it scores 1. Anything under 15/25 is set to `"stage": "nurture"` and gets no copy.
6. **Gift + icebreakers.** One true gift. Icebreaker A and B: 20 words or fewer, a specific dated fact, no compliments, no "I". Set `icebreaker_choice` to A, or B for every other lead so the A/B metric gets data.
7. **Draft each step** of the sequence that matches the contact's degree (`config/outreach.toml` → `sequences.first_degree | second_degree | third_degree`), indexed exactly like the config `steps` array (0-based). Respect each step's word or character ceiling. The connect note is 300 characters or fewer and has no pitch. Booking link: `owner.booking_url`. Put it only in the close-out or right after a positive reply, never in a connect note. Email bodies carry no signature (it's appended when sending). Skip email steps for contacts with no verified email; the planner skips them anyway.
8. **Write the JSON** to `data/research/<YYYY-MM-DD>-<slug>.json` and load it:
   ```json
   [{"id": "li-0007", "route": "obdg", "campaign": "obdg-saas-founders",
     "location": "Austin, Texas, United States", "employees": 45, "industry": "Software",
     "email": "x@y.com", "email_status": "verified",
     "fit": 5, "signal": 4, "pain": 4, "reach": 4, "capacity": 3,
     "signal_note": "2026-10-02 · posted SDR role · careers page",
     "pain_note": "demo CTA routes to a generic form",
     "gift": "3-fix pipeline teardown", "icebreaker_a": "...", "icebreaker_b": "...", "icebreaker_choice": "A",
     "messages": [{"step": 0, "channel": "linkedin_connect", "body": "..."},
                  {"step": 2, "channel": "email", "subject": "...", "body": "..."}]}]
   ```
   `python3 crm/ob.py research-in data/research/<file>.json`
9. **Present for approval (gate b):** the top leads with score, reason and Icebreaker A, and the full copy for the top 3. After Dave's edits, update the JSON, re-load it, then run `python3 crm/ob.py approve <ids>`. **Only approved contacts enter the daily queue.**

## Never
Fabricate a signal, a mutual connection, a result or an email. Name a mutual to the prospect. Write copy that could go to another company with two words changed.
