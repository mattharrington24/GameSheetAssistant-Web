# GameSheet Assistant Web — Deployment Build

Cross-platform GameSheet Assistant for macOS, Windows, Chromebook, and iPad browsers.

## Local run

```bash
python3 -m venv .venv
source .venv/bin/activate          # macOS/Linux
# .venv\Scripts\activate         # Windows PowerShell
pip install -r requirements.txt
PORT=5001 python app.py
```

Open `http://127.0.0.1:5001`.

## Private login

Set these environment variables before starting:

```bash
export SECRET_KEY="replace-with-a-long-random-string"
export APP_PASSWORD="choose-a-private-password"
PORT=5001 python app.py
```

When `APP_PASSWORD` is set, all app pages and import requests require sign-in. The `/health` endpoint remains public for hosting health checks.

## Saved batches

Current game, workflow position, batch queue, completed games, and skipped games are saved in the browser's local storage. Closing and reopening the browser resumes the session on that device.

## Deploy on Render

1. Put this folder in a GitHub repository.
2. In Render, choose **New → Blueprint** and connect the repository.
3. Render reads `render.yaml` automatically.
4. Set `APP_PASSWORD` in the Render environment settings.
5. Deploy and open the generated HTTPS address.

You may also create a normal Python Web Service using:

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn --workers 2 --threads 4 --timeout 60 --bind 0.0.0.0:$PORT app:app`
- Health check: `/health`

## Docker

```bash
docker build -t gamesheet-assistant .
docker run --rm -p 5000:5000 \
  -e SECRET_KEY="replace-me" \
  -e APP_PASSWORD="replace-me" \
  gamesheet-assistant
```

## Security notes

- Use HTTPS in production.
- Set a unique, long `SECRET_KEY`.
- Set `APP_PASSWORD` before sharing the URL.
- Do not commit passwords or secrets to GitHub.
- Confirm your intended use of SportsEngine pages complies with applicable access policies.


## Finish-game safety

The final workflow step asks for confirmation before marking a game complete. After completion, an **Undo** action remains available for 30 seconds and restores the most recently completed game to its final workflow step.
