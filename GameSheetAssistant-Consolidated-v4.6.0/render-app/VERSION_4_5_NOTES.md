# GameSheet Assistant Web 4.5

## Corrected inferred goalie order

- Web Fill now recalculates an inferred goalie plan before using any previously saved workflow order.
- When period-shot totals allow either order, the goalie with the unique longest verified stint is treated as the starter.
- Added a regression test proving stale reversed workflow data is repaired during export.

For game 29033862, the exported shifts are now:

- Princeton/Big Lake/Becker: Shelby Ulm starts; Mackenzie Dembinski enters at the start of the third period.
- Chisago Lakes: Anna Hanson starts; Breanna Ritter enters at the start of the third period.
