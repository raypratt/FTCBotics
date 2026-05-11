"""Entry point: ingest then export."""
import sys
import os

# Ensure imports resolve from the pipeline directory
sys.path.insert(0, os.path.dirname(__file__))

from ingest import run
from export import export_all

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", help="Limit ingest to one event code")
    parser.add_argument("--export-only", action="store_true")
    args = parser.parse_args()

    if not args.export_only:
        run(event_filter=args.event)

    export_all()
