-- The state of each queue as of the report date.
SELECT c.complaint_type,
       t.target_days,
       SUM(c.closed_d IS NULL)                                                  AS open_now,
       SUM(c.closed_d IS NULL AND :as_of_d - c.created_d > t.target_days)       AS open_over_target,
       SUM(c.created_d >= :recent_start_d) * 1.0 / :recent_weeks                AS opened_per_week,
       SUM(c.closed_d  >= :recent_start_d) * 1.0 / :recent_weeks                AS closed_per_week,
       SUM(c.closed_d >= :prior_start_d AND c.closed_d < :recent_start_d) * 1.0
           / :prior_weeks                                                       AS prior_closed_per_week
FROM clean c
JOIN targets t USING (complaint_type)
GROUP BY c.complaint_type, t.target_days
ORDER BY open_now DESC;
