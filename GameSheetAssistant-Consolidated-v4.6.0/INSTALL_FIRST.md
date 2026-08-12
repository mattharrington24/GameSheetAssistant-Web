# GameSheet Assistant consolidated release

This package contains a matched pair:

- `render-app/`: the complete GameSheet Assistant web application, release 4.6.0
- `chrome-extension/`: GameSheet Web Fill helper 0.9.5

Both parts must be updated together. Do not mix either folder with an older release.

## 1. Update GitHub and Render

Extract this ZIP into Downloads, then run the following as one command in Terminal:

```bash
cd ~/Downloads/GameSheetAssistant-Web && rsync -av --exclude='.git' ~/Downloads/GameSheetAssistant-Consolidated-v4.6.0/render-app/ ./ && git add -A && git commit -m "Install consolidated GameSheet Assistant v4.6.0" && git push origin main
```

Wait until Render reports that the deployment from the new commit succeeded. Then hard-refresh GameSheet Assistant and re-import the SportsEngine game.

## 2. Reload the Chrome extension

1. Open `chrome://extensions`.
2. Turn on **Developer mode**.
3. Remove the older GameSheet Assistant Web Helper, or use **Load unpacked** for a clean installation.
4. Select this package's `chrome-extension` folder.
5. Confirm the extension displays version **0.9.5**.

If it is already loaded from this exact folder, click its reload button instead.

## 3. Use the matched workflow

1. Import or re-import the SportsEngine game in GameSheet Assistant.
2. Click **Copy Web Fill Data**.
3. Open the correct completed game's **Edit Game** page in GameSheet.
4. Paste the newly copied data into the extension.
5. Click **Check Page**, **Analyze Form**, and then **Fill Form**.
6. Review every populated field before clicking GameSheet's **Save Changes**.

## Goalie verification

For any game with multiple goalies, verify these fields before saving:

- The inferred starter is the first shift at period 1, `17:00`.
- A replacement appears only at the inferred change time.
- The same goalie is not incorrectly shown as both the starter and a later replacement.
- Empty-net shifts use the rounded minute before the goal and restore the goalie at the goal time.

## Validation completed

- 47 Python tests passed.
- Web-app JavaScript syntax passed.
- Chrome-extension JavaScript syntax passed.
- Extension manifest validation passed.

