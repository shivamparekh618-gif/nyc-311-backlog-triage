"""Build the backlog briefing from a 311 extract.

    python run.py                 # real data if data/nyc_311_requests.csv exists, else the sample
    python run.py --sample        # force the bundled synthetic sample
    python run.py --input my.csv  # any extract with the NYC 311 columns
"""

import argparse
import csv
from datetime import timedelta
from pathlib import Path

from triage import config
from triage.analyze import analyze
from triage.load import connect, load
from triage.report import write_report


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sample", action="store_true", help="use the synthetic sample")
    parser.add_argument("--input", type=Path, help="path to a 311 CSV extract")
    args = parser.parse_args()

    if args.input:
        path, synthetic = args.input, False
    elif not args.sample and config.REAL_FILE.exists():
        path, synthetic = config.REAL_FILE, False
    else:
        if not config.SAMPLE_FILE.exists():
            from triage import generate
            generate.main()
        path, synthetic = config.SAMPLE_FILE, True

    conn = connect()
    meta = load(conn, path)
    queues = analyze(conn, meta)
    label = "Synthetic DOT requests, Brooklyn" if synthetic else f"NYC 311 extract ({path.name})"

    config.OUTPUT_DIR.mkdir(exist_ok=True)
    fields = ["type", "status", "open_now", "over_target", "over_share", "target_days", "median_days_to_close",
              "median_open_age", "opened_per_week", "closed_per_week", "net_per_week", "backlog_4w_ago",
              "projected_open", "weeks_to_clear"]
    with open(config.OUTPUT_DIR / "queue_summary.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for q in queues:
            writer.writerow({k: round(v, 2) if isinstance(v, float) else v for k, v in q.items()})
    with open(config.OUTPUT_DIR / "weekly_backlog.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["complaint_type", "week_start", "opened", "closed", "backlog_end_of_week"])
        for q in queues:
            for w in q["weeks"]:
                start = meta["anchor"] + timedelta(weeks=w["week"])
                writer.writerow([q["type"], start.date().isoformat(), w["opened"], w["closed"], w["backlog"]])

    path = write_report(queues, meta, label, synthetic)
    print(f"{meta['quality']['rows_used']:,} requests analysed from {label}")
    for q in queues:
        print(f"  {q['status']:<8} {q['type']:<26} {q['open_now']:>5} open, {q['net_per_week']:+6.1f}/week")
    print(f"Briefing: {path}")


if __name__ == "__main__":
    main()
