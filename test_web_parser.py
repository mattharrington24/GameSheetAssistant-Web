from pathlib import Path
from web_parser import SportsEngineParser, _normalize_overtime_goalie_minutes, _resolve_missing_period_shots

FIXTURES = Path(__file__).parent / "test_fixtures"


def test_all_saved_fixtures_parse():
    files = sorted(FIXTURES.glob("*.html"))
    assert len(files) == 8
    for path in files:
        data = SportsEngineParser.from_html(path.read_text(encoding="utf-8")).parse_all()
        assert int(data["game"]["away_score"]) + int(data["game"]["home_score"]) == len(data["goals"]), path.name
        assert data["workflow"], path.name
        assert all(check["ok"] for check in data["validation"]), path.name


def test_missing_period_shots_are_inferred_from_game_total():
    assert _resolve_missing_period_shots(["3", "3", "-", "6"], 3) == ["3", "3", "0", "6"]


def _goalie(team, minutes="51:00"):
    return {"team": team, "number": "30", "name": "Goalie", "minutes": minutes}


def test_overtime_tie_normalizes_single_goalies_to_59_minutes():
    game = {"status": "FINAL/OT", "away_team": "Away", "home_team": "Home", "away_score": "3", "home_score": "3"}
    shots = {"periods": ["1", "2", "3", "OT1"]}
    result = _normalize_overtime_goalie_minutes(game, shots, [], [_goalie("Away"), _goalie("Home")])
    assert [goalie["minutes"] for goalie in result] == ["59:00", "59:00"]


def test_overtime_winner_uses_elapsed_time_of_winning_goal():
    game = {"status": "FINAL/OT", "away_team": "Away", "home_team": "Home", "away_score": "4", "home_score": "3"}
    shots = {"periods": ["1", "2", "3", "OT1"]}
    goals = [{"period": "OT", "elapsed": "3:08"}]
    result = _normalize_overtime_goalie_minutes(game, shots, goals, [_goalie("Away"), _goalie("Home")])
    assert [goalie["minutes"] for goalie in result] == ["54:08", "54:08"]


def test_overtime_normalization_does_not_overwrite_existing_or_split_minutes():
    game = {"status": "FINAL/OT", "away_team": "Away", "home_team": "Home", "away_score": "2", "home_score": "2"}
    shots = {"periods": ["1", "2", "3", "OT1"]}
    goalies = [_goalie("Away", "59:00"), _goalie("Home", "34:00"), _goalie("Home", "17:00")]
    result = _normalize_overtime_goalie_minutes(game, shots, [], goalies)
    assert [goalie["minutes"] for goalie in result] == ["59:00", "34:00", "17:00"]
