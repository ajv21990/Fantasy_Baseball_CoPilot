import html as _html
import streamlit as st
from core import utils
from core.league_client import get_team_by_name
from core import ratings_store



def _pid_map(league) -> dict:
    """playerId -> player object across every team's roster."""
    out = {}
    for team in league.teams:
        for p in getattr(team, "roster", []) or []:
            pid = getattr(p, "playerId", None)
            if pid is not None:
                out[int(pid)] = p
    return out


def _stars_html(n: float, size: str = "1rem") -> str:
    """Unicode star bar for an integer or average rating."""
    filled = int(round(n))
    filled = max(0, min(5, filled))
    stars = "★" * filled + "☆" * (5 - filled)
    return (f'<span style="color:#fbbf24;font-size:{size};letter-spacing:2px;'
            f'font-weight:700;">{stars}</span>')



def _stat_rows_html(player) -> str:
    bd = utils.get_player_breakdown(player)
    pitcher = utils.is_pitcher(player)
    cats = utils.PITCHER_STATS if pitcher else utils.BATTER_STATS
    rows = ""
    for cat in cats:
        val = bd.get(cat)
        val_str = utils.format_stat(cat, val)
        color = utils.stat_color_style(cat, val, bd) if val is not None else "color:#4b5563"
        rows += (
            f'<div style="display:flex;justify-content:space-between;align-items:center;padding:2px 0;">'
            f'<span style="font-size:0.62rem;text-transform:uppercase;letter-spacing:0.08em;'
            f'color:#64748b;font-weight:700;">{cat}</span>'
            f'<span style="font-size:0.8rem;font-weight:700;{color}">{val_str}</span>'
            f'</div>'
        )
    return rows


def _player_card(player, name: str, extra_html: str = "") -> str:
    """Compact player card (name, pos, pro team, key stats) + optional footer html."""
    pos = getattr(player, "position", "") or "" if player is not None else ""
    pro_team = _html.escape(getattr(player, "proTeam", "") or "") if player is not None else ""
    pitcher = utils.is_pitcher(player) if player is not None else False
    pos_pill = utils.pos_pill_html(pos, pitcher)
    stats_html = _stat_rows_html(player) if player is not None else (
        '<div style="font-size:0.7rem;color:#ef4444;">no longer on a roster</div>')
    return (
        f'<div class="stat-card" style="min-width:170px;max-width:260px;flex:1;padding:14px 16px;">'
        f'<div style="display:flex;align-items:flex-start;justify-content:space-between;'
        f'gap:6px;margin-bottom:6px;flex-wrap:wrap;">'
        f'<div style="font-size:0.85rem;font-weight:700;color:#f1f5f9;line-height:1.25;flex:1;">'
        f'{_html.escape(name)}</div>{pos_pill}</div>'
        f'<div style="font-size:0.7rem;color:#64748b;margin-bottom:8px;">{pro_team}</div>'
        f'<div>{stats_html}</div>'
        f'{extra_html}'
        f'</div>'
    )


def _section_header(title: str, top: bool = True) -> None:
    mt = "1.5rem" if top else "0"
    st.markdown(
        f'<div style="font-size:1rem;font-weight:700;color:#f1f5f9;letter-spacing:0.06em;'
        f'text-transform:uppercase;margin:{mt} 0 0.75rem 0;padding-bottom:0.5rem;'
        f'border-bottom:1px solid #1e2d40;">{title}</div>',
        unsafe_allow_html=True,
    )


# ── Main render ───────────────────────────────────────────────────────────────

def render(league, my_team_name: str = ""):
    # Toast queued by a save on the previous run (st.rerun cancels an inline toast,
    # so it's shown here at the top of the following run instead).
    _toast = st.session_state.pop("pr_rate_toast", None)
    if _toast:
        st.toast(_toast, icon="⭐")

    st.markdown("""
<div class="page-header">
  <span class="ph-icon">⭐</span>
  <span class="ph-title">Player Rater</span>
  <span class="ph-subtitle">Rate &amp; gauge trade value</span>
</div>
""", unsafe_allow_html=True)

    # ── Team selector (which team am I, for rating) ───────────────────────────
    try:
        sorted_teams = league.standings()
    except Exception:
        sorted_teams = list(league.teams)

    default_idx = 0
    if my_team_name:
        for i, t in enumerate(sorted_teams):
            if my_team_name.lower() in t.team_name.lower():
                default_idx = i
                break

    labels = [f"{i}. {t.team_name}" for i, t in enumerate(sorted_teams, 1)]
    label_to_name = {lbl: t.team_name for lbl, t in zip(labels, sorted_teams)}
    selected_label = st.selectbox("Your team", labels, index=default_idx)
    selected_team = label_to_name[selected_label]
    st.caption(f"Rating as **{selected_team}** — switch teams above to rate as someone else. "
               "Add your own players to the rater on the **Teams** page.")

    # ── Load data ─────────────────────────────────────────────────────────────
    try:
        listings = ratings_store.get_listings()
        all_ratings = ratings_store.get_ratings()
    except Exception as e:
        st.error(f"Could not load Player Rater data: {e}")
        return

    pid_map = _pid_map(league)

    # ── Section A: Rate other teams' listed players ───────────────────────────
    _section_header("Rate Other Teams' Players", top=False)

    others = [l for l in listings if l["team"] != selected_team]
    my_ratings = {int(r["player_id"]): int(r["stars"])
                  for r in all_ratings if r["rater_team"] == selected_team}

    if not others:
        st.info("No other teams have listed any players yet.")
    else:
        with st.form("rate_form"):
            # group by owning team
            by_team: dict[str, list] = {}
            for l in others:
                by_team.setdefault(l["team"], []).append(l)

            for owning_team in sorted(by_team):
                st.markdown(
                    f'<div style="font-size:0.72rem;font-weight:800;color:#60a5fa;'
                    f'text-transform:uppercase;letter-spacing:0.1em;margin:0.75rem 0 0.4rem 0;">'
                    f'{_html.escape(owning_team)}</div>',
                    unsafe_allow_html=True,
                )
                for l in by_team[owning_team]:
                    pid = int(l["player_id"])
                    player = pid_map.get(pid)
                    cur = my_ratings.get(pid)
                    cur_html = (f'<div style="margin-top:8px;font-size:0.65rem;color:#64748b;">'
                                f'Your rating: {_stars_html(cur, "0.85rem") if cur else "—"}</div>')
                    st.markdown(_player_card(player, l["player_name"], cur_html),
                                unsafe_allow_html=True)
                    st.feedback("stars", key=f"rate_{pid}")
                    if cur:  # already rated → offer a remove option
                        st.checkbox("🗑️ Remove my rating", key=f"del_{pid}")

            submitted = st.form_submit_button("Save my ratings", use_container_width=True)

        if submitted:
            saved = deleted = 0
            for l in others:
                pid = int(l["player_id"])
                # Delete takes precedence if both the box is checked and a star set.
                if st.session_state.get(f"del_{pid}"):
                    if pid in my_ratings:
                        ratings_store.delete_rating(selected_team, pid)
                        deleted += 1
                    # Reset the widgets so the stars/checkbox clear on rerun (they'd
                    # otherwise retain their values in session_state across reruns).
                    st.session_state.pop(f"rate_{pid}", None)
                    st.session_state.pop(f"del_{pid}", None)
                    continue
                v = st.session_state.get(f"rate_{pid}")
                if v is not None:  # None = untouched → leave existing rating unchanged
                    ratings_store.set_rating(selected_team, pid, int(v) + 1)
                    saved += 1
            if saved or deleted:
                parts = []
                if saved:
                    parts.append(f"{saved} saved")
                if deleted:
                    parts.append(f"{deleted} removed")
                st.session_state["pr_rate_toast"] = "Ratings updated — " + ", ".join(parts) + "."
            else:
                st.session_state["pr_rate_toast"] = "No changes to save."
            st.rerun()

    # ── Section B: How my listed players are rated ────────────────────────────
    _section_header("How My Players Are Rated")

    mine = [l for l in listings if l["team"] == selected_team]
    if not mine:
        st.info("You haven't listed any players yet. Add them on the **Teams** page "
                "(select your team → ⭐ Player Rater).")
        return

    for l in mine:
        pid = int(l["player_id"])
        rs = [r for r in all_ratings if int(r["player_id"]) == pid]
        name = _html.escape(l["player_name"])
        on_roster = pid in pid_map
        roster_flag = "" if on_roster else (
            ' <span style="font-size:0.62rem;color:#ef4444;">(no longer on roster)</span>')

        if rs:
            avg = sum(int(r["stars"]) for r in rs) / len(rs)
            header = (f'{_stars_html(avg, "1.2rem")} '
                      f'<span style="font-size:0.8rem;color:#94a3b8;font-weight:600;">'
                      f'{avg:.1f} avg · {len(rs)} vote{"s" if len(rs) != 1 else ""}</span>')
            breakdown = ""
            for r in sorted(rs, key=lambda x: -int(x["stars"])):
                breakdown += (
                    f'<div style="display:flex;justify-content:space-between;align-items:center;'
                    f'padding:3px 0;border-top:1px solid #1e2d40;">'
                    f'<span style="font-size:0.72rem;color:#94a3b8;">'
                    f'{_html.escape(r["rater_team"])}</span>'
                    f'{_stars_html(int(r["stars"]), "0.85rem")}</div>'
                )
        else:
            header = '<span style="font-size:0.8rem;color:#64748b;">No ratings yet</span>'
            breakdown = ""

        st.markdown(
            f'<div class="stat-card" style="padding:14px 18px;margin-bottom:0.6rem;">'
            f'<div style="font-size:0.95rem;font-weight:700;color:#f1f5f9;margin-bottom:6px;">'
            f'{name}{roster_flag}</div>'
            f'<div style="margin-bottom:6px;">{header}</div>'
            f'{breakdown}'
            f'</div>',
            unsafe_allow_html=True,
        )
