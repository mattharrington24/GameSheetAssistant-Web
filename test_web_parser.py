from pathlib import Path
from web_parser import SportsEngineParser, _resolve_missing_period_shots

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
