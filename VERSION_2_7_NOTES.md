# Version 2.7 — Goalie-Order Tiebreaker

- Handles games where zero-shot periods allow multiple goalie orders to fit identical minutes and save totals.
- Uses SportsEngine's preserved goalie-table order as a tiebreaker only after that ordering passes all full-period minutes and shots-faced checks.
- Shows the inference basis on the starting-goalie card.
- Adds a regression test for Cretin-Derham Hall vs. Irondale/St. Anthony: Hannah Fritz starts, Erin Hannon enters for the third period.
