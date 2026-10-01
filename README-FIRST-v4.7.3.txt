GameSheet Assistant Web v4.7.3 - Missing Event Time Fix

FIXES IN THIS VERSION
- Fixes the active_periods parser error from v4.7.2.
- Imports a goal or penalty even when its time is blank or marked with ?.
- Assigns a stable randomized time between 2:00 and 23:00 remaining.
- The same scoresheet event receives the same generated time on every import.
- Adds the generated time to the Web Fill warnings for review.
- Correctly reads dates and game numbers that Word splits across text runs.
- Retains the goalie-order, High Sticking, and Cross-Checking fixes.

GAME 25 TEST
- Missing first-period Maroon goal: assigned 6:26 remaining
- Final score validation: Maroon 2, Forest 1
- Starting goalies: Maroon #30 and Forest #30
- Date: 8/30/26
- Game number: 25

UPDATE
Replace ppl_parser.py and static/app.js in the existing repository, then commit
and push to main. Render should deploy automatically. No Chrome helper update
is required if v0.9.15 is installed.
