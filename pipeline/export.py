"""
Exports calculated data to static JSON files consumed by the Next.js frontend.

Output structure:
  frontend/public/data/
    meta.json                         -- last updated timestamp, season info
    teams.json                        -- full team leaderboard (all teams, ranked)
    team/{team_number}.json           -- per-team detail + EPA history
    events.json                       -- event list
    event/{event_code}.json           -- per-event matches + team EPAs
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from database import get_conn
from config import EXPORT_PATH, SEASON


def _write(path: str, data):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        json.dump(data, f, separators=(",", ":"))


def export_all():
    conn = get_conn()
    now = datetime.now(timezone.utc).isoformat()
    base = EXPORT_PATH

    # ── meta ──────────────────────────────────────────────────────────────────
    _write(f"{base}/meta.json", {"season": SEASON, "updated_at": now})

    # ── teams leaderboard ─────────────────────────────────────────────────────
    rows = conn.execute("""
        SELECT
            ts.team_number,
            t.name,
            t.city,
            t.state_prov,
            t.country,
            ts.total_epa,
            ts.auto_epa,
            ts.teleop_epa,
            ts.endgame_epa,
            ts.movement_rp,
            ts.goal_rp,
            ts.pattern_rp,
            ts.qual_n,
            ts.wins,
            ts.losses,
            ts.ties,
            ts.avg_score
        FROM team_season ts
        LEFT JOIN teams t ON t.team_number = ts.team_number
        ORDER BY ts.total_epa DESC
    """).fetchall()

    teams_list = []
    for rank, row in enumerate(rows, 1):
        d = dict(row)
        d["rank"] = rank
        teams_list.append(d)

    _write(f"{base}/teams.json", teams_list)
    print(f"  Exported {len(teams_list)} teams.")

    # ── per-team detail ───────────────────────────────────────────────────────
    for team_row in teams_list:
        tn = team_row["team_number"]

        # EPA history across the season
        history = conn.execute("""
            SELECT
                h.total_epa, h.auto_epa, h.teleop_epa, h.endgame_epa,
                h.movement_rp, h.goal_rp, h.pattern_rp, h.qual_n,
                h.event_code,
                m.match_number, m.tournament_level, m.actual_start
            FROM team_epa_history h
            JOIN matches m ON m.id = h.match_id
            WHERE h.team_number = ?
            ORDER BY m.actual_start ASC, m.id ASC
        """, (tn,)).fetchall()

        # Events this team participated in
        events = conn.execute("""
            SELECT DISTINCT e.event_code, e.name, e.start_date, e.end_date,
                            e.city, e.state_prov, e.type
            FROM team_epa_history h
            JOIN events e ON e.event_code = h.event_code
            WHERE h.team_number = ?
            ORDER BY e.start_date ASC
        """, (tn,)).fetchall()

        team_info = conn.execute(
            "SELECT * FROM teams WHERE team_number=?", (tn,)
        ).fetchone()

        payload = {
            **team_row,
            "team_info": dict(team_info) if team_info else {},
            "epa_history": [dict(r) for r in history],
            "events": [dict(r) for r in events],
        }
        _write(f"{base}/team/{tn}.json", payload)

    print(f"  Exported {len(teams_list)} team detail files.")

    # ── events list ───────────────────────────────────────────────────────────
    events = conn.execute("""
        SELECT event_code, name, type, start_date, end_date, city, state_prov, country
        FROM events
        WHERE season = ?
        ORDER BY start_date ASC
    """, (SEASON,)).fetchall()

    _write(f"{base}/events.json", [dict(r) for r in events])
    print(f"  Exported {len(events)} events.")

    # ── per-event detail ──────────────────────────────────────────────────────
    for ev in events:
        code = ev["event_code"]

        matches = conn.execute("""
            SELECT
                m.id, m.match_number, m.tournament_level, m.series,
                m.actual_start, m.red1, m.red2, m.blue1, m.blue2,
                m.red_score, m.blue_score, m.red_auto, m.blue_auto,
                m.red_foul, m.blue_foul
            FROM matches m
            WHERE m.event_code = ?
            ORDER BY m.actual_start ASC, m.tournament_level ASC, m.id ASC
        """, (code,)).fetchall()

        # Team EPA snapshots at this event (latest per team)
        team_epas = conn.execute("""
            SELECT
                h.team_number,
                t.name,
                MAX(h.total_epa) as peak_total_epa,
                h.total_epa, h.auto_epa, h.teleop_epa, h.endgame_epa,
                h.qual_n
            FROM team_epa_history h
            LEFT JOIN teams t ON t.team_number = h.team_number
            WHERE h.event_code = ?
            GROUP BY h.team_number
            ORDER BY h.total_epa DESC
        """, (code,)).fetchall()

        payload = {
            "event": dict(ev),
            "matches": [dict(m) for m in matches],
            "team_epas": [dict(r) for r in team_epas],
        }
        _write(f"{base}/event/{code}.json", payload)

    print(f"  Exported {len(events)} event detail files.")
    conn.close()


if __name__ == "__main__":
    export_all()
