# GameSheet Assistant Web v4.7.2

## PPL Goalie Starter and High Sticking Fixes

- Infers a 25-minute goalie stint from the period-save grid when Minutes Played
  is blank. A goalie with saves only in the first period is identified as the
  starter; the goalie with second-period saves is the replacement.
- Normalizes `High stick`, `High-sticking`, and `High sticking` to GameSheet's
  `High Sticking` penalty option.
- Retains the v4.7.1 Cross-Checking correction.
