---
name: li-log
description: Turn Dave's plain-English updates about prospects into CRM events. Covers sent, accepted, replied, meeting booked/held, proposal, won/lost, opt-out. Use when Dave says things like "Avery replied, wants a call next week", "Jordan booked for Thursday", "sent everything except Casey", "mark Taylor as not interested", "closed Northwind".
---

# li-log — keep the CRM honest

1. Resolve each person: `python3 crm/ob.py list --search "<name or company>"`. If more than one contact matches, ask which one. Never guess.
2. Map the update to an event:

| Dave says | Command |
|---|---|
| sent / done / messaged | `log <id> sent` (advances the sequence) |
| accepted my invite | `log <id> accepted` |
| replied, interested / wants a call | `log <id> replied --sentiment interested --note "..."` |
| replied with a question | `--sentiment question` |
| "not now", "reach out in Q1" | `--sentiment not_now` (moves to nurture; put the date in the note) |
| not interested | `--sentiment not_interested` |
| pointed me to someone else | `--sentiment referral`, then add the referral as a new contact via `research-in` |
| booked a call | `log <id> booked --note "<date>"` |
| had the call | `log <id> held --note "<outcome, next step>"` |
| sent proposal / won / lost | `log <id> proposal|won|lost --note "..."` |
| unsubscribe / stop / bounced | `log <id> optout` or `log <id> bounce` |
| "hold li-00xx" (don't send) | `log <id> nurture --note "held by Dave"`; the sender run won't touch it |

3. Confirm back in one line per contact.
4. For a positive reply, draft the response. Interested → two concrete time options plus `https://cal.com/ideabazi-daveb/30min`. Question → answer it in 60 words or fewer, then a soft ask. Dave sends it.
5. Refresh with `python3 crm/ob.py dashboard`.
