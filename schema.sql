-- Play-by-play schema. Everything downstream (season totals, career
-- totals, streaks, the game calendar) is a QUERY over these four
-- tables, not a separately-stored number. That's the whole design
-- idea: store the raw plays once, derive everything else on demand.

DROP TABLE IF EXISTS plate_appearances;
DROP TABLE IF EXISTS games;
DROP TABLE IF EXISTS players;
DROP TABLE IF EXISTS seasons;

CREATE TABLE seasons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL,
    league TEXT NOT NULL,           -- e.g. "SuTh"
    UNIQUE (year, league)
);

CREATE TABLE players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    jersey_number INTEGER
);

CREATE TABLE games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    season_id INTEGER NOT NULL REFERENCES seasons(id),
    game_number INTEGER NOT NULL,
    date TEXT,                      -- stored as "YYYY-MM-DD"
    time TEXT,
    opponent TEXT,
    location TEXT,
    team_runs INTEGER,
    opponent_runs INTEGER,
    temperature TEXT,
    dew_point TEXT,
    humidity TEXT,
    wind TEXT,
    wind_speed TEXT,
    wind_gust TEXT,
    pressure TEXT,
    precipitation TEXT,
    weather TEXT,
    ground TEXT,
    sun TEXT,
    UNIQUE (season_id, game_number)
);

CREATE TABLE plate_appearances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL REFERENCES games(id),
    player_id INTEGER NOT NULL REFERENCES players(id),
    batting_order INTEGER,          -- B# column
    outs_before INTEGER,            -- O column: outs when this PA started
    on_1st INTEGER NOT NULL DEFAULT 0,  -- stored as 0/1, not TRUE/FALSE
    on_2nd INTEGER NOT NULL DEFAULT 0,
    on_3rd INTEGER NOT NULL DEFAULT 0,
    result TEXT NOT NULL,           -- 1B, 2B, 3B, HR, BB, SO, GO, FO, LO, PO, DP, FC, SF
    rbi INTEGER NOT NULL DEFAULT 0,
    scored INTEGER NOT NULL DEFAULT 0,  -- 1 if this player scored a run
    pitch_sequence TEXT
);

-- Indexes matter here: every stats query filters or groups by player
-- and/or game, so these keep things fast even once you've got several
-- seasons of play-by-play loaded in.
CREATE INDEX idx_pa_player ON plate_appearances(player_id);
CREATE INDEX idx_pa_game ON plate_appearances(game_id);
CREATE INDEX idx_games_season ON games(season_id);
