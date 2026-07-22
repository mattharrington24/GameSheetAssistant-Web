# Version 2.8 — Missing Period-Shot Resolution

- Resolves one missing period-shot value when the other periods and game total determine it exactly.
- Converts the Cretin-Derham Hall vs. Irondale/St. Anthony line from `3, 3, missing, total 6` to `3, 3, 0, total 6`.
- Prevents `NaN` from appearing for that resolved period in the Summary.
- Allows goalie inference to use the resolved zero-shot period.
- Adds regression tests confirming Hannah Fritz starts and Erin Hannon enters for the third period.
