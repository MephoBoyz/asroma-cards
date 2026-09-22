#!/usr/bin/env python3

import html
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "config.json"
DATA_PATH = ROOT / "public" / "data" / "roma.json"
OUTPUT_DIR = ROOT / "public" / "cards"
TEMP_DIR = ROOT / ".generated" / "card-html"

WIDTH = 1080
HEIGHT = 1350
ROME_TIMEZONE = ZoneInfo("Europe/Rome")
BULGARIA_TIMEZONE = ZoneInfo("Europe/Sofia")

TEXT = {
    "en": {
        "last_match": "LAST MATCH",
        "next_match": "NEXT MATCH",
        "full_time": "FULL TIME",
        "vs": "VS",
        "home": "HOME",
        "away": "AWAY",
        "matchday": "MATCHDAY",
        "standings": "STANDINGS",
        "recent_form": "RECENT FORM",
        "place": "PLACE",
        "points": "POINTS",
        "played": "PLAYED",
        "wins": "WINS",
        "draws": "DRAWS",
        "losses": "LOSSES",
        "goals": "GOALS",
        "goal_difference": "GOAL DIFFERENCE",
        "wins_short": "W",
        "draws_short": "D",
        "losses_short": "L",
        "in_construction": "GIALLOROSSI · AS ROMA DATA"
    },
    "bg": {
        "last_match": "ПОСЛЕДЕН МАЧ",
        "next_match": "СЛЕДВАЩ МАЧ",
        "full_time": "КРАЕН РЕЗУЛТАТ",
        "vs": "СРЕЩУ",
        "home": "ДОМАКИН",
        "away": "ГОСТ",
        "matchday": "КРЪГ",
        "standings": "КЛАСИРАНЕ",
        "recent_form": "ПОСЛЕДНА ФОРМА",
        "place": "МЯСТО",
        "points": "ТОЧКИ",
        "played": "ИЗИГРАНИ",
        "wins": "ПОБЕДИ",
        "draws": "РАВНИ",
        "losses": "ЗАГУБИ",
        "goals": "ГОЛОВЕ",
        "goal_difference": "ГОЛОВА РАЗЛИКА",
        "wins_short": "П",
        "draws_short": "Р",
        "losses_short": "З",
        "in_construction": "GIALLOROSSI · AS ROMA DATA"
    }
}


def safe(value, fallback="—"):
    if value is None:
        return fallback

    value = str(value).strip()
    return value if value else fallback


def escape(value):
    return html.escape(safe(value))


def parse_date(value):
    if not value:
        return None

    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def format_date(value, language):
    utc_date = parse_date(value)

    if not utc_date:
        return "—"

    rome_date = utc_date.astimezone(ROME_TIMEZONE)

    months_en = [
        "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
        "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"
    ]
    months_bg = [
        "ЯНУ", "ФЕВ", "МАР", "АПР", "МАЙ", "ЮНИ",
        "ЮЛИ", "АВГ", "СЕП", "ОКТ", "НОЕ", "ДЕК"
    ]

    months = months_bg if language == "bg" else months_en

    date_label = (
        f"{rome_date.day:02d} {months[rome_date.month - 1]} "
        f"{rome_date.year}"
    )

    rome_time = f"{rome_date.hour:02d}:{rome_date.minute:02d} {rome_date.tzname()}"

    if language == "en":
        return f"{date_label} • {rome_time}"

    sofia_date = utc_date.astimezone(BULGARIA_TIMEZONE)
    sofia_time = f"{sofia_date.hour:02d}:{sofia_date.minute:02d} {sofia_date.tzname()}"

    return f"{date_label} • {rome_time} / {sofia_time}"


def local_team_name(name, language):
    name = safe(name)

    if language == "bg":
        translations = {
            "AS Roma": "АС РОМА",
            "Atalanta BC": "АТАЛАНТА",
            "Fenerbahçe SK": "ФЕНЕРБАХЧЕ",
            "FC Internazionale Milano": "ИНТЕР",
            "Torino FC": "ТОРИНО",
            "ACF Fiorentina": "ФИОРЕНТИНА",
            "US Lecce": "ЛЕЧЕ",
            "Real Madrid CF": "РЕАЛ МАДРИД",
            "Como 1907": "КОМО"
        }
        return translations.get(name, name).upper()

    return name.upper()


def local_competition_name(name, language):
    name = safe(name)

    if language == "bg":
        translations = {
            "Serie A": "СЕРИЯ А",
            "UEFA Champions League": "ШАМПИОНСКА ЛИГА",
            "UEFA Europa League": "ЛИГА ЕВРОПА",
            "UEFA Conference League": "ЛИГА НА КОНФЕРЕНЦИИТЕ",
            "Coppa Italia": "КУПА НА ИТАЛИЯ"
        }
        return translations.get(name, name).upper()

    return name.upper()


def match_score(match):
    score = match.get("score", {}).get("full_time", {})
    home = score.get("home")
    away = score.get("away")

    if home is None or away is None:
        return None

    return f"{home} – {away}"


def image_tag(url, alt, css_class):
    if not url:
        return f'<div class="{css_class} crest-fallback">?</div>'

    return (
        f'<img class="{css_class}" '
        f'src="{html.escape(url, quote=True)}" '
        f'alt="{html.escape(alt, quote=True)}">'
    )


def competition_label(match, language):
    competition = match.get("competition", {})
    name = local_competition_name(competition.get("name"), language)
    matchday = match.get("matchday")

    if matchday:
        return f"{name} · {TEXT[language]['matchday']} {matchday}"

    return name


def watermark_text(config, language):
    return config.get("card_design", {}).get(
        "watermark",
        TEXT[language]["in_construction"]
    )


def shared_style(background):
    return f"""
    * {{
      box-sizing: border-box;
    }}

    html, body {{
      width: {WIDTH}px;
      height: {HEIGHT}px;
      margin: 0;
      overflow: hidden;
      background: #110b0e;
      font-family: "Oswald", Arial, sans-serif;
    }}

    .card {{
      position: relative;
      width: {WIDTH}px;
      height: {HEIGHT}px;
      overflow: hidden;
      color: #f7f1e7;
      background:
        linear-gradient(140deg, rgba(105, 14, 29, 0.96) 0%, rgba(24, 10, 14, 0.94) 56%, rgba(10, 8, 10, 0.98) 100%),
        url("{html.escape(background, quote=True)}") center / cover no-repeat;
    }}

    .card::before {{
      position: absolute;
      inset: 0;
      content: "";
      opacity: 0.18;
      background-image:
        linear-gradient(rgba(217, 170, 82, 0.14) 1px, transparent 1px),
        linear-gradient(90deg, rgba(217, 170, 82, 0.14) 1px, transparent 1px);
      background-size: 52px 52px;
      mask-image: linear-gradient(to bottom, #000 0%, transparent 84%);
    }}

    .card::after {{
      position: absolute;
      right: -210px;
      bottom: -270px;
      width: 760px;
      height: 760px;
      border: 1px solid rgba(217, 170, 82, 0.24);
      border-radius: 50%;
      content: "";
      box-shadow:
        0 0 0 70px rgba(217, 170, 82, 0.04),
        0 0 0 140px rgba(217, 170, 82, 0.025);
    }}

    .content {{
      position: relative;
      z-index: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      width: 100%;
      height: 100%;
      padding: 70px 62px 54px;
    }}

    .title {{
      margin: 0;
      color: #fffaf1;
      font-size: 72px;
      font-weight: 600;
      line-height: 1;
      letter-spacing: 1.5px;
      text-align: center;
    }}

    .competition {{
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 17px;
      width: 100%;
      margin-top: 38px;
      color: #f2d38f;
      font-size: 27px;
      font-weight: 500;
      letter-spacing: 2.8px;
      text-align: center;
    }}

    .competition-emblem-wrap {{
      display: grid;
      place-items: center;
      width: 62px;
      height: 62px;
      border: 1px solid rgba(217, 170, 82, 0.8);
      border-radius: 50%;
      background: rgba(255, 250, 241, 0.94);
      box-shadow: 0 8px 18px rgba(0, 0, 0, 0.28);
    }}

    .competition-emblem {{
      width: 45px;
      height: 45px;
      object-fit: contain;
    }}

    .watermark {{
      color: rgba(241, 209, 139, 0.9);
      font-size: 18px;
      letter-spacing: 3px;
      text-align: right;
    }}

    .crest-fallback {{
      display: grid;
      place-items: center;
      color: #e7bc6d;
      border: 2px solid #e7bc6d;
      border-radius: 50%;
      font-size: 78px;
    }}
    """


def html_document(language, body, style):
    return f"""<!doctype html>
<html lang="{language}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width={WIDTH}, height={HEIGHT}, initial-scale=1">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>{style}</style>
</head>
<body>
  {body}
</body>
</html>
"""


def match_card_html(data, config, match, language, card_type):
    text = TEXT[language]
    team = data.get("team", {})
    artwork = team.get("artwork", {})
    team_info = team.get("football_data", {})

    home = match.get("home_team", {})
    away = match.get("away_team", {})
    competition = match.get("competition", {})

    home_name = local_team_name(home.get("name"), language)
    away_name = local_team_name(away.get("name"), language)

    roma_crest = (
        artwork.get("badge")
        or team_info.get("crest")
        or "https://crests.football-data.org/100.png"
    )

    home_crest = roma_crest if "roma" in safe(home.get("name")).lower() else home.get("crest")
    away_crest = roma_crest if "roma" in safe(away.get("name")).lower() else away.get("crest")

    title = text["last_match"] if card_type == "last" else text["next_match"]
    match_label = text["full_time"] if card_type == "last" else title
    date_text = format_date(match.get("utc_date"), language)
    competition_text = competition_label(match, language)
    competition_emblem = competition.get("emblem")
    score = match_score(match)

    center = (
        f'<div class="score">{escape(score)}</div>'
        if score and card_type == "last"
        else f'<div class="versus">{text["vs"]}</div>'
    )

    background = artwork.get("fanart_1") or ""

    style = shared_style(background) + """
    .match-area {
      display: grid;
      grid-template-columns: 1fr 194px 1fr;
      align-items: center;
      gap: 22px;
      flex: 1;
      width: 100%;
      padding: 42px 0 22px;
    }

    .club {
      display: flex;
      flex-direction: column;
      align-items: center;
      min-width: 0;
      text-align: center;
    }

    .club-crest {
      width: 205px;
      height: 205px;
      object-fit: contain;
      filter: drop-shadow(0 18px 20px rgba(0, 0, 0, 0.35));
    }

    .club-name {
      margin-top: 28px;
      color: #fffaf1;
      font-size: 42px;
      font-weight: 600;
      line-height: 1.02;
      letter-spacing: 0.3px;
    }

    .club-type {
      margin-top: 13px;
      color: #d9aa52;
      font-size: 20px;
      letter-spacing: 4px;
    }

    .middle {
      text-align: center;
    }

    .score {
      color: #f4d08a;
      font-size: 82px;
      font-weight: 700;
      line-height: 1;
      white-space: nowrap;
    }

    .versus {
      color: #f4d08a;
      font-size: 44px;
      font-weight: 600;
      letter-spacing: 5px;
    }

    .match-label {
      margin-top: 19px;
      color: #d5c4ab;
      font-size: 19px;
      letter-spacing: 3px;
    }

    .bottom {
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      width: 100%;
      gap: 24px;
      padding-top: 28px;
      border-top: 1px solid rgba(217, 170, 82, 0.38);
    }

    .date {
      color: #fff8ed;
      font-size: 25px;
      letter-spacing: 0.9px;
    }
    """

    body = f"""
    <article class="card">
      <div class="content">
        <h1 class="title">{escape(title)}</h1>

        <div class="competition">
          <div class="competition-emblem-wrap">
            {image_tag(competition_emblem, competition_text, "competition-emblem")}
          </div>
          <span>{escape(competition_text)}</span>
        </div>

        <main class="match-area">
          <section class="club">
            {image_tag(home_crest, home_name, "club-crest")}
            <div class="club-name">{escape(home_name)}</div>
            <div class="club-type">{text["home"]}</div>
          </section>

          <section class="middle">
            {center}
            <div class="match-label">{escape(match_label)}</div>
          </section>

          <section class="club">
            {image_tag(away_crest, away_name, "club-crest")}
            <div class="club-name">{escape(away_name)}</div>
            <div class="club-type">{text["away"]}</div>
          </section>
        </main>

        <footer class="bottom">
          <div class="date">{escape(date_text)}</div>
          <div class="watermark">{escape(watermark_text(config, language))}</div>
        </footer>
      </div>
    </article>
    """

    return html_document(language, body, style)


def standings_card_html(data, config, language):
    text = TEXT[language]
    team = data.get("team", {})
    artwork = team.get("artwork", {})
    team_info = team.get("football_data", {})

    standing = (
        data.get("standings", {})
        .get("serie_a", {})
        .get("roma", {})
        or {}
    )

    competition = data.get("standings", {}).get("serie_a", {})
    competition_name = (
        competition.get("name_bg")
        if language == "bg"
        else competition.get("name_en")
    ) or "Serie A"

    crest = artwork.get("badge") or team_info.get("crest")
    position = standing.get("position", "—")
    points = standing.get("points", "—")
    played = standing.get("played_games", "—")
    wins = standing.get("won", "—")
    draws = standing.get("draw", "—")
    losses = standing.get("lost", "—")
    goals_for = standing.get("goals_for", "—")
    goals_against = standing.get("goals_against", "—")
    difference = standing.get("goal_difference", "—")

    if isinstance(difference, int) and difference > 0:
        difference = f"+{difference}"

    background = artwork.get("fanart_2") or artwork.get("fanart_1") or ""

    style = shared_style(background) + """
    .team-row {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 28px;
      margin-top: 52px;
    }

    .team-crest {
      width: 140px;
      height: 140px;
      object-fit: contain;
      filter: drop-shadow(0 16px 18px rgba(0, 0, 0, 0.34));
    }

    .team-name {
      color: #fffaf1;
      font-size: 58px;
      font-weight: 600;
      letter-spacing: 1px;
    }

    .main-stat {
      display: grid;
      grid-template-columns: 1fr 1fr;
      width: 100%;
      margin-top: 62px;
      border-top: 1px solid rgba(217, 170, 82, 0.42);
      border-bottom: 1px solid rgba(217, 170, 82, 0.42);
    }

    .main-stat-item {
      padding: 38px 26px 34px;
      text-align: center;
    }

    .main-stat-item + .main-stat-item {
      border-left: 1px solid rgba(217, 170, 82, 0.32);
    }

    .main-number {
      color: #f4d08a;
      font-size: 150px;
      font-weight: 700;
      line-height: 0.82;
    }

    .main-label {
      margin-top: 20px;
      color: #d8c7ad;
      font-size: 24px;
      letter-spacing: 4px;
    }

    .record-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      width: 100%;
      gap: 12px;
      margin-top: 48px;
    }

    .record-item {
      padding: 20px 10px;
      border: 1px solid rgba(217, 170, 82, 0.24);
      border-radius: 10px;
      background: rgba(14, 8, 10, 0.34);
      text-align: center;
    }

    .record-number {
      color: #fff8ed;
      font-size: 42px;
      font-weight: 600;
      line-height: 1;
    }

    .record-label {
      margin-top: 10px;
      color: #d5c4ab;
      font-size: 16px;
      letter-spacing: 2px;
    }

    .goals {
      margin-top: 42px;
      color: #fff8ed;
      font-size: 30px;
      letter-spacing: 1.4px;
      text-align: center;
    }

    .goals strong {
      color: #f4d08a;
      font-size: 42px;
    }

    .bottom {
      display: flex;
      justify-content: flex-end;
      width: 100%;
      margin-top: auto;
      padding-top: 28px;
      border-top: 1px solid rgba(217, 170, 82, 0.38);
    }
    """

    team_name = "АС РОМА" if language == "bg" else "AS ROMA"

    body = f"""
    <article class="card">
      <div class="content">
        <h1 class="title">{text["standings"]}</h1>

        <div class="competition">
          <span>{escape(str(competition_name).upper())}</span>
        </div>

        <div class="team-row">
          {image_tag(crest, team_name, "team-crest")}
          <div class="team-name">{team_name}</div>
        </div>

        <section class="main-stat">
          <div class="main-stat-item">
            <div class="main-number">{escape(position)}</div>
            <div class="main-label">{text["place"]}</div>
          </div>
          <div class="main-stat-item">
            <div class="main-number">{escape(points)}</div>
            <div class="main-label">{text["points"]}</div>
          </div>
        </section>

        <section class="record-grid">
          <div class="record-item">
            <div class="record-number">{escape(played)}</div>
            <div class="record-label">{text["played"]}</div>
          </div>
          <div class="record-item">
            <div class="record-number">{escape(wins)}</div>
            <div class="record-label">{text["wins"]}</div>
          </div>
          <div class="record-item">
            <div class="record-number">{escape(draws)}</div>
            <div class="record-label">{text["draws"]}</div>
          </div>
          <div class="record-item">
            <div class="record-number">{escape(losses)}</div>
            <div class="record-label">{text["losses"]}</div>
          </div>
        </section>

        <div class="goals">
          {text["goals"]}: <strong>{escape(goals_for)}–{escape(goals_against)}</strong>
          &nbsp; • &nbsp;
          {text["goal_difference"]}: <strong>{escape(difference)}</strong>
        </div>

        <footer class="bottom">
          <div class="watermark">{escape(watermark_text(config, language))}</div>
        </footer>
      </div>
    </article>
    """

    return html_document(language, body, style)


def result_for_roma(match):
    home_name = safe(match.get("home_team", {}).get("name"))
    away_name = safe(match.get("away_team", {}).get("name"))
    score = match.get("score", {}).get("full_time", {})

    home_score = score.get("home")
    away_score = score.get("away")

    if home_score is None or away_score is None:
        return "D"

    roma_is_home = "roma" in home_name.lower()
    roma_score = home_score if roma_is_home else away_score
    opponent_score = away_score if roma_is_home else home_score

    if roma_score > opponent_score:
        return "W"
    if roma_score < opponent_score:
        return "L"
    return "D"


def result_letter(result, language):
    mapping = {
        "W": TEXT[language]["wins_short"],
        "D": TEXT[language]["draws_short"],
        "L": TEXT[language]["losses_short"]
    }
    return mapping.get(result, "—")


def recent_form_card_html(data, config, language):
    text = TEXT[language]
    team = data.get("team", {})
    artwork = team.get("artwork", {})
    team_info = team.get("football_data", {})
    matches = data.get("recent_matches", [])[:5]

    crest = artwork.get("badge") or team_info.get("crest")
    background = artwork.get("fanart_3") or artwork.get("fanart_1") or ""

    wins = sum(1 for match in matches if result_for_roma(match) == "W")
    draws = sum(1 for match in matches if result_for_roma(match) == "D")
    losses = sum(1 for match in matches if result_for_roma(match) == "L")

    goals_for = 0
    goals_against = 0

    for match in matches:
        score = match.get("score", {}).get("full_time", {})
        home_score = score.get("home")
        away_score = score.get("away")

        if home_score is None or away_score is None:
            continue

        home_name = safe(match.get("home_team", {}).get("name"))
        roma_is_home = "roma" in home_name.lower()

        goals_for += home_score if roma_is_home else away_score
        goals_against += away_score if roma_is_home else home_score

    style = shared_style(background) + """
    .team-row {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 24px;
      margin-top: 48px;
    }

    .team-crest {
      width: 118px;
      height: 118px;
      object-fit: contain;
      filter: drop-shadow(0 16px 18px rgba(0, 0, 0, 0.34));
    }

    .team-name {
      color: #fffaf1;
      font-size: 52px;
      font-weight: 600;
      letter-spacing: 1px;
    }

    .form-badges {
      display: flex;
      justify-content: center;
      gap: 14px;
      margin: 48px 0 36px;
    }

    .form-badge {
      display: grid;
      place-items: center;
      width: 92px;
      height: 92px;
      border-radius: 50%;
      color: #fffaf1;
      font-size: 42px;
      font-weight: 600;
    }

    .form-badge.win {
      border: 2px solid #e7bc6d;
      background: rgba(94, 25, 37, 0.88);
    }

    .form-badge.draw {
      border: 2px solid #b9aca0;
      background: rgba(103, 92, 87, 0.7);
    }

    .form-badge.loss {
      border: 2px solid #d7797d;
      background: rgba(117, 29, 40, 0.86);
    }

    .results {
      width: 100%;
      border-top: 1px solid rgba(217, 170, 82, 0.34);
    }

    .result-row {
      display: grid;
      grid-template-columns: 1fr auto 1fr;
      align-items: center;
      gap: 18px;
      padding: 22px 4px;
      border-bottom: 1px solid rgba(217, 170, 82, 0.22);
    }

    .result-home,
    .result-away {
      color: #fffaf1;
      font-size: 28px;
      font-weight: 500;
      line-height: 1.1;
    }

    .result-away {
      text-align: right;
    }

    .result-score {
      color: #f4d08a;
      font-size: 34px;
      font-weight: 600;
      white-space: nowrap;
    }

    .summary {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      width: 100%;
      gap: 12px;
      margin-top: 34px;
    }

    .summary-item {
      padding: 18px 8px;
      border: 1px solid rgba(217, 170, 82, 0.24);
      border-radius: 10px;
      background: rgba(14, 8, 10, 0.34);
      text-align: center;
    }

    .summary-number {
      color: #f4d08a;
      font-size: 36px;
      font-weight: 600;
      line-height: 1;
    }

    .summary-label {
      margin-top: 8px;
      color: #d5c4ab;
      font-size: 15px;
      letter-spacing: 1.7px;
    }

    .bottom {
      display: flex;
      justify-content: flex-end;
      width: 100%;
      margin-top: auto;
      padding-top: 24px;
      border-top: 1px solid rgba(217, 170, 82, 0.38);
    }
    """

    team_name = "АС РОМА" if language == "bg" else "AS ROMA"

    rows = []

    for match in matches:
        home = local_team_name(match.get("home_team", {}).get("name"), language)
        away = local_team_name(match.get("away_team", {}).get("name"), language)
        score = match_score(match) or "—"

        rows.append(
            f"""
            <div class="result-row">
              <div class="result-home">{escape(home)}</div>
              <div class="result-score">{escape(score)}</div>
              <div class="result-away">{escape(away)}</div>
            </div>
            """
        )

    if not rows:
        rows.append(
            """
            <div class="result-row">
              <div class="result-home">—</div>
              <div class="result-score">—</div>
              <div class="result-away">—</div>
            </div>
            """
        )

    form_badges = []

    for match in matches:
        result = result_for_roma(match)
        class_name = {
            "W": "win",
            "D": "draw",
            "L": "loss"
        }.get(result, "draw")

        form_badges.append(
            f'<div class="form-badge {class_name}">'
            f'{escape(result_letter(result, language))}'
            f'</div>'
        )

    body = f"""
    <article class="card">
      <div class="content">
        <h1 class="title">{text["recent_form"]}</h1>

        <div class="team-row">
          {image_tag(crest, team_name, "team-crest")}
          <div class="team-name">{team_name}</div>
        </div>

        <section class="form-badges">
          {''.join(form_badges)}
        </section>

        <section class="results">
          {''.join(rows)}
        </section>

        <section class="summary">
          <div class="summary-item">
            <div class="summary-number">{wins}</div>
            <div class="summary-label">{text["wins"]}</div>
          </div>
          <div class="summary-item">
            <div class="summary-number">{goals_for}</div>
            <div class="summary-label">{text["goals"]}</div>
          </div>
          <div class="summary-item">
            <div class="summary-number">{goals_against}</div>
            <div class="summary-label">{text["losses"]}</div>
          </div>
        </section>

        <footer class="bottom">
          <div class="watermark">{escape(watermark_text(config, language))}</div>
        </footer>
      </div>
    </article>
    """

    return html_document(language, body, style)


def render_card(browser, html_file, output_file):
    page = browser.new_page(
        viewport={
            "width": WIDTH,
            "height": HEIGHT
        },
        device_scale_factor=1
    )

    page.goto(html_file.as_uri(), wait_until="networkidle")
    page.screenshot(
        path=str(output_file),
        clip={
            "x": 0,
            "y": 0,
            "width": WIDTH,
            "height": HEIGHT
        },
        type="png"
    )
    page.close()


def main():
    if not CONFIG_PATH.exists():
        raise RuntimeError(f"Missing config file: {CONFIG_PATH}")

    if not DATA_PATH.exists():
        raise RuntimeError(f"Missing data file: {DATA_PATH}")

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    languages = config.get("project", {}).get(
        "supported_languages",
        ["en", "bg"]
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()

        try:
            for language in languages:
                if language not in TEXT:
                    print(f"Skipping unsupported language: {language}")
                    continue

                coppa_italia = data.get("coppa_italia", {}) or {}

                match_cards = [
                    ("last-match", data.get("last_match"), "last"),
                    ("next-match", data.get("next_match"), "next"),
                    (
                        "coppa-italia-last-match",
                        coppa_italia.get("last_match"),
                        "last"
                    ),
                    (
                        "coppa-italia-next-match",
                        coppa_italia.get("next_match"),
                        "next"
                    )
                ]

                for filename_prefix, match, card_type in match_cards:
                    if not match:
                        print(f"Skipping {filename_prefix}: no match data.")
                        continue

                    html_content = match_card_html(
                        data,
                        config,
                        match,
                        language,
                        card_type
                    )

                    html_file = TEMP_DIR / f"{filename_prefix}-{language}.html"
                    png_file = OUTPUT_DIR / f"{filename_prefix}-{language}.png"

                    html_file.write_text(html_content, encoding="utf-8")
                    render_card(browser, html_file, png_file)

                    print(f"Created: {png_file.relative_to(ROOT)}")

                standings_html = standings_card_html(data, config, language)
                standings_file = TEMP_DIR / f"standings-{language}.html"
                standings_png = OUTPUT_DIR / f"standings-{language}.png"

                standings_file.write_text(standings_html, encoding="utf-8")
                render_card(browser, standings_file, standings_png)

                print(f"Created: {standings_png.relative_to(ROOT)}")

                form_html = recent_form_card_html(data, config, language)
                form_file = TEMP_DIR / f"recent-form-{language}.html"
                form_png = OUTPUT_DIR / f"recent-form-{language}.png"

                form_file.write_text(form_html, encoding="utf-8")
                render_card(browser, form_file, form_png)

                print(f"Created: {form_png.relative_to(ROOT)}")
        finally:
            browser.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
