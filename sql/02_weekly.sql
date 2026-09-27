-- Per complaint type and week: requests opened, requests closed, and the
-- backlog (still open) at the end of the week.
SELECT c.complaint_type,
       w.week,
       SUM(c.created_d >= w.week * 7 AND c.created_d < (w.week + 1) * 7)                     AS opened,
       SUM(c.closed_d  >= w.week * 7 AND c.closed_d  < (w.week + 1) * 7)                     AS closed,
       SUM(c.created_d < (w.week + 1) * 7 AND (c.closed_d IS NULL OR c.closed_d >= (w.week + 1) * 7)) AS backlog
FROM clean c
CROSS JOIN weeks w
GROUP BY c.complaint_type, w.week
ORDER BY c.complaint_type, w.week;
