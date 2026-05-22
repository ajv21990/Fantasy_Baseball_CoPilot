# Fantasy Baseball CoPilot ⚾

A local dashboard for ESPN fantasy baseball leagues. Browse standings, scout free agents, track your roster, and analyze your current matchup — all in one dark-themed UI that runs in your browser.

> Built for private ESPN leagues using H2H Most Categories scoring.

---

## Features

- **Standings** — W-L table, category win/loss records by team, and season stats ranked across the league
- **Teams** — Browse any team's full roster with stat color-coding; defaults to your own team
- **Current Matchup** — Category-by-category breakdown of your active week with live scores
- **Free Agents** — Smart pickup tool: identifies your 3 weakest scoring categories, then surfaces the best available free agents *and* trade targets to address them
- **Transactions** — Recent adds, drops, waiver claims, and trades across the league

---

## Requirements

- Python 3.9 or later
- An ESPN Fantasy Baseball account with access to the league
- The league must be from 2019 or later (ESPN API limitation for free agents / transactions)

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/ajv21990/Fantasy_Baseball_CoPilot.git
cd Fantasy_Baseball_CoPilot
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate        # Mac / Linux
venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## Configuration

### Step 1 — Get your ESPN cookies

The ESPN API requires two browser cookies to authenticate. These are tied to your account.

1. Go to [fantasy.espn.com](https://fantasy.espn.com) and log in
2. Open DevTools:
   - Mac: **Cmd + Option + I**
   - Windows / Linux: **F12**
3. Navigate to **Application** → **Storage** → **Cookies** → `https://www.espn.com`
4. Find and copy:
   - `espn_s2` — a long alphanumeric string
   - `SWID` — looks like `{XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}` (include the curly braces)

> **Note:** These cookies expire periodically. If the app stops loading data, re-copy them from your browser and update your `.env`.

### Step 2 — Create your `.env` file

```bash
cp .env.example .env
```

Open `.env` and fill in your values:

```
ESPN_S2=AEBxxxxxx...your_full_cookie_value...
SWID={A1B2C3D4-XXXX-XXXX-XXXX-XXXXXXXXXXXX}
MY_TEAM_NAME=Your Team Name
```

`MY_TEAM_NAME` is used to highlight your team across all pages and power the personalized Free Agents analysis. It only needs to partially match your team name (case-insensitive).

### Step 3 — Configure your league(s)

Edit `config/leagues.json`. Your `league_id` is in the ESPN URL when you're on your league's page:

```
fantasy.espn.com/baseball/league?leagueId=XXXXXXXX
```

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

Add multiple objects to the array to support multiple leagues — the sidebar will show a dropdown to switch between them.

---

## Running the app

```bash
streamlit run app.py
```

The dashboard opens at [http://localhost:8501](http://localhost:8501).

---

## Sharing with league-mates

Each person needs their own ESPN cookies (they're account-specific), so the easiest path for sharing is:

1. Everyone clones this repo
2. Each person creates their own `.env` with their credentials and team name
3. Each person runs `streamlit run app.py` locally

For a hosted version (one URL for the whole league), see [Streamlit Community Cloud](https://streamlit.io/cloud) — free tier, connects directly to this GitHub repo. Credentials are stored as Streamlit Secrets instead of a `.env` file.

---

## Tech stack

| Library | Purpose |
|---|---|
| [Streamlit](https://streamlit.io) | Web UI framework |
| [espn-api](https://github.com/cwendt94/espn-api) | Unofficial ESPN Fantasy API client |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | `.env` file loading |
| [pandas](https://pandas.pydata.org) | Data manipulation for standings tables |
