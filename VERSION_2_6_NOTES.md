# Version 2.6 — Stronger Starting-Goalie Inference

- Derives each goalie's shots faced from saves plus goals allowed.
- Matches those derived shots to the opponent's shots during exact full-period goalie stints.
- No longer rejects a valid goalie ordering solely because SportsEngine's reported shots-against field is inconsistent.
- Requires one unique ordering before identifying a starter or scheduling goalie-change reminders.
- Explains the inference directly on the starting-goalie card with the matching minutes, periods, and shot totals.
- Adds a regression test for the Hannah Fritz 34-minute, six-save example.
