from roster_compare import (
    compare_rosters,
    find_transfers,
    normalize_name,
    parse_roster,
    roster_team_name,
    roster_url_for_team_page,
    season_links,
    sportsengine_team_links,
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
    assert result["counts"] == {
        "previous": 2, "current": 2, "returning": 1, "new": 1,
        "departed": 1, "possible_matches": 0,
    }
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


def test_season_link_discovery_reads_sportsengine_page_nav():
    html = """
    <script>
    var pageNav = {"name":"MSHSL","children":[
      {"name":"Lake","url":"/page/show/5878610-lake?subseason=697635","children":[]},
      {"name":"Metro West","url":"/page/show/5878649-metro-west?subseason=697635","children":[]}
    ]};
    </script>
    """
    source = "https://stats.mngirlshockeyhub.com/page/show/5878509?subseason=697635"
    assert season_links(html, source, "page") == [
        "https://stats.mngirlshockeyhub.com/page/show/5878610-lake?subseason=697635",
        "https://stats.mngirlshockeyhub.com/page/show/5878649-metro-west?subseason=697635",
    ]


def test_team_nav_links_and_roster_pairing():
    html = """
    <script>
    var pageNav = {"node_type":"DivisionInstance","children":[
      {"node_type":"TeamInstance","url":"/page/show/5878655-holy-angels?subseason=697635","children":[]}
    ]};
    </script>
    """
    source = "https://stats.mngirlshockeyhub.com/page/show/5878649?subseason=697635"
    teams = sportsengine_team_links(html, source)
    assert teams == [
        "https://stats.mngirlshockeyhub.com/page/show/5878655-holy-angels?subseason=697635"
    ]
    assert roster_url_for_team_page(teams[0]) == (
        "https://stats.mngirlshockeyhub.com/roster/show/5878656?subseason=697635"
    )


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


def test_known_nickname_alias_is_returning():
    previous = parse_roster(roster_html("Andover - 2020-21", [
        ("6", "Isa Goettl", "F", "10"),
    ]))
    current = parse_roster(roster_html("Andover - 2021-22", [
        ("6", "Isabel Goettl", "F", "11"),
    ]))
    result = compare_rosters(previous, current)
    assert result["counts"]["returning"] == 1
    assert result["counts"]["new"] == 0
    assert result["counts"]["departed"] == 0


def test_similar_same_last_name_is_suggested_then_custom_alias_matches():
    previous = parse_roster(roster_html("Example - 2020-21", [
        ("4", "Madi Nelson", "D", "9"),
    ]))
    current = parse_roster(roster_html("Example - 2021-22", [
        ("4", "Madison Nelson", "D", "10"),
    ]))
    suggested = compare_rosters(previous, current)
    assert suggested["counts"]["possible_matches"] == 1
    matched = compare_rosters(
        previous,
        current,
        [{"previous": "Madi Nelson", "current": "Madison Nelson"}],
    )
    assert matched["counts"]["returning"] == 1


def test_all_unmatched_shared_last_names_need_review_even_when_first_names_differ():
    previous = parse_roster(roster_html("Example - 2020-21", [
        ("4", "Izzy Carter", "F", "9"),
        ("8", "Mia Carter", "D", "11"),
    ]))
    current = parse_roster(roster_html("Example - 2021-22", [
        ("4", "Elizabeth Carter", "F", "10"),
        ("9", "Sophia Carter", "D", "9"),
    ]))
    result = compare_rosters(previous, current)
    pairs = {
        (item["previous"]["name"], item["current"]["name"])
        for item in result["possible_matches"]
    }
    assert pairs == {
        ("Izzy Carter", "Elizabeth Carter"),
        ("Izzy Carter", "Sophia Carter"),
        ("Mia Carter", "Elizabeth Carter"),
        ("Mia Carter", "Sophia Carter"),
    }
