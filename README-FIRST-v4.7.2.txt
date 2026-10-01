GameSheet Assistant Web v4.7.2 - PPL Word Import

FIXES IN THIS VERSION
- Uses the period-save grid to determine goalie order when Minutes Played is
  blank. First-period saves identify the starter; second-period saves identify
  the replacement.
- Assigns the inferred PPL stint as 25:00 for the appropriate period.
- Maps "High stick" to GameSheet's "High Sticking" penalty option.
- Retains the v4.7.1 Cross-Checking correction.

UPDATE
Replace ppl_parser.py in the existing GameSheetAssistant-Web repository, then
commit and push to main. Render should deploy automatically. No Chrome helper
update is required if v0.9.15 is already installed.
