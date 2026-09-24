"""
STEP 4: the Flask server.

This does two jobs at once:
  1. Serves the frontend files (index.html, style.css, script.js) out of
     the static/ folder, so you visit one URL and get the whole site.
  2. Exposes /api/players, which queries SQLite and returns JSON — this
     is the "API" your JavaScript will fetch() from instead of reading
     data.json directly.

Run it with: python3 app.py
Then visit:  http://127.0.0.1:5000
"""

import sqlite3
from flask import Flask, g, jsonify

DB_FILE = "softball.db"

app = Flask(__name__, static_folder="static", static_url_path="")


def get_db():
    """
    Open one database connection per request and reuse it if this
    function gets called more than once during the same request.
    `g` is a special Flask object that only lives for the duration of
    a single request — a clean place to stash things like this.
    """
    if "db" not in g:
        g.db = sqlite3.connect(DB_FILE)
        g.db.row_factory = sqlite3.Row  # lets us access columns by name
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


@app.route("/")
def index():
    # Serves static/index.html at the root URL.
    return app.send_static_file("index.html")


@app.route("/api/players")
def get_players():
    db = get_db()
    rows = db.execute("SELECT * FROM players ORDER BY name").fetchall()

    players = []
    for row in rows:
        hits = row["singles"] + row["home_runs"]
        average = hits / row["at_bats"] if row["at_bats"] else 0
        obp = (hits + row["walks"]) / row["at_bats"] if row["at_bats"] else 0
        players.append({
            "name": row["name"],
            "games": row["games"],
            "atBats": row["at_bats"],       # snake_case in the database,
            "hits": hits,            # camelCase in the JSON —
            "walks": row["walks"],          # matches what the existing
            "homeRuns": row["home_runs"],   # frontend JS already expects
            "rbi": row["rbi"],
            "runs": row["runs"],
            "average": f"{average:.3f}",
            "obp": f"{obp:.3f}",
            "singles": row["singles"],
        })

    return jsonify(players)


if __name__ == "__main__":
    app.run(debug=True)
