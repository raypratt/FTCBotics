import os

SEASON = 2025

# Project root = one level up from this file
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FTC_API_BASE = "https://ftc-api.firstinspires.org/v2.0"
FTC_API_USER = os.environ.get("FTC_API_USER", "skipinator")
FTC_API_KEY = os.environ.get("FTC_API_KEY", "")

TOA_API_BASE = "https://theorangealliance.org/api"
TOA_API_KEY = os.environ.get("TOA_API_KEY", "")

DB_PATH = os.environ.get("DB_PATH", os.path.join(_ROOT, "pipeline", "data", "ftc.db"))
EXPORT_PATH = os.environ.get("EXPORT_PATH", os.path.join(_ROOT, "frontend", "public", "data"))

# EPA model constants (mirrors statbotics)
ELIM_WEIGHT = 1 / 3          # playoff matches count as 1/3
MEAN_REVERSION = 0.4         # cross-event regression toward mean
MIN_K = 0.2                  # floor on learning rate (after 12+ qual matches)
MAX_K = 0.5                  # ceiling on learning rate (early matches)

# Endgame point values
HANG_POINTS = {"FULL": 10, "PARTIAL": 5, "NONE": 0}

# Rate limiting: FIRST API allows ~10 req/sec; we stay conservative
REQUEST_DELAY = 0.25         # seconds between requests
