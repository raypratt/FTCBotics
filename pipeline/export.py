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
            t.home_region,
            t.league_code,
            t.league_name,
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

    # Compute country and state ranks + totals (teams_list already sorted by EPA desc)
    country_rank: dict[int, int] = {}
    state_rank: dict[int, int] = {}
    country_counter: dict[str, int] = {}
    state_counter: dict[tuple, int] = {}
    for d in teams_list:
        tn = d["team_number"]
        c = d.get("country") or ""
        s = d.get("state_prov") or ""
        country_counter[c] = country_counter.get(c, 0) + 1
        state_counter[(c, s)] = state_counter.get((c, s), 0) + 1
        country_rank[tn] = country_counter[c]
        state_rank[tn] = state_counter[(c, s)]

    # country_counter / state_counter now hold final totals for each group
    world_total = len(teams_list)
    for d in teams_list:
        tn = d["team_number"]
        c = d.get("country") or ""
        s = d.get("state_prov") or ""
        d["country_rank"] = country_rank[tn]
        d["state_rank"] = state_rank[tn]
        d["world_total"] = world_total
        d["country_total"] = country_counter[c]
        d["state_total"] = state_counter[(c, s)]

    _write(f"{base}/teams.json", teams_list)
    print(f"  Exported {len(teams_list)} teams.")

    # EPA lookup for predicted scores (season-end values)
    epa_lookup = {d["team_number"]: d["total_epa"] for d in teams_list}

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

        # Events with rich detail
        event_rows = conn.execute("""
            SELECT DISTINCT e.event_code, e.name, e.start_date, e.end_date,
                            e.city, e.state_prov, e.type
            FROM team_epa_history h
            JOIN events e ON e.event_code = h.event_code
            WHERE h.team_number = ?
            ORDER BY e.start_date ASC
        """, (tn,)).fetchall()

        events_out = []
        for ev in event_rows:
            ec = ev["event_code"]

            # Last EPA snapshot for this event
            epa_snap = conn.execute("""
                SELECT h.total_epa, h.auto_epa, h.teleop_epa, h.endgame_epa
                FROM team_epa_history h
                JOIN matches m ON m.id = h.match_id
                WHERE h.team_number = ? AND h.event_code = ?
                ORDER BY m.actual_start DESC, m.id DESC
                LIMIT 1
            """, (tn, ec)).fetchone()

            # All matches the team played at this event
            match_rows = conn.execute("""
                SELECT m.match_number, m.tournament_level, m.series,
                       m.actual_start, m.red1, m.red2, m.blue1, m.blue2,
                       m.red_score, m.blue_score
                FROM matches m
                WHERE m.event_code = ?
                  AND (m.red1=? OR m.red2=? OR m.blue1=? OR m.blue2=?)
                ORDER BY m.actual_start ASC, m.id ASC
            """, (ec, tn, tn, tn, tn)).fetchall()

            wins = losses = ties = 0
            match_list = []
            for m in match_rows:
                r1, r2, b1, b2 = m["red1"], m["red2"], m["blue1"], m["blue2"]
                rs, bs = m["red_score"], m["blue_score"]

                if tn in (r1, r2):
                    alliance = "RED"
                    partner = r2 if tn == r1 else r1
                    opp1, opp2 = b1, b2
                    a_score, o_score = rs, bs
                else:
                    alliance = "BLUE"
                    partner = b2 if tn == b1 else b1
                    opp1, opp2 = r1, r2
                    a_score, o_score = bs, rs

                if a_score is not None and o_score is not None:
                    if a_score > o_score:
                        result = "W"
                        if m["tournament_level"] == "QUALIFICATION":
                            wins += 1
                    elif a_score < o_score:
                        result = "L"
                        if m["tournament_level"] == "QUALIFICATION":
                            losses += 1
                    else:
                        result = "T"
                        if m["tournament_level"] == "QUALIFICATION":
                            ties += 1
                else:
                    result = None

                pred_a = round(epa_lookup.get(tn, 0) + epa_lookup.get(partner or 0, 0), 1)
                pred_o = round(epa_lookup.get(opp1 or 0, 0) + epa_lookup.get(opp2 or 0, 0), 1)

                match_list.append({
                    "match_number": m["match_number"],
                    "tournament_level": m["tournament_level"],
                    "series": m["series"],
                    "alliance": alliance,
                    "partner": partner,
                    "opp1": opp1,
                    "opp2": opp2,
                    "alliance_score": a_score,
                    "opp_score": o_score,
                    "predicted_alliance": pred_a,
                    "predicted_opp": pred_o,
                    "result": result,
                })

            events_out.append({
                **dict(ev),
                "epa_end": dict(epa_snap) if epa_snap else None,
                "record": {"wins": wins, "losses": losses, "ties": ties},
                "matches": match_list,
            })

        team_info = conn.execute(
            "SELECT * FROM teams WHERE team_number=?", (tn,)
        ).fetchone()

        payload = {
            **team_row,
            "team_info": dict(team_info) if team_info else {},
            "epa_history": [dict(r) for r in history],
            "events": events_out,
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
