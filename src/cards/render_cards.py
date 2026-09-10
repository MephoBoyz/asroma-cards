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
TIMEZONE = ZoneInfo("Europe/Rome")


TEXT = {
    "en": {
        "last_match": "LAST MATCH",
        "next_match": "NEXT MATCH",
        "final": "FINAL",
        "vs": "VS",
        "home": "HOME",
        "away": "AWAY",
        "in_construction": "IN CONSTRUCTION",
        "updated": "DATA UPDATED"
    },
    "bg": {
        "last_match": "ПОСЛЕДЕН МАЧ",
        "next_match": "СЛЕДВАЩ МАЧ",
        "final": "КРАЕН",
        "vs": "СРЕЩУ",
        "home": "ДОМАКИН",
        "away": "ГОСТ",
        "in_construction": "В ПРОЦЕС НА РАЗРАБОТКА",
        "updated": "ДАННИ ОБНОВЕНИ"
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

    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(TIMEZONE)


def format_date(value, language):
    date = parse_date(value)

    if not date:
        return "—"

    months_en = [
        "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
        "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"
    ]

    months_bg = [
        "ЯНУ", "ФЕВ", "МАР", "АПР", "МАЙ", "ЮНИ",
        "ЮЛИ", "АВГ", "СЕП", "ОКТ", "НОЕ", "ДЕК"
    ]

    months = months_bg if language == "bg" else months_en

    return (
        f"{date.day:02d} {months[date.month - 1]} {date.year} "
        f"• {date.hour:02d}:{date.minute:02d}"
    )


def local_team_name(name, language):
    if language == "bg" and "roma" in safe(name).lower():
        return "АС РОМА"

    return safe(name).upper()


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


def card_html(data, config, match, language, card_type):
    text = TEXT[language]
    team = data.get("team", {})
    artwork = team.get("artwork", {})
    team_info = team.get("football_data", {})

    home = match.get("home_team", {})
    away = match.get("away_team", {})
    competition = match.get("competition", {})

    roma_crest = (
        artwork.get("badge")
        or team_info.get("crest")
        or home.get("crest")
        or away.get("crest")
    )

    home_name = local_team_name(home.get("name"), language)
    away_name = local_team_name(away.get("name"), language)

    home_crest = home.get("crest")
    away_crest = away.get("crest")

    if "roma" in safe(home.get("name")).lower():
        home_crest = roma_crest

    if "roma" in safe(away.get("name")).lower():
        away_crest = roma_crest

    title = text["last_match"] if card_type == "last" else text["next_match"]
    date_text = format_date(match.get("utc_date"), language)
    competition_name = safe(competition.get("name")).upper()
    competition_emblem = competition.get("emblem")
    score = match_score(match)

    center = (
        f'<div class="score">{escape(score)}</div>'
        if score and card_type == "last"
        else f'<div class="versus">{text["vs"]}</div>'
    )

    status_text = text["final"] if card_type == "last" else date_text
    home_label = text["home"]
    away_label = text["away"]
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
      opacity: 0.23;
      background-image:
        linear-gradient(rgba(217, 170, 82, 0.14) 1px, transparent 1px),
        linear-gradient(90deg, rgba(217, 170, 82, 0.14) 1px, transparent 1px);
      background-size: 52px 52px;
      mask-image: linear-gradient(to bottom, #000 0%, transparent 88%);
    }}

    .card::after {{
      position: absolute;
      right: -210px;
      bottom: -270px;
      width: 760px;
      height: 760px;
      border: 1px solid rgba(217, 170, 82, 0.25);
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
      width: 100%;
      height: 100%;
      padding: 72px 70px 58px;
    }}

    .top {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 30px;
    }}

    .eyebrow {{
      margin: 0 0 10px;
      color: #e7bc6d;
      font-size: 29px;
      font-weight: 600;
      letter-spacing: 7px;
    }}

    .title {{
      max-width: 730px;
      margin: 0;
      color: #fffaf1;
      font-size: 72px;
      font-weight: 600;
      line-height: 0.98;
      letter-spacing: 1px;
    }}

    .roma-badge {{
      width: 122px;
      height: 122px;
      object-fit: contain;
      filter: drop-shadow(0 12px 16px rgba(0, 0, 0, 0.35));
    }}

    .competition {{
      display: flex;
      align-items: center;
      gap: 16px;
      margin-top: 46px;
      color: #d8c7ad;
      font-size: 27px;
      font-weight: 500;
      letter-spacing: 2.2px;
    }}

    .competition-emblem {{
      width: 48px;
      height: 48px;
      object-fit: contain;
    }}

    .match-area {{
      display: grid;
      grid-template-columns: 1fr 190px 1fr;
      align-items: center;
      gap: 22px;
      flex: 1;
      padding: 48px 0 26px;
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
      font-size: 44px;
      font-weight: 600;
      line-height: 1;
      letter-spacing: 0.3px;
    }}

    .club-type {{
      margin-top: 13px;
      color: #d9aa52;
      font-size: 21px;
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

    .final-label {{
      margin-top: 18px;
      color: #d5c4ab;
      font-size: 20px;
      letter-spacing: 3px;
    }}

    .bottom {{
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 24px;
      padding-top: 28px;
      border-top: 1px solid rgba(217, 170, 82, 0.38);
    }}

    .date {{
      color: #fff8ed;
      font-size: 27px;
      letter-spacing: 1.2px;
    }}

    .watermark {{
      color: rgba(241, 209, 139, 0.9);
      font-size: 19px;
      letter-spacing: 3.5px;
      text-align: right;
    }}
  </style>
</head>
<body>
  <article class="card">
    <div class="content">
      <header class="top">
        <div>
          <p class="eyebrow">{text["updated"]}</p>
          <h1 class="title">{title}</h1>
        </div>
        {image_tag(roma_crest, "AS Roma", "roma-badge")}
      </header>

      <div class="competition">
        {image_tag(competition_emblem, competition_name, "competition-emblem")}
        <span>{escape(competition_name)}</span>
      </div>

      <main class="match-area">
        <section class="club">
          {image_tag(home_crest, home_name, "club-crest")}
          <div class="club-name">{escape(home_name)}</div>
          <div class="club-type">{home_label}</div>
        </section>

        <section class="middle">
          {center}
          <div class="final-label">{escape(status_text)}</div>
        </section>

        <section class="club">
          {image_tag(away_crest, away_name, "club-crest")}
          <div class="club-name">{escape(away_name)}</div>
          <div class="club-type">{away_label}</div>
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

                    print(
                        f"Created: "
                        f"{png_file.relative_to(ROOT)}"
                    )
        finally:
            browser.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
