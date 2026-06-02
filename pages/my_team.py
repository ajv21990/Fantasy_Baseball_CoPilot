import html as _html
import streamlit as st
from core.league_client import get_my_team, get_team_by_name
from core import utils
from core import ratings_store

# ── Slot classification ───────────────────────────────────────────────────────
_ACTIVE_SLOTS = {"C", "1B", "2B", "3B", "SS", "OF", "SP", "RP", "UTIL", "DH", "P",
                 "1B/3B", "2B/SS", "IF"}
_IL_SLOTS     = {"IL", "IL15", "IL60"}

_TH = ('background:#0d1a2e;color:#7a8fa6;font-size:0.7rem;text-transform:uppercase;'
       'letter-spacing:0.08em;padding:8px 12px;border-bottom:2px solid #1e2d40;font-weight:700;')


# ── Small helpers ─────────────────────────────────────────────────────────────

def _you_badge() -> str:
    return (' <span style="font-size:0.6rem;background:#fbbf24;color:#0a0e17;'
            'border-radius:4px;padding:1px 5px;font-weight:700;">YOU</span>')


def _ordinal(n) -> str:
    if n is None:
        return "—"
    n = int(n)
    if 11 <= n % 100 <= 13:
        return f"{n}th"
    return f"{n}{('th','st','nd','rd','th')[min(n % 10, 4)]}"


def _slot_border_color(slot: str) -> str:
    if slot in _IL_SLOTS:     return "#ef4444"
    if slot in _ACTIVE_SLOTS: return "#22c55e"
    return "#4b5563"


def _slot_badge_html(slot: str) -> str:
    c = _slot_border_color(slot)
    if c == "#22c55e":
        s = "background:rgba(34,197,94,0.15);color:#22c55e;border:1px solid rgba(34,197,94,0.35);"
    elif c == "#ef4444":
        s = "background:rgba(239,68,68,0.15);color:#ef4444;border:1px solid rgba(239,68,68,0.35);"
    else:
        s = "background:rgba(75,85,99,0.15);color:#6b7280;border:1px solid rgba(75,85,99,0.3);"
    return (f'<span style="border-radius:6px;padding:2px 8px;font-size:0.68rem;'
            f'font-weight:700;letter-spacing:0.05em;{s}">{_html.escape(slot) if slot else "—"}</span>')


def _pos_pill_html(pos: str, is_pitcher: bool) -> str:
    if is_pitcher:
        s = "background:rgba(249,115,22,0.15);color:#f97316;border:1px solid rgba(249,115,22,0.3);"
    else:
        s = "background:rgba(59,130,246,0.15);color:#60a5fa;border:1px solid rgba(59,130,246,0.3);"
    return (f'<span style="border-radius:6px;padding:2px 7px;font-size:0.68rem;'
            f'font-weight:700;{s}">{_html.escape(pos) if pos else "—"}</span>')


def _injury_html(val: str) -> str:
    if not val:
        return ""
    if val in ("IL", "IL15", "IL60", "OUT"):
        style = ("background:rgba(239,68,68,0.25);color:#ef4444;"
                 "border:1px solid rgba(239,68,68,0.5);")
    elif val == "DTD":
        style = ("background:rgba(249,115,22,0.25);color:#f97316;"
                 "border:1px solid rgba(249,115,22,0.5);")
    elif val == "SUSP":
        style = ("background:rgba(168,85,247,0.25);color:#a855f7;"
                 "border:1px solid rgba(168,85,247,0.5);")
    else:
        return ""
    return (f'<span style="border-radius:12px;padding:2px 9px;font-size:0.72rem;'
            f'font-weight:700;letter-spacing:0.05em;{style}">{val}</span>')


_SLOT_ORDER = {"#22c55e": 0, "#4b5563": 1, "#ef4444": 2}

_BAT_POS_ORDER = {
    "C": 0, "1B": 1, "1B/3B": 2, "2B": 3, "2B/SS": 4,
    "3B": 5, "SS": 6, "IF": 7, "OF": 8, "UTIL": 9, "DH": 10,
}
_PIT_POS_ORDER = {"SP": 0, "RP": 1, "P": 2}


def _bat_sort_key(p):
    slot = getattr(p, "lineupSlot", "") or ""
    return (_SLOT_ORDER.get(_slot_border_color(slot), 1), _BAT_POS_ORDER.get(slot, 99))


def _pit_sort_key(p):
    slot = getattr(p, "lineupSlot", "") or ""
    return (_SLOT_ORDER.get(_slot_border_color(slot), 1), _PIT_POS_ORDER.get(slot, 99))


def _player_stats_row(player) -> dict:
    raw = getattr(player, "stats", {}) or {}
    bd  = raw.get(0, {})
    if isinstance(bd, dict):
        bd = bd.get("breakdown", {})
    return bd if isinstance(bd, dict) else {}


# ── Cached quick-stats for hero card ─────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def _team_quick_stats(_league, team_name: str) -> dict:
    for team in _league.teams:
        if team.team_name != team_name:
            continue
        hr = k = 0.0
        ab_total = ops_w = er = outs = ph = pbb = 0.0
        for player in getattr(team, "roster", []):
            raw = getattr(player, "stats", {}) or {}
            bd  = raw.get(0, {})
            if isinstance(bd, dict):
                bd = bd.get("breakdown", {})
            if not isinstance(bd, dict):
                continue
            if utils.is_pitcher(player):
                k    += bd.get("K",    0) or 0
                er   += bd.get("ER",   0) or 0
                outs += bd.get("OUTS", 0) or 0
                ph   += bd.get("P_H",  0) or 0
                pbb  += bd.get("P_BB", 0) or 0
            else:
                hr += bd.get("HR", 0) or 0
                ab  = bd.get("AB", 0) or 0
                ab_total += ab
                ops_w    += (bd.get("OPS", 0) or 0) * ab
        ip = outs / 3 if outs > 0 else 0
        return {
            "HR":  int(hr),
            "OPS": round(ops_w / ab_total, 3) if ab_total > 0 else None,
            "K":   int(k),
            "ERA": round((er / ip) * 9, 2) if ip >= 1 else None,
        }
    return {}


# ── Roster HTML table ─────────────────────────────────────────────────────────

def _roster_table_html(players: list, stat_cols: list, section_label: str,
                       section_color: str, section_border: str, is_pitcher: bool) -> str:
    if not players:
        return ""

    ncols = 5 + len(stat_cols)
    sep = (f'<tr style="background:rgba({",".join(str(int(section_color.lstrip("#")[i:i+2],16)) for i in (0,2,4))},0.08);">'
           f'<td colspan="{ncols}" style="padding:5px 18px;font-size:0.65rem;font-weight:800;'
           f'letter-spacing:0.12em;color:{section_color};text-transform:uppercase;'
           f'border-top:1px solid rgba({",".join(str(int(section_color.lstrip("#")[i:i+2],16)) for i in (0,2,4))},0.2);">'
           f'{section_label}</td></tr>')

    stat_hdrs = "".join(
        f'<th style="{_TH}text-align:right;">{s}</th>' for s in stat_cols
    )
    header_row = (f'<tr>'
                  f'<th style="{_TH}">Slot</th>'
                  f'<th style="{_TH}">Player</th>'
                  f'<th style="{_TH}">Pos</th>'
                  f'<th style="{_TH}">Team</th>'
                  f'<th style="{_TH}">Inj</th>'
                  f'{stat_hdrs}</tr>')

    rows_html = ""
    for i, p in enumerate(players):
        slot      = getattr(p, "lineupSlot", "") or ""
        border_c  = _slot_border_color(slot)
        pos       = getattr(p, "position", "") or ""
        pro_team  = _html.escape(getattr(p, "proTeam", "") or "")
        name_esc  = _html.escape(p.name)
        pct_owned = getattr(p, "percent_owned", 0) or 0
        inj_html  = _injury_html(utils.injury_badge(p))
        stats     = _player_stats_row(p)
        row_bg    = "background:rgba(13,26,46,0.5);" if i % 2 == 0 else "background:rgba(10,14,23,0.4);"

        stat_cells = "".join(
            f'<td style="padding:8px 12px;text-align:right;font-weight:600;font-size:0.88rem;'
            f'{utils.stat_color_style(s, stats.get(s), stats)}">'
            f'{utils.format_stat(s, stats.get(s))}</td>'
            for s in stat_cols
        )

        rows_html += (
            f'<tr style="{row_bg}border-left:3px solid {border_c};">'
            f'<td style="padding:8px 12px;white-space:nowrap;">{_slot_badge_html(slot)}</td>'
            f'<td style="padding:8px 14px;color:#f1f5f9;font-weight:600;font-size:0.88rem;">'
            f'  {name_esc}'
            f'  <div style="font-size:0.65rem;color:#4b5563;margin-top:1px;">{pct_owned:.1f}% owned</div>'
            f'</td>'
            f'<td style="padding:8px 12px;">{_pos_pill_html(pos, is_pitcher)}</td>'
            f'<td style="padding:8px 12px;color:#64748b;font-size:0.8rem;">{pro_team}</td>'
            f'<td style="padding:8px 12px;">{inj_html}</td>'
            f'{stat_cells}'
            f'</tr>'
        )

    return (f'<div style="border-radius:10px;overflow:hidden;border:1px solid #1e2d40;'
            f'margin-bottom:0.75rem;overflow-x:auto;">'
            f'<table style="width:100%;border-collapse:collapse;font-size:0.85rem;">'
            f'<thead>{sep}{header_row}</thead>'
            f'<tbody>{rows_html}</tbody>'
            f'</table></div>')


# ── Main render ───────────────────────────────────────────────────────────────

def render(league, my_team_name: str = ""):
    # Toast queued by a save on the previous run (st.rerun cancels an inline toast,
    # so it's shown here at the top of the following run instead).
    _toast = st.session_state.pop("pr_toast", None)
    if _toast:
        st.toast(_toast, icon="⚾")

    st.markdown("""
<div class="page-header">
  <span class="ph-icon">👤</span>
  <span class="ph-title">Teams</span>
  <span class="ph-subtitle">Roster &amp; Stats</span>
</div>
""", unsafe_allow_html=True)

    # ── Team selector ─────────────────────────────────────────────────────────
    try:
        sorted_teams = league.standings()
    except Exception:
        sorted_teams = list(league.teams)

    labels       = [f"{i}. {t.team_name}" for i, t in enumerate(sorted_teams, 1)]
    label_to_name = {f"{i}. {t.team_name}": t.team_name
                     for i, t in enumerate(sorted_teams, 1)}

    default_idx = 0
    if my_team_name:
        for i, t in enumerate(sorted_teams):
            if my_team_name.lower() in t.team_name.lower():
                default_idx = i
                break

    selected_label = st.selectbox("Select team", labels, index=default_idx,
                                   label_visibility="collapsed")
    selected_name  = label_to_name[selected_label]
    team = get_team_by_name(league, selected_name)
    if team is None:
        st.warning("Team not found.")
        return

    is_my_team = bool(my_team_name and my_team_name.lower() in team.team_name.lower())
    rank = next((i for i, t in enumerate(sorted_teams, 1)
                 if t.team_name == team.team_name), None)

    # ── Standing badge style ──────────────────────────────────────────────────
    if rank == 1:
        rank_c, rank_bg, rank_bd = "#fbbf24", "rgba(251,191,36,0.18)", "rgba(251,191,36,0.4)"
    elif rank == 2:
        rank_c, rank_bg, rank_bd = "#94a3b8", "rgba(148,163,184,0.18)", "rgba(148,163,184,0.4)"
    elif rank == 3:
        rank_c, rank_bg, rank_bd = "#cd7c4f", "rgba(205,124,79,0.18)", "rgba(205,124,79,0.4)"
    else:
        rank_c, rank_bg, rank_bd = "#4b5563", "rgba(75,85,99,0.18)", "rgba(75,85,99,0.3)"
    rank_str = f"{_ordinal(rank)} Place" if rank else "—"

    wins   = team.wins
    losses = team.losses
    ties   = getattr(team, "ties", 0)

    you_html = _you_badge() if is_my_team else ""

    ties_html = ""
    if ties > 0:
        ties_html = (f'&nbsp;<span style="font-size:2.2rem;font-weight:900;'
                     f'color:#eab308;line-height:1;">{ties}</span>'
                     f'<span style="font-size:1rem;color:#4b5563;font-weight:700;margin-left:3px;">T</span>')

    # ── Quick stats for hero cards ────────────────────────────────────────────
    with st.spinner("Loading team stats..."):
        quick = _team_quick_stats(league, team.team_name)

    hr_val  = str(quick.get("HR", "—"))
    ops_val = utils.format_stat("OPS", quick.get("OPS")) if quick.get("OPS") is not None else "—"
    k_val   = str(quick.get("K",  "—"))
    era_val = utils.format_stat("ERA", quick.get("ERA")) if quick.get("ERA") is not None else "—"

    # ── Hero card ─────────────────────────────────────────────────────────────
    # Build as a string (no triple-quote f-string) so empty you_html/ties_html
    # never inject a blank line that CommonMark would use to end the HTML block.
    _hero = (
        '<div style="background:linear-gradient(135deg,#111827 0%,#0d1a2e 60%,#1a0d0d 100%);'
        'border:1px solid #1e2d40;border-left:4px solid #dc2626;border-radius:14px;'
        'padding:24px 28px;margin-bottom:1.25rem;">'
        '<div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;flex-wrap:wrap;">'
        + you_html
        + f'<div style="font-size:1.8rem;font-weight:900;color:#f1f5f9;letter-spacing:0.03em;flex:1;line-height:1.15;">{_html.escape(team.team_name)}</div>'
        f'<span style="background:{rank_bg};color:{rank_c};border:1px solid {rank_bd};'
        f'border-radius:20px;padding:5px 16px;font-size:0.82rem;font-weight:700;'
        f'letter-spacing:0.08em;white-space:nowrap;">{rank_str}</span>'
        '</div>'
        '<div style="display:flex;align-items:baseline;gap:6px;margin-bottom:18px;flex-wrap:wrap;">'
        f'<span style="font-size:3rem;font-weight:900;color:#22c55e;line-height:1;">{wins}</span>'
        '<span style="font-size:1.1rem;color:#4b5563;font-weight:700;">W</span>'
        '<span style="font-size:1.8rem;color:#374151;font-weight:900;margin:0 4px;">&ndash;</span>'
        f'<span style="font-size:3rem;font-weight:900;color:#ef4444;line-height:1;">{losses}</span>'
        '<span style="font-size:1.1rem;color:#4b5563;font-weight:700;">L</span>'
        + ties_html
        + '</div>'
        '<div style="height:1px;background:#1e2d40;margin-bottom:16px;"></div>'
        '<div class="stat-card-row" style="margin-bottom:0;">'
        '<div class="stat-card gold">'
        '<div class="sc-label">Team HR</div>'
        f'<div class="sc-value">{hr_val}</div>'
        '<div class="sc-sub">home runs</div>'
        '</div>'
        '<div class="stat-card green">'
        '<div class="sc-label">Team OPS</div>'
        f'<div class="sc-value" style="font-size:1.3rem;">{ops_val}</div>'
        '<div class="sc-sub">on-base + slugging</div>'
        '</div>'
        '<div class="stat-card blue">'
        '<div class="sc-label">Team K</div>'
        f'<div class="sc-value">{k_val}</div>'
        '<div class="sc-sub">strikeouts</div>'
        '</div>'
        '<div class="stat-card red">'
        '<div class="sc-label">Team ERA</div>'
        f'<div class="sc-value" style="font-size:1.3rem;">{era_val}</div>'
        '<div class="sc-sub">earned run avg</div>'
        '</div>'
        '</div>'
        '</div>'
    )
    st.markdown(_hero, unsafe_allow_html=True)

    # ── Roster ────────────────────────────────────────────────────────────────
    roster   = getattr(team, "roster", []) or []
    batters  = sorted([p for p in roster if not utils.is_pitcher(p)], key=_bat_sort_key)
    pitchers = sorted([p for p in roster if utils.is_pitcher(p)],     key=_pit_sort_key)

    total = len(roster)
    st.markdown(
        f'<div style="font-size:0.85rem;font-weight:700;color:#f1f5f9;letter-spacing:0.08em;text-transform:uppercase;margin:1.5rem 0 0.75rem 0;padding-bottom:0.5rem;border-bottom:1px solid #1e2d40;">'
        f'Roster <span style="font-size:0.72rem;color:#64748b;font-weight:400;text-transform:none;margin-left:8px;">{total} players &nbsp;&middot;&nbsp; <span style="color:#22c55e;">&#9632; active</span> &nbsp; <span style="color:#4b5563;">&#9632; bench</span> &nbsp; <span style="color:#ef4444;">&#9632; IL</span></span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if not roster:
        st.info("No roster data available.")
        return

    bat_html = _roster_table_html(
        batters, utils.BATTER_STATS,
        section_label="Batting", section_color="#f97316", section_border="#f97316",
        is_pitcher=False,
    )
    pit_html = _roster_table_html(
        pitchers, utils.PITCHER_STATS,
        section_label="Pitching", section_color="#60a5fa", section_border="#3b82f6",
        is_pitcher=True,
    )
    st.markdown(bat_html + pit_html, unsafe_allow_html=True)

    # ── Player Rater listing control ──────────────────────────────────────────
    _render_player_rater_control(team)


# ── Player Rater listing control ──────────────────────────────────────────────

def _pr_subheader_html(label: str, color: str, count: int) -> str:
    """Batting/Pitching subsection label, mirroring the roster section style."""
    return (
        f'<div style="display:flex;align-items:center;gap:8px;margin:0.25rem 0 0.4rem 0;">'
        f'<span style="font-size:0.65rem;font-weight:800;letter-spacing:0.12em;'
        f'color:{color};text-transform:uppercase;">{label}</span>'
        f'<span style="flex:1;height:1px;background:rgba('
        f'{",".join(str(int(color.lstrip("#")[i:i+2],16)) for i in (0,2,4))},0.25);"></span>'
        f'<span style="font-size:0.6rem;color:#64748b;font-weight:700;">{count} listed</span>'
        f'</div>'
    )


def _pr_checkbox_grid(entries: list, listed_ids: set, team_name: str, cols: int = 3) -> list:
    """Render a multi-column grid of player checkboxes. Returns checked player ids."""
    checked = []
    columns = st.columns(cols)
    for i, (pid, name, pos) in enumerate(entries):
        with columns[i % cols]:
            label = f"{name}  ·  {pos}" if pos else name
            if st.checkbox(label, value=pid in listed_ids,
                           key=f"pr_cb_{team_name}_{pid}"):
                checked.append(pid)
    return checked


def _render_player_rater_control(team) -> None:
    """Card under the roster to add/remove this team's players on the Player Rater.
    Mirrors the roster's Batting/Pitching layout so it reads as a related control,
    but uses an interactive checkbox grid instead of a stats table."""
    roster = getattr(team, "roster", []) or []
    try:
        listed_ids = {int(l["player_id"]) for l in ratings_store.get_listings()
                      if l["team"] == team.team_name}
    except Exception as e:
        st.warning(f"Player Rater storage unavailable: {e}")
        return

    # Split into batters / pitchers (same grouping as the roster table)
    batters, pitchers, name_by_pid = [], [], {}
    for p in roster:
        pid = getattr(p, "playerId", None)
        if pid is None:
            continue
        pid = int(pid)
        name_by_pid[pid] = p.name
        entry = (pid, p.name, getattr(p, "position", "") or "")
        (pitchers if utils.is_pitcher(p) else batters).append(entry)

    all_entries = batters + pitchers
    n_listed = sum(1 for pid, _, _ in all_entries if pid in listed_ids)

    # Header — gold accent to differentiate from the roster's red/section colors
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:10px;'
        f'margin:1.75rem 0 0.5rem 0;padding-bottom:0.5rem;'
        f'border-bottom:1px solid #1e2d40;">'
        f'<span style="font-size:0.95rem;font-weight:800;color:#fbbf24;'
        f'letter-spacing:0.06em;text-transform:uppercase;">⭐ Player Rater</span>'
        f'<span style="font-size:0.72rem;color:#64748b;font-weight:600;">'
        f'mark trade pieces for the league to rate</span>'
        f'<span style="margin-left:auto;background:rgba(251,191,36,0.15);'
        f'color:#fbbf24;border:1px solid rgba(251,191,36,0.35);border-radius:20px;'
        f'padding:2px 12px;font-size:0.72rem;font-weight:700;white-space:nowrap;">'
        f'{n_listed} listed</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if not all_entries:
        st.info("No ratable players on this roster.")
        return

    # Bordered card holding the interactive grid (visually echoes the roster card)
    with st.container(border=True):
        st.caption(f"Check players to put **{team.team_name}**'s trade pieces on the block, "
                   "then Save. Other teams rate them on the **Player Rater** page.")

        with st.form(f"pr_form_{team.team_name}"):
            checked_pids = []
            if batters:
                n = sum(1 for pid, _, _ in batters if pid in listed_ids)
                st.markdown(_pr_subheader_html("Batting", "#f97316", n),
                            unsafe_allow_html=True)
                checked_pids += _pr_checkbox_grid(batters, listed_ids, team.team_name)
            if pitchers:
                n = sum(1 for pid, _, _ in pitchers if pid in listed_ids)
                st.markdown(_pr_subheader_html("Pitching", "#60a5fa", n),
                            unsafe_allow_html=True)
                checked_pids += _pr_checkbox_grid(pitchers, listed_ids, team.team_name)

            saved = st.form_submit_button("⚾ Save Player Rater list",
                                          use_container_width=True, type="primary")

    if saved:
        checked = set(checked_pids)
        to_add = checked - listed_ids
        to_remove = listed_ids - checked
        if not to_add and not to_remove:
            st.info("No changes to save.")
            return
        try:
            for pid in to_add:
                ratings_store.list_player(team.team_name, pid, name_by_pid.get(pid, "Unknown"))
            for pid in to_remove:
                ratings_store.unlist_player(team.team_name, pid)
        except Exception as e:
            st.error(f"Could not save: {e}")
            return
        st.session_state["pr_toast"] = (
            f"Player Rater list saved — {len(to_add)} added, {len(to_remove)} removed.")
        st.rerun()
