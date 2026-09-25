"""
Same job as before — serve the frontend and expose player stats as
JSON — but now every stat is computed live from plate_appearances
instead of being pre-stored. This is the season view for now; game,
career, and streak views are natural next additions on top of the
same underlying tables.
"""

import os
import sqlite3
from flask import Flask, g, jsonify, request

DB_FILE = os.environ.get("DB_FILE", "softball.db")

app = Flask(__name__, static_folder="static", static_url_path="")

# Same classification used by import_data.py — kept in sync so a stat
# means the same thing whether we're importing or querying.
AT_BAT_RESULTS = {"1B", "2B", "3B", "HR", "SO", "GO", "FO", "LO", "PO", "DP", "FC"}
HIT_RESULTS = {"1B", "2B", "3B", "HR"}


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_FILE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


@app.route("/")
def index():
    return app.send_static_file("index.html")


def latest_season_id(db):
    row = db.execute(
        "SELECT id FROM seasons ORDER BY year DESC, id DESC LIMIT 1"
    ).fetchone()
    return row["id"] if row else None


@app.route("/api/players")
def get_players():
    db = get_db()

    # ?season=2024 picks a specific year; with none given, default to
    # the most recent season in the database rather than mixing years
    # together, which would silently produce meaningless totals.
    season_year = request.args.get("season")
    if season_year:
        season_row = db.execute(
            "SELECT id FROM seasons WHERE year = ?", (season_year,)
        ).fetchone()
        season_id = season_row["id"] if season_row else None
    else:
        season_id = latest_season_id(db)

    if season_id is None:
        return jsonify([])

    rows = db.execute(
        """
        SELECT p.id, p.name,
               pa.result, pa.rbi, pa.scored, pa.game_id
        FROM plate_appearances pa
        JOIN players p ON pa.player_id = p.id
        JOIN games g ON pa.game_id = g.id
        WHERE g.season_id = ?
        """,
        (season_id,),
    ).fetchall()

    # Aggregate in Python rather than SQL here — the AB/hit
    # classification depends on the AT_BAT_RESULTS/HIT_RESULTS sets
    # above, which is easier to express clearly this way than as a
    # giant SQL CASE statement.
    totals = {}
    for row in rows:
        player = totals.setdefault(row["id"], {
            "name": row["name"],
            "games": set(),
            "plateAppearances": 0,
            "atBats": 0,
            "hits": 0,
            "singles": 0,
            "doubles": 0,
            "triples": 0,
            "walks": 0,
            "homeRuns": 0,
            "rbi": 0,
            "runs": 0,
        })

        player["games"].add(row["game_id"])
        player["plateAppearances"] += 1
        if row["result"] in AT_BAT_RESULTS:
            player["atBats"] += 1
        if row["result"] in HIT_RESULTS:
            player["hits"] += 1
        if row["result"] == "1B":
            player["singles"] += 1
        if row["result"] == "2B":
            player["doubles"] += 1
        if row["result"] == "3B":
            player["triples"] += 1
        if row["result"] == "HR":
            player["homeRuns"] += 1
        if row["result"] == "BB":
            player["walks"] += 1
        player["rbi"] += row["rbi"]
        player["runs"] += row["scored"]

    players = []
    for player in totals.values():
        average = player["hits"] / player["atBats"] if player["atBats"] else 0
        obp = (player["hits"] + player["walks"]) / player["atBats"] if player["atBats"] else 0
        totalBases = player["singles"] + player["doubles"] * 2 + player["triples"] * 3 + player["homeRuns"] * 4
        slg = totalBases / player["atBats"] if player["atBats"] else 0
        ops = obp + slg if player["atBats"] else 0
        players.append({
            "name": player["name"],
            "games": len(player["games"]),
            "plateAppearances": player["plateAppearances"],
            "atBats": player["atBats"],
            "hits": player["hits"],
            "singles": player["singles"],
            "doubles": player["doubles"],
            "triples": player["triples"],
            "homeRuns": player["homeRuns"],
            "walks": player["walks"],
            "rbi": player["rbi"],
            "runs": player["runs"],
            "totalBases": totalBases,
            "average": f"{average:.3f}",
            "obp": f"{obp:.3f}",
            "slg": f"{slg:.3f}",
            "ops": f"{ops:.3f}",
        })

    return jsonify(players)


if __name__ == "__main__":
    app.run(debug=True)
