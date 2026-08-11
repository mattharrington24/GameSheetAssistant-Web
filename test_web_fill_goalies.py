import json
import subprocess
from pathlib import Path

from workflow import _goalie_steps


ROOT = Path(__file__).resolve().parent


def test_web_fill_uses_workflow_starter_to_resolve_ambiguous_goalie_order():
    source = (ROOT / "static" / "app.js").read_text()
    source = source.split("async function copyWebFillData", 1)[0]
    data = {
        "game": {
            "away_team": "St. Cloud",
            "home_team": "Opponent",
            "away_score": 1,
            "home_score": 2,
        },
        "shots": {"periods": ["1", "2", "3"], "away": [4, 4, 4], "home": [5, 7, 5]},
        "goals": [],
        "penalties": [],
        # SportsEngine lists Stevens first even though the workflow has already
        # inferred Falconer as the starter. Equal first/third-period shot totals
        # make both goalie orders mathematically valid.
        "goalies": [
            {"team": "St. Cloud", "number": "1", "name": "Abby Stevens", "minutes": "17:00", "saves": "5", "goals_against": "0"},
            {"team": "St. Cloud", "number": "30", "name": "Kailee Falconer", "minutes": "34:00", "saves": "10", "goals_against": "2"},
            {"team": "Opponent", "number": "35", "name": "Other Goalie", "minutes": "51:00", "saves": "11", "goals_against": "1"},
        ],
        "workflow": [
            {
                "kind": "goalie-start",
                "team": "St. Cloud",
                "title": "Starting Goalie — Inferred",
                "body": "INFERRED ORDER — VERIFIED BY MINUTES AND SHOTS\n\n#30 Kailee Falconer",
                "starter_number": "30",
                "goalie_stints": [
                    {"number": "30", "name": "Kailee Falconer", "start": 0, "end": 2},
                    {"number": "1", "name": "Abby Stevens", "start": 2, "end": 3},
                ],
            }
        ],
        "source_url": "fixture",
    }
    script = source + f"\nstate.data={json.dumps(data)};console.log(JSON.stringify(buildWebFillPayload().goalie_shifts));"
    result = subprocess.run(["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True)
    shifts = json.loads(result.stdout)
    st_cloud = [row for row in shifts if row["team"] == "St. Cloud"]

    assert st_cloud[0]["period"] == "1"
    assert st_cloud[0]["goalie"] == "#30 Kailee Falconer"
    assert st_cloud[1]["period"] == "3"
    assert st_cloud[1]["goalie"] == "#1 Abby Stevens"


def test_web_fill_preserves_verified_starter_order_for_both_teams():
    source = (ROOT / "static" / "app.js").read_text().split("async function copyWebFillData", 1)[0]
    data = {
        "game": {"away_team": "Princeton/Big Lake/Becker", "home_team": "Chisago Lakes", "away_score": 1, "home_score": 2},
        "shots": {"periods": ["1", "2", "3"], "away": [5, 7, 4], "home": [6, 8, 3]},
        "goals": [], "penalties": [], "source_url": "fixture",
        "goalies": [
            {"team": "Princeton/Big Lake/Becker", "number": "1", "name": "Mackenzie Dembinski", "minutes": "17:00", "saves": "3", "goals_against": "0"},
            {"team": "Princeton/Big Lake/Becker", "number": "33", "name": "Shelby Ulm", "minutes": "34:00", "saves": "11", "goals_against": "2"},
            {"team": "Chisago Lakes", "number": "1", "name": "Breanna Ritter", "minutes": "17:00", "saves": "3", "goals_against": "0"},
            {"team": "Chisago Lakes", "number": "40", "name": "Anna Hanson", "minutes": "34:00", "saves": "11", "goals_against": "1"},
        ],
        "workflow": [
            {"kind": "goalie-start", "team": "Princeton/Big Lake/Becker", "title": "Starting Goalie — Inferred", "body": "#33 Shelby Ulm", "starter_number": "33", "goalie_stints": [
                {"number": "33", "name": "Shelby Ulm", "start": 0, "end": 2},
                {"number": "1", "name": "Mackenzie Dembinski", "start": 2, "end": 3},
            ]},
            {"kind": "goalie-start", "team": "Chisago Lakes", "title": "Starting Goalie — Inferred", "body": "#40 Anna Hanson", "starter_number": "40", "goalie_stints": [
                {"number": "40", "name": "Anna Hanson", "start": 0, "end": 2},
                {"number": "1", "name": "Breanna Ritter", "start": 2, "end": 3},
            ]},
        ],
    }
    script = source + f"\nstate.data={json.dumps(data)};console.log(JSON.stringify(buildWebFillPayload().goalie_shifts));"
    result = subprocess.run(["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True)
    shifts = json.loads(result.stdout)

    princeton = [row for row in shifts if row["team"] == "Princeton/Big Lake/Becker"]
    chisago = [row for row in shifts if row["team"] == "Chisago Lakes"]
    assert [(row["period"], row["goalie"]) for row in princeton] == [("1", "#33 Shelby Ulm"), ("3", "#1 Mackenzie Dembinski")]
    assert [(row["period"], row["goalie"]) for row in chisago] == [("1", "#40 Anna Hanson"), ("3", "#1 Breanna Ritter")]


def test_web_fill_repairs_stale_reversed_workflow_goalie_order():
    source = (ROOT / "static" / "app.js").read_text().split("async function copyWebFillData", 1)[0]
    data = {
        "game": {"away_team": "Princeton/Big Lake/Becker", "home_team": "Chisago Lakes", "away_score": 1, "home_score": 2},
        # Matching first/third totals are the condition that previously let
        # SportsEngine's non-chronological goalie list reverse both teams.
        "shots": {"periods": ["1", "2", "3"], "away": [5, 7, 5], "home": [6, 8, 6]},
        "goals": [], "penalties": [], "source_url": "fixture",
        "goalies": [
            {"team": "Princeton/Big Lake/Becker", "number": "1", "name": "Mackenzie Dembinski", "minutes": "17:00", "saves": "5", "goals_against": "1"},
            {"team": "Princeton/Big Lake/Becker", "number": "33", "name": "Shelby Ulm", "minutes": "34:00", "saves": "12", "goals_against": "2"},
            {"team": "Chisago Lakes", "number": "1", "name": "Breanna Ritter", "minutes": "17:00", "saves": "4", "goals_against": "1"},
            {"team": "Chisago Lakes", "number": "40", "name": "Anna Hanson", "minutes": "34:00", "saves": "9", "goals_against": "3"},
        ],
        # Simulate a game already saved in browser state by an older release.
        "workflow": [
            {"kind": "goalie-start", "team": "Princeton/Big Lake/Becker", "title": "Starting Goalie — Inferred", "starter_number": "1", "goalie_stints": [
                {"number": "1", "start": 0, "end": 1}, {"number": "33", "start": 1, "end": 3},
            ]},
            {"kind": "goalie-start", "team": "Chisago Lakes", "title": "Starting Goalie — Inferred", "starter_number": "1", "goalie_stints": [
                {"number": "1", "start": 0, "end": 1}, {"number": "40", "start": 1, "end": 3},
            ]},
        ],
    }
    script = source + f"\nstate.data={json.dumps(data)};console.log(JSON.stringify(buildWebFillPayload().goalie_shifts));"
    result = subprocess.run(["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True)
    shifts = json.loads(result.stdout)

    assert [(row["period"], row["goalie"]) for row in shifts if row["team"] == data["game"]["away_team"]] == [
        ("1", "#33 Shelby Ulm"), ("3", "#1 Mackenzie Dembinski")
    ]
    assert [(row["period"], row["goalie"]) for row in shifts if row["team"] == data["game"]["home_team"]] == [
        ("1", "#40 Anna Hanson"), ("3", "#1 Breanna Ritter")
    ]


def test_web_fill_does_not_override_current_verified_goalie_order():
    source = (ROOT / "static" / "app.js").read_text().split("async function copyWebFillData", 1)[0]
    data = {
        "game": {"away_team": "Princeton/Big Lake/Becker", "home_team": "Chisago Lakes", "away_score": 1, "home_score": 2},
        "shots": {"periods": ["1", "2", "3"], "away": [5, 7, 5], "home": [6, 8, 6]},
        "goals": [], "penalties": [], "source_url": "fixture",
        "goalies": [
            {"team": "Princeton/Big Lake/Becker", "number": "1", "name": "Mackenzie Dembinski", "minutes": "34:00", "saves": "12", "goals_against": "2"},
            {"team": "Princeton/Big Lake/Becker", "number": "33", "name": "Shelby Ulm", "minutes": "17:00", "saves": "5", "goals_against": "1"},
            {"team": "Chisago Lakes", "number": "1", "name": "Breanna Ritter", "minutes": "34:00", "saves": "9", "goals_against": "3"},
            {"team": "Chisago Lakes", "number": "40", "name": "Anna Hanson", "minutes": "17:00", "saves": "4", "goals_against": "1"},
        ],
        "workflow": [
            {"kind": "goalie-start", "team": "Princeton/Big Lake/Becker", "starter_number": "33", "goalie_plan_basis": "verified by minutes and period shots", "goalie_stints": [
                {"number": "33", "name": "Shelby Ulm", "start": 0, "end": 2},
                {"number": "1", "name": "Mackenzie Dembinski", "start": 2, "end": 3},
            ]},
            {"kind": "goalie-start", "team": "Chisago Lakes", "starter_number": "40", "goalie_plan_basis": "verified by minutes and period shots", "goalie_stints": [
                {"number": "40", "name": "Anna Hanson", "start": 0, "end": 2},
                {"number": "1", "name": "Breanna Ritter", "start": 2, "end": 3},
            ]},
        ],
    }
    script = source + f"\nstate.data={json.dumps(data)};console.log(JSON.stringify(buildWebFillPayload().goalie_shifts));"
    result = subprocess.run(["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True)
    shifts = json.loads(result.stdout)

    assert [(row["period"], row["goalie"]) for row in shifts if row["team"] == data["game"]["away_team"]] == [
        ("1", "#33 Shelby Ulm"), ("3", "#1 Mackenzie Dembinski")
    ]
    assert [(row["period"], row["goalie"]) for row in shifts if row["team"] == data["game"]["home_team"]] == [
        ("1", "#40 Anna Hanson"), ("3", "#1 Breanna Ritter")
    ]


def test_goalie_steps_export_the_verified_plan_as_structured_data():
    game = {"away_team": "Princeton/Big Lake/Becker", "home_team": "Chisago Lakes"}
    ulm = {"team": game["away_team"], "number": "33", "name": "Shelby Ulm", "minutes": "34:00", "goals_against": "2"}
    dembinski = {"team": game["away_team"], "number": "1", "name": "Mackenzie Dembinski", "minutes": "17:00", "goals_against": "0"}
    hanson = {"team": game["home_team"], "number": "40", "name": "Anna Hanson", "minutes": "34:00", "goals_against": "1"}
    ritter = {"team": game["home_team"], "number": "1", "name": "Breanna Ritter", "minutes": "17:00", "goals_against": "0"}

    def plan(starter, replacement, opponent):
        return {
            "periods": ["1", "2", "3"],
            "opponent": opponent,
            "basis": "verified fixture",
            "stints": [
                {"goalie": starter, "start": 0, "end": 2, "shots_faced": 12, "matched_shots": 12},
                {"goalie": replacement, "start": 2, "end": 3, "shots_faced": 4, "matched_shots": 4},
            ],
        }

    steps = _goalie_steps(game, [dembinski, ulm, ritter, hanson], {
        game["away_team"]: plan(ulm, dembinski, game["home_team"]),
        game["home_team"]: plan(hanson, ritter, game["away_team"]),
    })
    by_team = {step["team"]: step for step in steps}

    assert by_team[game["away_team"]]["starter_number"] == "33"
    assert [stint["number"] for stint in by_team[game["away_team"]]["goalie_stints"]] == ["33", "1"]
    assert by_team[game["home_team"]]["starter_number"] == "40"
    assert [stint["number"] for stint in by_team[game["home_team"]]["goalie_stints"]] == ["40", "1"]
