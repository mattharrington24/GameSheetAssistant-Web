"""Parse and compare SportsEngine roster pages."""
from __future__ import annotations

import re
import unicodedata
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup


NAME_HEADERS = {"name", "player", "player name"}
NUMBER_HEADERS = {"#", "no", "no.", "number", "jersey", "jersey number"}
POSITION_HEADERS = {"pos", "pos.", "position"}
GRADE_HEADERS = {"grade", "gr", "gr.", "year"}
SPORTSENGINE_HOSTS = {
    "stats.mngirlshockeyhub.com",
    "www.mngirlshockeyhub.com",
    "mngirlshockeyhub.com",
}


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _header_key(value: str) -> str:
    return _clean(value).lower()


def normalize_name(value: str) -> str:
    """Create a conservative key while preserving the displayed player name."""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(character for character in value if not unicodedata.combining(character))
    value = value.casefold().replace("’", "'")
    if "," in value:
        last, first = value.split(",", 1)
        value = f"{first} {last}"
    return re.sub(r"[^a-z0-9]+", "", value)


def normalize_team(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(character for character in value if not unicodedata.combining(character))
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _first_index(headers: list[str], choices: set[str]) -> int | None:
    for index, header in enumerate(headers):
        if header in choices:
            return index
    return None


def parse_roster(html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")
    players: list[dict[str, str]] = []

    for table in soup.find_all("table"):
        header_row = table.find("thead")
        if not header_row:
            continue
        headers = [_header_key(cell.get_text(" ", strip=True)) for cell in header_row.find_all(["th", "td"])]
        name_index = _first_index(headers, NAME_HEADERS)
        if name_index is None:
            continue

        number_index = _first_index(headers, NUMBER_HEADERS)
        position_index = _first_index(headers, POSITION_HEADERS)
        grade_index = _first_index(headers, GRADE_HEADERS)

        for row in table.select("tbody tr"):
            cells = row.find_all(["td", "th"])
            if name_index >= len(cells):
                continue
            name_cell = cells[name_index]
            profile_link = name_cell.find("a", href=re.compile(r"/roster_players/"))
            name = _clean((profile_link or name_cell).get_text(" ", strip=True))
            if not name or name.casefold() in {"name", "player", "totals"}:
                continue

            def cell_value(index: int | None) -> str:
                return _clean(cells[index].get_text(" ", strip=True)) if index is not None and index < len(cells) else ""

            players.append(
                {
                    "name": name,
                    "number": cell_value(number_index),
                    "position": cell_value(position_index),
                    "grade": cell_value(grade_index),
                }
            )

    unique: dict[str, dict[str, str]] = {}
    for player in players:
        key = normalize_name(player["name"])
        if key and key not in unique:
            unique[key] = player
    if not unique:
        raise ValueError("No players were found on this roster page.")

    # SportsEngine's visible H1 is often the generic site name; the document
    # title contains the actual team and season.
    title = soup.find("title")
    if not title:
        title = soup.find("h1")
    return {"title": _clean(title.get_text(" ", strip=True)) if title else "SportsEngine Roster", "players": list(unique.values())}


def roster_team_name(title: str) -> str:
    title = re.sub(r"\s*[-–—]\s*MN Girls['’] Hockey Hub.*$", "", title, flags=re.IGNORECASE)
    title = re.split(r"\s+[-–—]\s+20\d{2}(?:-\d{2,4})?\b", title, maxsplit=1)[0]
    title = re.split(r"\s+[-–—]\s+(?:Regular|Roster)\b", title, maxsplit=1, flags=re.IGNORECASE)[0]
    return _clean(title) or "Unknown team"


def season_links(html: str, source_url: str, link_type: str) -> list[str]:
    """Extract same-season SportsEngine page or roster links."""
    source = urlparse(source_url)
    subseason = parse_qs(source.query).get("subseason", [""])[0]
    pattern = r"^/page/show/\d+" if link_type == "page" else r"^/roster/show/\d+"
    soup = BeautifulSoup(html, "lxml")
    links: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        absolute = urljoin(source_url, anchor["href"])
        parsed = urlparse(absolute)
        if parsed.hostname not in SPORTSENGINE_HOSTS or not re.match(pattern, parsed.path):
            continue
        query = parse_qs(parsed.query)
        target_subseason = query.get("subseason", [""])[0]
        if subseason and target_subseason and target_subseason != subseason:
            continue
        if subseason and not target_subseason:
            query["subseason"] = [subseason]
        query_text = "&".join(
            f"{key}={value}"
            for key in sorted(query)
            for value in query[key]
        )
        links.add(urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", query_text, "")))
    return sorted(links)


def find_transfers(previous_rosters: list[dict[str, Any]], current_rosters: list[dict[str, Any]]) -> dict[str, Any]:
    def player_index(rosters: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        index: dict[str, list[dict[str, Any]]] = {}
        for roster in rosters:
            for player in roster["players"]:
                item = {**player, "team": roster["team"], "roster_url": roster.get("source_url", "")}
                index.setdefault(normalize_name(player["name"]), []).append(item)
        return index

    previous = player_index(previous_rosters)
    current = player_index(current_rosters)
    transfers: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []
    for key in previous.keys() & current.keys():
        old_entries = previous[key]
        new_entries = current[key]
        changed = [
            (old, new)
            for old in old_entries
            for new in new_entries
            if normalize_team(old["team"]) != normalize_team(new["team"])
        ]
        if not changed:
            continue
        record = {
            "name": new_entries[0]["name"],
            "previous": old_entries,
            "current": new_entries,
            "previous_team": changed[0][0]["team"],
            "current_team": changed[0][1]["team"],
            "confidence": "Likely" if len(old_entries) == 1 and len(new_entries) == 1 else "Review",
        }
        (transfers if record["confidence"] == "Likely" else ambiguous).append(record)

    transfers.sort(key=lambda item: item["name"].casefold())
    ambiguous.sort(key=lambda item: item["name"].casefold())
    ava = next(
        (
            item for item in transfers + ambiguous
            if normalize_name(item["name"]) == normalize_name("Ava Lindsay")
            and normalize_team(item["previous_team"]) == normalize_team("Breck")
            and normalize_team(item["current_team"]) == normalize_team("Minnetonka")
        ),
        None,
    )
    return {
        "transfers": transfers,
        "ambiguous": ambiguous,
        "ava_lindsay_found": bool(ava),
        "counts": {
            "previous_teams": len(previous_rosters),
            "current_teams": len(current_rosters),
            "previous_players": sum(len(roster["players"]) for roster in previous_rosters),
            "current_players": sum(len(roster["players"]) for roster in current_rosters),
            "likely_transfers": len(transfers),
            "needs_review": len(ambiguous),
        },
    }


def compare_rosters(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    previous_by_name = {normalize_name(player["name"]): player for player in previous["players"]}
    current_by_name = {normalize_name(player["name"]): player for player in current["players"]}
    returning_keys = previous_by_name.keys() & current_by_name.keys()
    new_keys = current_by_name.keys() - previous_by_name.keys()
    departed_keys = previous_by_name.keys() - current_by_name.keys()

    def by_name(player: dict[str, str]) -> str:
        return player["name"].casefold()

    returning = [
        {"previous": previous_by_name[key], "current": current_by_name[key]}
        for key in returning_keys
    ]
    returning.sort(key=lambda item: by_name(item["current"]))
    new = sorted((current_by_name[key] for key in new_keys), key=by_name)
    departed = sorted((previous_by_name[key] for key in departed_keys), key=by_name)
    return {
        "previous": previous,
        "current": current,
        "returning": returning,
        "new": new,
        "departed": departed,
        "counts": {
            "previous": len(previous_by_name),
            "current": len(current_by_name),
            "returning": len(returning),
            "new": len(new),
            "departed": len(departed),
        },
    }
