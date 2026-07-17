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
    assert "Return #2 B" in goal["body"]
    assert penalty["warning"] and goal["warning"]


def test_missing_shots_stay_safe():
    shots=sample_shots(); shots["away"][0]="-"
    steps=build_entry_steps(sample_game(),shots,[],[],[])
    shot=next(s for s in steps if s.get("period")=="1st" and s["kind"]=="shots")
    assert "Away: -" in shot["body"]
    assert "Leader: Not available" in shot["body"]
