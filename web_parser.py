"""SportsEngine hockey box-score parser for the web application.

This module is stateless: every parse receives HTML directly, making it safe for
multiple web users and avoiding temporary shared files.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from bs4 import BeautifulSoup

from converter import convert_to_time_remaining
from workflow import build_entry_steps

TIME_RE = re.compile(r"^\d{1,2}:\d{2}$")
PERIOD_RE = re.compile(r"^(1st|2nd|3rd|OT\d*)$", re.IGNORECASE)
SCORE_RE = re.compile(r"^\d+$")


def html_to_lines(html: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    return [line.strip() for line in soup.get_text("\n").splitlines() if line.strip()]


@dataclass
class SportsEngineParser:
    lines: list[str]

    @classmethod
    def from_html(cls, html: str) -> "SportsEngineParser":
        return cls(html_to_lines(html))

    def _find_first(self, labels: set[str], start: int = 0) -> int:
        for index in range(start, len(self.lines)):
            if self.lines[index] in labels:
                return index
        raise ValueError(f"None of these labels were found: {', '.join(sorted(labels))}")

    @staticmethod
    def _is_period(value: str) -> bool:
        return bool(PERIOD_RE.fullmatch(value))

    @staticmethod
    def _period_for_converter(period: str) -> str:
        return "OT" if period.upper().startswith("OT") else period[0]

    def game_header(self) -> dict[str, str]:
        i = self._find_first({"FINAL", "FINAL/OT"})
        return {
            "date": self.lines[i - 2],
            "venue": self.lines[i - 1],
            "status": self.lines[i],
            "away_team": self.lines[i + 1],
            "away_score": self.lines[i + 3],
            "home_score": self.lines[i + 5],
            "home_team": self.lines[i + 8],
        }

    def shots(self) -> dict[str, Any]:
        game = self.game_header()
        i = self.lines.index("SHOTS")
        cursor = i + 1
        period_headers: list[str] = []
        while cursor < len(self.lines) and self.lines[cursor] != game["away_team"]:
            period_headers.append(self.lines[cursor])
            cursor += 1
        if cursor >= len(self.lines):
            raise ValueError("Away team not found in SHOTS table")

        away_team = self.lines[cursor]
        cursor += 1
        value_count = len(period_headers)
        away = self.lines[cursor:cursor + value_count]
        cursor += value_count
        if cursor >= len(self.lines):
            raise ValueError("Home team not found in SHOTS table")
        home_team = self.lines[cursor]
        cursor += 1
        home = self.lines[cursor:cursor + value_count]

        if away_team != game["away_team"] or home_team != game["home_team"]:
            raise ValueError("SHOTS table team names did not match the game header")
        if len(away) != value_count or len(home) != value_count:
            raise ValueError("Incomplete SHOTS table")

        periods = period_headers[:-1] if period_headers and period_headers[-1] == "T" else period_headers
        return {
            "periods": periods,
            "away_team": away_team,
            "away": away,
            "home_team": home_team,
            "home": home,
        }

    def _section_between(self, start_label: str, end_label: str) -> list[str]:
        start = self.lines.index(start_label)
        end = self.lines.index(end_label, start + 1)
        return self.lines[start:end]

    def _event_details_until_boundary(self, lines: list[str], start: int) -> tuple[list[str], int]:
        details: list[str] = []
        cursor = start
        while cursor < len(lines):
            value = lines[cursor]
            if self._is_period(value) or TIME_RE.fullmatch(value):
                break
            if (
                SCORE_RE.fullmatch(value)
                and cursor + 1 < len(lines)
                and SCORE_RE.fullmatch(lines[cursor + 1])
            ):
                break
            details.append(value)
            cursor += 1
        return details, cursor

    def goals(self) -> list[dict[str, Any]]:
        game = self.game_header()
        teams = {game["away_team"], game["home_team"]}
        lines = self._section_between("Scoring Summary", "Penalty Summary")
        goals: list[dict[str, Any]] = []
        period: str | None = None
        index = 0

        while index < len(lines):
            line = lines[index]
            if self._is_period(line):
                period = "OT" if line.upper().startswith("OT") else line
                index += 1
                continue

            if TIME_RE.fullmatch(line) and period and index + 3 < len(lines):
                team = lines[index + 1]
                if team in teams and lines[index + 2].startswith("#"):
                    scorer_number = lines[index + 2]
                    scorer_name = lines[index + 3]
                    details, next_index = self._event_details_until_boundary(lines, index + 4)
                    details_text = " ".join(details)
                    strength_match = re.search(
                        r"\((even strength|power play|short handed|shorthanded)\)",
                        details_text,
                        re.IGNORECASE,
                    )
                    strength = strength_match.group(1).lower() if strength_match else "unknown"
                    if "empty net" in details_text.lower():
                        strength = f"{strength} / empty net" if strength != "unknown" else "empty net"
                    if "penalty shot" in details_text.lower():
                        strength = f"{strength} / penalty shot" if strength != "unknown" else "penalty shot"

                    assists: list[str] = []
                    for detail_index, item in enumerate(details):
                        for number in re.findall(r"#\d+", item):
                            name = ""
                            if detail_index + 1 < len(details):
                                candidate = details[detail_index + 1].strip(" ,()")
                                if candidate and not candidate.startswith("#"):
                                    name = candidate
                            assist = f"{number} {name}".strip()
                            if assist not in assists:
                                assists.append(assist)

                    goals.append({
                        "period": period,
                        "elapsed": line,
                        "remaining": convert_to_time_remaining(line, self._period_for_converter(period)),
                        "team": team,
                        "scorer": f"{scorer_number} {scorer_name}",
                        "strength": strength,
                        "assists": assists[:2],
                    })
                    index = next_index
                    continue
            index += 1
        return goals

    def _penalty_section(self) -> list[str]:
        start = self.lines.index("Penalty Summary")
        end = next(i for i in range(start + 1, len(self.lines)) if self.lines[i].endswith(" Skaters"))
        return self.lines[start:end]

    def penalties(self) -> list[dict[str, str]]:
        game = self.game_header()
        teams = {game["away_team"], game["home_team"]}
        lines = self._penalty_section()
        penalties: list[dict[str, str]] = []
        period: str | None = None
        index = 0

        while index < len(lines):
            line = lines[index]
            if self._is_period(line):
                period = line
                index += 1
                continue
            if TIME_RE.fullmatch(line) and period and index + 2 < len(lines):
                team = lines[index + 1]
                if team in teams:
                    cursor = index + 2
                    player_number = ""
                    player_name = "Team/Bench"
                    if cursor < len(lines) and lines[cursor].startswith("#"):
                        player_number = lines[cursor]
                        cursor += 1
                        if cursor < len(lines):
                            player_name = lines[cursor]
                            cursor += 1
                    if cursor >= len(lines):
                        index += 1
                        continue
                    penalties.append({
                        "period": period,
                        "elapsed": line,
                        "remaining": convert_to_time_remaining(line, self._period_for_converter(period)),
                        "team": team,
                        "player": f"{player_number} {player_name}".strip(),
                        "penalty": lines[cursor],
                    })
                    index = cursor + 1
                    continue
            index += 1
        return penalties

    def goalies(self) -> list[dict[str, str]]:
        game = self.game_header()
        goalies: list[dict[str, str]] = []
        for team in [game["away_team"], game["home_team"]]:
            title = f"{team} Goalies"
            if title not in self.lines:
                continue
            start = self.lines.index(title)
            other_team = game["home_team"] if team == game["away_team"] else game["away_team"]
            other_title = f"{other_team} Goalies"
            if other_title in self.lines[start + 1:]:
                end = self.lines.index(other_title, start + 1)
            elif "Game Details" in self.lines[start + 1:]:
                end = self.lines.index("Game Details", start + 1)
            else:
                end = len(self.lines)
            section = self.lines[start:end]
            for i in range(len(section) - 6):
                if section[i].isdigit() and TIME_RE.fullmatch(section[i + 2]):
                    values = section[i:i + 7]
                    if all(re.fullmatch(r"\d+", value) for value in values[3:6]):
                        goalie = {
                            "team": team,
                            "number": values[0],
                            "name": values[1],
                            "minutes": values[2],
                            "shots_against": values[3],
                            "goals_against": values[4],
                            "saves": values[5],
                            "save_percentage": values[6],
                        }
                        if goalie not in goalies:
                            goalies.append(goalie)
        return goalies

    def validation(self, game: dict[str, str], goals: list[dict[str, Any]], goalies: list[dict[str, str]]) -> list[dict[str, Any]]:
        checks: list[dict[str, Any]] = []
        for side in ("away", "home"):
            team = game[f"{side}_team"]
            final_score = int(game[f"{side}_score"])
            parsed = sum(1 for goal in goals if goal["team"] == team)
            checks.append({
                "ok": parsed == final_score,
                "label": f"{team} goals",
                "detail": f"Parsed {parsed}; final score {final_score}",
            })
        for goalie in goalies:
            actual = int(goalie["shots_against"])
            calculated = int(goalie["goals_against"]) + int(goalie["saves"])
            checks.append({
                "ok": actual == calculated,
                "label": f"{goalie['team']} #{goalie['number']} {goalie['name']}",
                "detail": f"Saves + GA = {calculated}; shots against {actual}",
            })
        return checks

    def parse_all(self) -> dict[str, Any]:
        game = self.game_header()
        shots = self.shots()
        goals = self.goals()
        penalties = self.penalties()
        goalies = self.goalies()
        return {
            "game": game,
            "shots": shots,
            "goals": goals,
            "penalties": penalties,
            "goalies": goalies,
            "validation": self.validation(game, goals, goalies),
            "workflow": build_entry_steps(game, shots, goals, penalties, goalies),
        }
