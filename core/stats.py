import streamlit as st
from core import utils


@st.cache_data(ttl=300, show_spinner=False)
def fetch_team_season_stats(_league) -> dict:
    """Aggregate season stats per team by summing player roster season totals."""
    team_stats = {}
    for team in _league.teams:
        b = {"R": 0.0, "HR": 0.0, "RBI": 0.0, "SB": 0.0}
        p = {"K": 0.0, "W": 0.0, "SV": 0.0}
        ab_total, ops_weighted = 0.0, 0.0
        er_total, outs_total, h_allowed, bb_allowed = 0.0, 0.0, 0.0, 0.0

        for player in getattr(team, "roster", []):
            raw = getattr(player, "stats", {}) or {}
            bd = raw.get(0, {})
            if isinstance(bd, dict):
                bd = bd.get("breakdown", {})
            if not isinstance(bd, dict):
                continue
            if utils.is_pitcher(player):
                p["K"]  += bd.get("K",  0) or 0
                p["W"]  += bd.get("W",  0) or 0
                p["SV"] += bd.get("SV", 0) or 0
                er_total   += bd.get("ER",   0) or 0
                outs_total += bd.get("OUTS", 0) or 0
                h_allowed  += bd.get("P_H",  0) or 0
                bb_allowed += bd.get("P_BB", 0) or 0
            else:
                b["R"]   += bd.get("R",   0) or 0
                b["HR"]  += bd.get("HR",  0) or 0
                b["RBI"] += bd.get("RBI", 0) or 0
                b["SB"]  += bd.get("SB",  0) or 0
                ab = bd.get("AB", 0) or 0
                ab_total += ab
                ops_weighted += (bd.get("OPS", 0) or 0) * ab

        ip = outs_total / 3 if outs_total > 0 else 0
        team_stats[team.team_name] = {
            "R":    int(b["R"]),
            "HR":   int(b["HR"]),
            "RBI":  int(b["RBI"]),
            "SB":   int(b["SB"]),
            "OPS":  round(ops_weighted / ab_total, 3) if ab_total > 0 else None,
            "K":    int(p["K"]),
            "W":    int(p["W"]),
            "SV":   int(p["SV"]),
            "ERA":  round((er_total / ip) * 9, 2) if ip >= 1 else None,
            "WHIP": round((h_allowed + bb_allowed) / ip, 3) if ip >= 1 else None,
        }
    return team_stats


@st.cache_data(ttl=300, show_spinner=False)
def fetch_category_wins(_league, current_period: int) -> dict:
    """Aggregate category wins per team across all completed matchup periods."""
    totals: dict[str, dict[str, int]] = {}

    for period in range(1, current_period + 1):
        try:
            box_scores = _league.box_scores(matchup_period=period)
        except Exception:
            continue

        for box in box_scores:
            sides = []
            if hasattr(box, "home_team") and box.home_team:
                sides.append((box.home_team.team_name, getattr(box, "home_stats", {})))
            if hasattr(box, "away_team") and box.away_team:
                sides.append((box.away_team.team_name, getattr(box, "away_stats", {})))

            for team_name, stats in sides:
                if team_name not in totals:
                    totals[team_name] = {}
                for cat, data in stats.items():
                    result = data.get("result", "") if isinstance(data, dict) else ""
                    if cat not in totals[team_name]:
                        totals[team_name][cat] = {"W": 0, "L": 0, "T": 0}
                    if result == "WIN":
                        totals[team_name][cat]["W"] += 1
                    elif result == "LOSS":
                        totals[team_name][cat]["L"] += 1
                    elif result == "TIE":
                        totals[team_name][cat]["T"] += 1

    return totals
