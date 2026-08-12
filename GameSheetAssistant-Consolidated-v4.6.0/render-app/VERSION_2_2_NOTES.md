# Version 2.2 — Earliest Active Minor Release

This update fixes power-play goals that occur while two opponent minor penalties are active.

## Changed

- A power-play goal now releases the earliest active standard minor.
- The goal card identifies the exact penalty and instructs the operator to set its On time to the goal time.
- The related penalty card shows the corrected Back On Ice time.
- Manual review remains only when two eligible earliest minors began at exactly the same time and cannot be distinguished safely.

## Regression coverage

- Single active minor
- Two active minors / 5-on-3
- Simultaneous eligible minors
- Missing shot values

All automated tests pass.
