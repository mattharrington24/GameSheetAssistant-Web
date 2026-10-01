# GameSheet Assistant Web v4.7.3

## Missing Event Time and Parser Fix

- Fixes the `active_periods is not defined` regression introduced in v4.7.2.
- Imports goals and penalties whose time is blank or marked with `?`.
- Assigns a deterministic randomized time between 2:00 and 23:00 remaining in
  a standard PPL period.
- The same event receives the same generated time every time the document is
  imported.
- Adds the generated time to the Web Fill warnings for review.
- Correctly joins dates and game numbers when Word splits them across text
  runs, such as `8/30` + `/26` and `2` + `5`.
- Retains the goalie-period inference, High Sticking, and Cross-Checking fixes.
