import html as _html
import math

RATE_STATS = {"AVG", "OBP", "SLG", "OPS", "ERA", "WHIP", "BAA"}
TWO_DP_STATS = {"ERA"}
THREE_DP_STATS = {"AVG", "OBP", "SLG", "OPS", "WHIP", "BAA"}

# Only the categories used in this league
BATTER_STATS = ["R", "HR", "RBI", "SB", "OPS"]
PITCHER_STATS = ["K", "W", "SV", "ERA", "WHIP"]
LEAGUE_CATS = set(BATTER_STATS + PITCHER_STATS)

# Full-season individual player quality thresholds — (below_avg, above_avg).
# Counting stats are prorated by _season_fraction at runtime so the bands
# stay meaningful early in the year (e.g. 18 R in late May ≈ on pace for 65).
# Rate stats (OPS, ERA, WHIP) are time-invariant and never scaled.
STAT_THRESHOLDS = {
    "R":    (65,    95),
    "HR":   (18,    32),
    "RBI":  (60,    90),
    "SB":   (10,    25),
    "OPS":  (0.750, 0.880),
    "K":    (80,    150),
    "W":    (8,     14),
    "SV":   (15,    35),
    "ERA":  (3.50,  4.50),
    "WHIP": (1.15,  1.35),
}
LOWER_IS_BETTER = {"ERA", "WHIP"}
COUNTING_STATS  = {"R", "HR", "RBI", "SB", "K", "W", "SV"}

# Full-season usage baseline for per-player participation scaling (batters only).
# Used to compute how much of a "full season" a hitter has accumulated, so injured
# batters returning mid-season are graded on pace rather than raw totals.
# Pitcher counting stats are intentionally NOT scaled this way — see
# compute_player_fraction for why.
FULL_SEASON_AB = 550  # typical full-season at-bats for a position player

# Season progress fraction (0.0–1.0).  Set once per page load via
# set_season_fraction() after the league object is available.
_season_fraction: float = 1.0


def compute_season_fraction(league) -> float:
    """Return fraction of the season elapsed based on ESPN scoring period IDs."""
    try:
        current = getattr(league, "scoringPeriodId", None)
        first   = getattr(league, "firstScoringPeriod", 1)
        final   = getattr(league, "finalScoringPeriod", None)
        if current is not None and final and final > first:
            return max(0.05, min(1.0, (current - first) / (final - first)))
    except Exception:
        pass
    return 1.0


def set_season_fraction(fraction: float) -> None:
    """Update the module-level season fraction used by stat_color_style."""
    global _season_fraction
    _season_fraction = max(0.05, min(1.0, float(fraction)))


def compute_player_fraction(bd: dict, stat: str) -> float:
    """Return effective season fraction for one player based on accumulated usage.

    Only batter counting stats (R, HR, RBI, SB) are scaled by the player's personal
    participation (AB / full-season AB). An injured hitter who missed time has fewer
    AB than healthy peers, so scaling their thresholds down grades them on pace rather
    than penalizing missed games. Capped at _season_fraction so a player can't look
    better than the season position allows.

    Pitcher counting stats (K, W, SV) are deliberately NOT scaled per-player: innings
    pitched vary enormously by role (a starter throws 3-4x a reliever's volume), so
    normalizing by individual IP turns these volume categories into rate stats and
    grades nearly every pitcher green. They fall back to the global season fraction.
    """
    if stat not in COUNTING_STATS or stat in PITCHER_STATS:
        return _season_fraction
    ab = float(bd.get("AB", 0) or 0)
    frac = ab / FULL_SEASON_AB
    return max(0.05, min(_season_fraction, frac))


def stat_color_style(stat: str, value, bd: dict = None) -> str:
    """Return a CSS color+weight string for a stat value. Empty string if unknown stat.

    Pass bd (the player's breakdown dict) for per-player views so injured hitters with
    fewer AB are graded against appropriately scaled thresholds. Omit bd (or pass None)
    for team-level aggregates, which use the global season fraction instead.
    """
    if stat not in STAT_THRESHOLDS:
        return ""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return ""
    if math.isnan(v) or math.isinf(v):
        return ""

    lo, hi = STAT_THRESHOLDS[stat]
    if stat in COUNTING_STATS:
        fraction = compute_player_fraction(bd, stat) if bd is not None else _season_fraction
        lo = lo * fraction
        hi = hi * fraction

    if stat in LOWER_IS_BETTER:
        if v <= lo:
            return "color:#22c55e;font-weight:700"
        if v >= hi:
            return "color:#ef4444;font-weight:700"
        return "color:#eab308;font-weight:600"
    else:
        if v >= hi:
            return "color:#22c55e;font-weight:700"
        if v < lo:
            return "color:#ef4444;font-weight:700"
        return "color:#eab308;font-weight:600"

PITCHER_POSITIONS = {"SP", "RP", "P"}

VALID_POSITIONS = ["C", "1B", "2B", "3B", "SS", "OF", "SP", "RP", "UTIL", "DH"]


def format_stat(name: str, value) -> str:
    if value is None:
        return "-"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)

    if math.isnan(v) or math.isinf(v):
        return "-"

    if name in THREE_DP_STATS:
        return f"{v:.3f}"
    if name in TWO_DP_STATS:
        return f"{v:.2f}"
    if v == int(v):
        return str(int(v))
    return f"{v:.1f}"


def result_color(result: str) -> str:
    if result == "WIN":
        return "green"
    if result == "LOSS":
        return "red"
    return "gray"


def result_arrow(result: str) -> str:
    if result == "WIN":
        return "▲"
    if result == "LOSS":
        return "▼"
    return "—"


def injury_badge(player) -> str:
    status = getattr(player, "injuryStatus", None) or ""
    mapping = {
        "INJURY_RESERVE": "IL",
        "FIFTEEN_DAY_DL": "IL15",
        "SIXTY_DAY_DL": "IL60",
        "DAY_TO_DAY": "DTD",
        "OUT": "OUT",
        "SUSPENSION": "SUSP",
    }
    return mapping.get(status, "")


def is_pitcher(player) -> bool:
    pos = getattr(player, "eligibleSlots", []) or []
    return any(p in PITCHER_POSITIONS for p in pos)


def position_options() -> list[str]:
    return VALID_POSITIONS


# ── Shared HTML utilities (used by multiple page modules) ─────────────────────

# Table header cell style — used in standings, my_team, free_agents
TABLE_HEADER_STYLE = (
    'background:#0d1a2e;color:#7a8fa6;font-size:0.7rem;text-transform:uppercase;'
    'letter-spacing:0.08em;padding:8px 12px;border-bottom:2px solid #1e2d40;font-weight:700;'
)


def get_player_breakdown(player) -> dict:
    """Extract the current-season stat breakdown dict from an espn-api player object."""
    raw = getattr(player, "stats", {}) or {}
    bd = raw.get(0, {})
    if isinstance(bd, dict):
        bd = bd.get("breakdown", {})
    return bd if isinstance(bd, dict) else {}


def ordinal(n) -> str:
    """Return an ordinal string for an integer (1 → '1st', 11 → '11th', etc.)."""
    if n is None:
        return "—"
    n = int(n)
    if 11 <= n % 100 <= 13:
        return f"{n}th"
    return f"{n}{('th', 'st', 'nd', 'rd', 'th')[min(n % 10, 4)]}"


def pos_pill_html(pos: str, is_pitcher: bool) -> str:
    """Return an HTML <span> pill badge for a player's position."""
    if is_pitcher:
        s = "background:rgba(249,115,22,0.15);color:#f97316;border:1px solid rgba(249,115,22,0.3);"
    else:
        s = "background:rgba(59,130,246,0.15);color:#60a5fa;border:1px solid rgba(59,130,246,0.3);"
    return (
        f'<span style="border-radius:6px;padding:2px 7px;font-size:0.68rem;'
        f'font-weight:700;{s}">{_html.escape(pos) if pos else "—"}</span>'
    )


def injury_badge_html(val: str) -> str:
    """Return an HTML <span> badge for an injury status string, or '' if healthy."""
    if not val:
        return ""
    if val in ("IL", "IL15", "IL60", "OUT"):
        style = (
            "background:rgba(239,68,68,0.25);color:#ef4444;"
            "border:1px solid rgba(239,68,68,0.5);"
        )
    elif val == "DTD":
        style = (
            "background:rgba(249,115,22,0.25);color:#f97316;"
            "border:1px solid rgba(249,115,22,0.5);"
        )
    elif val == "SUSP":
        style = (
            "background:rgba(168,85,247,0.25);color:#a855f7;"
            "border:1px solid rgba(168,85,247,0.5);"
        )
    else:
        return ""
    return (
        f'<span style="border-radius:12px;padding:2px 9px;font-size:0.72rem;'
        f'font-weight:700;letter-spacing:0.05em;{style}">{val}</span>'
    )
