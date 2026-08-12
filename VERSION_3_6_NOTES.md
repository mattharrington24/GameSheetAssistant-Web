# Version 3.6

- Corrects inferred multi-goalie ordering when SportsEngine uses ordinal period labels such as `1st` and the shots table uses numeric labels such as `1`.
- Exports a starter at `1st — 17:00` and a full-period replacement at the correct later period boundary.
- Recognizes SportsEngine `Major (5:00)` and `Misconduct (10:00)` durations as five and ten minutes.
- Splits a combined major/misconduct record into separate GameSheet penalties when necessary.
- When a major and misconduct occur together, the offender serves the misconduct and a stable, deterministically selected teammate serves the major.
- Chrome helper version 0.9.0 includes the paired-penalty serving-player logic.
