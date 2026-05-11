"""
EPA calculator for FTC 2025-26.

Model mirrors statbotics:
  - EWMA with decaying K-factor based on qual matches played
  - Separate component EPAs: auto, teleop, endgame
  - Ranking point probability tracked separately
  - Playoff matches weighted at ELIM_WEIGHT (1/3)
  - Foul points excluded from EPA calculation
  - Match count only increments on qual matches
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
import sqlite3

from config import ELIM_WEIGHT, MIN_K, MAX_K


# ── EPA state ─────────────────────────────────────────────────────────────────

@dataclass
class TeamEPA:
    total: float = 0.0
    auto: float = 0.0
    teleop: float = 0.0
    endgame: float = 0.0
    movement_rp: float = 0.0
    goal_rp: float = 0.0
    pattern_rp: float = 0.0
    qual_n: int = 0          # qual matches played (drives K decay)
    wins: int = 0
    losses: int = 0
    ties: int = 0
    score_sum: float = 0.0   # for avg_score

    def as_dict(self) -> dict:
        avg = self.score_sum / max(1, self.qual_n + self.wins + self.losses + self.ties)
        return {
            "total_epa": round(self.total, 3),
            "auto_epa": round(self.auto, 3),
            "teleop_epa": round(self.teleop, 3),
            "endgame_epa": round(self.endgame, 3),
            "movement_rp": round(self.movement_rp, 4),
            "goal_rp": round(self.goal_rp, 4),
            "pattern_rp": round(self.pattern_rp, 4),
            "qual_n": self.qual_n,
            "wins": self.wins,
            "losses": self.losses,
            "ties": self.ties,
            "avg_score": round(avg, 2),
        }


def _k(qual_n: int, is_elim: bool) -> float:
    """Learning rate: decays from MAX_K to MIN_K, halved for elim matches."""
    # Matches statbotics: full rate until 6 matches, then linear decay to floor
    base = max(MIN_K, MAX_K - (MAX_K - MIN_K) / 6 * max(0, qual_n - 6))
    # statbotics multiplies by 2/3 for post-2015 seasons
    base = base * (2 / 3)
    return base * (ELIM_WEIGHT if is_elim else 1.0)


# ── calculator ────────────────────────────────────────────────────────────────

class EPACalculator:
    def __init__(self):
        self.teams: dict[int, TeamEPA] = {}

    def _get(self, team: int) -> TeamEPA:
        if team not in self.teams:
            self.teams[team] = TeamEPA()
        return self.teams[team]

    def process_match(
        self,
        match: sqlite3.Row,
        scores: dict,          # {"RED": {...}, "BLUE": {...}}
        is_elim: bool,
        dq_teams: set[int],
    ) -> list[dict]:
        """
        Update EPA for all four teams and return history rows to persist.
        Returns empty list if the match should be skipped (all-DQ elim, no scores).
        """
        if "RED" not in scores or "BLUE" not in scores:
            return []

        red_teams = [match["red1"], match["red2"]]
        blue_teams = [match["blue1"], match["blue2"]]
        all_teams = red_teams + blue_teams

        # Skip elim matches where an entire alliance is DQ'd
        if is_elim:
            if all(t in dq_teams for t in red_teams) or all(t in dq_teams for t in blue_teams):
                return []

        red_s = scores["RED"]
        blue_s = scores["BLUE"]

        # Earned scores (exclude foul points — gifted, not earned)
        red_earned = red_s["auto_points"] + red_s["teleop_points"]
        blue_earned = blue_s["auto_points"] + blue_s["teleop_points"]

        # Component earned scores
        def components(s):
            return {
                "total": s["auto_points"] + s["teleop_points"],
                "auto": s["auto_points"],
                "teleop": s["teleop_artifact_points"] + s["teleop_depot_points"] + s["teleop_pattern_points"],
                "endgame": s["teleop_base_points"],
                "movement_rp": float(s["movement_rp"]),
                "goal_rp": float(s["goal_rp"]),
                "pattern_rp": float(s["pattern_rp"]),
            }

        red_comp = components(red_s)
        blue_comp = components(blue_s)

        # Predicted alliance scores (sum of team EPAs)
        def predict(teams: list[int]) -> dict:
            epas = [self._get(t) for t in teams]
            return {
                "total": sum(e.total for e in epas),
                "auto": sum(e.auto for e in epas),
                "teleop": sum(e.teleop for e in epas),
                "endgame": sum(e.endgame for e in epas),
                "movement_rp": sum(e.movement_rp for e in epas) / 2,
                "goal_rp": sum(e.goal_rp for e in epas) / 2,
                "pattern_rp": sum(e.pattern_rp for e in epas) / 2,
            }

        red_pred = predict(red_teams)
        blue_pred = predict(blue_teams)

        # Error = actual - predicted (alliance level)
        def err(actual: dict, pred: dict) -> dict:
            return {k: actual[k] - pred[k] for k in actual}

        red_err = err(red_comp, red_pred)
        blue_err = err(blue_comp, blue_pred)

        # Win/loss tracking
        red_won = red_earned > blue_earned
        blue_won = blue_earned > red_earned
        tied = red_earned == blue_earned

        history_rows = []

        for team, alliance_err, alliance_s in [
            *[(t, red_err, red_s) for t in red_teams],
            *[(t, blue_err, blue_s) for t in blue_teams],
        ]:
            state = self._get(team)
            k = _k(state.qual_n, is_elim)

            # Update each EPA component: new = old + K * (error / 2 teams)
            contrib_err = {key: val / 2 for key, val in alliance_err.items()}

            state.total += k * contrib_err["total"]
            state.auto += k * contrib_err["auto"]
            state.teleop += k * contrib_err["teleop"]
            state.endgame += k * contrib_err["endgame"]
            state.movement_rp = max(0.0, min(1.0, state.movement_rp + k * contrib_err["movement_rp"]))
            state.goal_rp = max(0.0, min(1.0, state.goal_rp + k * contrib_err["goal_rp"]))
            state.pattern_rp = max(0.0, min(1.0, state.pattern_rp + k * contrib_err["pattern_rp"]))

            is_red = team in red_teams
            earned = red_earned if is_red else blue_earned
            state.score_sum += earned / 2  # team's share

            if not is_elim:
                state.qual_n += 1
                if is_red:
                    if red_won: state.wins += 1
                    elif tied: state.ties += 1
                    else: state.losses += 1
                else:
                    if blue_won: state.wins += 1
                    elif tied: state.ties += 1
                    else: state.losses += 1

            history_rows.append({
                "team_number": team,
                "match_id": match["id"],
                "event_code": match["event_code"],
                "total_epa": round(state.total, 4),
                "auto_epa": round(state.auto, 4),
                "teleop_epa": round(state.teleop, 4),
                "endgame_epa": round(state.endgame, 4),
                "movement_rp": round(state.movement_rp, 5),
                "goal_rp": round(state.goal_rp, 5),
                "pattern_rp": round(state.pattern_rp, 5),
                "qual_n": state.qual_n,
            })

        return history_rows

    def get_season_rows(self, updated_at: str) -> list[dict]:
        rows = []
        for team_number, state in self.teams.items():
            d = state.as_dict()
            d["team_number"] = team_number
            d["updated_at"] = updated_at
            rows.append(d)
        return rows
