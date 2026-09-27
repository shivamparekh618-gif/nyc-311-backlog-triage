"""One-page HTML briefing for a team lead. No dependencies."""

from datetime import timedelta
from html import escape

from . import config

CSS = """
:root {
  color-scheme: light;
  --bg: #f6f6f4; --card: #fcfcfb; --ink: #0b0b0b; --ink-2: #52514e; --ink-3: #8a8983;
  --rule: #e4e3de; --bar: #2a78d6; --bar-hi: #1c5aa6; --mark: #0b0b0b;
  --grow: #b42318; --grow-bg: #fdecea; --chronic: #8a5a00; --chronic-bg: #fff4d6;
  --ok: #1d6b3a; --ok-bg: #e6f4ea; --note-bg: #eef4fc;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --bg: #111110; --card: #1a1a19; --ink: #ffffff; --ink-2: #c3c2b7; --ink-3: #8f8e86;
    --rule: #2c2c2a; --bar: #3987e5; --bar-hi: #7fb2f0; --mark: #ffffff;
    --grow: #ff8a80; --grow-bg: #3a1714; --chronic: #f2c14e; --chronic-bg: #33280c;
    --ok: #7fd49b; --ok-bg: #12301c; --note-bg: #16233a;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink);
       font: 14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
main { max-width: 1120px; margin: 0 auto; padding: 28px 16px 48px; }
header { display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; flex-wrap: wrap; }
h1 { font-size: 22px; margin: 0 0 4px; }
h2 { font-size: 15px; margin: 32px 0 10px; text-transform: uppercase; letter-spacing: .04em; color: var(--ink-2); }
.sub { color: var(--ink-2); margin: 0; }
.badge { font-size: 12px; padding: 4px 10px; border-radius: 999px; background: var(--note-bg); color: var(--ink-2); }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 12px; }
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-top: 20px; }
.card { background: var(--card); border: 1px solid var(--rule); border-radius: 10px; padding: 14px 16px; }
.kpi .v { font-size: 28px; font-weight: 650; font-variant-numeric: tabular-nums; }
.kpi .l { color: var(--ink-2); font-size: 13px; }
.card h3 { margin: 0 0 6px; font-size: 15px; }
.card p { margin: 6px 0; color: var(--ink-2); }
.card .do { color: var(--ink); font-weight: 600; }
.chip { font-size: 12px; font-weight: 600; padding: 2px 8px; border-radius: 999px; white-space: nowrap; }
.chip.Growing { color: var(--grow); background: var(--grow-bg); }
.chip.Chronic { color: var(--chronic); background: var(--chronic-bg); }
.chip.Healthy { color: var(--ok); background: var(--ok-bg); }
.mini { display: grid; grid-template-columns: repeat(auto-fit, minmax(330px, 1fr)); gap: 12px; }
.mini h3 { display: flex; justify-content: space-between; align-items: center; font-size: 14px; }
.mini .cap { color: var(--ink-2); font-size: 12px; margin: 0 0 6px; }
svg text { fill: var(--ink-2); font-size: 11px; }
svg .bar { fill: var(--bar); }
svg .bar:hover { fill: var(--bar-hi); }
svg .axis { stroke: var(--rule); }
svg .event { stroke: var(--mark); stroke-dasharray: 3 3; }
svg .event-label { fill: var(--ink); font-weight: 600; }
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; background: var(--card); border: 1px solid var(--rule); border-radius: 10px; overflow: hidden; }
th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--rule); white-space: nowrap; }
th { font-size: 12px; color: var(--ink-2); font-weight: 600; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
tr:last-child td { border-bottom: 0; }
dl { display: grid; grid-template-columns: 1fr auto; gap: 4px 12px; margin: 0; }
dd { margin: 0; text-align: right; font-variant-numeric: tabular-nums; }
.muted { color: var(--ink-2); }
footer { margin-top: 32px; color: var(--ink-3); font-size: 12px; }
"""


def n(x, digits=0):
    return f"{x:,.{digits}f}"


def backlog_chart(q, anchor, event=None):
    weeks = q["weeks"]
    top = max(w["backlog"] for w in weeks) or 1
    w, h, left, bottom, pad = 340, 110, 30, 18, 14
    plot_w, plot_h = w - left - 6, h - bottom - pad
    step = plot_w / len(weeks)
    bw = max(step - 2, 1)
    out = [f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="Weekly open backlog, {escape(q["type"])}">']
    for frac in (0, 1):
        y = pad + plot_h * (1 - frac)
        out.append(f'<line class="axis" x1="{left}" x2="{w - 6}" y1="{y:.1f}" y2="{y:.1f}"/>')
        out.append(f'<text x="{left - 6}" y="{y + 4:.1f}" text-anchor="end">{n(top * frac)}</text>')
    for i, wk in enumerate(weeks):
        bh = plot_h * wk["backlog"] / top
        x = left + i * step + 1
        y = pad + plot_h - bh
        start = anchor + timedelta(weeks=wk["week"])
        tip = (f"Week of {start:%b %d}: {wk['backlog']} open at week end, "
               f"{wk['opened']} opened, {wk['closed']} closed")
        out.append(f'<g><title>{tip}</title><rect class="bar" x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" '
                   f'height="{bh:.1f}" rx="{min(2, bw / 2):.1f}"/></g>')
        if i % 5 == 2:
            out.append(f'<text x="{x + bw / 2:.1f}" y="{h - 5}" text-anchor="middle">{start:%b %d}</text>')
    if event:
        i, label = event
        x = left + i * step
        out.append(f'<line class="event" x1="{x:.1f}" x2="{x:.1f}" y1="{pad - 4}" y2="{pad + plot_h}"/>')
        out.append(f'<text class="event-label" x="{x + 4:.1f}" y="{pad + 2}">{escape(label)}</text>')
    out.append("</svg>")
    return "".join(out)


def focus_cards(queues):
    cards = []
    for q in queues:
        if q["status"] == "Growing":
            drop = q.get("closure_drop")
            cause = ""
            if drop:
                cause = (f"<p>Reports held at about <b>{n(q['opened_per_week'])}/week</b>, but closures fell from "
                         f"{n(drop['before'])} to <b>{n(drop['after'])}/week</b> starting the week of {drop['week']}. "
                         f"The demand didn't change. Capacity did.</p>")
            back_to = q["backlog_4w_ago"]
            need = q["opened_per_week"] + (q["open_now"] - back_to) / 8
            cards.append(f"""<div class="card"><h3>Focus: {escape(q['type'])} <span class="chip Growing">Growing</span></h3>
<p>The backlog went from {n(back_to)} to <b>{n(q['open_now'])}</b> open in 4 weeks, and {q['over_share']:.0%} of it is
past the {n(q['target_days'])}-day target.</p>{cause}
<p>If nothing changes: about <b>{n(q['projected_open'])} open</b> in {config.PROJECTION_WEEKS} weeks.
Getting back to {n(back_to)} within 8 weeks takes about <b>{n(need)} closures/week</b>.</p>
<p class="do">Next step: find out what changed the week of {drop['week'] if drop else 'the slowdown'} before moving anyone.</p></div>""")
        elif q["status"] == "Chronic":
            cover = q["closed_per_week"] / q["opened_per_week"] if q["opened_per_week"] else 0
            opened_all = sum(w["opened"] for w in q["weeks"])
            cover_all = sum(w["closed"] for w in q["weeks"]) / opened_all if opened_all else 0
            cards.append(f"""<div class="card"><h3>Plan for: {escape(q['type'])} <span class="chip Chronic">Chronic</span></h3>
<p><b>{q['over_share']:.0%}</b> of {n(q['open_now'])} open requests are past the {n(q['target_days'])}-day target.
Closures cover only <b>{cover:.0%}</b> of new reports lately, and {cover_all:.0%} across the whole period.</p>
<p>No single event caused this, so a short-term crew move won't fix it. It needs a capacity or policy decision:
more sustained capacity, or triage by severity with an honest target.</p>
<p class="do">Next step: bring this to the monthly planning review, not the weekly stand-up.</p></div>""")
    spikes = [q for q in queues if q["status"] == "Healthy" and q["peak_backlog"] >= 4 * max(q["open_now"], 1)
              and q["peak_backlog"] >= 50]
    for q in spikes[:1]:
        cards.append(f"""<div class="card"><h3>No action: {escape(q['type'])} <span class="chip Healthy">Healthy</span></h3>
<p>In the week of {q['peak_week']} this was the biggest backlog on the board: <b>{n(q['peak_backlog'])} open</b>
after reports spiked. Crews brought it back down to <b>{n(q['open_now'])}</b> with no intervention, and it now closes
more than it receives.</p>
<p class="do">Worth noting: the process already absorbs short spikes. The team shouldn't react to one bad week.</p></div>""")
    return "".join(cards)


def queue_table(queues):
    rows = []
    for q in queues:
        mc = "–" if q["median_days_to_close"] is None else n(q["median_days_to_close"], 1)
        rows.append(f"""<tr><td>{escape(q['type'])}</td><td><span class="chip {q['status']}">{q['status']}</span></td>
<td class="num">{n(q['open_now'])}</td><td class="num">{n(q['over_target'])} ({q['over_share']:.0%})</td>
<td class="num">{n(q['target_days'])}</td><td class="num">{mc}</td>
<td class="num">{n(q['opened_per_week'], 1)}</td><td class="num">{n(q['closed_per_week'], 1)}</td>
<td class="num">{q['net_per_week']:+.1f}</td><td class="num">{n(q['projected_open'])}</td></tr>""")
    return f"""<div class="table-wrap"><table><thead><tr><th>Complaint type</th><th>Status</th>
<th class="num">Open</th><th class="num">Past target</th><th class="num">Target (days)</th>
<th class="num">Median days to close</th><th class="num">Opened / wk</th><th class="num">Closed / wk</th>
<th class="num">Net / wk</th><th class="num">Open in {config.PROJECTION_WEEKS} wks</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>"""


def write_report(queues, meta, source_label, synthetic):
    anchor = meta["anchor"]
    total_open = sum(q["open_now"] for q in queues)
    over = sum(q["over_target"] for q in queues)
    first = anchor
    last = meta["as_of"] - timedelta(days=1)
    growing = [q for q in queues if q["status"] == "Growing"]
    growing_over = sum(q["over_target"] for q in growing)

    minis = []
    for q in queues:
        event = None
        if q.get("closure_drop"):
            i = next(k for k, w in enumerate(q["weeks"])
                     if (anchor + timedelta(weeks=w["week"])).strftime("%b %d") == q["closure_drop"]["week"])
            event = (i, "closures drop")
        elif q["status"] == "Healthy" and q["peak_backlog"] >= 50 and q["peak_backlog"] >= 4 * max(q["open_now"], 1):
            i = next(k for k, w in enumerate(q["weeks"]) if w["backlog"] == q["peak_backlog"])
            event = (i, "spike")
        minis.append(f"""<div class="card"><h3>{escape(q['type'])} <span class="chip {q['status']}">{q['status']}</span></h3>
<p class="cap">Open at the end of each week · {n(q['open_now'])} now</p>{backlog_chart(q, anchor, event)}</div>""")

    ql = meta["quality"]
    dq = f"""<div class="card"><dl>
<dt>Rows in extract</dt><dd>{n(ql['rows_raw'])}</dd>
<dt>Duplicate reports (same type + address within {config.DUPLICATE_WINDOW_HOURS}h)</dt><dd>{n(ql['duplicates'])}</dd>
<dt>Placeholder closed date (1900-01-01)</dt><dd>{n(ql['placeholder_closed_date'])}</dd>
<dt>Closed date before created date</dt><dd>{n(ql['closed_before_created'])}</dd>
<dt>Marked closed with no closed date</dt><dd>{n(ql['closed_without_date'])}</dd>
<dt>…close time recovered from last resolution update</dt><dd>{n(ql['close_time_recovered'])}</dd>
<dt>…close time unknown, left out</dt><dd>{n(ql['close_time_unknown'])}</dd>
<dt>Requests analysed</dt><dd>{n(ql['rows_used'])}</dd></dl></div>"""

    badge = "Portfolio prototype &middot; synthetic sample" if synthetic else "Portfolio prototype &middot; NYC Open Data"
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>311 Backlog Briefing</title><style>{CSS}</style></head>
<body><main>
<header><div><h1>311 backlog briefing</h1>
<p class="sub">{escape(source_label)} &middot; requests created {first:%b %d} – {last:%b %d, %Y} &middot; as of {meta['as_of']:%a %b %d}</p></div>
<span class="badge">{badge}</span></header>
<div class="kpis">
<div class="card kpi"><div class="v">{n(total_open)}</div><div class="l">open requests</div></div>
<div class="card kpi"><div class="v">{n(over)}</div><div class="l">past their resolution target ({over / total_open:.0%})</div></div>
<div class="card kpi"><div class="v">{len(growing)}</div><div class="l">complaint type{'s' if len(growing) != 1 else ''} with a growing backlog</div></div>
<div class="card kpi"><div class="v">{growing_over / over:.0%}</div><div class="l">of past-target requests are in that queue</div></div>
</div>
<h2>Where to focus</h2>
<div class="grid">{focus_cards(queues)}</div>
<h2>Backlog by complaint type</h2>
<div class="mini">{''.join(minis)}</div>
<h2>All queues</h2>
{queue_table(queues)}
<p class="muted">Rates use the last {config.RECENT_WEEKS} full weeks. Targets are placeholder assumptions, not official NYC service levels.</p>
<h2>Data quality</h2>
<div class="grid">{dq}</div>
<footer>Generated by <span>python run.py</span>.{' Data is synthetic, in the NYC 311 schema.' if synthetic else ''}</footer>
</main></body></html>
"""
    path = config.OUTPUT_DIR / "backlog_briefing.html"
    path.write_text(html)
    return path
