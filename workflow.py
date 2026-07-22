"""Build a GameSheet-first, period-by-period data-entry workflow."""
from __future__ import annotations

import re
from copy import deepcopy
from itertools import permutations


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


def _goalie_pull_time(goal_remaining: str) -> str:
    """Return the whole-minute mark immediately before an empty-net goal."""
    remaining_seconds = _seconds(goal_remaining)
    if remaining_seconds == 10**9:
        return "Confirm in GameSheet"
    pull_seconds = ((remaining_seconds // 60) + 1) * 60
    return _format_clock(pull_seconds)


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


def _penalty_card_details(penalty: dict) -> tuple[str, str]:
    """Return a clean penalty type and human-readable duration."""
    text = str(penalty.get("penalty", "")).strip()
    penalty_type = text.split(" - ", 1)[0].strip() or "Confirm in GameSheet"
    duration_match = re.search(r"\((\d+):(\d{1,2})\)", text)
    if duration_match:
        seconds = int(duration_match.group(1)) * 60 + int(duration_match.group(2))
    elif _is_standard_minor(penalty):
        seconds = 120
    else:
        seconds = 0
    # SportsEngine sometimes reports an ordinary minor as 0:0.
    if seconds == 0 and _is_standard_minor(penalty):
        seconds = 120
    if seconds and seconds % 60 == 0:
        minutes = seconds // 60
        duration = f"{minutes} minute{'s' if minutes != 1 else ''}"
    elif seconds:
        duration = _format_clock(seconds)
    else:
        duration = "Confirm in GameSheet"
    return penalty_type, duration


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


def _period_length(period: str) -> int:
    return 8 * 60 if str(period).upper().strip().startswith("OT") else 17 * 60


def _stat_int(value) -> int | None:
    text = str(value).strip()
    return int(text) if text.isdigit() else None


def _goalie_shots_faced(goalie: dict) -> int | None:
    """Prefer the auditable saves + goals-against total over a reported SA field."""
    saves = _stat_int(goalie.get("saves"))
    goals_against = _stat_int(goalie.get("goals_against"))
    if saves is not None and goals_against is not None:
        return saves + goals_against
    return _stat_int(goalie.get("shots_against"))


def _infer_goalie_plans(game: dict, shots: dict, goals: list[dict], goalies: list[dict], periods: list[str]) -> dict[str, dict]:
    """Infer full-period goalie stints when one ordering fits minutes and shots."""
    plans = {}
    for team in (game["away_team"], game["home_team"]):
        played = [g for g in goalies if g.get("team") == team and _seconds(g.get("minutes", "")) not in (0, 10**9)]
        if len(played) < 2 or len(played) > len(periods):
            continue
        opponent = game["home_team"] if team == game["away_team"] else game["away_team"]
        opponent_shots = shots.get("home" if team == game["away_team"] else "away", [])[:len(periods)]
        if len(opponent_shots) < len(periods) or not all(str(value).isdigit() for value in opponent_shots):
            continue
        period_lengths = [_period_length(period) for period in periods]
        valid = []
        for ordering in permutations(played):
            period_cursor = 0
            stints = []
            fits = True
            for goalie in ordering:
                duration = _seconds(goalie.get("minutes", ""))
                start_period = period_cursor
                covered = 0
                while period_cursor < len(periods) and covered < duration:
                    covered += period_lengths[period_cursor]
                    period_cursor += 1
                if covered != duration:
                    fits = False
                    break
                expected_sa = sum(int(value) for value in opponent_shots[start_period:period_cursor])
                shots_faced = _goalie_shots_faced(goalie)
                if shots_faced is None or expected_sa != shots_faced:
                    fits = False
                    break
                stints.append({
                    "goalie": goalie,
                    "start": start_period,
                    "end": period_cursor,
                    "shots_faced": shots_faced,
                    "matched_shots": expected_sa,
                })
            if fits and period_cursor == len(periods):
                valid.append(stints)
        if len(valid) == 1:
            plans[team] = {"stints": valid[0], "inferred": True, "opponent": opponent}
    return plans


def _goalie_steps(game: dict, goalies: list[dict], goalie_plans: dict[str, dict]) -> list[dict]:
    steps = []
    for team in (game["away_team"], game["home_team"]):
        team_goalies = [g for g in goalies if g.get("team") == team]
        played = [g for g in team_goalies if g.get("minutes") != "0:00"]
        plan = goalie_plans.get(team)
        if plan:
            stints = plan["stints"]
            starter_stint = stints[0]
            starter = starter_stint["goalie"]
            covered_periods = [goalie_plans[team]["periods"][i] for i in range(starter_stint["start"], starter_stint["end"])]
            period_text = " and ".join(_period_label(period) for period in covered_periods)
            changes = "\n".join(
                f"Goalie change: #{stint['goalie']['number']} {stint['goalie']['name']} starts {_period_label(stint_period)}."
                for stint in stints[1:]
                for stint_period in [goalie_plans[team]["periods"][stint["start"]]]
            )
            body = (
                "INFERRED STARTER — VERIFIED BY MINUTES AND SHOTS\n\n"
                f"#{starter['number']} {starter['name']}\n"
                f"Played {starter['minutes']} · {starter_stint['shots_faced']} shots faced · "
                f"{starter.get('goals_against', '—')} GA\n\n"
                f"Why: {starter['minutes']} exactly covers {period_text}, and "
                f"{starter_stint['shots_faced']} shots faced (saves + goals allowed) matches "
                f"{plan['opponent']}'s {starter_stint['matched_shots']} shots in those periods.\n\n"
                f"{changes}"
            )
        elif len(played) == 1:
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
            "title": "Starting Goalie — Inferred" if plan else "Starting Goalie",
            "kind": "goalie-start",
            "team": team,
            "body": body,
        })
    return steps


def _goalie_change_steps(goalie_plans: dict[str, dict], period: str) -> list[dict]:
    steps = []
    for team, plan in goalie_plans.items():
        for stint in plan["stints"][1:]:
            start_period = plan["periods"][stint["start"]]
            if not _same_period(start_period, period):
                continue
            goalie = stint["goalie"]
            steps.append({
                "title": f"GOALIE CHANGE — {_period_label(period).upper()}",
                "kind": "goalie-change",
                "period": period,
                "team": team,
                "body": (
                    f"⚠ CHANGE GOALIE BEFORE STARTING {_period_label(period).upper()}\n\n"
                    f"Select #{goalie['number']} {goalie['name']} for {team}.\n"
                    f"Inferred from {goalie['minutes']} played and {stint['shots_faced']} shots faced "
                    "(saves + goals allowed), matched to the opponent's period shots."
                ),
                "warning": True,
            })
    return steps


def build_entry_steps(game, shots, goals, penalties, goalies):
    goals, penalties = _mark_early_releases(goals, penalties)
    periods = list(shots.get("periods", []))
    for event in [*goals, *penalties]:
        period = event.get("period")
        if period and not any(_same_period(period, existing) for existing in periods):
            periods.append(period)
    periods.sort(key=_period_key)

    goalie_plans = _infer_goalie_plans(game, shots, goals, goalies, periods)
    for plan in goalie_plans.values():
        plan["periods"] = periods

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
    steps.extend(_goalie_steps(game, goalies, goalie_plans))

    running_score = {game["away_team"]: 0, game["home_team"]: 0}

    for period_index, period in enumerate(periods):
        steps.extend(_goalie_change_steps(goalie_plans, period))
        events = []
        events.extend(("goal", goal) for goal in goals if _same_period(goal.get("period", ""), period))
        events.extend(("penalty", penalty) for penalty in penalties if _same_period(penalty.get("period", ""), period))
        # SportsEngine timestamps are elapsed time, so ascending order is chronological.
        events.sort(key=lambda item: (_seconds(item[1].get("elapsed", "")), 0 if item[0] == "penalty" else 1))

        for event_number, (kind, event) in enumerate(events, start=1):
            if kind == "goal":
                warning = ""
                warning_card = False
                scoring_team = event.get("team", "")
                if scoring_team in running_score:
                    running_score[scoring_team] += 1

                special_instructions = []
                strength_text = event.get("strength", "").lower()
                if "empty net" in strength_text:
                    opponent = game["home_team"] if scoring_team == game["away_team"] else game["away_team"]
                    pull_time = _goalie_pull_time(event.get("remaining", ""))
                    special_instructions.append(
                        "⚠ EMPTY-NET GOAL — GOALIE CHANGE REQUIRED\n"
                        f"Set {opponent}'s goalie to EMPTY NET at {pull_time} remaining.\n"
                        f"After entering the goal, put {opponent}'s goalie BACK IN NET at "
                        f"{event.get('remaining', 'the goal time')} remaining."
                    )
                    warning_card = True

                if "penalty shot" in strength_text:
                    opponent = game["home_team"] if scoring_team == game["away_team"] else game["away_team"]
                    event_time = event.get("remaining", "Confirm in GameSheet")
                    special_instructions.append(
                        "⚠ PENALTY SHOT — GOALIE TIMING REQUIRED\n"
                        f"Set {opponent}'s goalie Off at {event_time} remaining AND "
                        f"Back On at {event_time} remaining."
                    )
                    warning_card = True

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
                special_text = "\n\n" + "\n\n".join(special_instructions) if special_instructions else ""
                body = (
                    f"Time Remaining: {event['remaining']}\n"
                    f"Scorer: {event['scorer']}\n"
                    f"Assists: {', '.join(event.get('assists', [])) or 'None'}\n"
                    f"Strength: {event.get('strength', 'unknown')}\n\n"
                    f"SCORE NOW: {game['away_team']} {running_score[game['away_team']]}, "
                    f"{game['home_team']} {running_score[game['home_team']]}"
                    f"{warning}"
                    f"{special_text}"
                )
                title = "Empty-Net Goal" if "empty net" in strength_text else "Penalty-Shot Goal" if "penalty shot" in strength_text else "Goal"
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

                penalty_type, duration = _penalty_card_details(event)
                on_line = f"{on_time} remaining" if on_time else "Not applicable / confirm in GameSheet"
                body = (
                    f"Off Ice Time: {event['remaining']} remaining\n"
                    f"Duration: {duration}\n"
                    f"Penalty Type: {penalty_type}\n"
                    f"Player: {event['player']}\n"
                    f"On Ice Time: {on_line}"
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
                "warning": bool(event.get("release_at") or event.get("release_player") or event.get("release_review") or (kind == "goal" and warning_card)),
            })

        shot_index = next((i for i, p in enumerate(shots.get("periods", [])) if _same_period(p, period)), None)
        if shot_index is not None:
            steps.append(_shot_step(shots, period, shot_index))

        if period_index + 1 < len(periods):
            next_period = periods[period_index + 1]
            steps.append({
                "title": f"MOVE TO {_period_label(next_period).upper()} NOW",
                "kind": "period-transition",
                "team": "",
                "body": (
                    f"⚠ STOP — MOVE GAMESHEET TO {_period_label(next_period).upper()} NOW ⚠\n\n"
                    "Do not enter the next event until the period has been changed in GameSheet."
                ),
                "warning": True,
            })

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
