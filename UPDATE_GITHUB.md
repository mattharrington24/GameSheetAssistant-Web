# Updating the live GitHub/Render version

This folder is clean and tested. It does not include Git history because GitHub ZIP downloads never include the hidden `.git` folder.

## Safest update method on your Mac

1. Keep this folder as the clean source package.
2. In Terminal, clone the existing repository into a fresh folder:

```bash
git clone https://github.com/mattharrington24/GameSheetAssistant-Web.git GameSheetAssistant-Web-Live
```

3. Copy the contents of this organized folder into `GameSheetAssistant-Web-Live`, replacing matching files. Do not delete the hidden `.git` folder in `GameSheetAssistant-Web-Live`.
4. Open `GameSheetAssistant-Web-Live` in VS Code.
5. Run:

```bash
git status
git add .
git commit -m "Add finish game workflow"
git push
```

Render should redeploy automatically after the push.

## Verification

The Done button is in `templates/index.html` and its behavior is in `static/app.js`.
Run tests with:

```bash
python3 -m pytest -q
```

Expected result: `4 passed`.
