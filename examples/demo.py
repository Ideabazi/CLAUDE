#!/usr/bin/env python3
"""Build a demo CRM with fictional contacts so the dashboard can be previewed.

    python3 examples/demo.py   ->  data/demo/dashboard.html

Uses its own database (data/demo/demo.db); the real data/crm.db is untouched.
"""
import datetime as dt
import json
import os
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "data" / "demo"
DB = DEMO / "demo.db"
ENV = os.environ | {"OB_DB": str(DB)}
random.seed(7)


def ob(*args):
    subprocess.run([sys.executable, str(ROOT / "crm" / "ob.py"), *args], env=ENV, check=True, stdout=subprocess.DEVNULL)


FIRST = ["Avery", "Jordan", "Casey", "Taylor", "Morgan", "Riley", "Quinn", "Drew", "Parker", "Reese", "Rowan", "Sage",
         "Emerson", "Hayden", "Logan", "Blair", "Cameron", "Dakota", "Elliot", "Finley", "Harper", "Jules", "Kendall",
         "Lane", "Marlowe", "Noel", "Oakley", "Peyton", "Remy", "Shiloh", "Tatum", "Wren", "Arden", "Bellamy", "Corey",
         "Devon", "Ellis", "Frankie", "Gray", "Indy"]
COS = [("Northwind SaaS", "Software Development", 42), ("Contoso Agency", "Marketing Services", 18),
       ("Tailspin Consulting", "Business Consulting", 25), ("Adatum Software", "Software Development", 75),
       ("Proseware Legal", "Law Practice", 60), ("Fabrikam Logistics", "Logistics", 140),
       ("Woodgrove Accounting", "Accounting", 35), ("Litware Health", "Healthcare", 210),
       ("Lucerne Data", "Data Infrastructure", 55), ("Wingtip Builders", "Construction", 90)]
TITLES = ["Founder & CEO", "CEO", "Owner", "President", "Co-Founder", "Managing Partner", "Founder"]
STATES = ["Austin, Texas", "Denver, Colorado", "Sacramento, California", "Raleigh, North Carolina",
          "Boston, Massachusetts", "Chicago, Illinois", "Seattle, Washington", "Miami, Florida"]


def main():
    DEMO.mkdir(parents=True, exist_ok=True)
    DB.unlink(missing_ok=True)
    ob("init")
    csv_path = DEMO / "demo_contacts.csv"
    rows = ["Name,Title,Company,Location,Company Size,Industry,Profile URL,Degree,Email,Email Status"]
    for i, first in enumerate(FIRST):
        co, ind, size = COS[i % len(COS)]
        deg = [1, 1, 2, 2, 2, 3][i % 6]
        rows.append(f'{first} Demo{i:02d},{TITLES[i % len(TITLES)]},{co} {i:02d},"{STATES[i % len(STATES)]}, United States",'
                    f'{size},{ind},https://www.linkedin.com/in/demo-{i:02d},{deg},{first.lower()}@demo{i:02d}.example,'
                    f'{"verified" if i % 3 else "inferred"}')
    csv_path.write_text("\n".join(rows))
    ob("import-csv", str(csv_path), "--source", "demo")
    ob("qualify")

    research = []
    for i in range(1, 33):
        cid = f"li-{i:04d}"
        deg = [1, 1, 2, 2, 2, 3][(i - 1) % 6]
        seq = {1: "first_degree", 2: "second_degree", 3: "third_degree"}[deg]
        channels = {"first_degree": ["linkedin_dm", "email", "linkedin_dm", "email", "linkedin_dm"],
                    "second_degree": ["linkedin_connect", "linkedin_dm", "email", "linkedin_dm", "email", "email"],
                    "third_degree": ["email", "linkedin_connect", "email", "linkedin_dm", "email", "email"]}[seq]
        research.append({
            "id": cid, "route": "obdg" if i % 3 else "aiweb", "campaign": "demo",
            "signal": random.randint(2, 5), "pain": random.randint(2, 5), "capacity": random.randint(2, 5),
            "icebreaker_a": "Demo icebreaker A", "icebreaker_b": "Demo icebreaker B",
            "icebreaker_choice": "A" if i % 2 else "B",
            "messages": [{"step": s, "channel": ch, "body": f"Demo copy for step {s}"} for s, ch in enumerate(channels)],
        })
    (DEMO / "research.json").write_text(json.dumps(research))
    ob("research-in", str(DEMO / "research.json"))
    ob("approve", *[f"li-{i:04d}" for i in range(1, 29)])

    # Simulate three weeks of daily runs
    start = dt.date.today() - dt.timedelta(days=21)
    for d in range(0, 21, 3):
        day = (start + dt.timedelta(days=d)).isoformat()
        ob("plan", "--volume", "4", "--date", day)
    for i in range(1, 29):
        cid = f"li-{i:04d}"
        day = start + dt.timedelta(days=(i - 1) // 4 * 3)
        ob("log", cid, "sent", "--at", f"{day}T09:{i:02d}:00")
        deg = [1, 1, 2, 2, 2, 3][(i - 1) % 6]
        if deg != 1 and random.random() < 0.55:
            ob("log", cid, "accepted", "--at", f"{day + dt.timedelta(days=1)}T12:00:00")
        r = random.random()
        reply_day = f"{day + dt.timedelta(days=4)}T15:00:00"
        if r < 0.12:
            ob("log", cid, "replied", "--sentiment", "interested", "--note", "wants to talk pipeline", "--at", reply_day)
            ob("log", cid, "booked", "--note", "30 min intro", "--at", reply_day)
            if random.random() < 0.6:
                ob("log", cid, "held", "--note", "audit scoped", "--at", f"{day + dt.timedelta(days=8)}T10:00:00")
        elif r < 0.22:
            ob("log", cid, "replied", "--sentiment", "question", "--note", "asked about pricing", "--at", reply_day)
        elif r < 0.30:
            ob("log", cid, "replied", "--sentiment", "not_now", "--note", "revisit in Q1", "--at", reply_day)
    ob("plan", "--volume", "0")
    ob("dashboard")
    print(DEMO / "dashboard.html")


if __name__ == "__main__":
    main()
