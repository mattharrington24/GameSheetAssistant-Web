GameSheet Assistant Web v4.7.0 - PPL Word Import

WHAT THIS IS
This is a complete GameSheetAssistant-Web project, based on the current main
branch and including the v4.6.1 Game Misconduct update.

NEW WORKFLOW
1. Sign in to GameSheet Assistant as usual.
2. Under PPL WORD IMPORT, choose the completed PPL .docx scoresheet.
3. Click Import PPL Scoresheet.
4. Review the parsed summary, goals, penalties, goalies, and validation.
5. Click Copy Web Fill Data and use the current Chrome helper on GameSheet.

DEPLOYMENT
Replace the matching files in your existing GameSheetAssistant-Web repository,
or use this complete folder as the project source. Commit and push to main;
Render should deploy automatically. requirements.txt now includes python-docx.

SUPPORTED PPL FORMAT
- Standard Premier Prep League Word scoresheet
- Two 25-minute periods
- Goals, assists, PP/SH/EN labels, penalties, goalie saves and minutes
- Team shots derived from goals plus opposing goalie saves

SportsEngine imports continue to use the existing high-school rules.
