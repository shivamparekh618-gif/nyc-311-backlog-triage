import csv
import tempfile
import unittest
from pathlib import Path

from triage import generate
from triage.analyze import analyze
from triage.load import connect, load

FIELDS = ["unique_key", "created_date", "closed_date", "agency", "complaint_type", "descriptor",
          "incident_address", "borough", "status", "resolution_action_updated_date"]


def write(path, rows):
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(FIELDS)
        writer.writerows(rows)


def row(key, created, closed="", status=None, ctype="Street Light Condition", address="1 MAIN STREET", updated=""):
    status = status or ("Closed" if closed else "Open")
    return [key, created, closed, "DOT", ctype, "Street Light Out", address, "BROOKLYN", status, updated]


class CleaningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp = Path(tempfile.mkdtemp())
        write(tmp / "x.csv", [
            row("1", "2026-04-06T09:00:00.000", "2026-04-08T09:00:00.000"),
            # same problem reported again two hours later: a duplicate
            row("2", "2026-04-06T11:00:00.000", "2026-04-08T09:00:00.000"),
            # placeholder closed date, real close time in the resolution update
            row("3", "2026-04-07T09:00:00.000", "1900-01-01T00:00:00.000", address="2 MAIN STREET",
                updated="2026-04-09T09:00:00.000"),
            # closed before it was created, and no usable fallback
            row("4", "2026-04-08T09:00:00.000", "2026-04-01T09:00:00.000", address="3 MAIN STREET"),
            # still open
            row("5", "2026-04-09T09:00:00.000", address="4 MAIN STREET"),
            # same address as #1 but a week later, after #1 was fixed: a new problem
            row("6", "2026-04-13T09:00:00.000", address="1 MAIN STREET"),
        ])
        cls.conn = connect()
        cls.meta = load(cls.conn, tmp / "x.csv")

    def test_quality_counts(self):
        q = self.meta["quality"]
        self.assertEqual(q["duplicates"], 1)
        self.assertEqual(q["placeholder_closed_date"], 1)
        self.assertEqual(q["closed_before_created"], 1)
        self.assertEqual(q["close_time_recovered"], 1)
        self.assertEqual(q["close_time_unknown"], 1)

    def test_clean_view_excludes_duplicates_and_unknown_close_times(self):
        keys = {k for (k,) in self.conn.execute("SELECT unique_key FROM clean")}
        self.assertEqual(keys, {"1", "3", "5", "6"})

    def test_weeks_start_on_monday(self):
        self.assertEqual(self.meta["anchor"].weekday(), 0)


class SampleStoryTests(unittest.TestCase):
    """The generated sample has three built-in storylines; the analysis should find each one."""

    @classmethod
    def setUpClass(cls):
        tmp = Path(tempfile.mkdtemp())
        rows = generate.generate()
        write(tmp / "s.csv", [[r[f] for f in FIELDS] for r in rows])
        conn = connect()
        cls.queues = {q["type"]: q for q in analyze(conn, load(conn, tmp / "s.csv"))}

    def test_street_lights_growing_after_closure_drop(self):
        q = self.queues["Street Light Condition"]
        self.assertEqual(q["status"], "Growing")
        self.assertEqual(q["closure_drop"]["week"], "Jun 29")

    def test_sidewalks_chronic(self):
        self.assertEqual(self.queues["Sidewalk Condition"]["status"], "Chronic")

    def test_storm_spike_recovered(self):
        q = self.queues["Street Condition"]
        self.assertEqual(q["status"], "Healthy")
        self.assertEqual(q["peak_week"], "May 11")
        self.assertLess(q["open_now"], q["peak_backlog"] / 4)

    def test_small_queues_are_not_flagged(self):
        for ctype in ("Broken Parking Meter", "Highway Condition", "Traffic Signal Condition"):
            self.assertEqual(self.queues[ctype]["status"], "Healthy", ctype)


if __name__ == "__main__":
    unittest.main()
