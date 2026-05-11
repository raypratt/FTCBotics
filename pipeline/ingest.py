"""
Main ingestion pipeline.

Run modes:
  python ingest.py              -- smart incremental (active events only)
  python ingest.py --event CODE -- single event refresh
  python ingest.py --full       -- force full refresh of all events
"""

import argparse
import sys
from datetime import datetime, timezone, timedelta

from database import (
    init_db, transaction, get_conn,
    upsert_team, upsert_event, upsert_match, upsert_match_score,
    get_unprocessed_matches, get_match_scores,
)
from ftc_api import (
    FTCApiClient,
    normalize_team, normalize_event, normalize_match, normalize_score,
)
from epa import EPACalculator

# How many days before/after event end date to keep re-fetching
_ACTIVE_WINDOW_DAYS = 3


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _is_active(event: dict) -> bool:
    """True if the event is ongoing or ended within the active window."""
    today = _today()
    start = (event.get("start_date") or "")[:10]
    end = (event.get("end_date") or start)[:10]
    cutoff = (datetime.now(timezone.utc) - timedelta(days=_ACTIVE_WINDOW_DAYS)).strftime("%Y-%m-%d")
    return start <= today and end >= cutoff


def _needs_refresh(event_code: str, conn) -> bool:
    """True if this event has no matches stored yet."""
    row = conn.execute(
        "SELECT COUNT(*) as n FROM matches WHERE event_code=?", (event_code,)
    ).fetchone()
    return row["n"] == 0


def ingest_teams(client: FTCApiClient, force: bool = False):
    """Fetch teams at most once per day unless forced."""
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) as n FROM teams").fetchone()["n"]
    conn.close()

    if count > 0 and not force:
        print(f"Teams: {count} cached, skipping fetch.")
        return

    print("Fetching teams...")
    raw_teams = client.get_all_teams()
    with transaction() as conn:
        for raw in raw_teams:
            upsert_team(conn, normalize_team(raw))
    print(f"  {len(raw_teams)} teams stored.")


def ingest_events(client: FTCApiClient) -> list[dict]:
    """Fetch the event list. Returns raw event dicts."""
    print("Fetching event list...")
    raw_events = client.get_events()
    with transaction() as conn:
        for raw in raw_events:
            upsert_event(conn, normalize_event(raw))
    print(f"  {len(raw_events)} events stored.")
    return raw_events


def ingest_event_matches(client: FTCApiClient, event_code: str):
    print(f"  [{event_code}] fetching matches...")
    raw_matches = client.get_matches(event_code)

    with transaction() as conn:
        for raw in raw_matches:
            norm = normalize_match(raw, event_code)
            if norm is None:
                continue
            upsert_match(conn, norm)

    for level in ("qual", "playoff"):
        try:
            raw_scores = client.get_scores(event_code, level)
        except Exception as e:
            print(f"    score fetch error ({level}): {e}")
            continue

        with transaction() as conn:
            for ms in raw_scores:
                level_name = "QUALIFICATION" if level == "qual" else "PLAYOFF"
                row = conn.execute("""
                    SELECT id FROM matches
                    WHERE event_code=? AND tournament_level=? AND series=? AND match_number=?
                """, (event_code, level_name, ms.get("matchSeries", 0), ms["matchNumber"])).fetchone()
                if row is None:
                    continue
                match_id = row["id"]
                for alliance_data in ms.get("alliances", []):
                    norm_score = normalize_score(alliance_data, match_id, alliance_data["alliance"])
                    upsert_match_score(conn, norm_score)


def recalculate_epa():
    """Recompute EPA for all unprocessed matches, ordered by start time."""
    print("Calculating EPA...")

    calc = EPACalculator()
    conn = get_conn()

    existing = conn.execute("SELECT * FROM team_season").fetchall()
    for row in existing:
        from epa import TeamEPA
        state = TeamEPA(
            total=row["total_epa"],
            auto=row["auto_epa"],
            teleop=row["teleop_epa"],
            endgame=row["endgame_epa"],
            movement_rp=row["movement_rp"],
            goal_rp=row["goal_rp"],
            pattern_rp=row["pattern_rp"],
            qual_n=row["qual_n"],
            wins=row["wins"],
            losses=row["losses"],
            ties=row["ties"],
        )
        calc.teams[row["team_number"]] = state

    unprocessed = get_unprocessed_matches(conn)
    conn.close()

    if not unprocessed:
        print("  No new matches to process.")
        return

    print(f"  Processing {len(unprocessed)} matches...")
    processed = 0

    with transaction() as conn:
        for match in unprocessed:
            is_elim = match["tournament_level"] != "QUALIFICATION"
            scores = get_match_scores(conn, match["id"])
            history_rows = calc.process_match(match, scores, is_elim, set())
            if not history_rows:
                continue

            for row in history_rows:
                conn.execute("""
                    INSERT OR IGNORE INTO team_epa_history
                        (team_number, match_id, event_code,
                         total_epa, auto_epa, teleop_epa, endgame_epa,
                         movement_rp, goal_rp, pattern_rp, qual_n)
                    VALUES
                        (:team_number, :match_id, :event_code,
                         :total_epa, :auto_epa, :teleop_epa, :endgame_epa,
                         :movement_rp, :goal_rp, :pattern_rp, :qual_n)
                """, row)
            processed += 1

        now = datetime.now(timezone.utc).isoformat()
        for row in calc.get_season_rows(now):
            conn.execute("""
                INSERT INTO team_season(
                    team_number, total_epa, auto_epa, teleop_epa, endgame_epa,
                    movement_rp, goal_rp, pattern_rp, qual_n,
                    wins, losses, ties, avg_score, updated_at)
                VALUES(
                    :team_number, :total_epa, :auto_epa, :teleop_epa, :endgame_epa,
                    :movement_rp, :goal_rp, :pattern_rp, :qual_n,
                    :wins, :losses, :ties, :avg_score, :updated_at)
                ON CONFLICT(team_number) DO UPDATE SET
                    total_epa=excluded.total_epa,
                    auto_epa=excluded.auto_epa,
                    teleop_epa=excluded.teleop_epa,
                    endgame_epa=excluded.endgame_epa,
                    movement_rp=excluded.movement_rp,
                    goal_rp=excluded.goal_rp,
                    pattern_rp=excluded.pattern_rp,
                    qual_n=excluded.qual_n,
                    wins=excluded.wins,
                    losses=excluded.losses,
                    ties=excluded.ties,
                    avg_score=excluded.avg_score,
                    updated_at=excluded.updated_at
            """, row)

    print(f"  EPA updated for {processed} matches, {len(calc.teams)} teams.")


def run(event_filter: str | None = None, full: bool = False):
    init_db()
    client = FTCApiClient()

    ingest_teams(client, force=full)
    raw_events = ingest_events(client)

    if event_filter:
        # Single-event mode: fetch regardless of active window
        targets = [e for e in raw_events if e["code"] == event_filter]
        if not targets:
            print(f"Event '{event_filter}' not found.")
            sys.exit(1)
        for e in targets:
            ingest_event_matches(client, e["code"])
    elif full:
        # Full refresh: fetch every event
        print(f"Full refresh: fetching all {len(raw_events)} events...")
        for e in raw_events:
            ingest_event_matches(client, e["code"])
    else:
        # Smart incremental: only active events or ones with no data yet
        conn = get_conn()
        targets = [
            e for e in raw_events
            if _is_active(e) or _needs_refresh(e["code"], conn)
        ]
        conn.close()
        print(f"Incremental: {len(targets)} events to fetch "
              f"({len(raw_events) - len(targets)} skipped as historical).")
        for e in targets:
            ingest_event_matches(client, e["code"])

    recalculate_epa()
    print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", help="Ingest a single event by code")
    parser.add_argument("--full", action="store_true", help="Force full refresh of all events")
    args = parser.parse_args()
    run(event_filter=args.event, full=args.full)
