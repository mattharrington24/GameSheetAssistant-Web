import json
import subprocess
from pathlib import Path


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
                "title": "Starting Goalie — Inferred Starter",
                "body": "INFERRED STARTER — VERIFIED BY MINUTES AND SHOTS\n\n#30 Kailee Falconer",
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
