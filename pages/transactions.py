import streamlit as st
import pandas as pd
from datetime import datetime


ACTIVITY_TYPES = {
    "All": None,
    "Add": "FA",
    "Waiver": "WAIVER",
    "Trade": "TRADED",
}

# Keys match the actual strings ESPN returns via ACTIVITY_MAP
ACTION_COLORS = {
    "FA ADDED":     "#22c55e",
    "WAIVER ADDED": "#3b82f6",
    "DROPPED":      "#ef4444",
    "TRADED":       "#a855f7",
}

ACTION_BADGE_STYLES = {
    "FA ADDED":     "background:#166534;color:#22c55e;border:1px solid #22c55e;",
    "WAIVER ADDED": "background:#1e3a5f;color:#60a5fa;border:1px solid #3b82f6;",
    "DROPPED":      "background:#7f1d1d;color:#fca5a5;border:1px solid #ef4444;",
    "TRADED":       "background:#3b0764;color:#d8b4fe;border:1px solid #a855f7;",
}

# Short display labels for the summary bar
ACTION_DISPLAY = {
    "FA ADDED":     "FA ADD",
    "WAIVER ADDED": "WAIVER",
    "DROPPED":      "DROPPED",
    "TRADED":       "TRADE",
}


def _action_badge(action: str) -> str:
    label = str(action).upper()
    style = ACTION_BADGE_STYLES.get(label,
        "background:rgba(100,116,139,0.3);color:#94a3b8;border:1px solid rgba(100,116,139,0.4);")
    display = ACTION_DISPLAY.get(label, label)
    return (f'<span style="border-radius:8px;padding:4px 12px;font-size:0.72rem;'
            f'font-weight:800;letter-spacing:0.07em;{style}">{display}</span>')


def render(league):
    # ── Page header ──────────────────────────────────────────────────────────
    st.markdown("""
<div class="page-header">
  <span class="ph-icon">📋</span>
  <span class="ph-title">Transactions</span>
  <span class="ph-subtitle">Recent Activity</span>
</div>
""", unsafe_allow_html=True)

    current_year = datetime.now().year
    if getattr(league, "year", current_year) < 2019:
        st.warning("Transaction history is only available for 2019 and later seasons.")
        return

    # ── Filter controls ───────────────────────────────────────────────────────
    col1, col2 = st.columns([1, 1])
    with col1:
        type_label = st.selectbox("Filter by type", list(ACTIVITY_TYPES.keys()))
    with col2:
        size = st.slider("Number to show", min_value=10, max_value=100, value=25, step=5)

    msg_type = ACTIVITY_TYPES[type_label]

    try:
        kwargs = {"size": size}
        if msg_type:
            kwargs["msg_type"] = msg_type
        activities = league.recent_activity(**kwargs)
    except Exception as e:
        st.error(f"Could not load transactions: {e}")
        return

    if not activities:
        st.info("No transactions found.")
        return

    rows = []
    for activity in activities:
        date_ms = getattr(activity, "date", 0) or 0
        date_str = datetime.fromtimestamp(date_ms / 1000).strftime("%b %d") if date_ms else "—"
        time_str = datetime.fromtimestamp(date_ms / 1000).strftime("%I:%M %p") if date_ms else ""
        actions = getattr(activity, "actions", []) or []
        for action_tuple in actions:
            if len(action_tuple) >= 3:
                team, action, player = action_tuple[0], action_tuple[1], action_tuple[2]
            else:
                continue
            team_name = getattr(team, "team_name", str(team)) if team else "—"
            player_name = getattr(player, "name", str(player)) if player else "—"
            player_pos = getattr(player, "position", "") if player else ""
            rows.append({
                "date_str": date_str,
                "time_str": time_str,
                "team_name": team_name,
                "action": str(action),
                "player_name": player_name,
                "player_pos": player_pos,
            })

    if not rows:
        st.info("No transaction details found.")
        return

    # ── Render as styled cards ────────────────────────────────────────────────
    # Group by transaction "groups" — same date + team batches
    for i, row in enumerate(rows):
        action_label = str(row["action"]).upper()
        badge_html = _action_badge(action_label)

        # Card border accent color
        accent = ACTION_COLORS.get(action_label, "#4b5563")

        pos = row["player_pos"]
        pos_html = ""
        if pos:
            pos_html = (f'<span style="background:rgba(100,116,139,0.2);color:#94a3b8;'
                        f'border:1px solid rgba(100,116,139,0.3);border-radius:6px;'
                        f'padding:1px 7px;font-size:0.68rem;font-weight:700;'
                        f'letter-spacing:0.06em;margin-left:8px;">{pos}</span>')

        # Alternating subtle background
        card_bg = "rgba(13,26,46,0.6)" if i % 2 == 0 else "rgba(10,14,23,0.4)"

        st.markdown(f"""
<div style="display:flex;align-items:center;gap:14px;padding:11px 18px;
            background:{card_bg};border-left:3px solid {accent};
            border-radius:0 8px 8px 0;margin-bottom:4px;
            border-top:1px solid rgba(30,45,64,0.5);
            border-right:1px solid rgba(30,45,64,0.5);
            border-bottom:1px solid rgba(30,45,64,0.5);">
  <!-- Date pill -->
  <div style="min-width:62px;text-align:center;background:rgba(30,45,64,0.8);
              border-radius:8px;padding:4px 8px;">
    <div style="font-size:0.75rem;font-weight:700;color:#94a3b8;line-height:1.2;">
      {row['date_str']}
    </div>
    <div style="font-size:0.6rem;color:#4b5563;line-height:1.2;">{row['time_str']}</div>
  </div>

  <!-- Team name -->
  <div style="min-width:140px;max-width:160px;white-space:nowrap;overflow:hidden;
              text-overflow:ellipsis;font-size:0.82rem;color:#94a3b8;font-weight:500;">
    {row['team_name']}
  </div>

  <!-- Action badge -->
  <div style="min-width:70px;">
    {badge_html}
  </div>

  <!-- Player name + position -->
  <div style="flex:1;display:flex;align-items:center;overflow:hidden;">
    <span style="font-size:0.9rem;font-weight:700;color:#f1f5f9;
                 white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
      {row['player_name']}
    </span>
    {pos_html}
  </div>
</div>
""", unsafe_allow_html=True)

    # ── Summary stats at bottom ───────────────────────────────────────────────
    action_counts: dict = {}
    for r in rows:
        a = str(r["action"]).upper()
        action_counts[a] = action_counts.get(a, 0) + 1

    summary_html = ""
    order = ["FA ADDED", "WAIVER ADDED", "DROPPED", "TRADED"]
    for act in order:
        cnt = action_counts.get(act, 0)
        if cnt > 0:
            style = ACTION_BADGE_STYLES.get(act,
                "background:rgba(100,116,139,0.3);color:#94a3b8;border:1px solid rgba(100,116,139,0.4);")
            display = ACTION_DISPLAY.get(act, act)
            summary_html += (f'<span style="border-radius:8px;padding:4px 14px;font-size:0.75rem;'
                             f'font-weight:700;letter-spacing:0.06em;{style}">'
                             f'{cnt} {display}</span> ')

    if summary_html:
        st.markdown(f"""
<div style="margin-top:16px;padding:12px 18px;background:#0d1a2e;
            border:1px solid #1e2d40;border-radius:8px;
            display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
  <span style="font-size:0.68rem;color:#4b5563;text-transform:uppercase;
               letter-spacing:0.1em;font-weight:700;margin-right:4px;">Summary:</span>
  {summary_html}
</div>
""", unsafe_allow_html=True)
