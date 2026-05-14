import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from config import DB_PATH


def get_conn(path: str = DB_PATH) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def transaction(path: str = DB_PATH):
    conn = get_conn(path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(path: str = DB_PATH):
    with transaction(path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS teams (
                team_number     INTEGER PRIMARY KEY,
                name            TEXT,
                city            TEXT,
                state_prov      TEXT,
                country         TEXT,
                rookie_year     INTEGER,
                home_region     TEXT,
                league_code     TEXT,
                league_name     TEXT
            );

            CREATE TABLE IF NOT EXISTS events (
                event_code      TEXT PRIMARY KEY,
                name            TEXT,
                type            TEXT,
                start_date      TEXT,
                end_date        TEXT,
                city            TEXT,
                state_prov      TEXT,
                country         TEXT,
                season          INTEGER NOT NULL,
                last_fetched    TEXT
            );

            CREATE TABLE IF NOT EXISTS matches (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                event_code      TEXT NOT NULL REFERENCES events(event_code),
                match_number    INTEGER NOT NULL,
                tournament_level TEXT NOT NULL,  -- QUALIFICATION | PLAYOFF
                series          INTEGER NOT NULL DEFAULT 0,
                actual_start    TEXT,
                red1            INTEGER,
                red2            INTEGER,
                blue1           INTEGER,
                blue2           INTEGER,
                red_score       INTEGER,
                blue_score      INTEGER,
                red_auto        INTEGER,
                blue_auto       INTEGER,
                red_foul        INTEGER,
                blue_foul       INTEGER,
                UNIQUE(event_code, tournament_level, series, match_number)
            );

            CREATE TABLE IF NOT EXISTS match_scores (
                id                      INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id                INTEGER NOT NULL REFERENCES matches(id),
                alliance                TEXT NOT NULL,  -- RED | BLUE
                auto_leave_points       INTEGER DEFAULT 0,
                auto_artifact_points    INTEGER DEFAULT 0,
                auto_pattern_points     INTEGER DEFAULT 0,
                auto_points             INTEGER DEFAULT 0,
                teleop_artifact_points  INTEGER DEFAULT 0,
                teleop_depot_points     INTEGER DEFAULT 0,
                teleop_pattern_points   INTEGER DEFAULT 0,
                teleop_base_points      INTEGER DEFAULT 0,
                teleop_points           INTEGER DEFAULT 0,
                foul_points_committed   INTEGER DEFAULT 0,
                movement_rp             INTEGER DEFAULT 0,
                goal_rp                 INTEGER DEFAULT 0,
                pattern_rp              INTEGER DEFAULT 0,
                total_points            INTEGER DEFAULT 0,
                robot1_auto             INTEGER DEFAULT 0,
                robot2_auto             INTEGER DEFAULT 0,
                robot1_teleop           TEXT DEFAULT 'NONE',
                robot2_teleop           TEXT DEFAULT 'NONE',
                UNIQUE(match_id, alliance)
            );

            -- Running EPA history: one row per team per match processed
            CREATE TABLE IF NOT EXISTS team_epa_history (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                team_number     INTEGER NOT NULL,
                match_id        INTEGER NOT NULL REFERENCES matches(id),
                event_code      TEXT NOT NULL,
                total_epa       REAL DEFAULT 0,
                auto_epa        REAL DEFAULT 0,
                teleop_epa      REAL DEFAULT 0,
                endgame_epa     REAL DEFAULT 0,
                movement_rp     REAL DEFAULT 0,
                goal_rp         REAL DEFAULT 0,
                pattern_rp      REAL DEFAULT 0,
                qual_n          INTEGER DEFAULT 0,
                UNIQUE(team_number, match_id)
            );

            -- Current season ratings (one row per team, updated in place)
            CREATE TABLE IF NOT EXISTS team_season (
                team_number     INTEGER PRIMARY KEY,
                total_epa       REAL DEFAULT 0,
                auto_epa        REAL DEFAULT 0,
                teleop_epa      REAL DEFAULT 0,
                endgame_epa     REAL DEFAULT 0,
                movement_rp     REAL DEFAULT 0,
                goal_rp         REAL DEFAULT 0,
                pattern_rp      REAL DEFAULT 0,
                qual_n          INTEGER DEFAULT 0,
                wins            INTEGER DEFAULT 0,
                losses          INTEGER DEFAULT 0,
                ties            INTEGER DEFAULT 0,
                avg_score       REAL DEFAULT 0,
                updated_at      TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_matches_event ON matches(event_code);
            CREATE INDEX IF NOT EXISTS idx_scores_match  ON match_scores(match_id);
            CREATE INDEX IF NOT EXISTS idx_epa_team      ON team_epa_history(team_number);
            CREATE INDEX IF NOT EXISTS idx_epa_event     ON team_epa_history(event_code);
        """)
        # Migrate existing databases
        for col_def in (
            "teams home_region TEXT",
            "teams league_code TEXT",
            "teams league_name TEXT",
            "events last_fetched TEXT",
        ):
            table, col = col_def.split(" ", 1)
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col}")
            except Exception:
                pass  # column already exists


# ── helpers ──────────────────────────────────────────────────────────────────

def upsert_team(conn: sqlite3.Connection, t: dict):
    conn.execute("""
        INSERT INTO teams(team_number, name, city, state_prov, country, rookie_year, home_region)
        VALUES(:team_number,:name,:city,:state_prov,:country,:rookie_year,:home_region)
        ON CONFLICT(team_number) DO UPDATE SET
            name=excluded.name, city=excluded.city,
            state_prov=excluded.state_prov, country=excluded.country,
            rookie_year=excluded.rookie_year, home_region=excluded.home_region
    """, t)


def update_team_league(conn: sqlite3.Connection, team_number: int, league_code: str, league_name: str):
    conn.execute(
        "UPDATE teams SET league_code=?, league_name=? WHERE team_number=?",
        (league_code, league_name, team_number),
    )


def mark_event_fetched(conn: sqlite3.Connection, event_code: str):
    conn.execute(
        "UPDATE events SET last_fetched=? WHERE event_code=?",
        (datetime.now(timezone.utc).isoformat(), event_code),
    )


def upsert_event(conn: sqlite3.Connection, e: dict):
    conn.execute("""
        INSERT INTO events(event_code,name,type,start_date,end_date,city,state_prov,country,season)
        VALUES(:event_code,:name,:type,:start_date,:end_date,:city,:state_prov,:country,:season)
        ON CONFLICT(event_code) DO UPDATE SET
            name=excluded.name, type=excluded.type,
            start_date=excluded.start_date, end_date=excluded.end_date
    """, e)


def upsert_match(conn: sqlite3.Connection, m: dict) -> int:
    conn.execute("""
        INSERT INTO matches(event_code,match_number,tournament_level,series,
            actual_start,red1,red2,blue1,blue2,
            red_score,blue_score,red_auto,blue_auto,red_foul,blue_foul)
        VALUES(:event_code,:match_number,:tournament_level,:series,
            :actual_start,:red1,:red2,:blue1,:blue2,
            :red_score,:blue_score,:red_auto,:blue_auto,:red_foul,:blue_foul)
        ON CONFLICT(event_code,tournament_level,series,match_number) DO UPDATE SET
            actual_start=excluded.actual_start,
            red_score=excluded.red_score, blue_score=excluded.blue_score,
            red_auto=excluded.red_auto, blue_auto=excluded.blue_auto,
            red_foul=excluded.red_foul, blue_foul=excluded.blue_foul
    """, m)
    row = conn.execute("""
        SELECT id FROM matches
        WHERE event_code=? AND tournament_level=? AND series=? AND match_number=?
    """, (m["event_code"], m["tournament_level"], m["series"], m["match_number"])).fetchone()
    return row["id"]


def upsert_match_score(conn: sqlite3.Connection, s: dict):
    conn.execute("""
        INSERT INTO match_scores(
            match_id, alliance,
            auto_leave_points, auto_artifact_points, auto_pattern_points, auto_points,
            teleop_artifact_points, teleop_depot_points, teleop_pattern_points,
            teleop_base_points, teleop_points,
            foul_points_committed, movement_rp, goal_rp, pattern_rp, total_points,
            robot1_auto, robot2_auto, robot1_teleop, robot2_teleop)
        VALUES(
            :match_id, :alliance,
            :auto_leave_points, :auto_artifact_points, :auto_pattern_points, :auto_points,
            :teleop_artifact_points, :teleop_depot_points, :teleop_pattern_points,
            :teleop_base_points, :teleop_points,
            :foul_points_committed, :movement_rp, :goal_rp, :pattern_rp, :total_points,
            :robot1_auto, :robot2_auto, :robot1_teleop, :robot2_teleop)
        ON CONFLICT(match_id, alliance) DO UPDATE SET
            auto_points=excluded.auto_points,
            teleop_points=excluded.teleop_points,
            foul_points_committed=excluded.foul_points_committed,
            total_points=excluded.total_points,
            movement_rp=excluded.movement_rp,
            goal_rp=excluded.goal_rp,
            pattern_rp=excluded.pattern_rp
    """, s)


def get_unprocessed_matches(conn: sqlite3.Connection):
    """Matches with scores that haven't been through the EPA calculator yet."""
    return conn.execute("""
        SELECT m.id, m.event_code, m.match_number, m.tournament_level, m.series,
               m.actual_start, m.red1, m.red2, m.blue1, m.blue2
        FROM matches m
        WHERE m.red_score IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM team_epa_history h
              WHERE h.match_id = m.id AND h.team_number = m.red1
          )
        ORDER BY m.actual_start ASC NULLS LAST, m.id ASC
    """).fetchall()


def get_match_scores(conn: sqlite3.Connection, match_id: int) -> dict:
    rows = conn.execute(
        "SELECT * FROM match_scores WHERE match_id=?", (match_id,)
    ).fetchall()
    return {r["alliance"]: dict(r) for r in rows}


def get_team_season(conn: sqlite3.Connection, team_number: int) -> dict | None:
    row = conn.execute(
        "SELECT * FROM team_season WHERE team_number=?", (team_number,)
    ).fetchone()
    return dict(row) if row else None
