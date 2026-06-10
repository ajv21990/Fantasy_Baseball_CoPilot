import html as _html
import streamlit as st
import pandas as pd
from datetime import datetime
from core import utils
from core.stats import fetch_team_season_stats as _fetch_team_season_stats
from core.stats import fetch_category_wins as _fetch_category_wins


# ── Shared HTML builders ─────────────────────────────────────────────────────

_GROUP_TH = ('font-size:0.68rem;font-weight:800;letter-spacing:0.12em;padding:6px 12px;'
             'text-transform:uppercase;border-bottom:1px solid;text-align:center;')
_BAT_HDR  = 'color:#f97316;border-color:#f97316;background:rgba(249,115,22,0.08);'
_PIT_HDR  = 'color:#60a5fa;border-color:#3b82f6;background:rgba(59,130,246,0.08);'


def _team_row_style(i, is_mine):
    if is_mine:
        return 'background:linear-gradient(90deg,rgba(251,191,36,0.12),rgba(17,24,39,0.9));border-left:3px solid #fbbf24;'
    return 'background:rgba(13,26,46,0.5);' if i % 2 == 0 else 'background:rgba(10,14,23,0.4);'


def _you_badge(is_mine):
    if not is_mine:
        return ""
    return ' <span style="font-size:0.6rem;background:#fbbf24;color:#0a0e17;border-radius:4px;padding:1px 5px;font-weight:700;">YOU</span>'


def _group_header_row(batting_cats, pitching_cats):
    bat = (f'<th colspan="{len(batting_cats)}" style="{_GROUP_TH}{_BAT_HDR}">Batting</th>'
           if batting_cats else "")
    pit = (f'<th colspan="{len(pitching_cats)}" style="{_GROUP_TH}{_PIT_HDR}">Pitching</th>'
           if pitching_cats else "")
    return f'<tr><th style="{utils.TABLE_HEADER_STYLE}"></th>{bat}{pit}</tr>'


def render(league, my_team_name: str = ""):
    # ── Page header ──────────────────────────────────────────────────────────
    st.markdown("""
<div class="page-header">
  <span class="ph-icon">🏆</span>
  <span class="ph-title">Standings</span>
  <span class="ph-subtitle">Season Rankings</span>
</div>
""", unsafe_allow_html=True)

    try:
        teams = league.standings()
    except Exception as e:
        st.error(f"Could not load standings: {e}")
        return

    if not teams:
        st.info("No standings data available.")
        return

    # ── Summary stat cards ───────────────────────────────────────────────────
    leader = teams[0]
    st.markdown(f"""
<div class="stat-card-row">
  <div class="stat-card blue">
    <div class="sc-label">Total Teams</div>
    <div class="sc-value">{len(teams)}</div>
    <div class="sc-sub">in this league</div>
  </div>
  <div class="stat-card gold">
    <div class="sc-label">Current Leader</div>
    <div class="sc-value" style="font-size:1.15rem;">{_html.escape(leader.team_name)}</div>
    <div class="sc-sub">first place</div>
  </div>
  <div class="stat-card green">
    <div class="sc-label">Leader's Record</div>
    <div class="sc-value">{leader.wins}-{leader.losses}</div>
    <div class="sc-sub">W &ndash; L</div>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── W-L standings table ──────────────────────────────────────────────────
    rows = [{"Rank": i, "Team": t.team_name, "W": t.wins, "L": t.losses,
             "T": getattr(t, "ties", 0)} for i, t in enumerate(teams, 1)]
    df = pd.DataFrame(rows)

    def _standings_html(df, my_team_name):
        headers = df.columns.tolist()
        hdr = "".join(
            f'<th style="{utils.TABLE_HEADER_STYLE}">{h}</th>' for h in headers
        )
        body = ""
        for _, row in df.iterrows():
            is_mine = my_team_name and my_team_name.lower() in str(row["Team"]).lower()
            rank = row["Rank"]
            rank_color = ("#fbbf24" if rank == 1 else
                          "#94a3b8" if rank == 2 else
                          "#cd7c4f" if rank == 3 else "#4b5563")
            row_style = _team_row_style(rank, is_mine)
            cells = ""
            for col in headers:
                val = row[col]
                if col == "Rank":
                    cells += f'<td style="padding:10px 14px;color:{rank_color};font-weight:800;font-size:1rem;">{val}</td>'
                elif col == "Team":
                    nc = "#fbbf24" if is_mine else "#f1f5f9"
                    fw = "700" if is_mine else "400"
                    cells += f'<td style="padding:10px 14px;color:{nc};font-weight:{fw};">{_html.escape(str(val))}{_you_badge(is_mine)}</td>'
                elif col == "W":
                    cells += f'<td style="padding:10px 14px;color:#22c55e;font-weight:700;">{val}</td>'
                elif col == "L":
                    cells += f'<td style="padding:10px 14px;color:#ef4444;font-weight:700;">{val}</td>'
                else:
                    cells += f'<td style="padding:10px 14px;color:#94a3b8;">{val}</td>'
            body += f'<tr style="{row_style}">{cells}</tr>'
        return (f'<div class="resp-table" style="border-radius:10px;border:1px solid #1e2d40;margin-bottom:1.5rem;">'
                f'<table style="width:100%;border-collapse:collapse;font-size:0.9rem;min-width:420px;">'
                f'<thead><tr>{hdr}</tr></thead><tbody>{body}</tbody></table></div>')

    st.markdown(_standings_html(df, my_team_name), unsafe_allow_html=True)

    # ── Category Wins by Team ────────────────────────────────────────────────
    st.markdown("""
<div style="font-size:1.1rem;font-weight:700;color:#f1f5f9;letter-spacing:0.06em;
            text-transform:uppercase;margin:1.5rem 0 0.75rem 0;
            padding-bottom:0.5rem;border-bottom:1px solid #1e2d40;">
  Category Wins by Team
</div>
""", unsafe_allow_html=True)

    current_period = getattr(league, "currentMatchupPeriod", 1)
    if current_period < 1:
        st.info("No completed matchup periods yet.")
        return

    with st.spinner("Loading category data..."):
        cat_totals = _fetch_category_wins(league, max(current_period - 1, 1))

    if not cat_totals:
        st.info("No category data available.")
        return

    team_order = [t.team_name for t in teams]

    # Only this league's categories, batting first then pitching
    present = {cat for team_data in cat_totals.values() for cat in team_data}
    batting_cats  = [c for c in utils.BATTER_STATS  if c in present]
    pitching_cats = [c for c in utils.PITCHER_STATS if c in present]
    all_ordered   = batting_cats + pitching_cats

    def _wlt_cell(w, l, t):
        label = f"{w}-{l}-{t}" if t > 0 else f"{w}-{l}"
        if w > l:
            style = "background:rgba(34,197,94,0.20);color:#22c55e;font-weight:700"
        elif w < l:
            style = "background:rgba(239,68,68,0.18);color:#ef4444;font-weight:700"
        else:
            style = "background:rgba(234,179,8,0.15);color:#eab308;font-weight:600"
        return f'<td style="padding:8px 12px;text-align:center;{style}">{label}</td>'

    def _cat_wins_html(team_order, cat_totals, batting_cats, pitching_cats, my_team_name):
        cat_hdr = "".join(
            f'<th style="{utils.TABLE_HEADER_STYLE}text-align:center;">{c}</th>'
            for c in batting_cats + pitching_cats
        )
        row2 = f'<tr><th style="{utils.TABLE_HEADER_STYLE}">Team</th>{cat_hdr}</tr>'
        body = ""
        for i, team_name in enumerate(team_order):
            is_mine = my_team_name and my_team_name.lower() in team_name.lower()
            cells = (f'<td style="padding:8px 12px;color:{"#fbbf24" if is_mine else "#f1f5f9"};'
                     f'font-weight:{"700" if is_mine else "400"};white-space:nowrap;">'
                     f'{_html.escape(team_name)}{_you_badge(is_mine)}</td>')
            data = cat_totals.get(team_name, {})
            for cat in batting_cats + pitching_cats:
                wlt = data.get(cat, {"W": 0, "L": 0, "T": 0})
                cells += _wlt_cell(wlt["W"], wlt["L"], wlt["T"])
            body += f'<tr style="{_team_row_style(i, is_mine)}">{cells}</tr>'
        return (f'<div style="border-radius:10px;overflow:hidden;border:1px solid #1e2d40;'
                f'margin-bottom:1.5rem;overflow-x:auto;">'
                f'<table style="width:100%;border-collapse:collapse;font-size:0.85rem;">'
                f'<thead>{_group_header_row(batting_cats, pitching_cats)}{row2}</thead>'
                f'<tbody>{body}</tbody></table></div>')

    st.markdown(_cat_wins_html(team_order, cat_totals, batting_cats, pitching_cats, my_team_name),
                unsafe_allow_html=True)

    # ── Season Stats by Team ─────────────────────────────────────────────────
    st.markdown("""
<div style="font-size:1.1rem;font-weight:700;color:#f1f5f9;letter-spacing:0.06em;
            text-transform:uppercase;margin:1.5rem 0 0.75rem 0;
            padding-bottom:0.5rem;border-bottom:1px solid #1e2d40;">
  Season Stats by Team
</div>
""", unsafe_allow_html=True)

    with st.spinner("Loading season stats..."):
        team_season_stats = _fetch_team_season_stats(league)

    if not team_season_stats:
        st.info("No season stats available.")
        return

    st.markdown("""
<div style="font-size:0.72rem;color:#64748b;margin-bottom:8px;">
  <span style="color:#f97316;font-weight:700;">&#9679; Batting:</span> R, HR, RBI, SB, OPS &nbsp;&nbsp;
  <span style="color:#60a5fa;font-weight:700;">&#9679; Pitching:</span> K, W, SV, ERA, WHIP &nbsp;&nbsp;
  <span style="color:#4b5563;font-style:italic;">Click any column header to sort</span>
</div>
""", unsafe_allow_html=True)

    stat_cols = batting_cats + pitching_cats
    rows = []
    for team_name in team_order:
        stats = team_season_stats.get(team_name, {})
        row = {"Team": team_name}
        for cat in stat_cols:
            val = stats.get(cat)
            if val is not None:
                # Negate higher-is-better stats so ascending click (Streamlit default)
                # shows the best value first
                row[cat] = float(val) if cat in utils.LOWER_IS_BETTER else -float(val)
            else:
                row[cat] = float("nan")
        rows.append(row)

    df_stats = pd.DataFrame(rows)

    def _fmt_val(cat, v):
        if pd.isna(v):
            return "—"
        actual = v if cat in utils.LOWER_IS_BETTER else -v
        if cat in utils.THREE_DP_STATS:
            return f"{actual:.3f}"
        if cat in utils.TWO_DP_STATS:
            return f"{actual:.2f}"
        return str(int(actual))

    fmt = {cat: (lambda v, c=cat: _fmt_val(c, v)) for cat in stat_cols}

    def _color_stats(col):
        if col.name == "Team":
            return [""] * len(col)
        negate = col.name not in utils.LOWER_IS_BETTER
        return [utils.stat_color_style(col.name, -v if negate else v) if not pd.isna(v) else ""
                for v in col]

    def _highlight_my_team(row):
        is_mine = my_team_name and my_team_name.lower() in str(row["Team"]).lower()
        if is_mine:
            return ["background-color:rgba(251,191,36,0.12);font-weight:bold"] * len(row)
        return [""] * len(row)

    styled = (df_stats.style
              .format(fmt, na_rep="—")
              .apply(_color_stats, axis=0)
              .apply(_highlight_my_team, axis=1))

    st.dataframe(styled, use_container_width=True, hide_index=True)
