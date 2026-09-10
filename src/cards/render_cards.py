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
        "in_construction": "IN CONSTRUCTION"
    },
    "bg": {
        "last_match": "ПОСЛЕДЕН МАЧ",
        "next_match": "СЛЕДВАЩ МАЧ",
        "full_time": "КРАЕН РЕЗУЛТАТ",
        "vs": "СРЕЩУ",
        "home": "ДОМАКИН",
        "away": "ГОСТ",
        "matchday": "КРЪГ",
        "in_construction": "В ПРОЦЕС НА РАЗРАБОТКА"
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
            "Real Madrid CF": "РЕАЛ МАДРИД"
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


def card_html(data, config, match, language, card_type):
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

    watermark = config.get("card_design", {}).get(
        "watermark",
        text["in_construction"]
    )

    if language == "bg" and watermark == "IN CONSTRUCTION":
        watermark = text["in_construction"]

    background = artwork.get("fanart_1") or ""

    return f"""<!doctype html>
<html lang="{language}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width={WIDTH}, height={HEIGHT}, initial-scale=1">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
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

    .match-area {{
      display: grid;
      grid-template-columns: 1fr 194px 1fr;
      align-items: center;
      gap: 22px;
      flex: 1;
      width: 100%;
      padding: 42px 0 22px;
    }}

    .club {{
      display: flex;
      flex-direction: column;
      align-items: center;
      min-width: 0;
      text-align: center;
    }}

    .club-crest {{
      width: 205px;
      height: 205px;
      object-fit: contain;
      filter: drop-shadow(0 18px 20px rgba(0, 0, 0, 0.35));
    }}

    .crest-fallback {{
      display: grid;
      place-items: center;
      color: #e7bc6d;
      border: 2px solid #e7bc6d;
      border-radius: 50%;
      font-size: 78px;
    }}

    .club-name {{
      margin-top: 28px;
      color: #fffaf1;
      font-size: 42px;
      font-weight: 600;
      line-height: 1.02;
      letter-spacing: 0.3px;
    }}

    .club-type {{
      margin-top: 13px;
      color: #d9aa52;
      font-size: 20px;
      letter-spacing: 4px;
    }}

    .middle {{
      text-align: center;
    }}

    .score {{
      color: #f4d08a;
      font-size: 82px;
      font-weight: 700;
      line-height: 1;
      white-space: nowrap;
    }}

    .versus {{
      color: #f4d08a;
      font-size: 44px;
      font-weight: 600;
      letter-spacing: 5px;
    }}

    .match-label {{
      margin-top: 19px;
      color: #d5c4ab;
      font-size: 19px;
      letter-spacing: 3px;
    }}

    .bottom {{
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      width: 100%;
      gap: 24px;
      padding-top: 28px;
      border-top: 1px solid rgba(217, 170, 82, 0.38);
    }}

    .date {{
      color: #fff8ed;
      font-size: 25px;
      letter-spacing: 0.9px;
    }}

    .watermark {{
      color: rgba(241, 209, 139, 0.9);
      font-size: 18px;
      letter-spacing: 3px;
      text-align: right;
    }}
  </style>
</head>
<body>
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
        <div class="watermark">{escape(watermark)}</div>
      </footer>
    </div>
  </article>
</body>
</html>
"""


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

    cards = [
        ("last-match", "last", data.get("last_match")),
        ("next-match", "next", data.get("next_match"))
    ]

    languages = config.get("project", {}).get(
        "supported_languages",
        ["en", "bg"]
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()

        try:
            for filename_prefix, card_type, match in cards:
                if not match:
                    print(f"Skipping {filename_prefix}: no match data.")
                    continue

                for language in languages:
                    if language not in TEXT:
                        print(f"Skipping unsupported language: {language}")
                        continue

                    html_content = card_html(
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
        finally:
            browser.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
