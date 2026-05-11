"""
Main ingestion pipeline.

Run modes:
  python ingest.py              -- full refresh (all events)
  python ingest.py --event CODE -- single event refresh
"""

import argparse
import sys
from datetime import datetime, timezone

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


def ingest_teams(client: FTCApiClient):
    print("Fetching teams...")
    raw_teams = client.get_all_teams()
    with transaction() as conn:
        for raw in raw_teams:
            upsert_team(conn, normalize_team(raw))
    print(f"  {len(raw_teams)} teams stored.")


def ingest_events(client: FTCApiClient) -> list[str]:
    print("Fetching events...")
    raw_events = client.get_events()
    codes = []
    with transaction() as conn:
        for raw in raw_events:
            upsert_event(conn, normalize_event(raw))
            codes.append(raw["code"])
    print(f"  {len(codes)} events stored.")
    return codes


def ingest_event_matches(client: FTCApiClient, event_code: str):
    print(f"  [{event_code}] fetching matches...")
    raw_matches = client.get_matches(event_code)

    with transaction() as conn:
        for raw in raw_matches:
            norm = normalize_match(raw, event_code)
            if norm is None:
                continue
            match_id = upsert_match(conn, norm)

            # fetch detailed scores for this match level
            level_str = "playoff" if norm["tournament_level"] != "QUALIFICATION" else "qual"
            # scores are fetched per-event below; we'll store what we get

    # Fetch qual and playoff scores separately (one API call each)
    for level in ("qual", "playoff"):
        try:
            raw_scores = client.get_scores(event_code, level)
        except Exception as e:
            print(f"    score fetch error ({level}): {e}")
            continue

        with transaction() as conn:
            for ms in raw_scores:
                # Resolve match_id
                level_name = "QUALIFICATION" if level == "qual" else "PLAYOFF"
                row = conn.execute("""
                    SELECT id FROM matches
                    WHERE event_code=? AND tournament_level=? AND series=? AND match_number=?
                """, (event_code, level_name, ms.get("matchSeries", 0), ms["matchNumber"])).fetchone()
                if row is None:
                    continue
                match_id = row["id"]

                for alliance_data in ms.get("alliances", []):
                    alliance = alliance_data["alliance"]  # "Red" or "Blue"
                    norm_score = normalize_score(alliance_data, match_id, alliance)
                    upsert_match_score(conn, norm_score)


def recalculate_epa():
    """Recompute EPA for all unprocessed matches, ordered by start time."""
    print("Calculating EPA...")

    # Load current season state so incremental updates work
    calc = EPACalculator()
    conn = get_conn()

    # Seed calculator from existing team_season rows
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
            dq_teams = set()  # TODO: parse DQ flags from match data if needed

            history_rows = calc.process_match(match, scores, is_elim, dq_teams)
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

        # Write final season ratings
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


def run(event_filter: str | None = None):
    init_db()
    client = FTCApiClient()

    ingest_teams(client)
    event_codes = ingest_events(client)

    if event_filter:
        event_codes = [c for c in event_codes if c == event_filter]
        if not event_codes:
            print(f"Event '{event_filter}' not found.")
            sys.exit(1)

    for code in event_codes:
        ingest_event_matches(client, code)

    recalculate_epa()
    print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", help="Ingest a single event by code")
    args = parser.parse_args()
    run(event_filter=args.event)
