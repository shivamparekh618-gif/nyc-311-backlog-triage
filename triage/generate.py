"""Generate a synthetic 311 extract in the same columns as the NYC Open Data API.

It stands in for one agency (DOT) in one borough over 21 weeks. Each complaint
type is a queue: requests arrive every day, crews close some every weekday.
Three storylines are built in, because they're the three situations a team
lead has to tell apart:

* Street Light Condition: closures drop sharply in week 13 and the backlog starts growing.
* Street Condition: a storm triples pothole reports for a week, then crews catch up.
* Sidewalk Condition: arrivals slightly outpace closures all along, so a large,
  old backlog builds slowly.

Plus the usual data problems: duplicate reports, placeholder and impossible
closed dates, and "Closed" records with no closed date.
"""

import csv
import random
from datetime import datetime, timedelta

from . import config

SEED = 7
START = datetime(2026, 4, 6)  # Monday
WEEKS = 21

# type: (arrivals per weekday, closures per weekday). Weekend arrivals run at
# 70% and crews only close requests on weekdays.
QUEUES = {
    "Street Condition": (26, 36),
    "Street Light Condition": (12, 16),
    "Traffic Signal Condition": (7, 10),
    "Sidewalk Condition": (5.5, 5.0),
    "Broken Parking Meter": (4, 5.6),
    "Highway Condition": (3, 4.4),
}
DESCRIPTORS = {
    "Street Condition": ["Pothole", "Cave-in", "Failed Street Repair", "Rough, Pitted or Cracked Roads"],
    "Street Light Condition": ["Street Light Out", "Street Light Cycling", "Lamppost Damaged"],
    "Traffic Signal Condition": ["Controller", "Ped Lamp", "LED Lense"],
    "Sidewalk Condition": ["Broken Sidewalk", "Sidewalk Collapsed"],
    "Broken Parking Meter": ["Out of Order", "No Receipt"],
    "Highway Condition": ["Pothole - Highway", "Guard Rail - Street"],
}
STREETS = ["ATLANTIC AVENUE", "FLATBUSH AVENUE", "OCEAN PARKWAY", "BEDFORD AVENUE", "FULTON STREET",
           "EASTERN PARKWAY", "KINGS HIGHWAY", "NOSTRAND AVENUE", "4 AVENUE", "CHURCH AVENUE",
           "MYRTLE AVENUE", "UTICA AVENUE", "CORTELYOU ROAD", "BAY RIDGE PARKWAY", "COURT STREET"]
OPEN_STATUSES = ["Open", "In Progress", "Assigned", "Pending"]

LIGHT_CUT_WEEK = 12      # 0-based: closures drop from week 13
LIGHT_CUT_FACTOR = 0.6
STORM_WEEK = 5
STORM_FACTOR = 3.0


def _ts(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000")


def _poisson(rng, lam):
    # Knuth's method is fine at these rates.
    if lam <= 0:
        return 0
    threshold, k, p = pow(2.718281828459045, -lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= threshold:
            return k
        k += 1


def generate(seed=SEED):
    rng = random.Random(seed)
    rows = []
    key = 0
    end = START + timedelta(weeks=WEEKS)

    for ctype, (arrive, close) in QUEUES.items():
        queue = []  # open (row, created) pairs, oldest first
        day = START
        while day < end:
            week = (day - START).days // 7
            weekend = day.weekday() >= 5
            lam = arrive * (0.7 if weekend else 1.0)
            if ctype == "Street Condition" and week == STORM_WEEK:
                lam *= STORM_FACTOR
            for _ in range(_poisson(rng, lam)):
                key += 1
                created = day + timedelta(seconds=rng.randint(6 * 3600, 23 * 3600))
                row = {
                    "unique_key": str(key),
                    "created_date": _ts(created),
                    "closed_date": "",
                    "agency": "DOT",
                    "complaint_type": ctype,
                    "descriptor": rng.choice(DESCRIPTORS[ctype]),
                    "incident_address": f"{rng.randint(1, 2400)} {rng.choice(STREETS)}",
                    "borough": "BROOKLYN",
                    "status": rng.choice(OPEN_STATUSES),
                    "resolution_action_updated_date": "",
                    "_created": created,
                    "_dupe_of": None,
                }
                rows.append(row)
                queue.append(row)
                # Neighbours often report the same problem again the same day.
                if rng.random() < 0.08:
                    key += 1
                    again = dict(row, unique_key=str(key), _dupe_of=row)
                    again["_created"] = created + timedelta(minutes=rng.randint(10, 600))
                    again["created_date"] = _ts(again["_created"])
                    rows.append(again)

            if not weekend:
                capacity = close
                if ctype == "Street Light Condition" and week >= LIGHT_CUT_WEEK:
                    capacity *= LIGHT_CUT_FACTOR
                n_close = min(len(queue), _poisson(rng, capacity))
                for _ in range(n_close):
                    # Mostly oldest-first, but crews also batch nearby jobs. Sidewalk
                    # repairs are scheduled by severity, so age barely matters.
                    oldest_first = 0.1 if ctype == "Sidewalk Condition" else 0.6
                    idx = 0 if rng.random() < oldest_first else rng.randrange(len(queue))
                    row = queue.pop(idx)
                    closed = day + timedelta(seconds=rng.randint(8 * 3600, 17 * 3600))
                    if closed <= row["_created"]:
                        closed = row["_created"] + timedelta(hours=rng.randint(1, 6))
                    row["_closed"] = closed
            day += timedelta(days=1)

    for row in rows:
        source = row["_dupe_of"] or row
        closed = source.get("_closed")
        if row["_dupe_of"] and closed and closed <= row["_created"]:
            closed = row["_created"] + timedelta(hours=1)
        if closed:
            row["status"] = "Closed"
            row["closed_date"] = _ts(closed)
            row["resolution_action_updated_date"] = _ts(closed)
            roll = rng.random()
            if roll < 0.005:
                row["closed_date"] = "1900-01-01T00:00:00.000"
            elif roll < 0.008:
                row["closed_date"] = _ts(row["_created"] - timedelta(days=rng.randint(1, 30)))
            elif roll < 0.018:
                row["closed_date"] = ""
        elif row["_dupe_of"]:
            row["status"] = row["_dupe_of"]["status"]

    # Keys are issued in creation order, like the real dataset.
    rows.sort(key=lambda r: r["_created"])
    key = 64000000
    for row in rows:
        key += rng.randint(1, 40)
        row["unique_key"] = str(key)
        for k in ("_created", "_closed", "_dupe_of"):
            row.pop(k, None)
    return rows


def main():
    rows = generate()
    config.SAMPLE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(config.SAMPLE_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {config.SAMPLE_FILE}")


if __name__ == "__main__":
    main()
