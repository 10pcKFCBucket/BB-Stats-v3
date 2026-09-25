#!/bin/sh
# Runs every time the container starts. The point of the check below is
# to make sure a restart or rebuild of the container never wipes out
# real data sitting in the mounted volume — init_db.py only runs the
# very first time, when there's no database there yet.
set -e

if [ ! -f "$DB_FILE" ]; then
  echo "No database found at $DB_FILE — creating one."
  python3 init_db.py
else
  echo "Found existing database at $DB_FILE — leaving it as is."
fi

exec gunicorn --reload --bind 0.0.0.0:5000 app:app
