"""Build a GameSheet-first, period-by-period data-entry workflow."""
from __future__ import annotations

import re
from copy import deepcopy


def _seconds(value: str) -> int:
    """Convert M:SS to elapsed seconds; unknown values sort last."""
    try:
        minutes, seconds = str(value).split(":", 1)
        return int(minutes) * 60 + int(seconds)
    except (TypeError, ValueError):
        return 10**9




def _format_clock(total_seconds: int) -> str:
    total_seconds = max(0, int(total_seconds))
    return f"{total_seconds // 60}:{total_seconds % 60:02d}"


def _scheduled_minor_on_time(remaining: str, period: str, periods: list[str]) -> str:
    """Return the full two-minute minor expiration shown on GameSheet cards.

    GameSheet needs a Back On Ice time for ordinary minors in order to infer
    manpower and correctly label shorthanded goals. Regulation periods are 17
    minutes and overtime periods are 8 minutes in this workflow.
    """
    remaining_seconds = _seconds(remaining)
    if remaining_seconds == 10**9:
        return "Confirm in GameSheet"

    if remaining_seconds >= 120:
        return _format_clock(remaining_seconds - 120)

    carry = 120 - remaining_seconds
    current_index = next((i for i, value in enumerate(periods) if _same_period(value, period)), None)
    next_period = periods[current_index + 1] if current_index is not None and current_index + 1 < len(periods) else None
    if next_period and str(next_period).upper().strip().startswith("OT"):
        next_length = 8 * 60
    else:
        next_length = 17 * 60
    return f"Next period — {_format_clock(next_length - carry)}"

def _period_key(value: str) -> tuple[int, int]:
    text = str(value).upper().strip()
    if text.startswith("1"):
        return (1, 0)
    if text.startswith("2"):
        return (2, 0)
    if text.startswith("3"):
        return (3, 0)
    if text.startswith("OT"):
        suffix = re.sub(r"\D", "", text)
        return (4, int(suffix or 1))
    return (99, 0)


def _period_label(value: str) -> str:
    text = str(value).upper().strip()
    if text.startswith("1"):
        return "1st Period"
    if text.startswith("2"):
        return "2nd Period"
    if text.startswith("3"):
        return "3rd Period"
    if text.startswith("OT"):
        suffix = re.sub(r"\D", "", text)
        return f"Overtime {suffix}" if suffix and suffix != "1" else "Overtime"
    return str(value)


def _same_period(left: str, right: str) -> bool:
    return _period_key(left) == _period_key(right)


def _is_standard_minor(penalty: dict) -> bool:
    text = penalty.get("penalty", "").lower()
    return "minor" in text and not any(term in text for term in ("major", "misconduct", "double minor"))


def _mark_early_releases(goals: list[dict], penalties: list[dict]) -> tuple[list[dict], list[dict]]:
    """Link PP goals to active opponent minors that should end at the goal time.

    SportsEngine sometimes reports minor duration as 0:0. It still represents a
    standard minor in the source layout, so the workflow treats it as two minutes.
    When multiple opponent minors are active (for example, a 5-on-3), the
    earliest active minor is the one released by a power-play goal. A manual
    review is required only when the earliest candidates began at the exact
    same time and the source data cannot distinguish which penalty should end.
    """
    goals = deepcopy(goals)
    penalties = deepcopy(penalties)

    for goal in goals:
        if "power play" not in goal.get("strength", "").lower():
            continue
        goal_time = _seconds(goal.get("elapsed", ""))
        candidates = []
        for index, penalty in enumerate(penalties):
            if not _same_period(goal.get("period", ""), penalty.get("period", "")):
                continue
            if penalty.get("team") == goal.get("team") or not _is_standard_minor(penalty):
                continue
            start = _seconds(penalty.get("elapsed", ""))
            if start <= goal_time < start + 120 and not penalty.get("release_at"):
                candidates.append((index, start))

        if candidates:
            # On a power-play goal, the earliest active non-coincidental minor
            # is released. This also applies when two minors create a 5-on-3.
            candidates.sort(key=lambda candidate: candidate[1])
            earliest_start = candidates[0][1]
            earliest = [candidate for candidate in candidates if candidate[1] == earliest_start]

            if len(earliest) == 1:
                penalty_index = earliest[0][0]
                penalties[penalty_index]["release_at"] = goal.get("remaining", "")
                penalties[penalty_index]["release_reason"] = "Power-play goal"
                linked_penalty = penalties[penalty_index]
                goal["release_player"] = linked_penalty.get("player", "Penalized player")
                goal["release_team"] = linked_penalty.get("team", "")
                goal["release_penalty"] = linked_penalty.get("penalty", "Minor penalty")
                goal["release_off_time"] = linked_penalty.get("remaining", "")
            else:
                # Simultaneous earliest minors cannot be resolved safely from
                # the SportsEngine summary alone.
                goal["release_review"] = True
                for penalty_index, _ in earliest:
                    penalties[penalty_index]["release_review"] = True
    return goals, penalties


def _shot_step(shots: dict, period: str, index: int) -> dict:
    def parsed(value):
        text = str(value).strip()
        return int(text) if text.isdigit() else None

    away_raw = shots.get("away", [])[index] if index < len(shots.get("away", [])) else "-"
    home_raw = shots.get("home", [])[index] if index < len(shots.get("home", [])) else "-"
    away = parsed(away_raw)
    home = parsed(home_raw)
    away_display = away if away is not None else "-"
    home_display = home if home is not None else "-"

    if away is None or home is None:
        leader = "Leader: Not available"
    elif away > home:
        leader = f"Leader: {shots['away_team']} (+{away - home})"
    elif home > away:
        leader = f"Leader: {shots['home_team']} (+{home - away})"
    else:
        leader = "Leader: Tie"

    return {
        "title": f"{_period_label(period)} Shots",
        "kind": "shots",
        "period": period,
        "team": "",
        "body": (
            "Enter shots before moving to the next period.\n\n"
            f"{shots['away_team']}: {away_display}\n"
            f"{shots['home_team']}: {home_display}\n\n"
            f"{leader}"
        ),
    }


def _goalie_steps(game: dict, goalies: list[dict]) -> list[dict]:
    steps = []
    for team in (game["away_team"], game["home_team"]):
        team_goalies = [g for g in goalies if g.get("team") == team]
        played = [g for g in team_goalies if g.get("minutes") != "0:00"]
        if len(played) == 1:
            goalie = played[0]
            body = (
                "Select this starting goalie before entering events.\n\n"
                f"#{goalie['number']} {goalie['name']}\n\n"
                "Confirm against the GameSheet lineup."
            )
        elif played:
            candidates = "\n".join(f"#{g['number']} {g['name']} — {g['minutes']} played" for g in played)
            body = (
                "Multiple goalies played. Select and confirm the starter before scoring.\n\n"
                f"{candidates}\n\n"
                "SportsEngine final stats do not reliably identify which goalie started."
            )
        elif team_goalies:
            candidates = "\n".join(f"#{g['number']} {g['name']}" for g in team_goalies)
            body = f"Confirm the starting goalie from the lineup.\n\n{candidates}"
        else:
            body = "No goalie record was parsed. Confirm and select the starting goalie manually."

        steps.append({
            "title": "Starting Goalie",
            "kind": "goalie-start",
            "team": team,
            "body": body,
        })
    return steps


def build_entry_steps(game, shots, goals, penalties, goalies):
    goals, penalties = _mark_early_releases(goals, penalties)
    steps = [{
        "title": "Game Information",
        "kind": "game-info",
        "team": "",
        "body": (
            f"{game['away_team']} {game['away_score']}\n"
            f"{game['home_team']} {game['home_score']}\n\n"
            f"Date: {game['date']}\n"
            f"Venue: {game['venue']}"
        ),
    }]
    steps.extend(_goalie_steps(game, goalies))

    periods = list(shots.get("periods", []))
    for event in [*goals, *penalties]:
        period = event.get("period")
        if period and not any(_same_period(period, existing) for existing in periods):
            periods.append(period)
    periods.sort(key=_period_key)

    for period in periods:
        events = []
        events.extend(("goal", goal) for goal in goals if _same_period(goal.get("period", ""), period))
        events.extend(("penalty", penalty) for penalty in penalties if _same_period(penalty.get("period", ""), period))
        # SportsEngine timestamps are elapsed time, so ascending order is chronological.
        events.sort(key=lambda item: (_seconds(item[1].get("elapsed", "")), 0 if item[0] == "penalty" else 1))

        for event_number, (kind, event) in enumerate(events, start=1):
            if kind == "goal":
                warning = ""
                if event.get("release_player"):
                    warning = (
                        "\n\n⚠ POWER-PLAY GOAL REMINDER\n"
                        f"You need to set the On time to {event['remaining']} for this specific penalty:\n"
                        f"{event['release_player']} — {event.get('release_penalty', 'Minor penalty')} "
                        f"({event['release_team']})\n"
                        f"Off: {event.get('release_off_time') or 'Confirm in GameSheet'}\n"
                        f"On: {event['remaining']}\n\n"
                        "This penalty ends early because of the power-play goal."
                    )
                elif event.get("release_review"):
                    warning = "\n\n⚠ REVIEW RELEASE TIME\nMultiple opponent minors may be active. Confirm which player returns."
                body = (
                    f"Time Remaining: {event['remaining']}\n"
                    f"Scorer: {event['scorer']}\n"
                    f"Assists: {', '.join(event.get('assists', [])) or 'None'}\n"
                    f"Strength: {event.get('strength', 'unknown')}"
                    f"{warning}"
                )
                title = "Goal"
            else:
                warning = ""
                on_time = ""
                if event.get("release_at"):
                    on_time = event["release_at"]
                    warning = (
                        "\n\n⚠ ENDS EARLY — POWER-PLAY GOAL\n"
                        f"Set Back On Ice to {event['release_at']} remaining. Use the early time shown above."
                    )
                elif event.get("release_review"):
                    warning = "\n\n⚠ REVIEW RELEASE TIME\nThis minor overlaps a power-play goal and may end early."
                elif _is_standard_minor(event):
                    on_time = _scheduled_minor_on_time(event.get("remaining", ""), period, periods)

                on_line = f"\nBack On Ice: {on_time} remaining" if on_time else ""
                body = (
                    f"Off Ice: {event['remaining']} remaining"
                    f"{on_line}\n"
                    f"Player: {event['player']}\n"
                    f"Penalty: {event['penalty']}"
                    f"{warning}"
                )
                title = "Penalty"

            steps.append({
                "title": f"{_period_label(period)} — {title}",
                "kind": kind,
                "period": period,
                "team": event.get("team", ""),
                "event_number": event_number,
                "body": body,
                "warning": bool(event.get("release_at") or event.get("release_player") or event.get("release_review")),
            })

        shot_index = next((i for i, p in enumerate(shots.get("periods", [])) if _same_period(p, period)), None)
        if shot_index is not None:
            steps.append(_shot_step(shots, period, shot_index))

    played_goalies = [g for g in goalies if g.get("minutes") != "0:00"]
    goalie_lines = []
    for goalie in played_goalies:
        goalie_lines.append(
            f"{goalie['team']} — #{goalie['number']} {goalie['name']}\n"
            f"{goalie['minutes']} played · {goalie['shots_against']} SA · "
            f"{goalie['goals_against']} GA · {goalie['saves']} saves"
        )
    steps.append({
        "title": "Final Goalie Review",
        "kind": "goalie-review",
        "team": "",
        "body": "Confirm goalie changes and final statistics.\n\n" + ("\n\n".join(goalie_lines) or "No goalie statistics were parsed."),
    })

    total_away = shots.get("away", ["-"])[-1] if shots.get("away") else "-"
    total_home = shots.get("home", ["-"])[-1] if shots.get("home") else "-"
    steps.append({
        "title": "Final Check",
        "kind": "final",
        "team": "",
        "body": (
            "Verify the final score, all events, goalie changes, and totals.\n\n"
            f"Final score: {game['away_team']} {game['away_score']} — "
            f"{game['home_team']} {game['home_score']}\n"
            f"Total shots: {shots['away_team']} {total_away} — {shots['home_team']} {total_home}"
        ),
    })
    return steps
