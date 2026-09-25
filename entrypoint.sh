#!/bin/sh
# Runs every time the container starts.
set -e

if [ ! -f "$DB_FILE" ]; then
  echo "No database found at $DB_FILE."
  echo "Run this once to create it from your CSV:"
  echo "  docker exec -it softball-stats python3 import_data.py your_file.csv"
else
  echo "Found existing database at $DB_FILE — leaving it as is."
fi

exec gunicorn --reload --bind 0.0.0.0:5000 app:app
