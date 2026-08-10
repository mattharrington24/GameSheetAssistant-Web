# GameSheet Assistant Web 4.3

## Goalie shift ordering fix

- Web Fill now uses the workflow's inferred starting goalie to resolve an otherwise ambiguous two-goalie order.
- If the workflow identifies one goalie as the starter, that goalie is exported at the start of period 1 and the other goalie is exported at the inferred change time.
- Added a regression test for the St. Cloud case where Kailee Falconer starts and Abby Stevens enters for period 3.

The Chrome helper remains version 0.9.4; it does not need to be replaced for this update.
