import streamlit as st

st.set_page_config(
    page_title="Fantasy Baseball Dashboard",
    page_icon="⚾",
    layout="wide",
)

import sys
import os
from datetime import datetime
sys.path.insert(0, os.path.dirname(__file__))

from core import auth, league_client, utils
from pages import standings, my_team, matchup, free_agents, transactions, player_rater

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ---- Hide Streamlit chrome ---- */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
[data-testid="stSidebarNav"] {display: none;}

/* Make header transparent but keep sidebar toggle + deploy button accessible */
header[data-testid="stHeader"] {
    background-color: transparent !important;
    border-bottom: none !important;
    overflow: visible !important;
}
/* Hide the Deploy button — we don't need it for a local tool */
[data-testid="stAppDeployButton"] {
    display: none !important;
}
/* Ensure sidebar collapse/expand toggle is always fully visible */
[data-testid="collapsedControl"] {
    display: flex !important;
    visibility: visible !important;
}

/* ---- Base background ---- */
.stApp {
    background-color: #0a0e17;
}

/* ---- Sidebar ---- */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1220 0%, #111827 100%);
    border-right: 1px solid #1e2d40;
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stRadio label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span {
    color: #b0bec5 !important;
}
[data-testid="stSidebar"] .stRadio [data-testid="stWidgetLabel"] {
    color: #7a8fa6 !important;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}

/* ---- Nav radio pill ---- */
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
    background: transparent;
    border-radius: 6px;
    padding: 6px 10px;
    margin: 2px 0;
    transition: background 0.15s;
    color: #cdd6e0 !important;
    font-size: 0.92rem;
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:has(input:checked) {
    background: rgba(220, 38, 38, 0.18);
    border-left: 3px solid #dc2626;
    color: #fff !important;
    font-weight: 600;
}

/* ---- Sidebar divider ---- */
[data-testid="stSidebar"] hr {
    border-color: #1e2d40;
}

/* ---- Top banner (injected via st.markdown) ---- */
.top-banner {
    background: linear-gradient(90deg, #0d1220 0%, #12203a 60%, #1a0a0a 100%);
    border-bottom: 2px solid #dc2626;
    padding: 12px 28px;
    margin: -1rem -1rem 1.5rem -1rem;
    display: flex;
    align-items: center;
    gap: 14px;
}
.top-banner .banner-icon {
    font-size: 1.8rem;
    line-height: 1;
}
.top-banner .banner-title {
    font-size: 1.35rem;
    font-weight: 800;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #f1f5f9;
}
.top-banner .banner-sub {
    font-size: 0.78rem;
    color: #64748b;
    margin-left: auto;
    letter-spacing: 0.05em;
}

/* ---- Page section headers ---- */
.page-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 1.5rem;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid #1e2d40;
}
.page-header .ph-icon {
    font-size: 1.6rem;
}
.page-header .ph-title {
    font-size: 1.6rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #f1f5f9;
}
.page-header .ph-subtitle {
    font-size: 0.8rem;
    color: #64748b;
    margin-left: 4px;
    align-self: flex-end;
    margin-bottom: 3px;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}

/* ---- Stat summary cards ---- */
.stat-card-row {
    display: flex;
    gap: 16px;
    margin-bottom: 1.5rem;
    flex-wrap: wrap;
}
.stat-card {
    background: linear-gradient(135deg, #111827 0%, #0d1a2e 100%);
    border: 1px solid #1e2d40;
    border-radius: 10px;
    padding: 16px 22px;
    min-width: 140px;
    flex: 1;
}
.stat-card .sc-label {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #64748b;
    margin-bottom: 4px;
}
.stat-card .sc-value {
    font-size: 1.6rem;
    font-weight: 800;
    color: #f1f5f9;
    line-height: 1.1;
}
.stat-card .sc-sub {
    font-size: 0.75rem;
    color: #94a3b8;
    margin-top: 3px;
}
.stat-card.gold .sc-value { color: #fbbf24; }
.stat-card.green .sc-value { color: #22c55e; }
.stat-card.red .sc-value { color: #ef4444; }
.stat-card.blue .sc-value { color: #3b82f6; }

/* ---- st.metric override ---- */
[data-testid="metric-container"] {
    background: linear-gradient(135deg, #111827 0%, #0d1a2e 100%);
    border: 1px solid #1e2d40;
    border-radius: 10px;
    padding: 14px 20px !important;
}
[data-testid="metric-container"] label {
    color: #64748b !important;
    font-size: 0.72rem !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #f1f5f9 !important;
    font-size: 1.8rem !important;
    font-weight: 800 !important;
}

/* ---- Dataframe / table ---- */
[data-testid="stDataFrame"] {
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #1e2d40;
}

/* ---- Tabs ---- */
[data-testid="stTabs"] [role="tablist"] {
    border-bottom: 1px solid #1e2d40;
    gap: 4px;
}
[data-testid="stTabs"] button[role="tab"] {
    color: #64748b;
    font-weight: 600;
    font-size: 0.85rem;
    letter-spacing: 0.04em;
    border-radius: 6px 6px 0 0;
    padding: 8px 18px;
}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    color: #f1f5f9;
    background: rgba(220, 38, 38, 0.15);
    border-bottom: 2px solid #dc2626;
}

/* ---- Expander ---- */
[data-testid="stExpander"] {
    border: 1px solid #1e2d40 !important;
    border-radius: 8px !important;
    background: #0d1220;
}

/* ---- Info / warning ---- */
.stAlert {
    border-radius: 8px;
}

/* ---- Spinner ---- */
[data-testid="stSpinner"] {
    color: #dc2626;
}

/* ---- Scrollbar ---- */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0a0e17; }
::-webkit-scrollbar-thumb { background: #1e2d40; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #2d4060; }

/* ── Mobile: responsive helper class for scrollable table wrappers ── */
.resp-table { overflow-x: auto; -webkit-overflow-scrolling: touch; }

/* ── Mobile: matchup scoreboard stacks vertically on narrow screens ── */
.matchup-scoreboard-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    flex-wrap: wrap;
}
.matchup-team-block { flex: 1; text-align: center; min-width: 130px; }
.matchup-vs-block   { text-align: center; min-width: 80px; }

/* ── Mobile breakpoints ──────────────────────────────────────── */
@media (max-width: 768px) {
    /* Tighten main content padding */
    section[data-testid="stMain"] .block-container,
    .main .block-container {
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
    }

    /* Top banner */
    .top-banner {
        padding: 8px 14px;
        margin: -1rem -0.75rem 1rem -0.75rem;
        gap: 8px;
        flex-wrap: wrap;
    }
    .top-banner .banner-title { font-size: 1rem; }
    .top-banner .banner-sub   { display: none; }

    /* Page header */
    .page-header { margin-bottom: 1rem; }
    .page-header .ph-icon     { font-size: 1.25rem; }
    .page-header .ph-title    { font-size: 1.25rem; }
    .page-header .ph-subtitle { display: none; }

    /* Stat cards — 2-column grid */
    .stat-card-row {
        display: grid !important;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
        margin-bottom: 1rem;
    }
    .stat-card { min-width: 0; padding: 12px 14px; }
    .stat-card .sc-value { font-size: 1.3rem; }

    /* Matchup scoreboard stacks cleanly */
    .matchup-team-block { flex-basis: 40%; }
}

@media (max-width: 480px) {
    /* Single-column stat cards on very small phones */
    .stat-card-row { grid-template-columns: 1fr 1fr; }

    /* Matchup: full-width stacked columns */
    .matchup-team-block { flex-basis: 100%; }
    .matchup-vs-block   { flex-basis: 100%; order: -1; padding: 4px 0; }
}
</style>
""", unsafe_allow_html=True)


def _is_auth_error(e: Exception) -> bool:
    """Return True when the exception looks like an ESPN auth/cookie failure."""
    msg = str(e).lower()
    return any(token in msg for token in (
        "401", "403", "private", "unauthorized", "forbidden",
        "access denied", "invalid", "cookie",
    ))


def show_cookie_expired_page():
    """Render a friendly cookie-expired error page and stop execution."""
    st.markdown("""
<div style="
    background:#0a0e17;
    min-height:60vh;
    display:flex;
    align-items:center;
    justify-content:center;
">
  <div style="
      background:linear-gradient(135deg,#111827 0%,#0d1a2e 100%);
      border:1px solid #dc2626;
      border-radius:14px;
      padding:40px 48px;
      max-width:520px;
      text-align:center;
  ">
    <div style="font-size:3rem;margin-bottom:16px;">🍪</div>
    <div style="
        font-size:1.5rem;font-weight:800;letter-spacing:0.06em;
        text-transform:uppercase;color:#f1f5f9;margin-bottom:12px;
    ">Session Expired</div>
    <div style="font-size:0.95rem;color:#94a3b8;margin-bottom:28px;line-height:1.6;">
      The ESPN cookies powering this app have expired. Tap below to notify the admin.
    </div>
    <a href="mailto:ajvillan22@yahoo.com?subject=Fantasy%20Baseball%20-%20Update%20Cookies"
       style="
           display:inline-block;
           background:#dc2626;
           color:#ffffff;
           font-weight:700;
           font-size:0.9rem;
           padding:10px 24px;
           border-radius:8px;
           text-decoration:none;
           letter-spacing:0.04em;
       ">
      Email Admin
    </a>
  </div>
</div>
""", unsafe_allow_html=True)
    st.stop()


def show_setup_instructions(error_msg: str):
    st.error("Setup Required")
    st.markdown(f"**{error_msg}**")
    st.markdown("""
## Quick Setup Guide

### Step 1 — Get your ESPN cookies
1. Go to [fantasy.espn.com](https://fantasy.espn.com) and log in
2. Open DevTools: **F12** (Windows/Linux) or **Cmd+Option+I** (Mac)
3. Go to **Application** → **Storage** → **Cookies** → `https://www.espn.com`
4. Copy the full value of `espn_s2` (very long alphanumeric string)
5. Copy the full value of `SWID` (looks like `{XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}`)

### Step 2 — Create your `.env` file
```
cp .env.example .env
```
Then edit `.env` and fill in your values:
```
ESPN_S2=AEBxxxxxx...your_full_cookie...
SWID={A1B2C3D4-xxxx-xxxx-xxxx-xxxxxxxxxxxx}
MY_TEAM_NAME=YourTeamName
```
> **Note:** `SWID` must include the curly braces `{ }`.

### Step 3 — Configure your leagues
Edit `config/leagues.json`. Your `league_id` is in the ESPN URL:
`fantasy.espn.com/baseball/league?leagueId=`**`XXXXXXXX`**

```json
[
  {
    "id": "my_league",
    "display_name": "My League Name",
    "league_id": 123456789,
    "year": 2025
  }
]
```

### Step 4 — Restart
Save your changes and refresh this page.
""")


def main():
    # Load credentials
    try:
        creds = auth.get_credentials()
    except EnvironmentError as e:
        show_setup_instructions(str(e))
        return

    # Load league definitions
    try:
        leagues = league_client.load_leagues()
    except Exception as e:
        st.error(f"Could not load config/leagues.json: {e}")
        return

    if not leagues:
        st.error("No leagues configured. Edit `config/leagues.json` to add your leagues.")
        return

    # ── Sidebar ──────────────────────────────────────────────────────────────
    st.sidebar.markdown("""
<div style="padding: 8px 0 16px 0;">
  <div style="font-size:1.05rem; font-weight:900; letter-spacing:0.15em;
              text-transform:uppercase; color:#f1f5f9; line-height:1.2;">
    ⚾ &nbsp;Fantasy
  </div>
  <div style="font-size:1.45rem; font-weight:900; letter-spacing:0.18em;
              text-transform:uppercase; color:#dc2626; line-height:1.2;">
    Baseball
  </div>
  <div style="height:3px; background:linear-gradient(90deg,#dc2626,transparent);
              margin-top:8px; border-radius:2px;"></div>
</div>
""", unsafe_allow_html=True)

    league_names = [lg["display_name"] for lg in leagues]
    selected_name = st.sidebar.selectbox("League", league_names)
    selected_league_cfg = next(lg for lg in leagues if lg["display_name"] == selected_name)

    # Load the selected league (cached per session)
    with st.spinner(f"Loading {selected_name}..."):
        try:
            league = league_client.get_league(
                league_id=selected_league_cfg["league_id"],
                year=selected_league_cfg["year"],
                espn_s2=creds["espn_s2"],
                swid=creds["swid"],
            )
        except Exception as e:
            if _is_auth_error(e):
                show_cookie_expired_page()
                return
            st.error(f"Could not connect to ESPN for **{selected_name}**: {e}")
            st.info("This usually means your ESPN cookies have expired. Re-copy them from your browser and update `.env`.")
            return

    # Prorate counting-stat colour thresholds to where we are in the season
    utils.set_season_fraction(utils.compute_season_fraction(league))

    st.sidebar.divider()

    # Sidebar — page navigation
    page = st.sidebar.radio(
        "Navigate",
        ["Standings", "Teams", "Current Matchup", "Free Agents", "Player Rater", "Transactions"],
    )

    if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
        st.cache_resource.clear()
        st.cache_data.clear()
        st.rerun()

    st.sidebar.divider()

    week_num = getattr(league, "currentMatchupPeriod", "?")
    season_year = selected_league_cfg["year"]
    now_str = datetime.now().strftime("%I:%M %p")
    st.sidebar.markdown(f"""
<div style="font-size:0.72rem; color:#374151; line-height:1.8; padding: 4px 0;">
  <span style="color:#4b5563;">SEASON</span>&nbsp;&nbsp;
  <span style="color:#94a3b8; font-weight:600;">{season_year}</span><br/>
  <span style="color:#4b5563;">WEEK</span>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  <span style="color:#94a3b8; font-weight:600;">{week_num}</span><br/>
  <span style="color:#4b5563;">CACHED</span>&nbsp;
  <span style="color:#4b5563;">{now_str}</span>
</div>
""", unsafe_allow_html=True)

    # Top banner
    st.markdown(f"""
<div class="top-banner">
  <div class="banner-icon">⚾</div>
  <div class="banner-title">Fantasy Baseball</div>
  <div class="banner-sub">{selected_name} &nbsp;·&nbsp; {season_year} Season &nbsp;·&nbsp; Week {week_num}</div>
</div>
""", unsafe_allow_html=True)

    # Route to page
    my_team_name = creds.get("my_team_name", "")

    if page == "Standings":
        standings.render(league, my_team_name)
    elif page == "Teams":
        my_team.render(league, my_team_name)
    elif page == "Current Matchup":
        matchup.render(league, my_team_name)
    elif page == "Free Agents":
        free_agents.render(league, my_team_name)
    elif page == "Player Rater":
        player_rater.render(league, my_team_name)
    elif page == "Transactions":
        transactions.render(league)


if __name__ == "__main__":
    main()
