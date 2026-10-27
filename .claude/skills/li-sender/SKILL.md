---
name: li-sender
description: The scheduled daily LinkedIn send run. Restore the CRM, check which invites were accepted and who replied, then send today's approved connection requests and messages from Dave's browser within the caps, log every send, and republish the dashboard. Use when a scheduled task says "daily LinkedIn send run", or when Dave says "send today's batch now".
---

# li-sender — send the approved touches from Dave's browser

**Authorization.** Dave authorized this run on 27 Oct 2026. It sends only copy already stored in the CRM, to contacts already approved (stage `ready` or `in_sequence`):
- at most **10 connection requests** (with the stored note)
- at most **20 messages** per day

Nothing else: no likes, comments, follows, InMail, posts, emails, edits to copy, or replies to people who answered. Dave handles replies.

## 0. Set up
1. **Get the repo on the right branch.** If the repo isn't in this container, attach `Ideabazi/CLAUDE` with `add_repo` and clone it. Then run `git fetch origin claude/youthful-euler-drnd4o && git checkout claude/youthful-euler-drnd4o`.
2. **Restore the CRM.** Read https://claude.ai/artifact/1VW4dQU9Jw6z4ppgEUB1k2 with the Artifact tool (`action: "read"`), then run `python3 crm/ob.py restore <saved file> --force`.
   - If this fails, stop and report. Never send from a missing or stale CRM: double-sends are the worst outcome here.
3. **Open the browser.**
   - Use whichever browser tool this session has, in this order: Claude in Chrome (`chrome-browser` skill), the desktop app's built-in browser (`built-in-browser` skill), or `mcp__remote-devices__Claude_Browser__*`. Load its tools in one ToolSearch call.
   - It must be Dave's own browser, already signed in to LinkedIn. Never open a fresh or headless browser (Playwright etc.): it isn't signed in and looks automated.
   - Open https://www.linkedin.com/feed/ and resize the window to 1440x1000.
   - If the browser is unreachable (desktop app closed, computer asleep) or LinkedIn isn't signed in, stop and report. Never enter credentials.

## Apply Dave's page updates (right after the restore, before anything else)
Dave can mark contacts on the dashboard: replied, booked, held, proposal, won, lost, hold, opted out, or a note. Each one is a document in the page's `actions` collection.
1. Load the `ArtifactData` tool with ToolSearch. Query url https://claude.ai/artifact/1VW4dQU9Jw6z4ppgEUB1k2, collection `actions`, `status == "pending"`.
2. Write the documents as a JSON list to `data/page-actions.json`, each with its document id as `_id`, then run `python3 crm/ob.py apply-actions data/page-actions.json`.
3. Use one `batch` to update every `_id` in its `applied` list to `{"status": "applied", "applied_at": "<now ISO>"}`. Leave any skipped ones pending and name them in the report.
4. Holds matter most here: a contact Dave marked "hold" must not be sent to today.

## 1. Sync first (view only, at most 25 profile or thread views)
For every contact whose connection request was sent but not accepted (`ob show <id>` → touches), open their `linkedin_url`.
- If the profile now shows them as **1st-degree** (a Message button, no Pending), run `python3 crm/ob.py log <id> accepted`.

For every contact who was sent a message, open the thread.
- If the newest message is from them, run `python3 crm/ob.py log <id> replied --note "<first ~15 words>"`. This stops their sequence. Add them to the report under **Replies**. Never answer.

Leave 20–40 seconds between views.

## 2. Plan
Run `python3 crm/ob.py plan --json`. The `queue` holds today's touches within the caps (10 connects, 20 messages).
- Skip any `email` touch: email isn't sent by this run.
- Send in this order: messages to people who accepted first, then connection requests.

## 3. Send, one at a time
For each touch:
1. **Open their profile and confirm it's the right person.**
   - Open `linkedin_url`. The name and the current company on the page must match the CRM.
   - If they don't match, or the page is ambiguous, run `log <id> skip --note "profile mismatch"` and move on.
2. **Connection request** (`linkedin_connect`):
   - Click **Connect**. It may sit under **More**. Choose **Add a note** and paste the stored body exactly.
   - Check that the note field holds the exact text, at 300 characters or fewer. Then click **Send**.
   - Confirm the button now reads **Pending**.
   - If LinkedIn offers no note option, don't send without one. Run `log <id> skip --note "no note option"`.
   - If they're already 1st-degree, run `log <id> accepted` and don't send.
3. **Message** (`linkedin_dm`):
   - Click **Message** and put the stored body into the compose box, one `<p>` per line.
   - Check the box text matches exactly, then click **Send**.
   - Confirm the sent bubble shows the same text.
   - If the thread's newest message is already from them, don't send. Run `log <id> replied` instead.
4. **Log** only after the send is confirmed: `python3 crm/ob.py log <id> sent`.
5. **Wait** a random 2–6 minutes before the next send. Use Bash `sleep` with `run_in_background`, because a foreground sleep is blocked.

**Stop the whole run immediately** on any of these:
- a CAPTCHA, a checkpoint, or a sign-in wall
- a message about the weekly invitation limit, messaging limits or unusual activity
- a send button that does nothing
- a confirmation that fails

Report exactly what you saw. Don't retry today.

## 4. Save and report
1. Run `python3 crm/ob.py dashboard --artifact --out data/dashboard-site.html`, then publish to https://claude.ai/artifact/1VW4dQU9Jw6z4ppgEUB1k2.
   - The publish is mandatory: it's how tomorrow's runs learn what was sent.
   - If it fails, run `python3 crm/ob.py backup data/backup-<date>.json`, retry once, and report.
2. Report to Dave, short:
   - sent today (connects / messages)
   - new accepts
   - **Replies**: name, company, first line, plus "reply yourself"
   - skipped, and why
   - anything held for tomorrow by the caps
