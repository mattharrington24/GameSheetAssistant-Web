from roster_compare import (
    compare_rosters,
    find_transfers,
    normalize_name,
    parse_roster,
    roster_team_name,
    season_links,
)


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


def test_season_link_discovery_keeps_subseason():
    html = """
    <a href="/page/show/111-breck?subseason=697635">Breck</a>
    <a href="/page/show/222-other?subseason=999999">Other year</a>
    <a href="/roster/show/333">Roster</a>
    """
    source = "https://stats.mngirlshockeyhub.com/page/show/1?subseason=697635"
    assert season_links(html, source, "page") == [
        "https://stats.mngirlshockeyhub.com/page/show/111-breck?subseason=697635"
    ]
    assert season_links(html, source, "roster") == [
        "https://stats.mngirlshockeyhub.com/roster/show/333?subseason=697635"
    ]


def test_team_name_from_sportsengine_title():
    assert roster_team_name("Breck - 2020-21 Regular & Postseason") == "Breck"
    assert roster_team_name("Minnetonka - MN Girls' Hockey Hub") == "Minnetonka"


def test_transfer_finder_confirms_ava_lindsay():
    previous = [{"team": "Breck", "source_url": "old", "players": [
        {"name": "Ava Lindsay", "number": "9", "position": "F", "grade": "10"}
    ]}]
    current = [{"team": "Minnetonka", "source_url": "new", "players": [
        {"name": "Ava Lindsay", "number": "11", "position": "F", "grade": "11"}
    ]}]
    result = find_transfers(previous, current)
    assert result["ava_lindsay_found"] is True
    assert result["transfers"][0]["previous_team"] == "Breck"
    assert result["transfers"][0]["current_team"] == "Minnetonka"
