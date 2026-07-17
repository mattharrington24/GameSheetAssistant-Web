"""Build an ordered, readable GameSheet data-entry workflow."""


def build_entry_steps(game, shots, goals, penalties, goalies):
    steps = []

    steps.append({
        "title": "Game Info",
        "body": (
            f"{game['away_team']} {game['away_score']}\n"
            f"{game['home_team']} {game['home_score']}\n\n"
            f"Date: {game['date']}\n"
            f"Venue: {game['venue']}"
        ),
    })

    # Goalies are shown before shots because they are normally selected early
    # in the GameSheet scoring workflow. Goalies with 0:00 are unused backups.
    for goalie in goalies:
        if goalie["minutes"] == "0:00":
            continue

        steps.append({
            "title": "Goalie",
            "body": (
                f"Team: {goalie['team']}\n"
                f"Goalie: #{goalie['number']} {goalie['name']}\n"
                f"Minutes: {goalie['minutes']}\n"
                f"Shots Against: {goalie['shots_against']}\n"
                f"Goals Against: {goalie['goals_against']}\n"
                f"Saves: {goalie['saves']}"
            ),
        })

    def shot_comparison(label, away_value, home_value):
        def parse_shots(value):
            text = str(value).strip()
            return int(text) if text.isdigit() else None

        away_shots = parse_shots(away_value)
        home_shots = parse_shots(home_value)
        away_display = away_shots if away_shots is not None else "-"
        home_display = home_shots if home_shots is not None else "-"

        lines = [
            label,
            f"{shots['away_team']}: {away_display}",
            f"{shots['home_team']}: {home_display}",
        ]

        if away_shots is None or home_shots is None:
            lines.append("Leader: Not available")
        elif away_shots > home_shots:
            lines.append(f"Leader: {shots['away_team']} (+{away_shots - home_shots})")
        elif home_shots > away_shots:
            lines.append(f"Leader: {shots['home_team']} (+{home_shots - away_shots})")
        else:
            lines.append("Leader: Tie")

        return "\n".join(lines)

    shot_sections = []
    for index, period in enumerate(shots.get("periods", [])):
        shot_sections.append(
            shot_comparison(
                f"{period} Period",
                shots["away"][index],
                shots["home"][index],
            )
        )

    shot_sections.append(
        shot_comparison(
            "Game Total",
            shots["away"][-1],
            shots["home"][-1],
        )
    )

    steps.append({
        "title": "Shots on Goal",
        "body": "\n\n".join(shot_sections),
    })

    for number, goal in enumerate(goals, start=1):
        steps.append({
            "title": f"Goal {number} of {len(goals)}",
            "body": (
                f"Period: {goal['period']}\n"
                f"Time Remaining: {goal['remaining']}\n"
                f"Team: {goal['team']}\n"
                f"Scorer: {goal['scorer']}\n"
                f"Strength: {goal['strength']}\n"
                f"Assists: {', '.join(goal['assists']) if goal['assists'] else 'None'}"
            ),
        })

    for number, penalty in enumerate(penalties, start=1):
        steps.append({
            "title": f"Penalty {number} of {len(penalties)}",
            "body": (
                f"Period: {penalty['period']}\n"
                f"Time Remaining: {penalty['remaining']}\n"
                f"Team: {penalty['team']}\n"
                f"Player: {penalty['player']}\n"
                f"Penalty: {penalty['penalty']}"
            ),
        })

    steps.append({
        "title": "Final Check",
        "body": "Verify the final score, shots, goalies, goals, and penalties in GameSheet.",
    })

    return steps
