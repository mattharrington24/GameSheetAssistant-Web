import os

os.environ.setdefault("APP_PASSWORD", "test-password")
os.environ.setdefault("SECRET_KEY", "test-secret")

import app as app_module


def test_health_is_public():
    client = app_module.app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["ok"] is True


def test_index_requires_login():
    client = app_module.app.test_client()
    response = client.get("/")
    assert response.status_code == 302
    assert "/login" in response.location


def test_login_allows_index():
    client = app_module.app.test_client()
    response = client.post("/login", data={"password": "test-password"}, follow_redirects=True)
    assert response.status_code == 200
    assert b"GameSheet Assistant" in response.data


def test_shot_workflow_labels_teams_and_leader():
    from workflow import build_entry_steps

    game = {
        "away_team": "Away Team",
        "away_score": "2",
        "home_team": "Home Team",
        "home_score": "1",
        "date": "Test Date",
        "venue": "Test Arena",
    }
    shots = {
        "periods": ["1st", "2nd", "3rd"],
        "away_team": "Away Team",
        "away": ["10", "5", "7", "22"],
        "home_team": "Home Team",
        "home": ["8", "5", "9", "22"],
    }

    steps = build_entry_steps(game, shots, [], [], [])
    shot_step = next(step for step in steps if step["title"] == "Shots on Goal")

    assert "Away Team: 10" in shot_step["body"]
    assert "Home Team: 8" in shot_step["body"]
    assert "Leader: Away Team (+2)" in shot_step["body"]
    assert "Leader: Tie" in shot_step["body"]
    assert "Leader: Home Team (+2)" in shot_step["body"]
    assert "Game Total" in shot_step["body"]


def test_workflow_handles_missing_shot_values():
    from workflow import build_entry_steps

    game = {
        "away_team": "Away",
        "home_team": "Home",
        "away_score": "0",
        "home_score": "0",
        "date": "",
        "venue": "",
    }
    shots = {
        "away_team": "Away",
        "home_team": "Home",
        "periods": ["1st", "2nd", "3rd"],
        "away": ["-", "5", "4", "-"],
        "home": ["3", "-", "4", "-"],
    }

    steps = build_entry_steps(game, shots, [], [], [])
    shot_step = next(step for step in steps if step["title"] == "Shots on Goal")

    assert "Away: -" in shot_step["body"]
    assert "Home: -" in shot_step["body"]
    assert "Leader: Not available" in shot_step["body"]
    assert "Leader: Tie" in shot_step["body"]
