"""
STEP 4: create the database.

Run this once (python3 init_db.py) before starting the server. It
creates a file called softball.db in this folder — that single file
*is* the database. SQLite doesn't need a separate server process running
like Postgres or MySQL would; it's just a file your Python code reads
and writes to, which makes it a great first database to learn on.

If you run this script again later, it drops and recreates the table,
so it's safe to re-run while you're experimenting.
"""

import sqlite3
import csv

DB_FILE = "softball.db"

# Same sample roster as the JSON version, so the site looks identical —
# only *where the data lives* has changed. Swap this out for your real
# stats once you're comfortable with how the pieces fit together.

with open("test.csv") as file:
    SAMPLE_PLAYERS = list(csv.reader(file))

connection = sqlite3.connect(DB_FILE)
cursor = connection.cursor()

# DROP TABLE IF EXISTS makes this script safely re-runnable.
cursor.execute("DROP TABLE IF EXISTS players")

cursor.execute("""
    CREATE TABLE players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        games INTEGER NOT NULL,
        at_bats INTEGER NOT NULL,
        singles INTEGER NOT NULL,
        walks INTEGER NOT NULL,
        home_runs INTEGER NOT NULL,
        rbi INTEGER NOT NULL,
        runs INTEGER NOT NULL
    )
""")

cursor.executemany(
    """
    INSERT INTO players (name, games, at_bats, singles, walks, home_runs, rbi, runs)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
    SAMPLE_PLAYERS,
)

connection.commit()
connection.close()

print(f"Created {DB_FILE} with {len(SAMPLE_PLAYERS)} players.")
