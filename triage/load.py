"""Clean a 311 extract and load it into SQLite.

Times are stored as fractional days since the Monday on or before the first
request, which keeps the weekly SQL simple.
"""

import csv
import sqlite3
from datetime import datetime, timedelta

from . import config

EARLIEST_VALID = datetime(2000, 1, 1)


def parse(text):
    text = (text or "").strip()
    if not text:
        return None
    return datetime.fromisoformat(text.replace("Z", "").split(".")[0])


def load(conn, path):
    with open(path, newline="") as f:
        raw = list(csv.DictReader(f))
    quality = {"rows_raw": len(raw), "placeholder_closed_date": 0, "closed_before_created": 0,
               "closed_without_date": 0, "close_time_recovered": 0, "close_time_unknown": 0,
               "duplicates": 0}

    records = []
    for r in raw:
        created = parse(r["created_date"])
        closed = parse(r["closed_date"])
        is_closed = r["status"].strip().lower() == "closed" or closed is not None
        valid = closed is not None and closed >= created and closed >= EARLIEST_VALID
        if closed is not None and closed < EARLIEST_VALID:
            quality["placeholder_closed_date"] += 1
        elif closed is not None and closed < created:
            quality["closed_before_created"] += 1
        elif closed is None and is_closed:
            quality["closed_without_date"] += 1
        if is_closed and not valid:
            # Fall back to the last resolution update, if it makes sense.
            fallback = parse(r.get("resolution_action_updated_date"))
            if fallback and fallback >= created:
                closed, valid = fallback, True
                quality["close_time_recovered"] += 1
            else:
                closed = None
                quality["close_time_unknown"] += 1
        records.append({
            "key": r["unique_key"],
            "type": r["complaint_type"].strip(),
            "descriptor": r["descriptor"].strip(),
            "address": " ".join(r["incident_address"].upper().split()),
            "created": created,
            "closed": closed if valid else None,
            "is_closed": is_closed,
        })

    # Same type, same address, within the window of an earlier report that was
    # still open: count it once. 311 does this too, but not consistently.
    records.sort(key=lambda x: (x["type"], x["address"], x["created"]))
    window = timedelta(hours=config.DUPLICATE_WINDOW_HOURS)
    prev = None
    for rec in records:
        rec["duplicate"] = False
        if (prev and rec["address"] and prev["type"] == rec["type"] and prev["address"] == rec["address"]
                and rec["created"] - prev["created"] <= window
                and (prev["closed"] is None or prev["closed"] > rec["created"])):
            rec["duplicate"] = True
            quality["duplicates"] += 1
            continue
        prev = rec

    first = min(r["created"] for r in records)
    anchor = datetime(first.year, first.month, first.day) - timedelta(days=first.weekday())
    last = max(r["created"] for r in records)
    as_of = datetime(last.year, last.month, last.day) + timedelta(days=1)

    def days(dt):
        return None if dt is None else (dt - anchor).total_seconds() / 86400

    conn.executescript((config.SQL_DIR / "01_schema.sql").read_text())
    conn.executemany("INSERT INTO requests VALUES (?,?,?,?,?,?,?,?)", [
        (r["key"], r["type"], r["descriptor"], r["address"], days(r["created"]), days(r["closed"]),
         int(r["is_closed"]), int(r["duplicate"])) for r in records
    ])
    n_weeks = int(days(as_of) // 7)
    conn.executemany("INSERT INTO weeks VALUES (?)", [(w,) for w in range(n_weeks)])
    types = sorted({r["type"] for r in records})
    conn.executemany("INSERT INTO targets VALUES (?,?)",
                     [(t, config.TARGET_DAYS.get(t, config.DEFAULT_TARGET_DAYS)) for t in types])
    quality["rows_used"] = len(records) - quality["duplicates"]
    return {"anchor": anchor, "as_of": as_of, "as_of_d": days(as_of), "n_weeks": n_weeks, "quality": quality}


def connect():
    return sqlite3.connect(":memory:")
