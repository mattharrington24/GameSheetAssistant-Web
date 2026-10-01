from ppl_parser import _first_run_any


def test_penalty_minutes_header_with_period():
    assert _first_run_any(["Offense", "Min.", "In"], "Min.", "Min") == 1


def test_penalty_minutes_header_without_period():
    assert _first_run_any(["Offense", "Min", "In"], "Min.", "Min") == 1
