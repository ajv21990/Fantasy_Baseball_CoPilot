import html as _html
import streamlit as st
from datetime import datetime
from core import utils
from core.stats import fetch_team_season_stats, fetch_category_wins

def _section_header_html(title: str, top_margin: bool = True) -> str:
    mt = "1.5rem" if top_margin else "0"
    return (
        f'<div style="font-size:1rem;font-weight:700;color:#f1f5f9;letter-spacing:0.06em;'
        f'text-transform:uppercase;margin:{mt} 0 0.75rem 0;'
        f'padding-bottom:0.5rem;border-bottom:1px solid #1e2d40;">{title}</div>'
    )


# ── Cached data fetcher ───────────────────────────────────────────────────────

@st.cache_data(ttl=600, show_spinner=False)
def _fetch_free_agents(_league, week: int, size: int, position) -> list:
    kwargs = {"size": size}
    if position:
        kwargs["position"] = position
    return _league.free_agents(**kwargs)




# ── Weakness scoring ──────────────────────────────────────────────────────────

def _compute_weaknesses(my_team_name: str, cat_wins: dict, team_stats: dict) -> list:
    """Returns up to 3 dicts sorted by weakness_score descending."""
    if not cat_wins or not team_stats:
        return []

    my_key = None
    for k in cat_wins:
        if my_team_name.lower() in k.lower():
            my_key = k
            break
    if my_key is None:
        return []

    all_keys = [t for t in cat_wins if t in team_stats]
    n = len(all_keys)
    if n < 2:
        return []

    results = []
    for cat in utils.LEAGUE_CATS:
        my_wlt = cat_wins.get(my_key, {}).get(cat, {})
        W = my_wlt.get("W", 0)
        L = my_wlt.get("L", 0)
        T = my_wlt.get("T", 0)
        total = max(W + L + T, 1)
        win_rate = W / total

        my_val = team_stats.get(my_key, {}).get(cat)

        teams_better = 0
        valid_vals = []
        for tn in all_keys:
            v = team_stats[tn].get(cat)
            if v is None:
                continue
            valid_vals.append(v)
            if tn == my_key:
                continue
            if my_val is None:
                teams_better += 1
                continue
            if cat in utils.LOWER_IS_BETTER:
                if v < my_val:
                    teams_better += 1
            else:
                if v > my_val:
                    teams_better += 1

        stat_rank_pct = 1.0 - (teams_better / n)
        league_avg = sum(valid_vals) / len(valid_vals) if valid_vals else None
        rank = teams_better + 1
        weakness_score = (1 - win_rate) * 0.6 + (1 - stat_rank_pct) * 0.4

        results.append({
            "cat": cat, "W": W, "L": L, "T": T,
            "win_rate": win_rate, "my_val": my_val,
            "league_avg": league_avg, "rank": rank,
            "n_teams": n, "weakness_score": weakness_score,
        })

    results.sort(key=lambda x: x["weakness_score"], reverse=True)
    return results[:3]


# ── Diagnosis cards (Section 1) ───────────────────────────────────────────────

def _render_diagnosis_cards(weaknesses: list) -> None:
    cards_html = ""
    for w in weaknesses:
        cat = w["cat"]
        is_bat = cat in utils.BATTER_STATS
        accent = "#f97316" if is_bat else "#60a5fa"
        accent_bg = "rgba(249,115,22,0.08)" if is_bat else "rgba(59,130,246,0.08)"
        accent_border = "rgba(249,115,22,0.3)" if is_bat else "rgba(59,130,246,0.3)"

        wlt_str = f"{w['W']}-{w['L']}-{w['T']}" if w["T"] > 0 else f"{w['W']}-{w['L']}"
        win_rate_pct = f"{w['win_rate']*100:.0f}%"

        my_val_str = utils.format_stat(cat, w["my_val"]) if w["my_val"] is not None else "—"
        avg_str    = utils.format_stat(cat, w["league_avg"]) if w["league_avg"] is not None else "—"

        rank = w["rank"]
        n    = w["n_teams"]
        if rank <= max(n // 3, 1):
            rank_color = "#22c55e"
        elif rank >= n - max(n // 3, 1) + 1:
            rank_color = "#ef4444"
        else:
            rank_color = "#eab308"

        stat_color = utils.stat_color_style(cat, w["my_val"]) if w["my_val"] is not None else "color:#94a3b8"

        cards_html += f"""
<div class="stat-card" style="border-top:3px solid {accent};background:linear-gradient(135deg,#111827,#0d1a2e);">
  <div style="font-size:0.68rem;text-transform:uppercase;letter-spacing:0.12em;
              color:{accent};font-weight:800;margin-bottom:8px;">{cat}</div>
  <div style="font-size:1.5rem;font-weight:900;color:#f1f5f9;line-height:1.1;
              margin-bottom:4px;">{wlt_str}</div>
  <div style="font-size:0.68rem;color:#64748b;margin-bottom:10px;">{win_rate_pct} win rate</div>
  <div style="height:1px;background:#1e2d40;margin-bottom:10px;"></div>
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
    <span style="font-size:0.65rem;color:#64748b;text-transform:uppercase;letter-spacing:0.08em;">My Stat</span>
    <span style="font-size:0.95rem;font-weight:700;{stat_color}">{my_val_str}</span>
  </div>
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
    <span style="font-size:0.65rem;color:#64748b;text-transform:uppercase;letter-spacing:0.08em;">Lg Avg</span>
    <span style="font-size:0.88rem;color:#94a3b8;font-weight:600;">{avg_str}</span>
  </div>
  <div style="text-align:center;background:{accent_bg};border:1px solid {accent_border};
              border-radius:6px;padding:4px 8px;font-size:0.72rem;font-weight:700;color:{rank_color};">
    Ranked {rank} of {n}
  </div>
</div>"""

    st.markdown(f'<div class="stat-card-row">{cards_html}</div>', unsafe_allow_html=True)


# ── Player filtering helpers ──────────────────────────────────────────────────

def _qualifies(player, target_cat: str):
    """Returns (val, bd) if player qualifies for target_cat, else None."""
    bd = utils.get_player_breakdown(player)
    val = bd.get(target_cat)
    if val is None:
        return None
    try:
        val = float(val)
    except (TypeError, ValueError):
        return None
    if val == 0 and target_cat in utils.COUNTING_STATS:
        return None
    if target_cat in ("ERA", "WHIP"):
        outs = bd.get("OUTS", 0) or 0
        if outs <= 0:
            return None
    return (val, bd)


def _get_recommended_pickups(players: list, target_cat: str, n: int = 4) -> list:
    """Returns top n (player, breakdown_dict) pairs from free agents."""
    is_pitching_cat = target_cat in utils.PITCHER_STATS
    candidates = []
    for p in players:
        if utils.is_pitcher(p) != is_pitching_cat:
            continue
        result = _qualifies(p, target_cat)
        if result is None:
            continue
        val, bd = result
        candidates.append((val, p, bd))

    ascending = target_cat in utils.LOWER_IS_BETTER
    candidates.sort(key=lambda x: x[0], reverse=not ascending)
    return [(p, bd) for _, p, bd in candidates[:n]]


def _get_trade_targets(league, my_team_name: str, target_cat: str, n: int = 4) -> list:
    """Returns top n (player, breakdown_dict, owning_team_name) triples from other rosters."""
    is_pitching_cat = target_cat in utils.PITCHER_STATS
    candidates = []
    for team in league.teams:
        if my_team_name and my_team_name.lower() in team.team_name.lower():
            continue
        for p in getattr(team, "roster", []):
            if utils.is_pitcher(p) != is_pitching_cat:
                continue
            result = _qualifies(p, target_cat)
            if result is None:
                continue
            val, bd = result
            candidates.append((val, p, bd, team.team_name))

    ascending = target_cat in utils.LOWER_IS_BETTER
    candidates.sort(key=lambda x: x[0], reverse=not ascending)
    return [(p, bd, tn) for _, p, bd, tn in candidates[:n]]


# ── Player card HTML ──────────────────────────────────────────────────────────

def _player_card_html(p, bd: dict, target_cat: str, owner_label: str = "") -> str:
    name = _html.escape(p.name)
    pos      = getattr(p, "position", "") or ""
    pro_team = _html.escape(getattr(p, "proTeam", "") or "")
    pct_owned = getattr(p, "percent_owned", 0) or 0
    pitcher = utils.is_pitcher(p)

    pos_pill = utils.pos_pill_html(pos, pitcher)
    inj_html = utils.injury_badge_html(utils.injury_badge(p))

    is_bat = target_cat in utils.BATTER_STATS
    target_accent = "#f97316" if is_bat else "#60a5fa"

    if owner_label:
        owner_esc = _html.escape(owner_label)
        accent_bg = "rgba(249,115,22,0.12)" if is_bat else "rgba(59,130,246,0.12)"
        accent_border = "rgba(249,115,22,0.3)" if is_bat else "rgba(59,130,246,0.3)"
        ownership_html = (
            f'<div style="background:{accent_bg};border:1px solid {accent_border};'
            f'border-radius:6px;padding:3px 8px;font-size:0.62rem;font-weight:700;'
            f'color:{target_accent};margin-bottom:10px;overflow:hidden;'
            f'text-overflow:ellipsis;white-space:nowrap;">'
            f'Trade from: {owner_esc}</div>'
        )
    else:
        bar_color = "#22c55e" if pct_owned >= 50 else ("#eab308" if pct_owned >= 20 else "#3b82f6")
        ownership_html = (
            f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:10px;">'
            f'<div style="flex:1;background:#1e2d40;border-radius:3px;height:4px;">'
            f'<div style="width:{min(pct_owned,100):.0f}%;background:{bar_color};'
            f'height:4px;border-radius:3px;"></div></div>'
            f'<span style="font-size:0.65rem;color:{bar_color};font-weight:700;'
            f'min-width:32px;text-align:right;">{pct_owned:.0f}%</span></div>'
        )

    stat_group = utils.PITCHER_STATS if pitcher else utils.BATTER_STATS
    ordered_cats = [target_cat] + [c for c in stat_group if c != target_cat]

    stat_rows_html = ""
    for cat in ordered_cats:
        val = bd.get(cat)
        val_str = utils.format_stat(cat, val)
        color_style = utils.stat_color_style(cat, val, bd) if val is not None else "color:#4b5563"
        label_color = target_accent if cat == target_cat else "#64748b"
        fw = "800" if cat == target_cat else "600"
        bottom_border = "border-bottom:1px solid #1e2d40;" if cat == target_cat else ""
        stat_rows_html += (
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:3px 0;{bottom_border}">'
            f'<span style="font-size:0.62rem;text-transform:uppercase;letter-spacing:0.08em;'
            f'color:{label_color};font-weight:700;">{cat}</span>'
            f'<span style="font-size:0.82rem;font-weight:{fw};{color_style}">{val_str}</span>'
            f'</div>'
        )

    return (
        f'<div class="stat-card" style="min-width:155px;max-width:230px;flex:1;padding:14px 16px;">'
        f'<div style="display:flex;align-items:flex-start;justify-content:space-between;'
        f'gap:6px;margin-bottom:6px;flex-wrap:wrap;">'
        f'<div style="font-size:0.85rem;font-weight:700;color:#f1f5f9;'
        f'line-height:1.25;flex:1;">{name}</div>'
        f'{pos_pill}</div>'
        f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:8px;">'
        f'<span style="font-size:0.7rem;color:#64748b;">{pro_team}</span>'
        f'{inj_html}</div>'
        f'{ownership_html}'
        f'<div>{stat_rows_html}</div>'
        f'</div>'
    )


# ── Card section renderer (Sections 2 & 3) ───────────────────────────────────

def _render_player_cards_section(cat: str, player_pairs: list, owner_labels: list = None) -> None:
    """
    Renders colored section header + flex row of player cards.
    player_pairs: list of (player, bd) for free agents
    owner_labels: parallel list of team name strings for trade targets (None = free agents)
    """
    is_bat = cat in utils.BATTER_STATS
    hdr_color = "#f97316" if is_bat else "#60a5fa"
    hdr_bg    = "rgba(249,115,22,0.08)" if is_bat else "rgba(59,130,246,0.08)"
    hdr_border = "rgba(249,115,22,0.2)" if is_bat else "rgba(59,130,246,0.2)"
    type_label = "Batting" if is_bat else "Pitching"

    header_html = (
        f'<div style="padding:6px 16px;background:{hdr_bg};'
        f'border-top:1px solid {hdr_border};border-bottom:1px solid {hdr_border};'
        f'font-size:0.65rem;font-weight:800;letter-spacing:0.12em;'
        f'color:{hdr_color};text-transform:uppercase;margin-bottom:8px;">'
        f'{type_label} &mdash; Target: {cat}</div>'
    )

    if not player_pairs:
        st.markdown(
            header_html + '<div style="color:#4b5563;font-size:0.8rem;'
                          'padding:8px 16px;margin-bottom:12px;">No qualifying players found.</div>',
            unsafe_allow_html=True,
        )
        return

    cards_html = ""
    for idx, (p, bd) in enumerate(player_pairs):
        owner = owner_labels[idx] if owner_labels else ""
        cards_html += _player_card_html(p, bd, cat, owner_label=owner)

    st.markdown(
        header_html + f'<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px;">{cards_html}</div>',
        unsafe_allow_html=True,
    )


# ── Full browser HTML table (Section 4) ──────────────────────────────────────

def _fa_table_html(players: list, stat_cols: list, sort_by: str,
                   is_pitcher: bool, section_label: str, section_color: str) -> str:
    if not players:
        return ""

    def sort_key(p):
        bd = utils.get_player_breakdown(p)
        if sort_by == "% Owned":
            return -(getattr(p, "percent_owned", 0) or 0)
        val = bd.get(sort_by)
        if val is None:
            return float("inf") if sort_by in utils.LOWER_IS_BETTER else float("-inf")
        return float(val) if sort_by in utils.LOWER_IS_BETTER else -float(val)

    sorted_players = sorted(players, key=sort_key)

    ncols = 5 + len(stat_cols)
    hex_c = section_color.lstrip("#")
    r, g, b = int(hex_c[0:2], 16), int(hex_c[2:4], 16), int(hex_c[4:6], 16)
    sep = (
        f'<tr style="background:rgba({r},{g},{b},0.08);">'
        f'<td colspan="{ncols}" style="padding:5px 18px;font-size:0.65rem;font-weight:800;'
        f'letter-spacing:0.12em;color:{section_color};text-transform:uppercase;'
        f'border-top:1px solid rgba({r},{g},{b},0.2);">{section_label}</td></tr>'
    )
    stat_hdrs = "".join(f'<th style="{utils.TABLE_HEADER_STYLE}text-align:right;">{s}</th>' for s in stat_cols)
    header_row = (
        f'<tr><th style="{utils.TABLE_HEADER_STYLE}">Pos</th>'
        f'<th style="{utils.TABLE_HEADER_STYLE}">Player</th>'
        f'<th style="{utils.TABLE_HEADER_STYLE}">Team</th>'
        f'<th style="{utils.TABLE_HEADER_STYLE}">Inj</th>'
        f'<th style="{utils.TABLE_HEADER_STYLE}text-align:right;">% Own</th>'
        f'{stat_hdrs}</tr>'
    )

    rows_html = ""
    for i, p in enumerate(sorted_players):
        bd = utils.get_player_breakdown(p)
        pos      = _html.escape(getattr(p, "position", "") or "")
        pro_team = _html.escape(getattr(p, "proTeam", "") or "")
        name_esc = _html.escape(p.name)
        pct_owned = getattr(p, "percent_owned", 0) or 0
        own_color = "#22c55e" if pct_owned >= 50 else ("#eab308" if pct_owned >= 20 else "#94a3b8")
        row_bg = "background:rgba(13,26,46,0.5);" if i % 2 == 0 else "background:rgba(10,14,23,0.4);"

        stat_cells = "".join(
            f'<td style="padding:8px 12px;text-align:right;font-weight:600;font-size:0.85rem;'
            f'{utils.stat_color_style(s, bd.get(s), bd)}">'
            f'{utils.format_stat(s, bd.get(s))}</td>'
            for s in stat_cols
        )

        rows_html += (
            f'<tr style="{row_bg}">'
            f'<td style="padding:8px 12px;">{utils.pos_pill_html(pos, is_pitcher)}</td>'
            f'<td style="padding:8px 14px;color:#f1f5f9;font-weight:600;font-size:0.85rem;">'
            f'{name_esc}'
            f'<div style="font-size:0.62rem;color:#4b5563;margin-top:1px;">{pct_owned:.1f}% owned</div></td>'
            f'<td style="padding:8px 12px;color:#64748b;font-size:0.78rem;">{pro_team}</td>'
            f'<td style="padding:8px 12px;">{utils.injury_badge_html(utils.injury_badge(p))}</td>'
            f'<td style="padding:8px 12px;text-align:right;color:{own_color};font-weight:700;">{pct_owned:.1f}%</td>'
            f'{stat_cells}</tr>'
        )

    return (
        f'<div style="border-radius:10px;overflow:hidden;border:1px solid #1e2d40;'
        f'margin-bottom:0.75rem;overflow-x:auto;">'
        f'<table style="width:100%;border-collapse:collapse;font-size:0.85rem;">'
        f'<thead>{sep}{header_row}</thead>'
        f'<tbody>{rows_html}</tbody>'
        f'</table></div>'
    )


# ── Main render ───────────────────────────────────────────────────────────────

def render(league, my_team_name: str = ""):
    st.markdown("""
<div class="page-header">
  <span class="ph-icon">🔍</span>
  <span class="ph-title">Free Agents</span>
  <span class="ph-subtitle">Available Players</span>
</div>
""", unsafe_allow_html=True)

    current_year = datetime.now().year
    if getattr(league, "year", current_year) < 2019:
        st.warning("Free agent data is only available for 2019 and later seasons.")
        return

    # ── Team selector ─────────────────────────────────────────────────────────
    try:
        sorted_teams = league.standings()
    except Exception:
        sorted_teams = list(league.teams)

    you_marker = " ★" if my_team_name else ""
    labels = []
    label_to_name = {}
    default_idx = 0
    for i, t in enumerate(sorted_teams):
        is_mine = my_team_name and my_team_name.lower() in t.team_name.lower()
        label = f"{i + 1}. {t.team_name}{you_marker if is_mine else ''}"
        labels.append(label)
        label_to_name[label] = t.team_name
        if is_mine:
            default_idx = i

    selected_label = st.selectbox(
        "Analyze team", labels, index=default_idx, label_visibility="collapsed"
    )
    selected_team_name = label_to_name[selected_label]

    # ── Section 1: Weak Spots ─────────────────────────────────────────────────
    short_name = selected_team_name.split()[0] if selected_team_name else "Team"
    st.markdown(
        _section_header_html(f"{short_name}'s Weak Spots", top_margin=True),
        unsafe_allow_html=True,
    )

    weaknesses = []
    current_period = getattr(league, "currentMatchupPeriod", 1)
    with st.spinner("Analyzing team..."):
        try:
            cat_wins   = fetch_category_wins(league, max(current_period - 1, 1))
            team_stats = fetch_team_season_stats(league)
            weaknesses = _compute_weaknesses(selected_team_name, cat_wins, team_stats)
        except Exception as e:
            st.warning(f"Could not compute weaknesses: {e}")

    if not weaknesses:
        st.info("No weakness data yet — check back after at least 1 completed matchup period.")
    else:
        _render_diagnosis_cards(weaknesses)

    # ── Fetch shared free agent pool ──────────────────────────────────────────
    current_week = getattr(league, "currentMatchupPeriod", getattr(league, "current_week", 1))
    with st.spinner("Loading free agents..."):
        try:
            all_players = _fetch_free_agents(league, current_week, 100, None)
        except Exception as e:
            st.error(f"Could not load free agents: {e}")
            return

    if not all_players:
        st.info("No free agents found.")
        return

    # ── Section 2: Recommended Pickups ───────────────────────────────────────
    if weaknesses:
        st.markdown(_section_header_html("Recommended Pickups"), unsafe_allow_html=True)
        for w in weaknesses:
            cat = w["cat"]
            picks = _get_recommended_pickups(all_players, cat, n=4)
            _render_player_cards_section(cat, picks)

    # ── Section 3: Trade Targets ──────────────────────────────────────────────
    if weaknesses:
        st.markdown(_section_header_html("Trade Targets"), unsafe_allow_html=True)
        for w in weaknesses:
            cat = w["cat"]
            raw_targets = _get_trade_targets(league, selected_team_name, cat, n=4)
            pairs  = [(p, bd) for p, bd, _ in raw_targets]
            trade_labels = [tn for _, _, tn in raw_targets]
            _render_player_cards_section(cat, pairs, owner_labels=trade_labels)

    # ── Section 4: Free Agent Browser ────────────────────────────────────────
    st.markdown(_section_header_html("Free Agent Browser"), unsafe_allow_html=True)

    st.markdown("""
<div style="background:#0d1a2e;border:1px solid #1e2d40;border-radius:10px;
            padding:16px 20px;margin-bottom:1.25rem;">
  <div style="font-size:0.68rem;color:#64748b;text-transform:uppercase;
              letter-spacing:0.1em;margin-bottom:10px;font-weight:700;">Filters</div>
""", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        pos_options = ["All"] + utils.position_options()
        selected_pos = st.selectbox("Position", pos_options)
    with col2:
        size = st.slider("Players to show", min_value=10, max_value=100, value=30, step=5)
    with col3:
        sort_options = ["% Owned"] + utils.BATTER_STATS + utils.PITCHER_STATS
        sort_by = st.selectbox("Sort by", sort_options)

    st.markdown("</div>", unsafe_allow_html=True)

    position_arg = None if selected_pos == "All" else selected_pos
    displayed = []
    for p in all_players:
        if position_arg:
            eligible  = getattr(p, "eligibleSlots", []) or []
            pos_field = getattr(p, "position", "") or ""
            if position_arg not in eligible and pos_field != position_arg:
                continue
        displayed.append(p)
        if len(displayed) >= size:
            break

    batters  = [p for p in displayed if not utils.is_pitcher(p)]
    pitchers = [p for p in displayed if utils.is_pitcher(p)]

    bat_html = _fa_table_html(batters,  utils.BATTER_STATS,  sort_by, False, "Batting",  "#f97316")
    pit_html = _fa_table_html(pitchers, utils.PITCHER_STATS, sort_by, True,  "Pitching", "#60a5fa")

    if bat_html or pit_html:
        st.markdown(bat_html + pit_html, unsafe_allow_html=True)
    else:
        st.info("No players match the selected filters.")
