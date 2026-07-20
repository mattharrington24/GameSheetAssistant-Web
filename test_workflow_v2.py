from workflow import build_entry_steps


def sample_game():
    return {"away_team":"Away","away_score":"1","home_team":"Home","home_score":"1","date":"Today","venue":"Arena"}


def sample_shots():
    return {"periods":["1st","2nd","3rd"],"away_team":"Away","away":["8","9","7","24"],"home_team":"Home","home":["6","10","8","24"]}


def test_period_events_are_chronological_and_shots_are_last():
    goals=[{"period":"1st","elapsed":"7:00","remaining":"10:00","team":"Away","scorer":"#1 A","strength":"even strength","assists":[]}]
    penalties=[{"period":"1st","elapsed":"3:00","remaining":"14:00","team":"Home","player":"#2 B","penalty":"Tripping - Minor (2:00)"}]
    steps=build_entry_steps(sample_game(),sample_shots(),goals,penalties,[])
    first=[s for s in steps if s.get("period")=="1st"]
    assert [s["kind"] for s in first]==["penalty","goal","shots"]


def test_starting_goalies_are_before_period_events():
    goalies=[{"team":"Away","number":"30","name":"A Goalie","minutes":"51:00","shots_against":"10","goals_against":"1","saves":"9"},
             {"team":"Home","number":"31","name":"H Goalie","minutes":"51:00","shots_against":"12","goals_against":"1","saves":"11"}]
    steps=build_entry_steps(sample_game(),sample_shots(),[],[],goalies)
    assert [s["kind"] for s in steps[:3]]==["game-info","goalie-start","goalie-start"]
    assert steps[1]["team"]=="Away" and steps[2]["team"]=="Home"


def test_pp_goal_marks_minor_for_early_release():
    goals=[{"period":"1st","elapsed":"10:00","remaining":"7:00","team":"Away","scorer":"#1 A","strength":"power play","assists":[]}]
    penalties=[{"period":"1st","elapsed":"9:32","remaining":"7:28","team":"Home","player":"#2 B","penalty":"Tripping - Minor (2:00)"}]
    steps=build_entry_steps(sample_game(),sample_shots(),goals,penalties,[])
    penalty=next(s for s in steps if s["kind"]=="penalty")
    goal=next(s for s in steps if s["kind"]=="goal")
    assert "Set Back On Ice to 7:00" in penalty["body"]
    assert "You need to set the On time to 7:00 for this specific penalty" in goal["body"]
    assert "#2 B — Tripping - Minor (2:00)" in goal["body"]
    assert "Off: 7:28" in goal["body"]
    assert "On: 7:00" in goal["body"]
    assert penalty["warning"] and goal["warning"]


def test_missing_shots_stay_safe():
    shots=sample_shots(); shots["away"][0]="-"
    steps=build_entry_steps(sample_game(),shots,[],[],[])
    shot=next(s for s in steps if s.get("period")=="1st" and s["kind"]=="shots")
    assert "Away: -" in shot["body"]
    assert "Leader: Not available" in shot["body"]


def test_pp_goal_with_two_active_minors_releases_earliest_penalty():
    goals=[{"period":"2nd","elapsed":"5:28","remaining":"11:32","team":"Home","scorer":"#55 Ashley Wagenbach","strength":"power play","assists":[]}]
    penalties=[
        {"period":"2nd","elapsed":"4:30","remaining":"12:30","team":"Away","player":"#8 First Penalty","penalty":"Tripping - Minor (2:00)"},
        {"period":"2nd","elapsed":"5:00","remaining":"12:00","team":"Away","player":"#12 Second Penalty","penalty":"Hooking - Minor (2:00)"},
    ]
    steps=build_entry_steps(sample_game(),sample_shots(),goals,penalties,[])
    goal=next(s for s in steps if s["kind"]=="goal")
    penalty_steps=[s for s in steps if s["kind"]=="penalty"]
    first=next(s for s in penalty_steps if "#8 First Penalty" in s["body"])
    second=next(s for s in penalty_steps if "#12 Second Penalty" in s["body"])

    assert "You need to set the On time to 11:32 for this specific penalty" in goal["body"]
    assert "#8 First Penalty" in goal["body"]
    assert "REVIEW RELEASE TIME" not in goal["body"]
    assert "Set Back On Ice to 11:32" in first["body"]
    assert "Set Back On Ice" not in second["body"]


def test_simultaneous_earliest_minors_still_require_review():
    goals=[{"period":"2nd","elapsed":"5:28","remaining":"11:32","team":"Home","scorer":"#55 Ashley Wagenbach","strength":"power play","assists":[]}]
    penalties=[
        {"period":"2nd","elapsed":"4:30","remaining":"12:30","team":"Away","player":"#8 A","penalty":"Tripping - Minor (2:00)"},
        {"period":"2nd","elapsed":"4:30","remaining":"12:30","team":"Away","player":"#12 B","penalty":"Hooking - Minor (2:00)"},
    ]
    steps=build_entry_steps(sample_game(),sample_shots(),goals,penalties,[])
    goal=next(s for s in steps if s["kind"]=="goal")
    assert "REVIEW RELEASE TIME" in goal["body"]


def test_standard_minor_shows_full_two_minute_on_time():
    penalties=[{"period":"1st","elapsed":"9:00","remaining":"8:00","team":"Home","player":"#2 B","penalty":"Holding - Minor (2:00)"}]
    steps=build_entry_steps(sample_game(),sample_shots(),[],penalties,[])
    penalty=next(s for s in steps if s["kind"]=="penalty")
    assert "Off Ice: 8:00 remaining" in penalty["body"]
    assert "Back On Ice: 6:00 remaining" in penalty["body"]


def test_pp_goal_overrides_scheduled_minor_on_time():
    goals=[{"period":"1st","elapsed":"10:00","remaining":"7:00","team":"Away","scorer":"#1 A","strength":"power play","assists":[]}]
    penalties=[{"period":"1st","elapsed":"9:32","remaining":"7:28","team":"Home","player":"#2 B","penalty":"Tripping - Minor (2:00)"}]
    steps=build_entry_steps(sample_game(),sample_shots(),goals,penalties,[])
    penalty=next(s for s in steps if s["kind"]=="penalty")
    assert "Back On Ice: 7:00 remaining" in penalty["body"]
    assert "Back On Ice: 5:28" not in penalty["body"]


def test_minor_carrying_into_next_period_shows_exact_on_time():
    penalties=[{"period":"1st","elapsed":"16:11","remaining":"0:49","team":"Home","player":"#2 B","penalty":"Holding - Minor (2:00)"}]
    steps=build_entry_steps(sample_game(),sample_shots(),[],penalties,[])
    penalty=next(s for s in steps if s["kind"]=="penalty")
    assert "Back On Ice: Next period — 15:49 remaining" in penalty["body"]


def test_period_transition_is_an_unmissable_separate_step():
    steps=build_entry_steps(sample_game(),sample_shots(),[],[],[])
    first_shots=next(i for i,s in enumerate(steps) if s.get("period")=="1st" and s["kind"]=="shots")
    transition=steps[first_shots+1]
    assert transition["kind"]=="period-transition"
    assert transition["warning"]
    assert "MOVE GAMESHEET TO 2ND PERIOD NOW" in transition["body"]


def test_each_goal_shows_running_score_in_chronological_order():
    game=sample_game()
    game.update({"away_team":"Minnetonka","away_score":"3","home_team":"Edina","home_score":"2"})
    goals=[
        {"period":"1st","elapsed":"2:00","remaining":"15:00","team":"Minnetonka","scorer":"#1 A","strength":"even strength","assists":[]},
        {"period":"1st","elapsed":"4:00","remaining":"13:00","team":"Edina","scorer":"#2 B","strength":"even strength","assists":[]},
        {"period":"2nd","elapsed":"1:00","remaining":"16:00","team":"Minnetonka","scorer":"#3 C","strength":"even strength","assists":[]},
    ]
    steps=build_entry_steps(game,sample_shots(),goals,[],[])
    goal_steps=[s for s in steps if s["kind"]=="goal"]
    assert "SCORE NOW: Minnetonka 1, Edina 0" in goal_steps[0]["body"]
    assert "SCORE NOW: Minnetonka 1, Edina 1" in goal_steps[1]["body"]
    assert "SCORE NOW: Minnetonka 2, Edina 1" in goal_steps[2]["body"]


def test_empty_net_goal_shows_rounded_pull_time_and_exact_return_time():
    goals=[{"period":"3rd","elapsed":"16:39","remaining":"0:21","team":"Away","scorer":"#1 A","strength":"even strength / empty net","assists":[]}]
    steps=build_entry_steps(sample_game(),sample_shots(),goals,[],[])
    goal=next(s for s in steps if s["kind"]=="goal")
    assert goal["warning"]
    assert goal["title"].endswith("Empty-Net Goal")
    assert "Home's goalie to EMPTY NET at 1:00 remaining" in goal["body"]
    assert "BACK IN NET at 0:21 remaining" in goal["body"]


def test_empty_net_goal_at_145_uses_200_pull_time():
    goals=[{"period":"3rd","elapsed":"15:15","remaining":"1:45","team":"Home","scorer":"#2 B","strength":"empty net","assists":[]}]
    goal=next(s for s in build_entry_steps(sample_game(),sample_shots(),goals,[],[]) if s["kind"]=="goal")
    assert "Away's goalie to EMPTY NET at 2:00 remaining" in goal["body"]
    assert "BACK IN NET at 1:45 remaining" in goal["body"]


def test_penalty_shot_goal_uses_same_off_and_on_time():
    goals=[{"period":"2nd","elapsed":"6:17","remaining":"10:43","team":"Away","scorer":"#1 A","strength":"penalty shot","assists":[]}]
    goal=next(s for s in build_entry_steps(sample_game(),sample_shots(),goals,[],[]) if s["kind"]=="goal")
    assert goal["warning"]
    assert goal["title"].endswith("Penalty-Shot Goal")
    assert "Home's goalie Off at 10:43 remaining AND Back On at 10:43 remaining" in goal["body"]
