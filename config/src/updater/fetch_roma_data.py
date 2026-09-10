import os
import json
import requests
from datetime import datetime, timezone

BASE_URL = "https://api.sportmonks.com/v3/football"
TOKEN = os.environ["SPORTMONKS_TOKEN"]

HEADERS = {
    "Accept": "application/json",
}

def req(path, params=None):
    url = f"{BASE_URL}{path}"
    params = params or {}
    params["api_token"] = TOKEN
    resp = requests.get(url, params=params, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.json()

def main():
    # Load config
    with open("config/config.json", "r", encoding="utf-8") as f:
        cfg = json.load(f)

    team_id = cfg["team"]["id"]

    # Example: get team info
    team_resp = req(f"/teams/{team_id}", {"includes": "country,venue"})
    team_data = team_resp["data"]

    # Fixtures: last and next for this team across all competitions
    # Use fixtures endpoint filtered by team
    fixtures_resp = req(
        "/fixtures",
        {
            "filter[team_id]": team_id,
            "includes": "league,season,stage,round,state,participants,events",
            "per_page": 10,
        },
    )
    fixtures = fixtures_resp["data"]

    # Sort by starting_at
    fixtures_sorted = sorted(
        fixtures,
        key=lambda x: x["starting_at"],
    )

    now = datetime.now(timezone.utc)
    past = [f for f in fixtures_sorted if f["starting_at"] < now.isoformat()]
    future = [f for f in fixtures_sorted if f["starting_at"] >= now.isoformat()]

    last_match = past[-1] if past else None
    next_match = future[0] if future else None

    # Standings: for each competition, get current season then standings
    standings = []
    for comp in cfg["competitions"]:
        # Get seasons for this league
        seasons_resp = req(f"/leagues/{comp['id']}/seasons")
        seasons = seasons_resp["data"]
        # pick current season (heuristic: latest end_date or is_current)
        current_season = None
        for s in seasons:
            if s.get("is_current"):
                current_season = s
                break
        if not current_season and seasons:
            current_season = seasons[-1]
        if not current_season:
            continue

        # Standings for this season
        std_resp = req(
            f"/seasons/{current_season['id']}/standings",
            {
                "includes": "team,league,season"
            },
        )
        std_data = std_resp["data"]
        # filter to our team row
        team_row = None
        for row in std_data:
            if row["team_id"] == team_id:
                team_row = row
                break

        standings.append({
            "competition_id": comp["id"],
            "competition_name_en": comp["name_en"],
            "competition_name_bg": comp["name_bg"],
            "season_id": current_season["id"],
            "row": team_row,
        })

    # Squad: players for this team
    squad_resp = req(
        f"/teams/{team_id}/squad",
        {
            "includes": "player,position,country"
        },
    )
    squad = squad_resp["data"]

    # Build normalized JSON
    roma_data = {
        "team": team_data,
        "last_match": last_match,
        "next_match": next_match,
        "standings": standings,
        "squad": squad,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    # Write to data/roma.json
    with open("data/roma.json", "w", encoding="utf-8") as f:
        json.dump(roma_data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
