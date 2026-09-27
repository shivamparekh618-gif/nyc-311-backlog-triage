"""Turn weekly queue numbers into a status and a recommendation per complaint type."""

from datetime import timedelta
from statistics import median

from . import config

PRIOR_WEEKS = 8


def run_sql(conn, name, params=None):
    return conn.execute((config.SQL_DIR / name).read_text(), params or {}).fetchall()


def weekly(conn):
    series = {}
    for ctype, week, opened, closed, backlog in run_sql(conn, "02_weekly.sql"):
        series.setdefault(ctype, []).append({"week": week, "opened": opened, "closed": closed, "backlog": backlog})
    return series


def closure_drop(weeks):
    """Find the week where the closure rate fell the most (4 weeks after vs 4 before)."""
    best = None
    for i in range(4, len(weeks) - 3):
        before = sum(w["closed"] for w in weeks[i - 4:i]) / 4
        after = sum(w["closed"] for w in weeks[i:i + 4]) / 4
        if before and (best is None or after / before < best[1]):
            best = (i, after / before, before, after)
    return best


def durations(conn, ctype, as_of_d, recent_start_d):
    closed = [r[0] for r in conn.execute(
        "SELECT closed_d - created_d FROM clean WHERE complaint_type = ? AND closed_d >= ?",
        (ctype, recent_start_d))]
    ages = [as_of_d - r[0] for r in conn.execute(
        "SELECT created_d FROM clean WHERE complaint_type = ? AND closed_d IS NULL", (ctype,))]
    return (median(closed) if closed else None, median(ages) if ages else None)


def analyze(conn, meta):
    n_weeks = meta["n_weeks"]
    recent_start_d = (n_weeks - config.RECENT_WEEKS) * 7
    prior_start_d = recent_start_d - PRIOR_WEEKS * 7
    series = weekly(conn)
    rows = run_sql(conn, "03_current.sql", {
        "as_of_d": meta["as_of_d"], "recent_start_d": recent_start_d, "recent_weeks": config.RECENT_WEEKS,
        "prior_start_d": prior_start_d, "prior_weeks": PRIOR_WEEKS,
    })

    def week_label(i):
        return (meta["anchor"] + timedelta(weeks=i)).strftime("%b %d")

    queues = []
    for ctype, target, open_now, over, opened_wk, closed_wk, prior_closed_wk in rows:
        weeks = series[ctype]
        net = opened_wk - closed_wk
        backlog_then = weeks[-1 - config.RECENT_WEEKS]["backlog"]
        grew = (open_now - backlog_then) / backlog_then if backlog_then else 0
        med_close, med_age = durations(conn, ctype, meta["as_of_d"], recent_start_d)
        peak = max(weeks, key=lambda w: w["backlog"])
        over_share = over / open_now if open_now else 0

        big_enough = open_now >= config.MIN_QUEUE
        if big_enough and net > 0 and grew >= config.GROWING_THRESHOLD * config.RECENT_WEEKS:
            status = "Growing"
        elif big_enough and over_share >= config.CHRONIC_OVER_TARGET_SHARE:
            status = "Chronic"
        else:
            status = "Healthy"

        q = {
            "type": ctype, "status": status, "target_days": target,
            "open_now": open_now, "over_target": over, "over_share": over_share,
            "opened_per_week": opened_wk, "closed_per_week": closed_wk,
            "prior_closed_per_week": prior_closed_wk, "net_per_week": net,
            "backlog_4w_ago": backlog_then, "growth_4w": grew,
            "median_days_to_close": med_close, "median_open_age": med_age,
            "projected_open": max(0, round(open_now + net * config.PROJECTION_WEEKS)),
            "weeks_to_clear": open_now / -net if net < 0 else None,
            "peak_backlog": peak["backlog"], "peak_week": week_label(peak["week"]),
            "weeks": weeks,
        }
        drop = closure_drop(weeks) if status == "Growing" else None
        if drop and drop[1] < 0.8:
            q["closure_drop"] = {"week": week_label(drop[0]), "before": drop[2], "after": drop[3], "ratio": drop[1]}
        queues.append(q)

    order = {"Growing": 0, "Chronic": 1, "Healthy": 2}
    queues.sort(key=lambda q: (order[q["status"]], -q["over_target"]))
    return queues
