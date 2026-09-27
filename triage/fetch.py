"""Download real NYC 311 service requests from NYC Open Data.

    python -m triage.fetch --agency DOT --borough BROOKLYN --start 2025-05-01 --end 2025-09-01

Dataset: "311 Service Requests from 2010 to Present" (id erm2-nwe9),
https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2010-to-Present/erm2-nwe9
Queried through the public Socrata (SODA) API; no key is needed for small pulls.
"""

import argparse
import csv
import io
import sys
import urllib.parse
import urllib.request

from . import config

ENDPOINT = "https://data.cityofnewyork.us/resource/erm2-nwe9.csv"
COLUMNS = [
    "unique_key", "created_date", "closed_date", "agency", "complaint_type", "descriptor",
    "incident_address", "borough", "status", "resolution_action_updated_date",
]
PAGE = 50000


def fetch(agency, borough, start, end, out_path):
    where = (f"agency = '{agency}' AND borough = '{borough}' "
             f"AND created_date >= '{start}T00:00:00' AND created_date < '{end}T00:00:00'")
    rows, offset = [], 0
    while True:
        params = urllib.parse.urlencode({
            "$select": ",".join(COLUMNS),
            "$where": where,
            "$order": "unique_key",
            "$limit": PAGE,
            "$offset": offset,
        })
        with urllib.request.urlopen(f"{ENDPOINT}?{params}", timeout=120) as resp:
            page = list(csv.DictReader(io.TextIOWrapper(resp, encoding="utf-8")))
        rows.extend(page)
        print(f"  fetched {len(rows)} rows", file=sys.stderr)
        if len(page) < PAGE:
            break
        offset += PAGE

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--agency", default="DOT")
    parser.add_argument("--borough", default="BROOKLYN")
    parser.add_argument("--start", required=True, help="YYYY-MM-DD, inclusive")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD, exclusive")
    args = parser.parse_args()
    n = fetch(args.agency, args.borough.upper(), args.start, args.end, config.REAL_FILE)
    print(f"wrote {n} rows to {config.REAL_FILE}")


if __name__ == "__main__":
    main()
