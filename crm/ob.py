#!/usr/bin/env python3
"""ob — Ideabazi LinkedIn outreach CRM.

A small, local, SQLite-backed CRM that Claude Code (and Dave) drive from the
terminal. Stdlib only. Data lives in data/crm.db (git-ignored: it holds PII).

    python3 crm/ob.py init
    python3 crm/ob.py import-linkedin data/imports/Connections.csv
    python3 crm/ob.py import-csv data/imports/salesnav.csv --degree 2 --source salesnav
    python3 crm/ob.py qualify
    python3 crm/ob.py list --stage qualified --limit 20
    python3 crm/ob.py research-in data/research/batch-01.json
    python3 crm/ob.py approve li-0007 li-0012
    python3 crm/ob.py plan --volume 10
    python3 crm/ob.py log li-0007 sent
    python3 crm/ob.py log li-0007 replied --sentiment interested --note "wants a call"
    python3 crm/ob.py metrics --by degree
    python3 crm/ob.py dashboard

Run any command with -h for options.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import os
import json
import re
import sqlite3
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "outreach.toml"
DATA = ROOT / "data"
DB_PATH = Path(os.environ.get("OB_DB", DATA / "crm.db"))
OUT = DB_PATH.parent  # queues + dashboard live next to the database
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

STAGES = [
    "new", "qualified", "disqualified", "researched", "ready", "in_sequence",
    "replied", "meeting_booked", "meeting_held", "proposal", "won", "lost",
    "nurture", "opted_out", "completed",
]
ACTIVE_STAGES = ("ready", "in_sequence")
SEQ_BY_DEGREE = {1: "first_degree", 2: "second_degree", 3: "third_degree"}

# Fields Claude's research JSON may set on a contact.
RESEARCH_FIELDS = {
    "first_name", "last_name", "title", "company", "company_domain", "email",
    "email_status", "location", "country", "employees", "industry", "degree",
    "mutuals", "warm_path", "recent_activity", "route", "campaign", "fit",
    "signal", "pain", "reach", "capacity", "signal_note", "pain_note", "gift",
    "icebreaker_a", "icebreaker_b", "icebreaker_choice", "notes", "stage", "sequence", "source",
}


# --------------------------------------------------------------------------- utils

def today() -> dt.date:
    return dt.date.today()


def now_iso() -> str:
    return dt.datetime.now().replace(microsecond=0).isoformat()


def load_config() -> dict:
    with CONFIG_PATH.open("rb") as f:
        return tomllib.load(f)


def connect() -> sqlite3.Connection:
    OUT.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)


def die(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def norm_url(url: str | None) -> str | None:
    if not url:
        return None
    url = url.strip().split("?")[0].rstrip("/")
    url = re.sub(r"^https?://([a-z]{2,3}\.)?linkedin\.com", "https://www.linkedin.com", url, flags=re.I)
    return url.lower() or None


def next_id(con: sqlite3.Connection) -> str:
    row = con.execute("SELECT id FROM contacts ORDER BY CAST(SUBSTR(id, 4) AS INTEGER) DESC LIMIT 1").fetchone()
    n = int(row["id"][3:]) + 1 if row else 1
    return f"li-{n:04d}"


def score_total(c) -> int:
    return sum(int(c[k] or 0) for k in ("fit", "signal", "pain", "reach", "capacity"))


def table(rows: list[dict], cols: list[str]) -> str:
    if not rows:
        return "(none)"
    cell = lambda r, c: "" if r.get(c) is None else str(r.get(c))
    widths = {c: min(max(len(c), *(len(cell(r, c)) for r in rows)), 42) for c in cols}
    line = "  ".join(c.ljust(widths[c]) for c in cols)
    out = [line, "  ".join("-" * widths[c] for c in cols)]
    for r in rows:
        out.append("  ".join(cell(r, c)[: widths[c]].ljust(widths[c]) for c in cols))
    return "\n".join(out)


# --------------------------------------------------------------------------- init / import

def cmd_init(args) -> None:
    con = connect()
    con.executescript(SCHEMA_PATH.read_text())
    con.commit()
    print(f"database ready: {DB_PATH}")


def upsert_contact(con, rec: dict, source: str, degree: int | None) -> str:
    """Insert or merge a contact keyed on LinkedIn URL (falls back to name+company)."""
    url = norm_url(rec.get("linkedin_url"))
    existing = None
    if url:
        existing = con.execute("SELECT * FROM contacts WHERE linkedin_url = ?", (url,)).fetchone()
    if not existing and rec.get("first_name") and rec.get("company"):
        existing = con.execute(
            "SELECT * FROM contacts WHERE lower(first_name)=lower(?) AND lower(last_name)=lower(?) AND lower(company)=lower(?)",
            (rec.get("first_name"), rec.get("last_name") or "", rec.get("company")),
        ).fetchone()
    fields = {k: v for k, v in rec.items() if v not in (None, "")}
    fields["linkedin_url"] = url
    if existing:
        # Never downgrade a known degree (1 beats 2 beats 3) and never blank a field.
        if degree and existing["degree"] and existing["degree"] < degree:
            degree = existing["degree"]
        updates = {k: v for k, v in fields.items() if v and not existing[k]}
        if degree:
            updates["degree"] = degree
        if updates:
            updates["updated_at"] = now_iso()
            sets = ", ".join(f"{k} = ?" for k in updates)
            con.execute(f"UPDATE contacts SET {sets} WHERE id = ?", (*updates.values(), existing["id"]))
        return existing["id"]
    cid = next_id(con)
    fields.update(id=cid, source=source, degree=degree, stage="new", created_at=now_iso(), updated_at=now_iso())
    cols = ", ".join(fields)
    con.execute(f"INSERT INTO contacts ({cols}) VALUES ({', '.join('?' * len(fields))})", tuple(fields.values()))
    return cid


def cmd_import_linkedin(args) -> None:
    """LinkedIn data export: Settings > Data privacy > Get a copy of your data > Connections."""
    text = Path(args.path).read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    start = next((i for i, l in enumerate(lines) if l.startswith("First Name")), None)
    if start is None:
        die("no 'First Name' header found — is this LinkedIn's Connections.csv?")
    con = connect()
    n = 0
    for row in csv.DictReader(lines[start:]):
        connected = row.get("Connected On") or ""
        try:
            connected = dt.datetime.strptime(connected, "%d %b %Y").date().isoformat()
        except ValueError:
            pass
        upsert_contact(con, {
            "first_name": row.get("First Name"), "last_name": row.get("Last Name"),
            "linkedin_url": row.get("URL"), "email": row.get("Email Address"),
            "email_status": "verified" if row.get("Email Address") else None,
            "company": row.get("Company"), "title": row.get("Position"),
            "connected_on": connected,
        }, source="linkedin_export", degree=1)
        n += 1
    con.commit()
    print(f"imported/merged {n} 1st-degree connections. Next: ob qualify")


# Header aliases for Sales Navigator / Apollo / Clay / FullEnrich / generic CSVs.
ALIASES = {
    "first_name": ["first name", "first_name", "firstname"],
    "last_name": ["last name", "last_name", "lastname"],
    "full_name": ["name", "full name", "full_name"],
    "title": ["title", "job title", "position", "headline", "current title"],
    "company": ["company", "company name", "organization", "account name", "current company"],
    "company_domain": ["website", "company website", "domain", "company domain"],
    "linkedin_url": ["linkedin", "linkedin url", "person linkedin url", "profile url", "linkedin profile", "url"],
    "email": ["email", "email address", "work email"],
    "email_status": ["email status"],
    "location": ["location", "city", "geography", "person location"],
    "country": ["country"],
    "employees": ["employees", "# employees", "company size", "headcount", "employee count"],
    "industry": ["industry"],
    "degree": ["degree", "connection degree", "li degree"],
    "mutuals": ["mutuals", "mutual connections", "shared connections"],
}


def map_row(row: dict) -> dict:
    lower = {k.strip().lower(): v for k, v in row.items() if k}
    out = {}
    for field, names in ALIASES.items():
        for n in names:
            if lower.get(n):
                out[field] = lower[n].strip()
                break
    if "full_name" in out and "first_name" not in out:
        parts = out["full_name"].split()
        out["first_name"], out["last_name"] = parts[0], " ".join(parts[1:])
    out.pop("full_name", None)
    if "employees" in out:
        m = re.search(r"\d[\d,]*", out["employees"])
        out["employees"] = int(m.group().replace(",", "")) if m else None
    if "degree" in out:
        m = re.search(r"[123]", out["degree"])
        out["degree"] = int(m.group()) if m else None
    if out.get("email_status"):
        s = out["email_status"].lower()
        out["email_status"] = "verified" if "verif" in s or s == "valid" else "inferred"
    return out


def cmd_import_csv(args) -> None:
    con = connect()
    n = 0
    with open(args.path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rec = map_row(row)
            if not rec.get("first_name") and not rec.get("linkedin_url"):
                continue
            degree = rec.pop("degree", None) or args.degree
            if rec.get("email") and not rec.get("email_status"):
                rec["email_status"] = "inferred"
            if args.campaign:
                rec["campaign"] = args.campaign
            upsert_contact(con, rec, source=args.source, degree=degree)
            n += 1
    con.commit()
    print(f"imported/merged {n} rows from {args.source}. Next: ob qualify")


# --------------------------------------------------------------------------- qualify

def guess_route(cfg, c) -> str | None:
    hay = " ".join(str(c[k] or "") for k in ("industry", "company", "title")).lower()
    best, hits = None, 0
    for r in cfg["routes"]:
        h = sum(1 for kw in r["industry_keywords"] if kw in hay)
        if h > hits:
            best, hits = r["slug"], h
    return best


def region_of(icp, c) -> str | None | bool:
    """Allowed region name, False if located elsewhere, None if the location is unknown."""
    geo = " ".join(str(c[k] or "") for k in ("location", "country")).lower()
    if not geo.strip():
        return None
    for region, markers in icp["regions"].items():
        if any(m in geo for m in markers):
            return region
    return False


OPEN_STAGES = ("new", "qualified", "disqualified", "researched", "ready", "in_sequence", "nurture")


def cmd_audit(args) -> None:
    """Score exported lists (Clay tables, Sales Navigator, etc.) against the ICP without importing them."""
    from collections import Counter
    cfg = load_config()
    icp = cfg["icp"]
    inc, exc = re.compile(icp["title_include"], re.I), re.compile(icp["title_exclude"], re.I)
    con = connect()
    known = {r[0] for r in con.execute("SELECT linkedin_url FROM contacts WHERE linkedin_url IS NOT NULL")}
    for path in args.paths:
        with open(path, newline="", encoding="utf-8-sig") as f:
            rows = [map_row(r) for r in csv.DictReader(f)]
        rows = [r for r in rows if r.get("first_name") or r.get("linkedin_url")]
        tally, regions, bad_titles = Counter(), Counter(), Counter()
        for r in rows:
            title = r.get("title") or ""
            cxo = bool(inc.search(title)) and not exc.search(title)
            region = region_of(icp, {"location": r.get("location"), "country": r.get("country")})
            emp = r.get("employees")
            size_ok = None if emp is None else icp["size"]["employees_min"] <= emp <= icp["size"]["employees_max"]
            if norm_url(r.get("linkedin_url")) in known:
                tally["already in CRM"] += 1
            if not cxo:
                tally["not owner/C-suite"] += 1
                bad_titles[title.strip().lower()[:40] or "(no title)"] += 1
            elif region is False:
                tally["outside regions"] += 1
            elif size_ok is False:
                tally["company size outside 5-500"] += 1
            elif region is None or size_ok is None:
                tally["fits title, needs location/size"] += 1
            else:
                tally["ICP fit"] += 1
                regions[region] += 1
            tally["has LinkedIn URL"] += bool(r.get("linkedin_url"))
            tally["has email"] += bool(r.get("email"))
        n = len(rows) or 1
        fit = tally["ICP fit"]
        verdict = ("already loaded: every row is in the CRM" if tally["already in CRM"] == len(rows) else
                   "outreach: import it" if fit / n >= 0.3 else
                   "partial: import, the ICP filter drops the rest" if fit else
                   "enrich first: titles fit but location/size are missing" if tally["fits title, needs location/size"] else
                   "skip: almost nothing fits the ICP")
        print(f"\n== {path}  ({len(rows)} people)")
        for k in ("ICP fit", "fits title, needs location/size", "not owner/C-suite", "outside regions",
                  "company size outside 5-500", "already in CRM", "has LinkedIn URL", "has email"):
            print(f"  {k:<34} {tally[k]:>6}  {100 * tally[k] / n:5.1f}%")
        if regions:
            print("  ICP fit by region: " + ", ".join(f"{k} {v}" for k, v in regions.most_common()))
        if bad_titles:
            print("  most common non-CXO titles: " + "; ".join(f"{t} ({c})" for t, c in bad_titles.most_common(5)))
        print(f"  verdict: {verdict}")


def cmd_qualify(args) -> None:
    """ICP filter: owner/C-suite title, allowed region, headcount band. Sets fit + reach.

    --enforce also re-checks contacts already being worked (researched, ready, in sequence,
    nurture) and disqualifies any that fail, including those whose location is unknown.
    """
    cfg = load_config()
    icp = cfg["icp"]
    inc = re.compile(icp["title_include"], re.I)
    exc = re.compile(icp["title_exclude"], re.I)
    con = connect()
    stages = OPEN_STAGES if args.enforce else ("new", "qualified", "disqualified")
    rows = con.execute(f"SELECT * FROM contacts WHERE stage IN ({','.join('?' * len(stages))})", stages).fetchall()
    stats = {"qualified": 0, "disqualified": 0, "kept": 0}
    for c in rows:
        title = c["title"] or ""
        reasons = []
        dm = bool(inc.search(title)) and not exc.search(title)
        if not dm:
            reasons.append("title")
        region = region_of(icp, c)
        if region is False:
            reasons.append("geo")
        elif region is None and args.enforce:
            reasons.append("geo-unknown")
        emp = c["employees"]
        size_ok = None if emp is None else icp["size"]["employees_min"] <= emp <= icp["size"]["employees_max"]
        if size_ok is False:
            reasons.append("size")
        route = c["route"] or guess_route(cfg, c)

        fit = (2 if dm else 0) + (1 if region else 0) + (1 if size_ok else 0) + (1 if route else 0)
        if region is None or size_ok is None:
            fit = max(fit, 2 if dm else 0)  # unknowns: research fills the gap
        email_v = c["email"] and c["email_status"] == "verified"
        reach = 5 if c["degree"] == 1 else 4 if email_v else 3 if (c["degree"] == 2 or c["email"]) else 2

        if reasons:
            stage = "disqualified"
        elif c["stage"] == "disqualified" and not c["disq_reason"]:
            stage = "disqualified"  # disqualified by hand during research (e.g. acquired); keep it
            reasons = None
        elif c["stage"] in ("new", "qualified", "disqualified"):
            stage = "qualified"
        else:
            stage = c["stage"]  # worked contacts that still fit keep their place
        if stage == "disqualified" and c["stage"] not in ("new", "qualified", "disqualified"):
            con.execute("INSERT INTO touches (contact_id, ts, event, detail) VALUES (?,?,?,?)",
                        (c["id"], now_iso(), "note", f"disqualified by ICP check: {','.join(reasons)}"))
        con.execute(
            "UPDATE contacts SET is_decision_maker=?, fit=?, reach=?, route=?, stage=?, disq_reason=?, "
            "next_touch_due=CASE WHEN ?='disqualified' THEN NULL ELSE next_touch_due END, "
            "country=COALESCE(country, ?), updated_at=? WHERE id=?",
            (int(dm), min(fit, 5), reach, route, stage, ",".join(reasons or []) or None, stage,
             region or None, now_iso(), c["id"]),
        )
        stats[stage if stage in stats else "kept"] += 1
    con.commit()
    unknown = con.execute(
        "SELECT COUNT(*) FROM contacts WHERE stage='qualified' AND (location IS NULL OR employees IS NULL)"
    ).fetchone()[0]
    print(f"qualified {stats['qualified']}, disqualified {stats['disqualified']}, still in progress {stats['kept']}")
    if unknown:
        print(f"{unknown} qualified contacts lack location or headcount: enrich them (Clay) before outreach.")


# --------------------------------------------------------------------------- browse

LIST_COLS = ["id", "degree", "stage", "score", "first_name", "last_name", "title", "company", "route", "next_touch_due"]


def cmd_list(args) -> None:
    con = connect()
    q, p = "SELECT * FROM contacts WHERE 1=1", []
    if args.stage:
        q += " AND stage = ?"; p.append(args.stage)
    if args.degree:
        q += " AND degree = ?"; p.append(args.degree)
    if args.route:
        q += " AND route = ?"; p.append(args.route)
    if args.search:
        q += " AND (lower(company) LIKE ? OR lower(first_name||' '||last_name) LIKE ? OR lower(title) LIKE ?)"
        s = f"%{args.search.lower()}%"; p += [s, s, s]
    rows = [dict(r) | {"score": score_total(r)} for r in con.execute(q, p).fetchall()]
    rows.sort(key=lambda r: (-(r["score"]), r["degree"] or 9, r["id"]))
    if args.json:
        print(json.dumps(rows[: args.limit], indent=2, default=str))
    else:
        print(table(rows[: args.limit], LIST_COLS))
        print(f"\n{len(rows)} matching contacts")


def cmd_show(args) -> None:
    con = connect()
    c = con.execute("SELECT * FROM contacts WHERE id = ?", (args.id,)).fetchone()
    if not c:
        die(f"no contact {args.id}")
    d = dict(c) | {"score": score_total(c)}
    d["messages"] = [dict(m) for m in con.execute("SELECT step, channel, subject, body, status FROM messages WHERE contact_id=? ORDER BY step", (args.id,))]
    d["touches"] = [dict(t) for t in con.execute("SELECT ts, channel, event, step, detail FROM touches WHERE contact_id=? ORDER BY ts", (args.id,))]
    print(json.dumps(d, indent=2, default=str))


# --------------------------------------------------------------------------- research in

def cmd_research_in(args) -> None:
    """Load Claude's research JSON: [{id|linkedin_url, <fields>, messages:[{step, channel, subject?, body}]}]."""
    items = json.loads(Path(args.path).read_text())
    if isinstance(items, dict):
        items = [items]
    con = connect()
    done = 0
    for it in items:
        cid = it.get("id")
        if not cid and it.get("linkedin_url"):
            row = con.execute("SELECT id FROM contacts WHERE linkedin_url=?", (norm_url(it["linkedin_url"]),)).fetchone()
            cid = row["id"] if row else upsert_contact(con, map_row(it) | {"linkedin_url": it["linkedin_url"]},
                                                      source=it.get("source", "research"), degree=it.get("degree"))
        if not cid or not con.execute("SELECT 1 FROM contacts WHERE id=?", (cid,)).fetchone():
            print(f"skip: unknown contact {cid or it}", file=sys.stderr)
            continue
        fields = {k: v for k, v in it.items() if k in RESEARCH_FIELDS}
        fields.setdefault("stage", "researched")
        fields["researched_at"] = now_iso()
        fields["updated_at"] = now_iso()
        sets = ", ".join(f"{k} = ?" for k in fields)
        con.execute(f"UPDATE contacts SET {sets} WHERE id = ?", (*fields.values(), cid))
        for m in it.get("messages", []):
            con.execute(
                "INSERT INTO messages (contact_id, step, channel, subject, body, status, created_at) VALUES (?,?,?,?,?, 'draft', ?) "
                "ON CONFLICT(contact_id, step) DO UPDATE SET channel=excluded.channel, subject=excluded.subject, body=excluded.body, status='draft'",
                (cid, m["step"], m["channel"], m.get("subject"), m["body"], now_iso()),
            )
        done += 1
    con.commit()
    print(f"loaded research for {done} contacts. Review with: ob list --stage researched ; then ob approve <ids>")


def cmd_approve(args) -> None:
    con = connect()
    for cid in args.ids:
        c = con.execute("SELECT stage, (SELECT COUNT(*) FROM messages WHERE contact_id=?) n FROM contacts WHERE id=?", (cid, cid)).fetchone()
        if not c:
            print(f"skip {cid}: not found"); continue
        if c["n"] == 0:
            print(f"skip {cid}: no drafted messages"); continue
        con.execute("UPDATE contacts SET stage='ready', updated_at=? WHERE id=?", (now_iso(), cid))
        con.execute("UPDATE messages SET status='approved' WHERE contact_id=?", (cid,))
        print(f"{cid}: ready")
    con.commit()


# --------------------------------------------------------------------------- sequencing

def sequence_for(cfg, c) -> tuple[str, list[dict]]:
    name = c["sequence"] or SEQ_BY_DEGREE.get(c["degree"] or 3, "third_degree")
    return name, cfg["sequences"][name]["steps"]


def accepted(con, cid) -> bool:
    return bool(con.execute("SELECT 1 FROM touches WHERE contact_id=? AND event='accepted'", (cid,)).fetchone())


def actionable_step(con, c, steps, start: int) -> int | None:
    """First step >= start the contact can actually receive."""
    enabled = load_config().get("sending", {}).get("channels")
    for i in range(start, len(steps)):
        ch = steps[i]["channel"]
        if enabled is not None and ch not in enabled:
            continue  # nothing sends on this channel yet; don't let it stall the sequence
        if ch == "email" and not (c["email"] and c["email_status"] == "verified"):
            continue
        if ch == "linkedin_dm" and c["degree"] != 1 and not accepted(con, c["id"]):
            continue
        if ch == "linkedin_connect" and (c["degree"] == 1 or accepted(con, c["id"])):
            continue
        return i
    return None


def sent_today(con, channel: str, day: dt.date) -> int:
    return con.execute("SELECT COUNT(*) FROM touches WHERE channel=? AND event='sent' AND date(ts)=?",
                       (channel, day.isoformat())).fetchone()[0]


def sent_this_week(con, channel: str, day: dt.date) -> int:
    start = day - dt.timedelta(days=6)
    return con.execute("SELECT COUNT(*) FROM touches WHERE channel=? AND event='sent' AND date(ts) BETWEEN ? AND ?",
                       (channel, start.isoformat(), day.isoformat())).fetchone()[0]


def cmd_plan(args) -> None:
    """Build today's queue: due follow-ups first, then N new starts by score, within caps."""
    cfg = load_config()
    caps = cfg["caps"]
    day = dt.date.fromisoformat(args.date) if args.date else today()
    volume = args.volume if args.volume is not None else caps["default_new_starts_per_day"]
    con = connect()
    budget = {
        "linkedin_connect": min(caps["connect_requests_per_day"] - sent_today(con, "linkedin_connect", day),
                                caps["connect_requests_per_week"] - sent_this_week(con, "linkedin_connect", day)),
        "linkedin_dm": caps["linkedin_dms_per_day"] - sent_today(con, "linkedin_dm", day),
        "email": caps["emails_per_day"] - sent_today(con, "email", day),
    }
    queue, skipped = [], []

    def take(c, kind):
        name, steps = sequence_for(cfg, c)
        idx = actionable_step(con, c, steps, c["step"] or 0)
        if idx is None:
            skipped.append((c["id"], "no reachable step left (needs accept / verified email)"))
            return False
        ch = steps[idx]["channel"]
        if budget[ch] <= 0:
            skipped.append((c["id"], f"{ch} cap reached"))
            return False
        budget[ch] -= 1
        msg = con.execute("SELECT subject, body FROM messages WHERE contact_id=? AND step=?", (c["id"], idx)).fetchone()
        queue.append({
            "id": c["id"], "kind": kind, "step": idx, "channel": ch, "angle": steps[idx]["angle"],
            "name": f"{c['first_name']} {c['last_name']}", "title": c["title"], "company": c["company"],
            "linkedin_url": c["linkedin_url"], "email": c["email"], "score": score_total(c), "degree": c["degree"],
            "subject": msg["subject"] if msg else None, "body": msg["body"] if msg else None, "sequence": name,
        })
        if kind == "start":
            con.execute("UPDATE contacts SET sequence=?, step=?, stage='in_sequence', seq_started=?, next_touch_due=?, updated_at=? WHERE id=?",
                        (name, idx, day.isoformat(), day.isoformat(), now_iso(), c["id"]))
        return True

    due = con.execute("SELECT * FROM contacts WHERE stage='in_sequence' AND next_touch_due <= ? ORDER BY next_touch_due",
                      (day.isoformat(),)).fetchall()
    for c in due:
        take(c, "follow-up")
    ready = sorted(con.execute("SELECT * FROM contacts WHERE stage='ready'").fetchall(),
                   key=lambda c: (-score_total(c), c["degree"] or 9))
    # Re-running plan the same day must not start a second batch.
    started = con.execute("SELECT COUNT(*) FROM contacts WHERE seq_started=? AND stage NOT IN ('disqualified', 'nurture')",
                          (day.isoformat(),)).fetchone()[0]
    for c in ready:
        if started >= volume:
            break
        started += take(c, "start")
    con.commit()

    out = OUT / f"queue-{day.isoformat()}.md"
    lines = [f"# Outreach queue — {day:%a %d %b %Y}", "",
             f"{len(queue)} touches ({sum(q['kind'] == 'start' for q in queue)} new starts). "
             f"Remaining budget: connects {budget['linkedin_connect']}, DMs {budget['linkedin_dm']}, emails {budget['email']}.",
             "", "After each send: `python3 crm/ob.py log <id> sent`", ""]
    for q in queue:
        lines += [f"## {q['id']} · {q['name']} — {q['title']} @ {q['company']}",
                  f"- {q['kind']} · step {q['step']} · **{q['channel']}** · {q['degree']}° · score {q['score']}/25",
                  f"- LinkedIn: {q['linkedin_url'] or '—'}" + (f" · Email: {q['email']}" if q["channel"] == "email" else ""),
                  f"- Angle: {q['angle']}"]
        if q["subject"]:
            lines.append(f"- Subject: {q['subject']}")
        lines += ["", "```", q["body"] or "(no draft for this step — run li-research to write it)", "```", ""]
    if skipped:
        lines += ["## Skipped", ""] + [f"- {cid}: {why}" for cid, why in skipped]
    out.write_text("\n".join(lines))
    if args.json:
        print(json.dumps({"queue": queue, "skipped": skipped, "budget": budget}, indent=2))
    else:
        print(table(queue, ["id", "kind", "channel", "step", "name", "company", "score"]))
        for cid, why in skipped:
            print(f"  skipped {cid}: {why}")
        print(f"\nqueue with copy: {rel(out)}")


EVENT_STAGE = {
    "replied": "replied", "booked": "meeting_booked", "held": "meeting_held", "proposal": "proposal",
    "won": "won", "lost": "lost", "nurture": "nurture", "optout": "opted_out", "bounce": "completed",
}


def cmd_log(args) -> None:
    cfg = load_config()
    con = connect()
    c = con.execute("SELECT * FROM contacts WHERE id=?", (args.id,)).fetchone()
    if not c:
        die(f"no contact {args.id}")
    name, steps = sequence_for(cfg, c)
    ts = args.at or now_iso()
    day = dt.date.fromisoformat(ts[:10])
    step = c["step"] or 0
    channel = args.channel
    detail = args.note
    if args.event == "sent":
        idx = actionable_step(con, c, steps, step)
        if idx is None:
            die(f"{args.id} has no pending step")
        channel = channel or steps[idx]["channel"]
        nxt = actionable_step(con, c, steps, idx + 1)
        # Connect not yet accepted? still schedule the next step; plan() will skip DMs until accepted.
        nxt = nxt if nxt is not None else (idx + 1 if idx + 1 < len(steps) else None)
        if nxt is None:
            con.execute("UPDATE contacts SET step=?, stage='completed', next_touch_due=NULL, last_touch_at=?, updated_at=? WHERE id=?",
                        (idx + 1, ts, now_iso(), c["id"]))
        else:
            gap = max(steps[nxt]["day"] - steps[idx]["day"], 2)
            con.execute("UPDATE contacts SET sequence=?, step=?, stage='in_sequence', next_touch_due=?, last_touch_at=?, updated_at=? WHERE id=?",
                        (name, nxt, (day + dt.timedelta(days=gap)).isoformat(), ts, now_iso(), c["id"]))
        con.execute("UPDATE messages SET status='sent' WHERE contact_id=? AND step=?", (c["id"], idx))
        step = idx
    elif args.event == "accepted":
        channel = "linkedin_connect"
    elif args.event in EVENT_STAGE:
        if args.event == "replied":
            detail = f"{args.sentiment or 'unknown'}: {args.note or ''}".strip(": ")
            stage = "nurture" if args.sentiment in ("not_now",) else "lost" if args.sentiment == "not_interested" else "replied"
        else:
            stage = EVENT_STAGE[args.event]
        con.execute("UPDATE contacts SET stage=?, next_touch_due=NULL, updated_at=? WHERE id=?", (stage, now_iso(), c["id"]))
    elif args.event == "skip":
        con.execute("UPDATE contacts SET step=?, updated_at=? WHERE id=?", (step + 1, now_iso(), c["id"]))
    con.execute("INSERT INTO touches (contact_id, ts, channel, event, step, variant, sentiment, detail) VALUES (?,?,?,?,?,?,?,?)",
                (c["id"], ts, channel, args.event, step, args.variant or c["icebreaker_choice"], args.sentiment, detail))
    con.commit()
    print(f"{c['id']}: {args.event} logged")


# --------------------------------------------------------------------------- metrics

def rate(a, b) -> str:
    return f"{(100 * a / b):.0f}%" if b else "—"


def compute_metrics(con, since: str | None, by: str | None) -> list[dict]:
    where = "WHERE c.id IN (SELECT contact_id FROM touches WHERE event='sent'" + (" AND date(ts) >= ?" if since else "") + ")"
    params = [since] if since else []
    group = {"degree": "c.degree", "route": "c.route", "campaign": "c.campaign", "variant": "c.icebreaker_choice",
             "sequence": "c.sequence", None: "'all'"}[by]
    q = f"""
    SELECT {group} AS grp,
      COUNT(*) AS contacted,
      SUM(EXISTS(SELECT 1 FROM touches t WHERE t.contact_id=c.id AND t.channel='linkedin_connect' AND t.event='sent')) AS connects,
      SUM(EXISTS(SELECT 1 FROM touches t WHERE t.contact_id=c.id AND t.event='accepted')) AS accepted,
      SUM(EXISTS(SELECT 1 FROM touches t WHERE t.contact_id=c.id AND t.event='replied')) AS replied,
      SUM(EXISTS(SELECT 1 FROM touches t WHERE t.contact_id=c.id AND t.event='replied' AND t.sentiment IN ('interested','question'))) AS positive,
      SUM(EXISTS(SELECT 1 FROM touches t WHERE t.contact_id=c.id AND t.event='booked')) AS booked,
      SUM(EXISTS(SELECT 1 FROM touches t WHERE t.contact_id=c.id AND t.event='held')) AS held,
      SUM(c.stage='won') AS won
    FROM contacts c {where} GROUP BY grp ORDER BY contacted DESC"""
    out = []
    for r in con.execute(q, params).fetchall():
        d = dict(r)
        d["accept_rate"] = rate(d["accepted"], d["connects"])
        d["reply_rate"] = rate(d["replied"], d["contacted"])
        d["positive_rate"] = rate(d["positive"], d["contacted"])
        d["meeting_rate"] = rate(d["booked"], d["contacted"])
        out.append(d)
    return out


def cmd_metrics(args) -> None:
    con = connect()
    rows = compute_metrics(con, args.since, args.by)
    print(table(rows, ["grp", "contacted", "accept_rate", "reply_rate", "positive_rate", "booked", "meeting_rate", "held", "won"]))
    stages = con.execute("SELECT stage, COUNT(*) n FROM contacts GROUP BY stage").fetchall()
    print("\npipeline: " + ", ".join(f"{s['stage']} {s['n']}" for s in sorted(stages, key=lambda s: STAGES.index(s["stage"]) if s["stage"] in STAGES else 99)))
    overdue = con.execute("SELECT COUNT(*) FROM contacts WHERE stage='in_sequence' AND next_touch_due < ?", (today().isoformat(),)).fetchone()[0]
    if overdue:
        print(f"overdue follow-ups: {overdue}  (run: ob plan)")


def cmd_export(args) -> None:
    con = connect()
    rows = [dict(r) | {"score": score_total(r)} for r in con.execute("SELECT * FROM contacts ORDER BY id")]
    if not rows:
        die("no contacts")
    path = Path(args.path)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"exported {len(rows)} contacts to {path}")


# --------------------------------------------------------------------------- page actions

PAGE_EVENTS = {"replied", "booked", "held", "proposal", "won", "lost", "optout", "hold", "note"}


def cmd_apply_actions(args) -> None:
    """Apply updates Dave made on the dashboard page.

    Input: a JSON list of the page's pending `actions` documents, each with `_id`
    (the document id), contact_id, event, sentiment, note and created_at. Prints the
    `_id`s it applied so the caller can mark those documents applied.
    """
    items = json.loads(Path(args.path).read_text())
    applied, skipped = [], []
    for a in sorted(items, key=lambda a: a.get("created_at") or ""):
        cid, ev = a.get("contact_id"), a.get("event")
        if ev not in PAGE_EVENTS or not cid:
            skipped.append((a.get("_id"), f"unknown event {ev!r}"))
            continue
        con = connect()
        if not con.execute("SELECT 1 FROM contacts WHERE id=?", (cid,)).fetchone():
            skipped.append((a.get("_id"), f"unknown contact {cid}"))
            continue
        note = (a.get("note") or "").strip() or None
        argv = ["log", cid, "nurture" if ev == "hold" else ev, "--at", (a.get("created_at") or now_iso())[:19]]
        if ev == "hold":
            note = "held by Dave" + (f": {note}" if note else "")
        if ev == "replied" and a.get("sentiment"):
            argv += ["--sentiment", a["sentiment"]]
        if note:
            argv += ["--note", note]
        main(argv)
        applied.append(a.get("_id"))
    print(json.dumps({"applied": applied, "skipped": skipped}))


# --------------------------------------------------------------------------- backup

TABLES = ("contacts", "messages", "touches")
BACKUP_RE = re.compile(r'<script type="application/json" id="crm-backup">(.*?)</script>', re.S)


def dump_db(con) -> dict:
    return {"version": 1, "exported_at": now_iso(),
            **{t: [dict(r) for r in con.execute(f"SELECT * FROM {t}")] for t in TABLES}}


def cmd_backup(args) -> None:
    con = connect()
    Path(args.path).write_text(json.dumps(dump_db(con), default=str))
    print(f"backup written: {args.path}")


def cmd_restore(args) -> None:
    """Restore from a backup JSON, or from a dashboard HTML page that embeds one."""
    text = Path(args.path).read_text()
    m = BACKUP_RE.search(text)
    data = json.loads(m.group(1).replace("<\\/", "</") if m else text)
    con = connect()
    con.executescript(SCHEMA_PATH.read_text())
    if con.execute("SELECT COUNT(*) FROM contacts").fetchone()[0] and not args.force:
        die("database is not empty; pass --force to replace it")
    for t in reversed(TABLES):
        con.execute(f"DELETE FROM {t}")
    for t in TABLES:
        for row in data.get(t, []):
            cols = ", ".join(row)
            con.execute(f"INSERT INTO {t} ({cols}) VALUES ({', '.join('?' * len(row))})", tuple(row.values()))
    con.commit()
    print(f"restored {', '.join(f'{len(data.get(t, []))} {t}' for t in TABLES)} (exported {data.get('exported_at')})")


# --------------------------------------------------------------------------- dashboard

def cmd_dashboard(args) -> None:
    from dashboard import render  # local module
    con = connect()
    contacts = [dict(r) | {"score": score_total(r)} for r in con.execute("SELECT * FROM contacts")]
    touches = [dict(r) for r in con.execute("SELECT * FROM touches ORDER BY ts DESC")]
    messages = [dict(r) for r in con.execute("SELECT contact_id, step, channel, subject, body, status FROM messages ORDER BY contact_id, step")]
    cfg = load_config()
    day = today()
    queue_md = OUT / f"queue-{day.isoformat()}.md"
    data = {
        "generated": now_iso(),
        "today": day.isoformat(),
        "owner": cfg["owner"],
        "caps": cfg["caps"],
        "sequences": {k: [st["channel"] for st in v["steps"]] for k, v in cfg["sequences"].items()},
        "stages": STAGES,
        "contacts": contacts,
        "touches": touches,
        "messages": messages,
        "metrics": {by or "all": compute_metrics(con, None, by) for by in (None, "degree", "route", "variant")},
        "queue_file": queue_md.name if queue_md.exists() else None,
    }
    out = Path(args.out) if args.out else OUT / "dashboard.html"
    # The artifact page doubles as the durable copy of the CRM: scheduled runs restore from it.
    backup = json.dumps(dump_db(con), default=str) if args.artifact else None
    out.write_text(render(data, artifact=args.artifact, backup=backup))
    print(f"dashboard: {rel(out)}  (open in a browser; contains PII — kept out of git)")


# --------------------------------------------------------------------------- cli

def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="ob", description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="create the database").set_defaults(fn=cmd_init)

    s = sub.add_parser("import-linkedin", help="import LinkedIn Connections.csv (1st-degree)")
    s.add_argument("path"); s.set_defaults(fn=cmd_import_linkedin)

    s = sub.add_parser("audit", help="check exported lists against the ICP without importing")
    s.add_argument("paths", nargs="+"); s.set_defaults(fn=cmd_audit)

    s = sub.add_parser("import-csv", help="import a Sales Navigator / Apollo / Clay CSV")
    s.add_argument("path")
    s.add_argument("--degree", type=int, choices=[1, 2, 3], help="default degree when the file has none")
    s.add_argument("--source", default="csv")
    s.add_argument("--campaign")
    s.set_defaults(fn=cmd_import_csv)

    s = sub.add_parser("qualify", help="rule-based ICP filter + fit/reach scores")
    s.add_argument("--enforce", action="store_true", help="also re-check contacts already being worked and disqualify misfits")
    s.set_defaults(fn=cmd_qualify)

    s = sub.add_parser("list", help="list contacts")
    s.add_argument("--stage", choices=STAGES)
    s.add_argument("--degree", type=int)
    s.add_argument("--route")
    s.add_argument("--search")
    s.add_argument("--limit", type=int, default=50)
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_list)

    s = sub.add_parser("show", help="full record for one contact")
    s.add_argument("id"); s.set_defaults(fn=cmd_show)

    s = sub.add_parser("research-in", help="load Claude's research/copy JSON")
    s.add_argument("path"); s.set_defaults(fn=cmd_research_in)

    s = sub.add_parser("approve", help="approve drafted copy; moves contacts to 'ready'")
    s.add_argument("ids", nargs="+"); s.set_defaults(fn=cmd_approve)

    s = sub.add_parser("plan", help="build today's outreach queue")
    s.add_argument("--volume", type=int, help="new contacts to start today (follow-ups are extra)")
    s.add_argument("--date", help="YYYY-MM-DD (default today)")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_plan)

    s = sub.add_parser("log", help="log an event for a contact")
    s.add_argument("id")
    s.add_argument("event", choices=["sent", "accepted", "replied", "booked", "held", "proposal", "won", "lost",
                                     "nurture", "optout", "bounce", "skip", "note"])
    s.add_argument("--sentiment", choices=["interested", "question", "not_now", "not_interested", "referral"])
    s.add_argument("--channel", choices=["linkedin_connect", "linkedin_dm", "email", "call", "other"])
    s.add_argument("--variant", choices=["A", "B"], help="icebreaker variant used")
    s.add_argument("--note")
    s.add_argument("--at", help="ISO timestamp (default now)")
    s.set_defaults(fn=cmd_log)

    s = sub.add_parser("metrics", help="funnel metrics")
    s.add_argument("--by", choices=["degree", "route", "campaign", "variant", "sequence"])
    s.add_argument("--since", help="YYYY-MM-DD")
    s.set_defaults(fn=cmd_metrics)

    s = sub.add_parser("export", help="export contacts to CSV")
    s.add_argument("path"); s.set_defaults(fn=cmd_export)

    s = sub.add_parser("apply-actions", help="apply updates made on the dashboard page (JSON list of action docs)")
    s.add_argument("path"); s.set_defaults(fn=cmd_apply_actions)

    s = sub.add_parser("backup", help="write the whole CRM to a JSON file")
    s.add_argument("path"); s.set_defaults(fn=cmd_backup)

    s = sub.add_parser("restore", help="restore the CRM from a backup JSON or a published dashboard page")
    s.add_argument("path")
    s.add_argument("--force", action="store_true", help="replace a non-empty database")
    s.set_defaults(fn=cmd_restore)

    s = sub.add_parser("dashboard", help="render data/dashboard.html")
    s.add_argument("--artifact", action="store_true", help="omit the html/head/body wrapper (for publishing as a claude.ai Artifact)")
    s.add_argument("--out", help="output path (default: next to the database)")
    s.set_defaults(fn=cmd_dashboard)

    args = p.parse_args(argv)
    if args.cmd not in ("init", "restore") and not DB_PATH.exists():
        die("no database yet — run: python3 crm/ob.py init")
    args.fn(args)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
