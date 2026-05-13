import time
import requests
from requests.auth import HTTPBasicAuth
from config import FTC_API_BASE, FTC_API_USER, FTC_API_KEY, REQUEST_DELAY, SEASON


class FTCApiClient:
    def __init__(self):
        self._auth = HTTPBasicAuth(FTC_API_USER, FTC_API_KEY)
        self._session = requests.Session()
        self._session.auth = self._auth
        self._session.headers.update({"Accept": "application/json"})
        self._last_request = 0.0

    def _get(self, path: str, params: dict = None) -> dict:
        elapsed = time.time() - self._last_request
        if elapsed < REQUEST_DELAY:
            time.sleep(REQUEST_DELAY - elapsed)
        url = f"{FTC_API_BASE}/{path}"
        resp = self._session.get(url, params=params, timeout=30)
        self._last_request = time.time()
        resp.raise_for_status()
        return resp.json()

    # ── endpoints ─────────────────────────────────────────────────────────────

    def get_teams(self, page: int = 1) -> dict:
        return self._get(f"{SEASON}/teams", {"page": page})

    def get_all_teams(self) -> list[dict]:
        teams = []
        page = 1
        while True:
            data = self.get_teams(page)
            batch = data.get("teams", [])
            teams.extend(batch)
            if len(teams) >= data.get("teamCountTotal", 0):
                break
            page += 1
        return teams

    def get_events(self) -> list[dict]:
        data = self._get(f"{SEASON}/events")
        return data.get("events", [])

    def get_matches(self, event_code: str) -> list[dict]:
        data = self._get(f"{SEASON}/matches/{event_code}")
        return data.get("matches", [])

    def get_scores(self, event_code: str, level: str = "qual") -> list[dict]:
        """level: 'qual' or 'playoff'"""
        data = self._get(f"{SEASON}/scores/{event_code}/{level}")
        return data.get("matchScores", [])

    def get_rankings(self, event_code: str) -> list[dict]:
        data = self._get(f"{SEASON}/rankings/{event_code}")
        return data.get("Rankings", [])


# ── normalizers ───────────────────────────────────────────────────────────────

def normalize_team(raw: dict) -> dict:
    return {
        "team_number": raw["teamNumber"],
        "name": raw.get("nameShort") or raw.get("nameFull", ""),
        "city": raw.get("city", ""),
        "state_prov": raw.get("stateProv", ""),
        "country": raw.get("country", ""),
        "rookie_year": raw.get("rookieYear"),
        "home_region": raw.get("homeRegion"),
    }


def normalize_event(raw: dict) -> dict:
    return {
        "event_code": raw["code"],
        "name": raw.get("name", ""),
        "type": raw.get("typeName", raw.get("type", "")),
        "start_date": raw.get("dateStart", ""),
        "end_date": raw.get("dateEnd", ""),
        "city": raw.get("city", ""),
        "state_prov": raw.get("stateprov", raw.get("stateProv", "")),
        "country": raw.get("country", ""),
        "season": SEASON,
    }


def normalize_match(raw: dict, event_code: str) -> dict | None:
    teams = {t["station"]: t["teamNumber"] for t in raw.get("teams", [])}
    level = raw.get("tournamentLevel", "QUALIFICATION")

    # Skip matches with no scores posted yet
    if raw.get("scoreRedFinal") is None:
        return None

    return {
        "event_code": event_code,
        "match_number": raw["matchNumber"],
        "tournament_level": level,
        "series": raw.get("series", 0),
        "actual_start": raw.get("actualStartTime"),
        "red1": teams.get("Red1"),
        "red2": teams.get("Red2"),
        "blue1": teams.get("Blue1"),
        "blue2": teams.get("Blue2"),
        "red_score": raw.get("scoreRedFinal"),
        "blue_score": raw.get("scoreBlueFinal"),
        "red_auto": raw.get("scoreRedAuto"),
        "blue_auto": raw.get("scoreBlueAuto"),
        "red_foul": raw.get("scoreRedFoul"),
        "blue_foul": raw.get("scoreBlueFoul"),
    }


def normalize_score(raw_alliance: dict, match_id: int, alliance: str) -> dict:
    return {
        "match_id": match_id,
        "alliance": alliance.upper(),
        "auto_leave_points": raw_alliance.get("autoLeavePoints", 0),
        "auto_artifact_points": raw_alliance.get("autoArtifactPoints", 0),
        "auto_pattern_points": raw_alliance.get("autoPatternPoints", 0),
        "auto_points": raw_alliance.get("autoPoints", 0),
        "teleop_artifact_points": raw_alliance.get("teleopArtifactPoints", 0),
        "teleop_depot_points": raw_alliance.get("teleopDepotPoints", 0),
        "teleop_pattern_points": raw_alliance.get("teleopPatternPoints", 0),
        "teleop_base_points": raw_alliance.get("teleopBasePoints", 0),
        "teleop_points": raw_alliance.get("teleopPoints", 0),
        "foul_points_committed": raw_alliance.get("foulPointsCommitted", 0),
        "movement_rp": 1 if raw_alliance.get("movementRP") else 0,
        "goal_rp": 1 if raw_alliance.get("goalRP") else 0,
        "pattern_rp": 1 if raw_alliance.get("patternRP") else 0,
        "total_points": raw_alliance.get("totalPoints", 0),
        "robot1_auto": 1 if raw_alliance.get("robot1Auto") else 0,
        "robot2_auto": 1 if raw_alliance.get("robot2Auto") else 0,
        "robot1_teleop": raw_alliance.get("robot1Teleop", "NONE"),
        "robot2_teleop": raw_alliance.get("robot2Teleop", "NONE"),
    }
