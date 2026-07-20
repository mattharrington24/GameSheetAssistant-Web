# Version 2.5 — Penalty Cards and Goalie-Stint Inference

- Restructures penalty cards into this entry order: Off Ice Time, Duration, Penalty Type, Player, On Ice Time.
- Cleans combined SportsEngine penalty labels into separate type and duration fields.
- Infers multi-goalie starters and full-period changes when one ordering exactly matches minutes played, period shots against, and goals allowed.
- Shows the inferred starter and planned goalie changes on the starting-goalie card.
- Adds a highlighted goalie-change workflow card before the applicable period.
- Keeps manual confirmation when the available totals do not produce one exact, defensible goalie sequence.
