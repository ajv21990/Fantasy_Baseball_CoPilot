import json
import os
import streamlit as st
from espn_api.baseball import League

_LEAGUES_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "leagues.json")


def load_leagues() -> list[dict]:
    with open(_LEAGUES_PATH) as f:
        return json.load(f)


@st.cache_resource(ttl=3600, show_spinner=False)
def get_league(league_id: int, year: int, espn_s2: str, swid: str) -> League:
    from espn_api.baseball.box_score import BoxScore, H2HCategoryBoxScore
    league = League(league_id=league_id, year=year, espn_s2=espn_s2, swid=swid)
    # ESPN sometimes returns scoring types not in the library's map (e.g. 'H2H_MOST_CATEGORIES'),
    # which falls back to the abstract BoxScore and crashes box_scores(). Force the concrete class.
    if league._box_score_class is BoxScore:
        league._box_score_class = H2HCategoryBoxScore
    return league


def get_my_team(league: League, my_team_name: str):
    if not my_team_name:
        return None
    name_lower = my_team_name.lower()
    for team in league.teams:
        if name_lower in team.team_name.lower():
            return team
    return None


def get_team_by_name(league: League, team_name: str):
    for team in league.teams:
        if team.team_name == team_name:
            return team
    return None
