FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (as a separate layer) so Docker can reuse
# this step on rebuilds unless requirements.txt itself changes — keeps
# rebuilds fast while you're iterating.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x entrypoint.sh

# /app/data is where the SQLite database will live. docker-compose.yml
# mounts this to a real folder on the NAS, so it's not lost if the
# container gets rebuilt.
RUN mkdir -p /app/data
ENV DB_FILE=/app/data/softball.db

EXPOSE 5000

ENTRYPOINT ["./entrypoint.sh"]
