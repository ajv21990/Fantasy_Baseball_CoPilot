"""Storage layer for the Player Rater feature.

The ONLY module that talks to the database. The UI (pages/player_rater.py and the
Player Rater control on pages/my_team.py) depends solely on the public functions
below, so the backend can be swapped without touching the UI.

Backend selection:
  - If st.secrets has [connections.supabase] url  → use that Postgres database.
  - Otherwise                                     → fall back to a local SQLite
    file (data/player_rater.db) so the feature works locally with zero setup.

SQL is kept portable (plain INSERT ... ON CONFLICT, timestamps passed from Python)
so the same code runs on both Postgres and SQLite. Tables are auto-created on first
use, so no manual migration step is required on either backend.
"""

import os
import datetime as dt

import streamlit as st
from sqlalchemy import create_engine, text


_CREATE_LISTINGS = """
CREATE TABLE IF NOT EXISTS listings (
    team        TEXT    NOT NULL,
    player_id   INTEGER NOT NULL,
    player_name TEXT    NOT NULL,
    created_at  TEXT    NOT NULL,
    PRIMARY KEY (team, player_id)
)
"""

_CREATE_RATINGS = """
CREATE TABLE IF NOT EXISTS ratings (
    rater_team TEXT    NOT NULL,
    player_id  INTEGER NOT NULL,
    stars      INTEGER NOT NULL,
    updated_at TEXT    NOT NULL,
    PRIMARY KEY (rater_team, player_id)
)
"""


def _db_url() -> str:
    """Postgres URL from secrets if configured, else a local SQLite file."""
    try:
        url = st.secrets["connections"]["supabase"]["url"]
        if url:
            return url
    except Exception:
        pass
    # Anchor the SQLite file to the project root (parent of this core/ dir) using an
    # absolute path. A relative "data/..." would resolve against Streamlit's current
    # working directory, which may differ from the project and be read-only.
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(root, "data")
    os.makedirs(data_dir, exist_ok=True)
    return f"sqlite:///{os.path.join(data_dir, 'player_rater.db')}"


@st.cache_resource(show_spinner=False)
def _engine():
    """Create (once per session) the SQLAlchemy engine and ensure tables exist."""
    url = _db_url()
    if url.startswith("sqlite"):
        eng = create_engine(url, connect_args={"check_same_thread": False})
    else:
        eng = create_engine(url, pool_pre_ping=True)
    with eng.begin() as c:
        c.execute(text(_CREATE_LISTINGS))
        c.execute(text(_CREATE_RATINGS))
    return eng


def _now() -> str:
    return dt.datetime.utcnow().isoformat(timespec="seconds")


# ── Listings ──────────────────────────────────────────────────────────────────

def get_listings() -> list[dict]:
    """All trade-block listings: [{team, player_id, player_name, created_at}]."""
    sql = text("SELECT team, player_id, player_name, created_at FROM listings")
    with _engine().connect() as c:
        return [dict(r) for r in c.execute(sql).mappings().all()]


def list_player(team: str, player_id: int, player_name: str) -> None:
    """Add a player to `team`'s list. No-op if already listed."""
    sql = text(
        "INSERT INTO listings (team, player_id, player_name, created_at) "
        "VALUES (:t, :pid, :name, :ts) "
        "ON CONFLICT (team, player_id) DO NOTHING"
    )
    with _engine().begin() as c:
        c.execute(sql, {"t": team, "pid": int(player_id),
                        "name": player_name, "ts": _now()})


def unlist_player(team: str, player_id: int) -> None:
    """Remove a player from `team`'s list AND clear that player's ratings."""
    with _engine().begin() as c:
        c.execute(text("DELETE FROM listings WHERE team = :t AND player_id = :pid"),
                  {"t": team, "pid": int(player_id)})
        c.execute(text("DELETE FROM ratings WHERE player_id = :pid"),
                  {"pid": int(player_id)})


# ── Ratings ───────────────────────────────────────────────────────────────────

def get_ratings() -> list[dict]:
    """All ratings: [{rater_team, player_id, stars, updated_at}]."""
    sql = text("SELECT rater_team, player_id, stars, updated_at FROM ratings")
    with _engine().connect() as c:
        return [dict(r) for r in c.execute(sql).mappings().all()]


def set_rating(rater_team: str, player_id: int, stars: int) -> None:
    """Insert or update the single (rater_team, player_id) rating (1-5 stars)."""
    sql = text(
        "INSERT INTO ratings (rater_team, player_id, stars, updated_at) "
        "VALUES (:rt, :pid, :s, :ts) "
        "ON CONFLICT (rater_team, player_id) DO UPDATE SET stars = :s, updated_at = :ts"
    )
    with _engine().begin() as c:
        c.execute(sql, {"rt": rater_team, "pid": int(player_id),
                        "s": int(stars), "ts": _now()})


def delete_rating(rater_team: str, player_id: int) -> None:
    """Remove this rater's rating for one player (no-op if none exists)."""
    sql = text("DELETE FROM ratings WHERE rater_team = :rt AND player_id = :pid")
    with _engine().begin() as c:
        c.execute(sql, {"rt": rater_team, "pid": int(player_id)})


def ratings_for(player_id: int) -> list[dict]:
    """All ratings for one player: [{rater_team, stars, updated_at}]."""
    sql = text("SELECT rater_team, stars, updated_at FROM ratings WHERE player_id = :pid")
    with _engine().connect() as c:
        return [dict(r) for r in c.execute(sql, {"pid": int(player_id)}).mappings().all()]
