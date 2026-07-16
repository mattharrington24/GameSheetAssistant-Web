from __future__ import annotations

import hmac
import os
import re
from functools import wraps
from urllib.parse import urlparse

import requests
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.middleware.proxy_fix import ProxyFix

from web_parser import SportsEngineParser

app = Flask(__name__)
app.config.update(
    MAX_CONTENT_LENGTH=2 * 1024 * 1024,
    SECRET_KEY=os.environ.get("SECRET_KEY", "local-development-only-change-me"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("FLASK_ENV") == "production",
)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

SPORTSENGINE_HOSTS = {
    "stats.mngirlshockeyhub.com",
    "www.mngirlshockeyhub.com",
    "mngirlshockeyhub.com",
}
GAME_ID_RE = re.compile(r"^\d{6,12}$")
APP_PASSWORD = os.environ.get("APP_PASSWORD", "").strip()


def auth_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if APP_PASSWORD and not session.get("authenticated"):
            if request.path.startswith("/api/"):
                return jsonify({"ok": False, "error": "Authentication required."}), 401
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def normalize_game_input(value: str) -> str:
    value = value.strip()
    if GAME_ID_RE.fullmatch(value):
        return f"https://stats.mngirlshockeyhub.com/game/show/{value}"
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in SPORTSENGINE_HOSTS:
        raise ValueError("Enter a MN Girls Hockey Hub SportsEngine game URL or numeric game ID.")
    if "/game/show/" not in parsed.path:
        raise ValueError("The URL must be a SportsEngine game page.")
    return value


def fetch_game(url: str) -> str:
    response = requests.get(
        url,
        timeout=25,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
            )
        },
    )
    response.raise_for_status()
    return response.text


@app.route("/login", methods=["GET", "POST"])
def login():
    if not APP_PASSWORD:
        return redirect(url_for("index"))

    error = ""
    if request.method == "POST":
        supplied = request.form.get("password", "")
        if hmac.compare_digest(supplied, APP_PASSWORD):
            session.clear()
            session["authenticated"] = True
            return redirect(request.args.get("next") or url_for("index"))
        error = "Incorrect password."
    return render_template("login.html", error=error)


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.get("/")
@auth_required
def index():
    return render_template("index.html", auth_enabled=bool(APP_PASSWORD))


@app.post("/api/import")
@auth_required
def import_game():
    payload = request.get_json(silent=True) or {}
    raw_input = str(payload.get("url", ""))
    try:
        url = normalize_game_input(raw_input)
        html = fetch_game(url)
        parsed = SportsEngineParser.from_html(html).parse_all()
        parsed["source_url"] = url
        return jsonify({"ok": True, "data": parsed})
    except (ValueError, requests.RequestException, IndexError) as error:
        return jsonify({"ok": False, "error": str(error)}), 400
    except Exception as error:
        app.logger.exception("Unexpected import error")
        return jsonify({"ok": False, "error": f"Unexpected parser error: {error}"}), 500


@app.get("/health")
def health():
    return jsonify({"ok": True, "service": "gamesheet-assistant"})


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
