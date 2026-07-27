from roster_compare import compare_rosters, normalize_name, parse_roster


def roster_html(title, players):
    rows = "".join(
        f'<tr><td class="jersey_no">{number}</td><td class="player_name"><a href="/roster_players/{index}">{name}</a></td><td>{position}</td><td>{grade}</td></tr>'
        for index, (number, name, position, grade) in enumerate(players, 1)
    )
    return f"""<html><head><title>{title}</title></head><body>
    <table class="stat_table"><thead><tr><th>#</th><th>Name</th><th>Pos.</th><th>Grade</th></tr></thead>
    <tbody>{rows}</tbody></table></body></html>"""


def test_name_normalization():
    assert normalize_name(" Smith, Anna ") == normalize_name("Anna Smith")
    assert normalize_name("Piper  Andrews") == normalize_name("Piper Andrews")


def test_parse_and_compare_rosters():
    previous = parse_roster(roster_html("2020-21", [
        ("8", "Anna Smith", "F", "10"),
        ("12", "Grace Lee", "D", "12"),
    ]))
    current = parse_roster(roster_html("2021-22", [
        ("19", "Smith, Anna", "F", "11"),
        ("7", "Maya Jones", "G", "9"),
    ]))
    result = compare_rosters(previous, current)
    assert result["counts"] == {"previous": 2, "current": 2, "returning": 1, "new": 1, "departed": 1}
    assert result["returning"][0]["current"]["name"] == "Smith, Anna"
    assert result["new"][0]["name"] == "Maya Jones"
    assert result["departed"][0]["name"] == "Grace Lee"


def test_empty_roster_is_rejected():
    try:
        parse_roster("<html><title>No roster</title></html>")
    except ValueError as error:
        assert "No players" in str(error)
    else:
        raise AssertionError("Expected missing roster error")
