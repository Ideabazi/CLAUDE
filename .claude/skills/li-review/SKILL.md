---
name: li-review
description: Weekly review of the LinkedIn outreach system. Funnel metrics by degree, offer route, icebreaker variant and sequence; what to keep, kill and test next; and config changes to the ICP, caps or cadence. Use when Dave says "how's outreach doing", "weekly review", "what's working", or on a Friday scheduled run.
---

# li-review — measure, then change one thing

1. Pull the numbers:
   - `python3 crm/ob.py metrics` (overall and pipeline)
   - `python3 crm/ob.py metrics --by degree`, `--by route`, `--by variant`, `--by sequence`
   - `python3 crm/ob.py metrics --since <7 days ago>` (this week's cohort)
2. Compare against these benchmarks (healthy founder-led LinkedIn outreach; adjust as Dave's data accumulates):

| Metric | Healthy | Act if below |
|---|---|---|
| Connect accept rate (2nd/3rd) | 35–50% | 25%: rework the connect note or tighten the ICP |
| Reply rate (contacted cohort) | 15–25% (1st-degree: 30%+) | 10%: icebreakers are generic or the gift is weak |
| Positive / replies | 40%+ | 30%: wrong route, or the offer isn't landing |
| Meetings / contacted | 4–8% | 3%: the ask is too big, so offer the gift before the call |

3. **Small numbers:** under 30 contacted in a group means a direction, not a conclusion. Say so, and don't call an A/B winner below about 30 per arm.
4. Output (keep it short):
   - **Scoreboard:** this week vs all-time.
   - **What's working:** one or two findings, each backed by a number.
   - **What to change:** one experiment for next week, with the exact config or copy change (for example, lower `caps.default_new_starts_per_day`, move a route's industries, or retire icebreaker pattern X).
   - **Pipeline hygiene:** overdue follow-ups, `replied` contacts with no next step, and `meeting_held` with no proposal.
5. Apply config edits only after Dave says yes.
