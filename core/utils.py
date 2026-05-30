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

# Full-season usage baselines for per-player participation scaling.
# Used to compute how much of a "full season" each individual player has accumulated,
# so injured players returning mid-season are graded on pace rather than raw totals.
FULL_SEASON_AB = 550  # typical full-season at-bats for a position player
_PITCHER_STAT_FULL_OUTS = {  # expected full-season outs per pitching counting stat
    "K":  540,   # 180 IP, starter-weighted
    "W":  540,   # 180 IP, starter-weighted
    "SV": 180,   # 60 IP, closer-weighted
}

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
    """Return effective season fraction for one player based on their accumulated usage.

    Injured players who missed time have fewer AB/OUTS than healthy peers. Using their
    personal participation fraction (instead of the global season fraction) means their
    counting-stat thresholds are scaled to their actual playing time, so they're graded
    on pace rather than penalized for missed games. Capped at _season_fraction so a
    player can't look better than the season position allows.
    """
    if stat not in COUNTING_STATS:
        return _season_fraction
    if stat in _PITCHER_STAT_FULL_OUTS:
        outs = float(bd.get("OUTS", 0) or 0)
        frac = outs / _PITCHER_STAT_FULL_OUTS[stat]
    else:
        ab = float(bd.get("AB", 0) or 0)
        frac = ab / FULL_SEASON_AB
    return max(0.05, min(_season_fraction, frac))


def stat_color_style(stat: str, value, bd: dict = None) -> str:
    """Return a CSS color+weight string for a stat value. Empty string if unknown stat.

    Pass bd (the player's breakdown dict) for per-player views so injured players with
    fewer AB/OUTS are graded against appropriately scaled thresholds. Omit bd (or pass
    None) for team-level aggregates, which use the global season fraction instead.
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
