"""Parse and compare SportsEngine roster pages."""
from __future__ import annotations

import re
import unicodedata
from typing import Any

from bs4 import BeautifulSoup


NAME_HEADERS = {"name", "player", "player name"}
NUMBER_HEADERS = {"#", "no", "no.", "number", "jersey", "jersey number"}
POSITION_HEADERS = {"pos", "pos.", "position"}
GRADE_HEADERS = {"grade", "gr", "gr.", "year"}


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

    title = soup.find("h1")
    if not title:
        title = soup.find("title")
    return {"title": _clean(title.get_text(" ", strip=True)) if title else "SportsEngine Roster", "players": list(unique.values())}


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
