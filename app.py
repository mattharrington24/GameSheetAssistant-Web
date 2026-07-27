from __future__ import annotations

import hmac
import json
import os
import re
import tempfile
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import wraps
from pathlib import Path
from urllib.parse import urlparse

import requests
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.middleware.proxy_fix import ProxyFix

from web_parser import SportsEngineParser
from roster_compare import (
    compare_rosters,
    find_transfers,
    parse_roster,
    roster_team_name,
    roster_url_for_team_page,
    season_links,
    sportsengine_team_links,
)

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
ROSTER_ID_RE = re.compile(r"^\d{6,12}$")
APP_PASSWORD = os.environ.get("APP_PASSWORD", "").strip()
TRANSFER_JOB_DIR = Path(tempfile.gettempdir()) / "gamesheet-transfer-jobs"
TRANSFER_JOB_DIR.mkdir(parents=True, exist_ok=True)


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


def normalize_roster_input(value: str) -> str:
    value = value.strip()
    if ROSTER_ID_RE.fullmatch(value):
        return f"https://stats.mngirlshockeyhub.com/roster/show/{value}"
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in SPORTSENGINE_HOSTS:
        raise ValueError("Enter a MN Girls Hockey Hub SportsEngine roster URL.")
    if not re.fullmatch(r"/roster/show/\d+", parsed.path.rstrip("/")):
        raise ValueError("The URL must be a SportsEngine roster page.")
    return value


def normalize_season_input(value: str) -> str:
    value = value.strip()
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in SPORTSENGINE_HOSTS:
        raise ValueError("Enter a MN Girls Hockey Hub SportsEngine season-hub URL.")
    if not re.match(r"^/page/show/\d+", parsed.path):
        raise ValueError("The URL must be a SportsEngine season-hub page.")
    if "subseason=" not in parsed.query:
        raise ValueError("The season-hub URL must include its subseason number.")
    return value


def request_aliases(payload: dict) -> list[dict[str, str]]:
    raw_aliases = payload.get("aliases", [])
    if not isinstance(raw_aliases, list):
        return []
    aliases: list[dict[str, str]] = []
    for item in raw_aliases[:200]:
        if not isinstance(item, dict):
            continue
        previous = str(item.get("previous", "")).strip()[:100]
        current = str(item.get("current", "")).strip()[:100]
        if previous and current:
            aliases.append({"previous": previous, "current": current})
    return aliases


def _job_path(job_id: str) -> Path:
    return TRANSFER_JOB_DIR / f"{job_id}.json"


def _write_job(job_id: str, data: dict) -> None:
    target = _job_path(job_id)
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(data), encoding="utf-8")
    os.replace(temporary, target)


def _read_job(job_id: str) -> dict | None:
    if not re.fullmatch(r"[a-f0-9]{32}", job_id):
        return None
    path = _job_path(job_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _fetch_pages(urls: list[str], workers: int = 3):
    """Yield fetched pages immediately so large HTML responses are not retained."""
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(fetch_game, url): url for url in urls}
        for future in as_completed(futures):
            url = futures.pop(future)
            try:
                yield url, future.result(), None
            except Exception as error:
                yield url, None, str(error)


def _discover_season_rosters(hub_url: str, update) -> tuple[list[dict], list[dict]]:
    hub_html = fetch_game(hub_url)
    visited = {hub_url}
    frontier = season_links(hub_html, hub_url, "page")
    roster_urls = set(season_links(hub_html, hub_url, "roster"))
    team_urls = set(sportsengine_team_links(hub_html, hub_url))
    failures: list[dict[str, str]] = []

    for depth in range(3):
        frontier = [url for url in frontier if url not in visited][:350]
        if not frontier:
            break
        update(f"Discovering team pages ({depth + 1}/3)", len(visited), len(visited) + len(frontier))
        next_frontier: set[str] = set()
        for url, html, error in _fetch_pages(frontier):
            if error:
                failures.append({"url": url, "error": error})
                continue
            visited.add(url)
            roster_urls.update(season_links(html, url, "roster"))
            team_urls.update(sportsengine_team_links(html, url))
            next_frontier.update(season_links(html, url, "page"))
        frontier = sorted(next_frontier - visited)

    # Historical SportsEngine pages often omit the roster tab from server-side
    # HTML. Team and roster nodes are paired sequentially in these league trees.
    roster_urls.update(roster_url_for_team_page(url) for url in team_urls)
    if not roster_urls:
        raise ValueError("No team roster links were found from this season hub.")

    update("Reading team rosters", 0, len(roster_urls))
    rosters: list[dict] = []
    for index, (url, html, error) in enumerate(_fetch_pages(sorted(roster_urls)), 1):
        if error:
            failures.append({"url": url, "error": error})
            continue
        try:
            roster = parse_roster(html)
            roster["team"] = roster_team_name(roster["title"])
            roster["source_url"] = url
            rosters.append(roster)
        except ValueError as error:
            failures.append({"url": url, "error": str(error)})
        if index % 5 == 0 or index == len(roster_urls):
            update("Reading team rosters", index, len(roster_urls))
    return rosters, failures


def _run_transfer_job(
    job_id: str,
    previous_url: str,
    current_url: str,
    aliases: list[dict[str, str]],
) -> None:
    job = {"status": "running", "stage": "Starting", "current": 0, "total": 1}

    def update(stage: str, current: int, total: int) -> None:
        job.update({"stage": stage, "current": current, "total": total})
        _write_job(job_id, job)

    try:
        update("Scanning previous season", 0, 1)
        previous, previous_failures = _discover_season_rosters(previous_url, update)
        update("Scanning current season", 0, 1)
        current, current_failures = _discover_season_rosters(current_url, update)
        result = find_transfers(previous, current, aliases)
        result["failures"] = previous_failures + current_failures
        result["previous_hub_url"] = previous_url
        result["current_hub_url"] = current_url
        job.update({"status": "complete", "stage": "Complete", "current": 1, "total": 1, "result": result})
    except Exception as error:
        app.logger.exception("Transfer scan failed")
        job.update({"status": "failed", "stage": "Failed", "error": str(error)})
    _write_job(job_id, job)


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


@app.get("/rosters")
@auth_required
def rosters():
    return render_template("rosters.html", auth_enabled=bool(APP_PASSWORD))


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


@app.post("/api/rosters/compare")
@auth_required
def compare_roster_pages():
    payload = request.get_json(silent=True) or {}
    try:
        previous_url = normalize_roster_input(str(payload.get("previous_url", "")))
        current_url = normalize_roster_input(str(payload.get("current_url", "")))
        previous = parse_roster(fetch_game(previous_url))
        current = parse_roster(fetch_game(current_url))
        result = compare_rosters(previous, current, request_aliases(payload))
        result["previous"]["source_url"] = previous_url
        result["current"]["source_url"] = current_url
        return jsonify({"ok": True, "data": result})
    except (ValueError, requests.RequestException) as error:
        return jsonify({"ok": False, "error": str(error)}), 400
    except Exception as error:
        app.logger.exception("Unexpected roster comparison error")
        return jsonify({"ok": False, "error": f"Unexpected roster comparison error: {error}"}), 500


@app.post("/api/transfers/start")
@auth_required
def start_transfer_scan():
    payload = request.get_json(silent=True) or {}
    try:
        previous_url = normalize_season_input(str(payload.get("previous_url", "")))
        current_url = normalize_season_input(str(payload.get("current_url", "")))
        aliases = request_aliases(payload)
    except ValueError as error:
        return jsonify({"ok": False, "error": str(error)}), 400
    job_id = uuid.uuid4().hex
    _write_job(job_id, {"status": "queued", "stage": "Queued", "current": 0, "total": 1})
    threading.Thread(
        target=_run_transfer_job,
        args=(job_id, previous_url, current_url, aliases),
        daemon=True,
    ).start()
    return jsonify({"ok": True, "job_id": job_id})


@app.get("/api/transfers/status/<job_id>")
@auth_required
def transfer_scan_status(job_id: str):
    job = _read_job(job_id)
    if job is None:
        return jsonify({"ok": False, "error": "Transfer scan not found."}), 404
    return jsonify({"ok": True, "job": job})


@app.get("/health")
def health():
    return jsonify({"ok": True, "service": "gamesheet-assistant"})


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
