# Version 3.5

- Corrects a legacy SportsEngine issue that reports a full-game overtime goalie as playing only 51:00.
- Uses 59:00 for an eight-minute overtime tie.
- For an overtime winner, uses 51:00 plus the elapsed time of the winning overtime goal.
- Does not add a duplicate OT goalie shift, because GameSheet’s web editor treats that as an invalid second shift and may show 0:00 played.
- Warns that GameSheet may continue to display 51:00 for a scoreless overtime tie even though the assistant correctly calculates 59:00.
- Leaves multi-goalie minute splits unchanged when the overtime allocation is ambiguous.
