import os
from dotenv import load_dotenv

load_dotenv()

def get_credentials() -> dict:
    espn_s2 = os.getenv("ESPN_S2")
    swid = os.getenv("SWID")
    my_team_name = os.getenv("MY_TEAM_NAME", "")
    admin_email = os.getenv("ADMIN_EMAIL", "")

    missing = []
    if not espn_s2 or espn_s2 == "your_espn_s2_cookie_value_here":
        missing.append("ESPN_S2")
    if not swid or swid == "{your-swid-value-in-braces-here}":
        missing.append("SWID")

    if missing:
        raise EnvironmentError(
            f"Missing ESPN credentials: {', '.join(missing)}\n\n"
            "To fix this:\n"
            "1. Log into fantasy.espn.com\n"
            "2. Open DevTools (F12) → Application → Cookies → https://www.espn.com\n"
            "3. Copy 'espn_s2' and 'SWID' values\n"
            "4. Copy .env.example → .env and fill them in"
        )

    return {"espn_s2": espn_s2, "swid": swid, "my_team_name": my_team_name, "admin_email": admin_email}
