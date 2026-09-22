# GameSheet Assistant Web v4.7.0

## Premier Prep League Word Import

- Adds a PPL Word `.docx` upload beside the existing SportsEngine importer.
- Reads the game date, location, game number, teams, rosters, goals, assists,
  strengths, penalties, goalie saves, goals against, and minutes played.
- Supports the PPL format of two 25-minute periods without changing the
  Minnesota high-school 17-minute workflow.
- Converts PPL clock values directly from time remaining and preserves the
  penalty `Out` time as the GameSheet back-on-ice time.
- Derives team shots by adding goals to the opposing goalie saves for each
  period.
- Infers goalie starters and period-boundary changes from the 25-minute stints
  and period save totals.
- Produces the existing `gamesheet-assistant-web-fill` payload used by the
  Chrome helper.

## Deployment

Install the updated dependencies from `requirements.txt`, then deploy the full
project to Render as usual. The existing `APP_PASSWORD` and other environment
settings do not change.

The Word importer currently expects the standard 55-row Premier Prep League
scoresheet layout represented by the supplied 2026 Game 3 and Game 4 examples.
