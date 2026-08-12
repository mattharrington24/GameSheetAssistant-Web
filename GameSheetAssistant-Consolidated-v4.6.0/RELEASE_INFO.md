# Release information

## Versions

- GameSheet Assistant web app: 4.6.0 consolidated release
- GameSheet Web Fill Chrome helper: 0.9.5

## Consolidated behavior

- The backend goalie plan is the authoritative source for Web Fill data.
- Verified multi-goalie plans preserve the inferred starter and replacement order.
- Full-period and partial-period goalie changes are supported.
- When period-shot totals tie, the longest verified goalie stint is preferred over unreliable display order.
- Empty-net goals generate goalie-off and goalie-restoration shifts.
- Team aliases and normalized program names are included, including Hudson/Hudson Raiders.
- Missing roster-dependent selections use safe fallback-player handling.
- Major and misconduct durations retain their full 5- and 10-minute timing.
- Overtime and known GameSheet web-editor limitations remain identified in warnings for manual review.

This release includes all application source, tests, deployment files, documentation, and the matched unpacked Chrome extension.
