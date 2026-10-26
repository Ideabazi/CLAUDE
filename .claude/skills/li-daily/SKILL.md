---
name: li-daily
description: Run Dave's daily LinkedIn outreach. Sync replies, build today's queue at the volume Dave chooses, hand over ready-to-paste copy, log the sends, and refresh the dashboard. Use when Dave says "today's outreach", "run my daily", "what's on the list today", "do 15 today", or on a scheduled morning run.
---

# li-daily — the 20-minute daily loop

Dave decides the volume. Claude does the prep, the bookkeeping and the measurement. Dave presses Send.

## 1. Sync replies first (a reply stops a sequence)
- **Email:** for every contact in `in_sequence` who has an email, search Gmail (dave@ideabazi.com) for messages from that address since `last_touch_at`. Ignore warmup mail.
- **LinkedIn:** there is no API, so ask Dave: "Any LinkedIn replies or accepted invites since yesterday? Paste or list names." If he's in a live session with the browser available, Claude may *read* his LinkedIn messaging inbox and My Network → Sent invitations (view only).
- Log each one: `python3 crm/ob.py log <id> accepted`, or `log <id> replied --sentiment interested|question|not_now|not_interested|referral --note "<20 words or fewer>"`.
- For every positive reply, draft a response with the **linkedin-inbox-responder** approach: answer the question, offer two specific times, and include `https://cal.com/ideabazi-daveb/30min`. Dave sends it.

## 2. Plan
- Volume: use what Dave said ("do 15 today"); otherwise `caps.default_new_starts_per_day`. Follow-ups that are due are always added on top, within the channel caps.
- `python3 crm/ob.py plan --volume N`
- If the `ready` pool is smaller than N, say so and offer `li-research` on the next qualified batch. Never start unapproved contacts.

## 3. Hand over
Show `data/queue-<date>.md` grouped by channel, in this order: **connect requests** (paste the note), **DMs**, then **emails**. For each touch, give the profile link and the exact copy.
- Email touches: offer to create Gmail drafts from dave@ideabazi.com with the signature appended (ideabazi-outbound gate d, one yes per batch). For Path B volume, use the Apollo flow in ideabazi-outbound instead.
- LinkedIn touches: Dave sends by hand. Claude may send connection requests in Dave's live browser only under ideabazi-outbound **hard rule 6**: a per-batch yes, 8 per day or fewer, 3–6 minutes apart, never unattended, and stop on any checkpoint. DMs are always sent by Dave.

## 4. Log
When Dave confirms ("sent all", "sent all except li-0012"), run `python3 crm/ob.py log <id> sent` for each, adding `--variant A|B` if the icebreaker differs from the stored choice. Unsent touches stay due and roll to tomorrow.

## 5. Close
Refresh the live dashboard (see CLAUDE.md: `ob dashboard --artifact --out data/dashboard-site.html`, then republish it to Dave's dashboard URL) and run `python3 crm/ob.py metrics`. Give a 3-line summary: touches sent today, replies and meetings so far this week, and the one thing to fix (for example "accept rate 18% on 2nd-degree, so test icebreaker B in the connect note").

## Scheduled (unattended) runs
Steps 1 (email only), 2 and 5 only. Prepare the queue and the drafts list, but send nothing, create no drafts and perform no LinkedIn actions.
