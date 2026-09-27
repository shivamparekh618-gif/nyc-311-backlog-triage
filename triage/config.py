"""Assumptions for the backlog analysis, kept in one place.

The resolution targets are my own placeholders, not official NYC service
levels. They are the first thing to replace after talking to the team.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SQL_DIR = ROOT / "sql"
OUTPUT_DIR = ROOT / "output"

SAMPLE_FILE = DATA_DIR / "sample_311_requests.csv"
REAL_FILE = DATA_DIR / "nyc_311_requests.csv"  # written by fetch.py

# Placeholder resolution targets (days) per complaint type.
TARGET_DAYS = {
    "Street Light Condition": 10,
    "Street Condition": 14,
    "Traffic Signal Condition": 3,
    "Sidewalk Condition": 30,
    "Broken Parking Meter": 7,
    "Highway Condition": 14,
}
DEFAULT_TARGET_DAYS = 14

# How many recent weeks define "current" inflow and closure rates.
RECENT_WEEKS = 4
# Two requests of the same type at the same address within this window are
# treated as one problem reported twice.
DUPLICATE_WINDOW_HOURS = 24

# A backlog is "growing" if it gains more than this share of its size per week.
GROWING_THRESHOLD = 0.05
# A backlog is "chronic" if at least this share of open items is past target.
CHRONIC_OVER_TARGET_SHARE = 0.4
# Queues smaller than this are too noisy to call growing or chronic.
MIN_QUEUE = 20
# Weeks of planning horizon for the "if nothing changes" projection.
PROJECTION_WEEKS = 4
