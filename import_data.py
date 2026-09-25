"""
Imports play-by-play CSV data into the database.

Run with: python3 import_data.py your_stats.csv

Two-pass approach:
  Pass 1 finds every "TEAM" row (one per game) and creates the
  season/game records from it — date, opponent, score, weather.
  Pass 2 finds every other row (one per plate appearance) and links it
  to the game created in pass 1.

Two passes instead of one avoids depending on TEAM rows always coming
before their game's plate appearances in the file — this works no
matter what order the rows are in.

IMPORTANT: this reads columns by POSITION, not by name. Your CSV header
has "Humidity", "Wind", and "Pressure" each appearing twice (the real
reading, then a duplicate you said to drop) — Python's usual
name-based CSV reading (DictReader) would silently let the second one
overwrite the first, quietly corrupting real weather data. Reading by
position sidesteps that entirely.
"""

import csv
import os
import sqlite3
import sys
from datetime import datetime

DB_FILE = os.environ.get("DB_FILE", "softball.db")
os.makedirs(os.path.dirname(DB_FILE) or ".", exist_ok=True)

# Column positions, matching your CSV header exactly. Columns 30-33
# (the duplicate Temp/Humidity/Wind/Pressure at the very end) are
# intentionally not listed here — we just never read those indexes.
COL = {
    "year": 0, "season": 1, "game_number": 2, "batting_order": 3,
    "player": 4, "jersey": 5, "outs_before": 6,
    "on_1st": 7, "on_2nd": 8, "on_3rd": 9,
    "result": 10, "rbi": 11, "scored": 12, "pitch_sequence": 13,
    "opponent_runs": 14, "date": 15, "time": 16, "opponent": 17,
    "location": 18, "temperature": 19, "dew_point": 20, "humidity": 21,
    "wind": 22, "wind_speed": 23, "wind_gust": 24, "pressure": 25,
    "precipitation": 26, "weather": 27, "ground": 28, "sun": 29,
}

# Which Result codes count as an official at-bat, and which of those
# are hits. Walks (BB) and sacrifice flies (SF) are neither — standard
# baseball/softball scoring rules, not a judgment call on our part.
AT_BAT_RESULTS = {"1B", "2B", "3B", "HR", "SO", "GO", "FO", "LO", "PO", "DP", "FC"}
HIT_RESULTS = {"1B", "2B", "3B", "HR"}


def get(row, key, default=""):
    idx = COL[key]
    return row[idx].strip() if idx < len(row) and row[idx] is not None else default


def parse_bool(value):
    return 1 if value.strip().upper() == "TRUE" else 0


def parse_int(value, default=0):
    value = value.strip()
    return int(value) if value else default


def parse_date(date_str, year):
    # Your CSV stores dates as "7/11" (month/day) with the year in its
    # own column — this stitches them back together into a real date.
    if not date_str:
        return None
    month, day = date_str.split("/")
    return datetime(int(year), int(month), int(day)).strftime("%Y-%m-%d")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 import_data.py your_stats.csv")
        sys.exit(1)

    csv_path = sys.argv[1]

    connection = sqlite3.connect(DB_FILE)
    connection.execute("PRAGMA foreign_keys = ON")
    cursor = connection.cursor()

    with open("schema.sql") as schema_file:
        cursor.executescript(schema_file.read())

    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        next(reader)  # skip header row
        rows = [row for row in reader if row and get(row, "player")]

    # --- Pass 1: seasons and games, from TEAM rows only ---

    season_ids = {}   # (year, league) -> id
    game_ids = {}      # (year, league, game_number) -> id
    games_created = 0

    for row in rows:
        if get(row, "player") != "TEAM":
            continue

        year = parse_int(get(row, "year"))
        league = get(row, "season")
        game_number = parse_int(get(row, "game_number"))

        season_key = (year, league)
        if season_key not in season_ids:
            cursor.execute(
                "INSERT INTO seasons (year, league) VALUES (?, ?)", season_key
            )
            season_ids[season_key] = cursor.lastrowid
        season_id = season_ids[season_key]

        cursor.execute(
            """
            INSERT INTO games (
                season_id, game_number, date, time, opponent, location,
                team_runs, opponent_runs, temperature, dew_point, humidity,
                wind, wind_speed, wind_gust, pressure, precipitation,
                weather, ground, sun
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                season_id, game_number,
                parse_date(get(row, "date"), year), get(row, "time"),
                get(row, "opponent"), get(row, "location"),
                parse_int(get(row, "scored")),      # team's own runs (R column on the TEAM row)
                parse_int(get(row, "opponent_runs")),  # RA column
                get(row, "temperature"), get(row, "dew_point"), get(row, "humidity"),
                get(row, "wind"), get(row, "wind_speed"), get(row, "wind_gust"),
                get(row, "pressure"), get(row, "precipitation"),
                get(row, "weather"), get(row, "ground"), get(row, "sun"),
            ),
        )
        game_ids[(year, league, game_number)] = cursor.lastrowid
        games_created += 1

    # --- Pass 2: players and plate appearances, from every other row ---

    player_ids = {}  # name -> id
    players_created = 0
    plate_appearances_created = 0
    skipped = 0

    for row in rows:
        name = get(row, "player")
        if name == "TEAM":
            continue

        year = parse_int(get(row, "year"))
        league = get(row, "season")
        game_number = parse_int(get(row, "game_number"))
        game_key = (year, league, game_number)

        if game_key not in game_ids:
            # This play's game has no TEAM row anywhere in the file —
            # can't link it to a game, so skip it and flag the count
            # rather than silently losing data.
            skipped += 1
            continue
        game_id = game_ids[game_key]

        if name not in player_ids:
            jersey = get(row, "jersey")
            cursor.execute(
                "INSERT INTO players (name, jersey_number) VALUES (?, ?)",
                (name, parse_int(jersey, None) if jersey else None),
            )
            player_ids[name] = cursor.lastrowid
            players_created += 1
        player_id = player_ids[name]

        cursor.execute(
            """
            INSERT INTO plate_appearances (
                game_id, player_id, batting_order, outs_before,
                on_1st, on_2nd, on_3rd, result, rbi, scored, pitch_sequence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                game_id, player_id,
                parse_int(get(row, "batting_order")),
                parse_int(get(row, "outs_before")),
                parse_bool(get(row, "on_1st")),
                parse_bool(get(row, "on_2nd")),
                parse_bool(get(row, "on_3rd")),
                get(row, "result"),
                parse_int(get(row, "rbi")),
                1 if get(row, "scored") else 0,
                get(row, "pitch_sequence"),
            ),
        )
        plate_appearances_created += 1

    connection.commit()
    connection.close()

    print(f"Seasons: {len(season_ids)}")
    print(f"Games: {games_created}")
    print(f"Players: {players_created}")
    print(f"Plate appearances: {plate_appearances_created}")
    if skipped:
        print(f"WARNING: skipped {skipped} play rows with no matching TEAM row — check your CSV.")


if __name__ == "__main__":
    main()
