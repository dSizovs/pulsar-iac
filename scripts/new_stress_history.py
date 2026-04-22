"""
Create a fresh Galaxy history for stress testing, and copy the input dataset
into it. Prints the new history_id and the new dataset_id — paste these into
submit_jobs.py and monitor_jobs.py for the next run.
"""
import argparse
import sys
from datetime import datetime, timezone

import requests

GALAXY_URL = "http://localhost:8080"
API_KEY = "158f39b893d924af6af674b6ce7b3efb"
SOURCE_HISTORY = "e85a3be143d5905b"
SOURCE_DATASET = "799c5dfe07c28b95"

HEADERS = {"x-api-key": API_KEY, "Content-Type": "application/json"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default=None,
                    help="History name (default: stress-test-<utc-timestamp>)")
    args = ap.parse_args()

    name = args.name or f"stress-test-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

    r = requests.post(f"{GALAXY_URL}/api/histories",
                      headers=HEADERS, json={"name": name}, timeout=10)
    r.raise_for_status()
    new_history_id = r.json()["id"]
    print(f"[+] created history: {name}  id={new_history_id}")

    r = requests.post(
        f"{GALAXY_URL}/api/histories/{new_history_id}/contents",
        headers=HEADERS,
        json={
            "source": "hda",
            "content": SOURCE_DATASET,
            "type": "dataset",
        },
        timeout=30,
    )
    r.raise_for_status()
    new_dataset_id = r.json()["id"]
    print(f"[+] copied dataset {SOURCE_DATASET} -> {new_dataset_id}")

    print()
    print("Update submit_jobs.py and monitor_jobs.py with:")
    print(f"  HISTORY_ID       = \"{new_history_id}\"")
    print(f"  INPUT_DATASET_ID = \"{new_dataset_id}\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
