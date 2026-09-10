#!/usr/bin/env python3

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "config.json"
OUTPUT_PATH = ROOT / "public" / "data" / "roma.json"

FOOTBALL_DATA_BASE_URL = "https://api.football-data.org/v4"
THESPORTSDB_BASE_URL = "https://www.thesportsdb.com/api/v1/json"


def env_value(name):
    value = (os.environ.get(name) or "").strip()

    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")

    return value


def get_json(url, headers=None, params=None, timeout=30):
    response = requests.get(
        url,
        headers=headers or {},
        params=params or {},
        timeout=timeout
    )

    if response.status_code != 200:
        preview = response.text[:500].replace("\n", " ")
        raise RuntimeError(
            f"Request failed: {response.status_code} for {response.url}. "
            f"Response: {preview}"
        )

    return response.json()


def get_optional_json(url, headers=None, params=None, timeout=30):
    try:
        return get_json(url, headers=headers, params=params, timeout=timeout)
    except Exception as error:
        print(f"Optional provider request failed: {error}")
        return None


def iso_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def safe_text(value, fallback=""):
    return value if isinstance(value, str) else fallback


def normalize_team(team):
    if not team:
        return None

    return {
        "id": team.get("id"),
        "name": team.get("name"),
        "short_name": team.get("shortName"),
        "tla": team.get("tla"),
        "crest": team.get("crest"),
        "website": team.get("website"),
        "founded": team.get("founded"),
        "venue": team.get("venue"),
        "club_colors": team.get("clubColors"),
        "area": {
            "id": team.get("area", {}).get("id"),
            "name": team.get("area", {}).get("name"),
            "code": team.get("area", {}).get("code")
        }
    }


def normalize_person(person):
    if not person:
        return None

    return {
        "id": person.get("id"),
        "name": person.get("name"),
        "short_name": person.get("shortName"),
        "tla": person.get("tla"),
        "crest": person.get("crest")
    }


def normalize_score(score):
    score = score or {}

    return {
        "winner": score.get("winner"),
        "duration": score.get("duration"),
        "full_time": {
            "home": score.get("fullTime", {}).get("home"),
            "away": score.get("fullTime", {}).get("away")
        },
        "half_time": {
            "home": score.get("halfTime", {}).get("home"),
            "away": score.get("halfTime", {}).get("away")
        },
        "extra_time": {
            "home": score.get("extraTime", {}).get("home"),
            "away": score.get("extraTime", {}).get("away")
        },
        "penalties": {
            "home": score.get("penalties", {}).get("home"),
            "away": score.get("penalties", {}).get("away")
        }
    }


def normalize_match(match):
    if not match:
        return None

    competition = match.get("competition", {})

    return {
        "id": match.get("id"),
        "utc_date": match.get("utcDate"),
        "status": match.get("status"),
        "matchday": match.get("matchday"),
        "stage": match.get("stage"),
        "group": match.get("group"),
        "last_updated": match.get("lastUpdated"),
        "competition": {
            "id": competition.get("id"),
            "name": competition.get("name"),
            "code": competition.get("code"),
            "type": competition.get("type"),
            "emblem": competition.get("emblem")
        },
        "home_team": normalize_person(match.get("homeTeam")),
        "away_team": normalize_person(match.get("awayTeam")),
        "score": normalize_score(match.get("score"))
    }


def normalize_squad(squad):
    normalized = []

    for player in squad or []:
        normalized.append({
            "id": player.get("id"),
            "name": player.get("name"),
            "position": player.get("position"),
            "date_of_birth": player.get("dateOfBirth"),
            "nationality": player.get("nationality"),
            "shirt_number": player.get("shirtNumber"),
            "market_value": player.get("marketValue"),
            "last_updated": player.get("lastUpdated")
        })

    return sorted(
        normalized,
        key=lambda player: (
            player.get("position") or "",
            player.get("shirt_number") or 999,
            player.get("name") or ""
        )
    )


def find_roma_standing(standings_payload, team_id):
    standings = standings_payload.get("standings", [])

    for standing_group in standings:
        table = standing_group.get("table", [])

        for row in table:
            team = row.get("team", {})

            if team.get("id") == team_id:
                return {
                    "stage": standing_group.get("stage"),
                    "type": standing_group.get("type"),
                    "group": standing_group.get("group"),
                    "position": row.get("position"),
                    "played_games": row.get("playedGames"),
                    "form": row.get("form"),
                    "won": row.get("won"),
                    "draw": row.get("draw"),
                    "lost": row.get("lost"),
                    "points": row.get("points"),
                    "goals_for": row.get("goalsFor"),
                    "goals_against": row.get("goalsAgainst"),
                    "goal_difference": row.get("goalDifference"),
                    "team": normalize_person(team)
                }

    return None


def fetch_artwork(api_key, team_search):
    url = f"{THESPORTSDB_BASE_URL}/{api_key}/searchteams.php"
    payload = get_optional_json(url, params={"t": team_search})

    if not payload:
        return {
            "provider": "TheSportsDB",
            "available": False
        }

    teams = payload.get("teams") or []

    if not teams:
        return {
            "provider": "TheSportsDB",
            "available": False
        }

    team = next(
        (
            item for item in teams
            if safe_text(item.get("strTeam")).lower() in {"as roma", "roma"}
        ),
        teams[0]
    )

    return {
        "provider": "TheSportsDB",
        "available": True,
        "team_id": team.get("idTeam"),
        "name": team.get("strTeam"),
        "league": team.get("strLeague"),
        "badge": team.get("strBadge"),
        "logo": team.get("strLogo"),
        "jersey": team.get("strEquipment"),
        "fanart_1": team.get("strFanart1"),
        "fanart_2": team.get("strFanart2"),
        "fanart_3": team.get("strFanart3"),
        "fanart_4": team.get("strFanart4"),
        "stadium": team.get("strStadium"),
        "stadium_thumb": team.get("strStadiumThumb")
    }


def main():
    football_data_token = env_value("FOOTBALL_DATA_TOKEN")
    thesportsdb_api_key = env_value("THESPORTSDB_API_KEY")

    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        config = json.load(file)

    team_config = config["team"]
    competitions_config = config["competitions"]

    team_id = team_config["football_data_team_id"]
    team_search = team_config["the_sports_db_search"]

    football_headers = {
        "X-Auth-Token": football_data_token,
        "Accept": "application/json"
    }

    print("Fetching AS Roma team profile...")
    team_payload = get_json(
        f"{FOOTBALL_DATA_BASE_URL}/teams/{team_id}",
        headers=football_headers
    )

    print("Fetching last completed match...")
    finished_payload = get_json(
        f"{FOOTBALL_DATA_BASE_URL}/teams/{team_id}/matches",
        headers=football_headers,
        params={
            "status": "FINISHED",
            "limit": 1
        }
    )

    print("Fetching next scheduled match...")
    scheduled_payload = get_json(
        f"{FOOTBALL_DATA_BASE_URL}/teams/{team_id}/matches",
        headers=football_headers,
        params={
            "status": "SCHEDULED",
            "limit": 1
        }
    )

    print("Fetching recent Roma fixtures...")
    recent_payload = get_json(
        f"{FOOTBALL_DATA_BASE_URL}/teams/{team_id}/matches",
        headers=football_headers,
        params={
            "status": "FINISHED",
            "limit": 5
        }
    )

    print("Fetching upcoming Roma fixtures...")
    upcoming_payload = get_json(
        f"{FOOTBALL_DATA_BASE_URL}/teams/{team_id}/matches",
        headers=football_headers,
        params={
            "status": "SCHEDULED",
            "limit": 5
        }
    )

    print("Fetching Serie A standings...")
    serie_a_payload = get_json(
        f"{FOOTBALL_DATA_BASE_URL}/competitions/SA/standings",
        headers=football_headers
    )

    print("Fetching AS Roma artwork...")
    artwork = fetch_artwork(thesportsdb_api_key, team_search)

    squad = normalize_squad(team_payload.get("squad", []))
    last_match = normalize_match(
        (finished_payload.get("matches") or [None])[0]
    )
    next_match = normalize_match(
        (scheduled_payload.get("matches") or [None])[0]
    )
    recent_matches = [
        normalize_match(match)
        for match in recent_payload.get("matches", [])
    ]
    upcoming_matches = [
        normalize_match(match)
        for match in upcoming_payload.get("matches", [])
    ]

    serie_a = competitions_config["serie_a"]

    output = {
        "meta": {
            "project": config["project"]["name"],
            "generated_at_utc": iso_now(),
            "timezone": config["project"]["timezone"],
            "default_language": config["project"]["default_language"],
            "supported_languages": config["project"]["supported_languages"],
            "show_squad": config["project"].get("show_squad", False),
            "source_status": {
                "football_data": "ok",
                "the_sports_db_artwork": (
                    "ok" if artwork.get("available") else "unavailable"
                ),
                "bigballsdata": "not_yet_integrated"
            }
        },
        "team": {
            "display_name_en": team_config["display_name_en"],
            "display_name_bg": team_config["display_name_bg"],
            "football_data": normalize_team(team_payload),
            "artwork": artwork
        },
        "last_match": last_match,
        "next_match": next_match,
        "recent_matches": recent_matches,
        "upcoming_matches": upcoming_matches,
        "standings": {
            "serie_a": {
                "competition_code": serie_a["football_data_code"],
                "name_en": serie_a["name_en"],
                "name_bg": serie_a["name_bg"],
                "table_updated_at": serie_a_payload.get("lastUpdated"),
                "roma": find_roma_standing(serie_a_payload, team_id)
            }
        },
        "squad": squad,
        "provider_notes": {
            "football_data": (
                "Primary source for Roma fixtures, results, "
                "squad and Serie A standings."
            ),
            "the_sports_db": (
                "Artwork enrichment source for badge, logo, "
                "jersey and fan-art links."
            ),
            "bigballsdata": (
                "Reserved for future Serie A events, lineups, "
                "advanced match statistics and player statistics."
            )
        }
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(output, file, ensure_ascii=False, indent=2)

    print(f"Created: {OUTPUT_PATH.relative_to(ROOT)}")
    print(f"Squad members: {len(squad)}")
    print(
        "Artwork available: "
        f"{'yes' if artwork.get('available') else 'no'}"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
