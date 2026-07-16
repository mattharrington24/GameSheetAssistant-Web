from pathlib import Path
from web_parser import SportsEngineParser

FIXTURES = Path(__file__).parent / "test_fixtures"


def test_all_saved_fixtures_parse():
    files = sorted(FIXTURES.glob("*.html"))
    assert len(files) == 8
    for path in files:
        data = SportsEngineParser.from_html(path.read_text(encoding="utf-8")).parse_all()
        assert int(data["game"]["away_score"]) + int(data["game"]["home_score"]) == len(data["goals"]), path.name
        assert data["workflow"], path.name
        assert all(check["ok"] for check in data["validation"]), path.name
