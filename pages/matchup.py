import html as _html
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from core import utils


def _ordinal(n) -> str:
    if n is None:
        return "—"
    n = int(n)
    if 11 <= n % 100 <= 13:
        return f"{n}th"
    return f"{n}{('th','st','nd','rd','th')[min(n % 10, 4)]}"


def _cat_result(cat: str, my_data: dict, opp_data: dict) -> str:
    """Return WIN/LOSS/TIE for a category.

    Prefers the ESPN-provided result field; falls back to comparing raw values
    mid-week when ESPN hasn't populated result yet.
    """
    r = my_data.get("result", "") if isinstance(my_data, dict) else ""
    if r in ("WIN", "LOSS", "TIE"):
        return r
    my_val  = my_data.get("value")  if isinstance(my_data, dict) else None
    opp_val = opp_data.get("value") if isinstance(opp_data, dict) else None
    if my_val is None or opp_val is None:
        return ""
    try:
        mv, ov = float(my_val), float(opp_val)
        if cat in utils.LOWER_IS_BETTER:
            return "WIN" if mv < ov else ("LOSS" if mv > ov else "TIE")
        return "WIN" if mv > ov else ("LOSS" if mv < ov else "TIE")
    except (ValueError, TypeError):
        return ""


def render(league, my_team_name: str = ""):
    st.markdown("""
<div class="page-header">
  <span class="ph-icon">⚔️</span>
  <span class="ph-title">Current Matchup</span>
  <span class="ph-subtitle">This Week</span>
</div>
""", unsafe_allow_html=True)

    try:
        box_scores = league.box_scores()
    except Exception as e:
        st.error(f"Could not load matchup data: {e}")
        return

    # ── Build matchup list ────────────────────────────────────────────────────
    valid_boxes = []
    labels = []
    default_idx = 0
    for box in box_scores:
        home = getattr(box, "home_team", None)
        away = getattr(box, "away_team", None)
        if not home or not away:
            continue
        valid_boxes.append(box)
        labels.append(f"{home.team_name}  vs  {away.team_name}")

    if not labels:
        st.info("No matchups found this week.")
        return

    selected_idx = st.selectbox(
        "Select matchup", range(len(labels)),
        format_func=lambda i: labels[i],
        label_visibility="collapsed",
    )

    box = valid_boxes[selected_idx]
    home_team  = getattr(box, "home_team", None)
    away_team  = getattr(box, "away_team", None)
    home_stats = getattr(box, "home_stats", {}) or {}
    away_stats = getattr(box, "away_stats", {}) or {}

    home_name = _html.escape(home_team.team_name if home_team else "Home")
    away_name = _html.escape(away_team.team_name if away_team else "Away")

    home_season_w = getattr(home_team, "wins",   0)
    home_season_l = getattr(home_team, "losses", 0)
    away_season_w = getattr(away_team, "wins",   0)
    away_season_l = getattr(away_team, "losses", 0)

    today      = datetime.now()
    week_start = today - timedelta(days=today.weekday())
    week_end   = week_start + timedelta(days=6)
    date_range = f"{week_start.strftime('%m/%d')} – {week_end.strftime('%m/%d')}"

    try:
        _standings = league.standings()
        _rank_map  = {t.team_id: i + 1 for i, t in enumerate(_standings)}
        home_rank  = _rank_map.get(getattr(home_team, "team_id", None))
        away_rank  = _rank_map.get(getattr(away_team, "team_id", None))
    except Exception:
        home_rank = away_rank = None

    home_rank_str = f"{_ordinal(home_rank)} Place" if home_rank else "—"
    away_rank_str = f"{_ordinal(away_rank)} Place" if away_rank else "—"

    current_period = getattr(league, "currentMatchupPeriod", "?")

    # ── Tally W-L-T directly from ESPN's cumulativeScore ────────────────────
    home_w = getattr(box, "home_wins",   0) or 0
    home_l = getattr(box, "home_losses", 0) or 0
    home_t = getattr(box, "home_ties",   0) or 0
    away_w = getattr(box, "away_wins",   0) or 0
    away_l = getattr(box, "away_losses", 0) or 0
    away_t = getattr(box, "away_ties",   0) or 0

    # ── Score colors (higher score = green) ──────────────────────────────────
    if home_w > away_w:
        home_score_color = "#22c55e"
        away_score_color = "#ef4444"
        status_badge = (
            '<span style="background:rgba(34,197,94,0.2);color:#22c55e;'
            'border:1px solid rgba(34,197,94,0.4);border-radius:20px;'
            'padding:4px 14px;font-size:0.75rem;font-weight:700;letter-spacing:0.08em;">'
            'HOME LEADS</span>'
        )
    elif away_w > home_w:
        home_score_color = "#ef4444"
        away_score_color = "#22c55e"
        status_badge = (
            '<span style="background:rgba(34,197,94,0.2);color:#22c55e;'
            'border:1px solid rgba(34,197,94,0.4);border-radius:20px;'
            'padding:4px 14px;font-size:0.75rem;font-weight:700;letter-spacing:0.08em;">'
            'AWAY LEADS</span>'
        )
    else:
        home_score_color = "#eab308"
        away_score_color = "#eab308"
        status_badge = (
            '<span style="background:rgba(234,179,8,0.2);color:#eab308;'
            'border:1px solid rgba(234,179,8,0.4);border-radius:20px;'
            'padding:4px 14px;font-size:0.75rem;font-weight:700;letter-spacing:0.08em;">'
            'TIED</span>'
        )

    home_score_str = f"{home_w}-{home_l}-{home_t}" if home_t > 0 else f"{home_w}-{home_l}"
    away_score_str = f"{away_w}-{away_l}-{away_t}" if away_t > 0 else f"{away_w}-{away_l}"

    scoreboard_html = (
        '<div style="background:linear-gradient(135deg,#0d1a2e 0%,#111827 50%,#1a0d1a 100%);'
        'border:1px solid #1e2d40;border-radius:14px;padding:28px 32px;margin-bottom:1.5rem;">'

        '<div style="text-align:center;font-size:0.72rem;color:#64748b;letter-spacing:0.15em;'
        'text-transform:uppercase;margin-bottom:4px;">'
        f'Week {current_period} &nbsp;&middot;&nbsp; Current Matchup'
        '</div>'
        f'<div style="text-align:center;font-size:0.68rem;color:#4b5563;margin-bottom:16px;">{date_range}</div>'

        '<div class="matchup-scoreboard-row">'

        # Home side
        '<div class="matchup-team-block">'
        '<div style="font-size:0.68rem;color:#4b5563;text-transform:uppercase;'
        'letter-spacing:0.1em;margin-bottom:6px;">Home</div>'
        f'<div style="font-size:1.1rem;font-weight:700;color:#f1f5f9;margin-bottom:4px;word-break:break-word;overflow-wrap:anywhere;">{home_name}</div>'
        f'<div style="font-size:0.72rem;color:#4b5563;margin-bottom:10px;">{home_season_w}–{home_season_l}</div>'
        f'<div style="font-size:3.5rem;font-weight:900;color:{home_score_color};line-height:1;">{home_score_str}</div>'
        f'<div style="font-size:0.75rem;color:#64748b;margin-top:6px;letter-spacing:0.05em;">{home_rank_str}</div>'
        '</div>'

        # Middle
        '<div class="matchup-vs-block">'
        '<div style="font-size:1.6rem;color:#374151;font-weight:900;line-height:1;">&#9876;&#65039;</div>'
        '<div style="font-size:0.65rem;color:#374151;letter-spacing:0.2em;'
        'text-transform:uppercase;margin-top:4px;">vs</div>'
        f'<div style="margin-top:12px;">{status_badge}</div>'
        '</div>'

        # Away side
        '<div class="matchup-team-block">'
        '<div style="font-size:0.68rem;color:#4b5563;text-transform:uppercase;'
        'letter-spacing:0.1em;margin-bottom:6px;">Away</div>'
        f'<div style="font-size:1.1rem;font-weight:700;color:#f1f5f9;margin-bottom:4px;word-break:break-word;overflow-wrap:anywhere;">{away_name}</div>'
        f'<div style="font-size:0.72rem;color:#4b5563;margin-bottom:10px;">{away_season_w}–{away_season_l}</div>'
        f'<div style="font-size:3.5rem;font-weight:900;color:{away_score_color};line-height:1;">{away_score_str}</div>'
        f'<div style="font-size:0.75rem;color:#64748b;margin-top:6px;letter-spacing:0.05em;">{away_rank_str}</div>'
        '</div>'

        '</div></div>'
    )
    st.markdown(scoreboard_html, unsafe_allow_html=True)

    # ── Category table ────────────────────────────────────────────────────────
    _present      = {c for c in list(home_stats.keys()) + list(away_stats.keys()) if c in utils.LEAGUE_CATS}
    batting_cats  = [c for c in utils.BATTER_STATS  if c in _present]
    pitching_cats = [c for c in utils.PITCHER_STATS if c in _present]
    all_cats = batting_cats + pitching_cats

    if not all_cats:
        st.info("No category data available yet for this matchup.")
        return

    rows = []
    for cat in all_cats:
        home_data = home_stats.get(cat, {}) if isinstance(home_stats.get(cat), dict) else {}
        away_data = away_stats.get(cat, {}) if isinstance(away_stats.get(cat), dict) else {}
        result = _cat_result(cat, home_data, away_data)
        rows.append({
            "Category":   cat,
            "Home":       utils.format_stat(cat, home_data.get("value")),
            "Result":     utils.result_arrow(result),
            "_result":    result,
            "Away":       utils.format_stat(cat, away_data.get("value")),
        })

    df = pd.DataFrame(rows)
    result_series = df["_result"]
    display_df = df.drop(columns=["_result"])

    def _category_table_html(df_display, result_series, batting_cats, pitching_cats):
        header_cols = list(df_display.columns)
        ncols = len(header_cols)
        header_html = "".join(
            f'<th style="background:#0d1a2e;color:#7a8fa6;font-size:0.72rem;'
            f'text-transform:uppercase;letter-spacing:0.08em;padding:10px 18px;'
            f'border-bottom:2px solid #1e2d40;font-weight:700;'
            f'text-align:{"center" if c == "Result" else "left"};">{c}</th>'
            for c in header_cols
        )
        _bat_sep = (f'<tr style="background:rgba(249,115,22,0.08);">'
                    f'<td colspan="{ncols}" style="padding:5px 18px;font-size:0.65rem;'
                    f'font-weight:800;letter-spacing:0.12em;color:#f97316;'
                    f'text-transform:uppercase;border-top:1px solid rgba(249,115,22,0.2);">'
                    f'Batting</td></tr>')
        _pit_sep = (f'<tr style="background:rgba(59,130,246,0.08);">'
                    f'<td colspan="{ncols}" style="padding:5px 18px;font-size:0.65rem;'
                    f'font-weight:800;letter-spacing:0.12em;color:#60a5fa;'
                    f'text-transform:uppercase;border-top:1px solid rgba(59,130,246,0.2);">'
                    f'Pitching</td></tr>')
        rows_html = ""
        for idx, row in df_display.iterrows():
            cat = row["Category"]
            result = result_series.iloc[idx]

            if batting_cats and cat == batting_cats[0]:
                rows_html += _bat_sep
            elif pitching_cats and cat == pitching_cats[0]:
                rows_html += _pit_sep

            if result == "WIN":
                row_bg = "background:rgba(34,197,94,0.12);border-left:3px solid #22c55e;"
            elif result == "LOSS":
                row_bg = "background:rgba(239,68,68,0.10);border-left:3px solid #ef4444;"
            else:
                row_bg = "background:rgba(13,26,46,0.4);"

            cells = ""
            for col in header_cols:
                val = row[col]
                if col == "Category":
                    cells += (f'<td style="padding:10px 18px;color:#94a3b8;'
                               f'font-size:0.8rem;font-weight:700;letter-spacing:0.06em;'
                               f'text-transform:uppercase;">{val}</td>')
                elif col == "Home":
                    color = "#22c55e" if result == "WIN" else ("#ef4444" if result == "LOSS" else "#f1f5f9")
                    cells += (f'<td style="padding:10px 18px;color:{color};'
                               f'font-weight:700;font-size:1rem;">{val}</td>')
                elif col == "Result":
                    if result == "WIN":
                        r_color, r_bg = "#22c55e", "rgba(34,197,94,0.2)"
                    elif result == "LOSS":
                        r_color, r_bg = "#ef4444", "rgba(239,68,68,0.2)"
                    else:
                        r_color, r_bg = "#64748b", "rgba(100,116,139,0.15)"
                    cells += (f'<td style="padding:10px 18px;text-align:center;">'
                               f'<span style="background:{r_bg};color:{r_color};'
                               f'border-radius:20px;padding:3px 12px;font-size:1.1rem;'
                               f'font-weight:900;">{val}</span></td>')
                elif col == "Away":
                    away_color = "#ef4444" if result == "WIN" else ("#22c55e" if result == "LOSS" else "#94a3b8")
                    cells += (f'<td style="padding:10px 18px;color:{away_color};'
                               f'font-weight:600;">{val}</td>')
                else:
                    cells += f'<td style="padding:10px 18px;color:#94a3b8;">{val}</td>'
            rows_html += f'<tr style="{row_bg}">{cells}</tr>'

        return (
            f'<div style="border-radius:10px;overflow:hidden;border:1px solid #1e2d40;margin-bottom:1.5rem;">'
            f'<table style="width:100%;border-collapse:collapse;font-size:0.9rem;">'
            f'<thead><tr>{header_html}</tr></thead>'
            f'<tbody>{rows_html}</tbody>'
            f'</table></div>'
        )

    st.markdown(_category_table_html(display_df, result_series, batting_cats, pitching_cats),
                unsafe_allow_html=True)

    # ── Both lineups in tabs ──────────────────────────────────────────────────
    home_lineup = getattr(box, "home_lineup", []) or []
    away_lineup = getattr(box, "away_lineup", []) or []

    if home_lineup or away_lineup:
        st.markdown("""
<div style="font-size:1rem;font-weight:700;color:#f1f5f9;letter-spacing:0.06em;
            text-transform:uppercase;margin:1.5rem 0 0.75rem 0;
            padding-bottom:0.5rem;border-bottom:1px solid #1e2d40;">
  Lineups
</div>
""", unsafe_allow_html=True)
        tab_home, tab_away = st.tabs([
            f"🏠 {home_team.team_name if home_team else 'Home'}",
            f"✈️ {away_team.team_name if away_team else 'Away'}",
        ])
        with tab_home:
            _render_lineup(home_lineup)
        with tab_away:
            _render_lineup(away_lineup)


def _render_lineup(lineup):
    rows = []
    for p in lineup:
        player = getattr(p, "playerPoolEntry", p)
        name = getattr(player, "name", getattr(p, "name", "Unknown"))
        slot = getattr(p, "slot_position", getattr(p, "lineupSlot", ""))
        rows.append({"Slot": slot, "Player": name})
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No lineup data available.")
