# GameSheet Web Fill (pilot)

This pilot reduces historical iPad entry while keeping a human review and final save.

## Install the Chrome helper once

1. Open `chrome://extensions` in Chrome.
2. Turn on **Developer mode**.
3. Click **Load unpacked**.
4. Select the `gamesheet-web-helper` folder from this project.

## Fill a game

1. Create, finish, and upload the shell game using the GameSheet iPad app.
2. Import the matching SportsEngine game in GameSheet Assistant.
3. Click **Copy Web Fill Data**.
4. Open the matching completed game’s **Edit Game** page in GameSheet.
5. Click the GameSheet Assistant Web Helper extension.
6. Click **Check Page**. The helper refuses to proceed if the teams do not match.
7. Click **Fill Form**.
8. Review every lineup, goalie shift, shot total, goal, assist, penalty, and time.
9. Click GameSheet’s **Save Changes** manually.
10. Verify the public box score and goalie totals.

## Pilot limitations

- The helper does not click **Save Changes**.
- Games with multiple goalies are flagged. Their shifts and split shots remain manual.
- Starting goalies and lineups should be selected when creating the shell game on the iPad.
- The helper does not create GameSheet play-by-play data.
- This is intentionally a pilot. Test it on one simple game before broader use.
